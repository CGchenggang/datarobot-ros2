#!/bin/bash
echo "=========================================="
echo "激光雷达诊断脚本"
echo "=========================================="
echo ""

# 等待 Gazebo 完全启动
echo "等待 5 秒让 Gazebo 完全启动..."
sleep 5

echo "1. 检查 Gazebo 话题列表:"
gz topic -l | grep scan
echo ""

echo "2. 检查 Gazebo 传感器列表:"
gz sensor -l
echo ""

echo "3. 检查 ROS 2 话题列表:"
ros2 topic list | grep scan
echo ""

echo "4. 检查 /scan 话题信息:"
ros2 topic info /scan
echo ""

echo "5. 尝试读取 Gazebo 内部激光雷达数据 (5秒超时):"
timeout 5 gz topic -e -t /scan || echo "没有数据输出"
echo ""

echo "6. 尝试读取 ROS 2 激光雷达数据 (5秒超时):"
timeout 5 ros2 topic echo /scan --once || echo "没有数据输出"
echo ""

echo "7. 检查 /scan 话题频率:"
timeout 3 ros2 topic hz /scan || echo "没有频率数据"
echo ""

echo "=========================================="
echo "诊断完成"
echo "=========================================="
