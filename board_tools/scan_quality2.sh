#!/usr/bin/env bash
# Step 1（重做）: 用 rclpy 直接订阅 /scan 取真实统计
# 避开 ros2 topic echo 对长数组的截断（它会把 ranges 截掉并打印 - '...'）
# 只上雷达，不碰电机。

source /opt/ros/jazzy/setup.bash
source /home/admin/xuniceshi_ws/install/setup.bash

cat > /tmp/scan_stats.py <<'PY'
import math
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import LaserScan

GOT = {'done': False}


class Stats(Node):
    def __init__(self):
        super().__init__('scan_stats')
        self.create_subscription(LaserScan, '/scan', self.cb, 10)

    def cb(self, m):
        if GOT['done']:
            return
        GOT['done'] = True
        r = list(m.ranges)
        n = len(r)
        finite = [v for v in r if math.isfinite(v) and v > 0]
        print("=" * 46)
        print("frame_id        : %s" % m.header.frame_id)
        print("总点数          : %d" % n)
        print("声明 range_min/max: %.3f / %.3f" % (m.range_min, m.range_max))
        print("有效点(有限且>0): %d  (%.1f%%)" % (len(finite), 100.0 * len(finite) / n if n else 0))
        print("无效(inf/nan)   : %d" % (n - len(finite)))
        if finite:
            fs = sorted(finite)
            print("距离 min/max    : %.3f / %.3f m" % (fs[0], fs[-1]))
            for p in (10, 25, 50, 75, 90, 99):
                print("   p%-3d          : %.3f m" % (p, fs[min(len(fs) - 1, len(fs) * p // 100)]))
        over = [v for v in r if math.isfinite(v) and v > m.range_max]
        print("超过 range_max  : %d 个" % len(over), end="")
        print("  (max=%.1f)" % max(over) if over else "")
        print("\n各扇区有效点数（每 45 度）:")
        for k in range(8):
            a, b = n * k // 8, n * (k + 1) // 8
            seg = [v for v in r[a:b] if math.isfinite(v) and v > 0]
            bar = '#' * min(40, len(seg) // 4)
            print("  %5d°~%5d° : %4d/%4d %s" % (-180 + 45 * k, -180 + 45 * (k + 1), len(seg), b - a, bar))
        print("=" * 46)
        raise SystemExit


rclpy.init()
node = Stats()
try:
    rclpy.spin(node)
except SystemExit:
    pass
finally:
    node.destroy_node()
    rclpy.shutdown()
PY

LOG=/tmp/scan_q2.log
: > "$LOG"
setsid ros2 launch datarobot_base bringup_with_lidar.launch.py \
    base:=false lidar:=true rviz:=false >"$LOG" 2>&1 &
sleep 12

echo "=== /scan 统计 ==="
timeout 20 python3 /tmp/scan_stats.py 2>&1

echo
echo "=== 清理 ==="
pkill -INT -f "bringup_with_lidar.launch.py" 2>/dev/null
sleep 1
pkill -f bluesea2_node 2>/dev/null
pkill -f robot_state_publisher 2>/dev/null
sleep 1
echo "已清理"
