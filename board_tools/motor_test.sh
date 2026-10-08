#!/usr/bin/env bash
# Step 2: 架空电机测试（在板子上运行）
# 检查：Motors enabled / 转向 / 里程计是否累积
# ⚠️ 会真的驱动轮子（需已架空）

source /opt/ros/jazzy/setup.bash
source /home/admin/xuniceshi_ws/install/setup.bash

cat > /tmp/motor_test.py <<'PY'
import math
import threading
import time
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry


class T(Node):
    def __init__(self):
        super().__init__('motor_test')
        self.pub = self.create_publisher(Twist, '/cmd_vel', 10)
        self.odom = None
        self.create_subscription(Odometry, '/odom', self.cb, 10)

    def cb(self, m):
        self.odom = m

    def pose(self):
        if self.odom is None:
            return None
        p = self.odom.pose.pose
        q = p.orientation
        yaw = math.atan2(2.0 * (q.w * q.z + q.x * q.y),
                         1.0 - 2.0 * (q.y * q.y + q.z * q.z))
        return (p.position.x, p.position.y, yaw)

    def drive(self, lin, ang, secs):
        t0 = time.time()
        while time.time() - t0 < secs:
            m = Twist()
            m.linear.x = float(lin)
            m.angular.z = float(ang)
            self.pub.publish(m)
            time.sleep(0.1)
        for _ in range(6):
            self.pub.publish(Twist())
            time.sleep(0.05)

    def wait_odom(self, timeout=8.0):
        t0 = time.time()
        while self.odom is None and time.time() - t0 < timeout:
            time.sleep(0.1)
        return self.odom is not None


rclpy.init()
n = T()
threading.Thread(target=rclpy.spin, args=(n,), daemon=True).start()

if not n.wait_odom():
    print("!! 8 秒内没收到 /odom —— 底盘驱动没起来？")
    raise SystemExit(1)

p0 = n.pose()
print("起点   x=%.4f y=%.4f yaw=%.4f" % p0)

print("\n>>> 前进 linear.x=0.2 m/s 持续 3 秒 —— 请看轮子是否都往前转 <<<")
n.drive(0.2, 0.0, 3.0)
p1 = n.pose()
print("前进后 x=%.4f y=%.4f yaw=%.4f" % p1)

time.sleep(1.0)

print("\n>>> 原地左转 angular.z=+0.5 rad/s 持续 3 秒 —— 左轮应慢/倒转，右轮应快/正转 <<<")
n.drive(0.0, 0.5, 3.0)
p2 = n.pose()
print("转向后 x=%.4f y=%.4f yaw=%.4f" % p2)

print("\n" + "=" * 50)
print("结果")
print("=" * 50)
dx = p1[0] - p0[0]
print("前进位移 Δx       : %.4f m   (指令 0.2 m/s × 3 s，期望 ≈ 0.60 m)" % dx)
print("前进位移 Δy       : %.4f m   (前进时 y 应基本不变)" % (p1[1] - p0[1]))
print("前进航向变化 Δyaw : %.4f rad (前进时 yaw 应基本不变)" % (p1[2] - p0[2]))
dyaw = p2[2] - p1[2]
print("转向航向变化 Δyaw : %.4f rad (指令 0.5 rad/s × 3 s，期望 ≈ 1.50 rad)" % dyaw)

print("\n判读：")
print(" - Δx 明显 > 0  → 里程计在累积（旧版 bug 会恒为 0），修复生效")
print(" - Δyaw ≈ 1.5   → 角速度换算正常")
print(" - 注意：默认 read_actual_speed=false，里程计用**指令转速**开环推算，")
print("         所以 Δx 增长**不能证明轮子真的转了** —— 轮子方向要靠肉眼确认。")

n.destroy_node()
rclpy.shutdown()
PY

LOG=/tmp/motor_test.log
: > "$LOG"
echo "=== 启动：只上底盘（base:=true lidar:=false rviz:=false）==="
setsid ros2 launch datarobot_base bringup_with_lidar.launch.py \
    base:=true lidar:=false rviz:=false >"$LOG" 2>&1 &
sleep 12

echo
echo "=== 启动日志关键行 ==="
grep -nE "Motors enabled|里程计转速来源|Write-only|Serial|串口|ERROR|Error|Traceback" "$LOG" | head -15

echo
echo "=== 运行电机测试 ==="
timeout 40 python3 /tmp/motor_test.py 2>&1

echo
echo "=== 清理 ==="
pkill -INT -f "bringup_with_lidar.launch.py" 2>/dev/null
sleep 1
pkill -f base_driver_node 2>/dev/null
pkill -f robot_state_publisher 2>/dev/null
sleep 2
echo "已清理（节点退出时会自动 enable_motors(False)）"
