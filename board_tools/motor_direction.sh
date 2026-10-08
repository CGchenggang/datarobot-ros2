#!/usr/bin/env bash
# Step 2b: 放慢、拉长的转向确认测试（在板子上运行）
# 动作：前进5s → 停2s → 前进5s → 停2s → 左转5s
# ⚠️ 会真的驱动轮子（需已架空）

source /opt/ros/jazzy/setup.bash
source /home/admin/xuniceshi_ws/install/setup.bash

cat > /tmp/dir_test.py <<'PY'
import math
import threading
import time
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry


class T(Node):
    def __init__(self):
        super().__init__('dir_test')
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

    def drive(self, lin, ang, secs, label):
        print("\n>>> %s   (%.1f 秒) <<<" % (label, secs), flush=True)
        t0 = time.time()
        while time.time() - t0 < secs:
            m = Twist()
            m.linear.x = float(lin)
            m.angular.z = float(ang)
            self.pub.publish(m)
            time.sleep(0.05)
        for _ in range(10):
            self.pub.publish(Twist())
            time.sleep(0.05)
        print("    —— 停 ——", flush=True)


rclpy.init()
n = T()
threading.Thread(target=rclpy.spin, args=(n,), daemon=True).start()

t0 = time.time()
while n.odom is None and time.time() - t0 < 8:
    time.sleep(0.1)
if n.odom is None:
    print("!! 没收到 /odom")
    raise SystemExit(1)

p0 = n.pose()
print("起点 x=%.4f y=%.4f yaw=%.4f" % p0, flush=True)

n.drive(0.25, 0.0, 5.0, "① 前进 —— 两个轮子都该往前转")
p1 = n.pose()
time.sleep(2.0)
n.drive(0.25, 0.0, 5.0, "② 再前进一遍 —— 确认轮子方向")
p2 = n.pose()
time.sleep(2.0)
n.drive(0.0, 0.6, 5.0, "③ 原地左转 —— 左轮慢/倒转，右轮快/正转")
p3 = n.pose()

print("\n" + "=" * 50)
print("Δx(①+② 前进)  : %.4f m" % (p2[0] - p0[0]))
print("Δyaw(③ 左转)   : %.4f rad" % (p3[2] - p2[2]))
print("=" * 50)
print("（这些只证明计算链路；轮子实际方向请看刚才的肉眼观察）")

n.destroy_node()
rclpy.shutdown()
PY

LOG=/tmp/dir_test.log
: > "$LOG"
setsid ros2 launch datarobot_base bringup_with_lidar.launch.py \
    base:=true lidar:=false rviz:=false >"$LOG" 2>&1 &
echo "启动中，12 秒后开始动…"
sleep 12

grep -nE "Motors enabled|里程计转速来源" "$LOG" | head -3
echo
timeout 60 python3 /tmp/dir_test.py 2>&1

echo
echo "=== 清理 ==="
pkill -INT -f "bringup_with_lidar.launch.py" 2>/dev/null
sleep 1
pkill -f base_driver_node 2>/dev/null
pkill -f robot_state_publisher 2>/dev/null
sleep 2
echo "已清理"
