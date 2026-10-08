#!/usr/bin/env bash
# 第 1 步：只上雷达，验证 /scan（这个脚本是**在板子上运行**的）
# 不启动底盘驱动，不涉及电机，安全。

source /opt/ros/jazzy/setup.bash
source /home/admin/xuniceshi_ws/install/setup.bash
cd /home/admin/xuniceshi_ws || exit 1

LOG=/tmp/lidar_test.log
: > "$LOG"

echo "=== 启动：只上雷达（base:=false lidar:=true rviz:=false）==="
setsid ros2 launch datarobot_base bringup_with_lidar.launch.py \
    base:=false lidar:=true rviz:=false >"$LOG" 2>&1 &
sleep 12

echo
echo "=== 话题列表 ==="
ros2 topic list 2>&1 | sort

echo
echo "=== /scan 发布频率（期望 10 Hz）==="
timeout 7 ros2 topic hz /scan 2>&1 | head -6

echo
echo "=== /scan 首帧内容（前 25 行）==="
timeout 8 ros2 topic echo /scan --once 2>&1 | head -25

echo
echo "=== 清理进程 ==="
pkill -INT -f "bringup_with_lidar.launch.py" 2>/dev/null
sleep 1
pkill -f "bluesea2_node" 2>/dev/null
pkill -f "robot_state_publisher" 2>/dev/null
sleep 2
echo "已清理"

echo
echo "=== 启动日志（尾部 30 行）==="
tail -30 "$LOG"
