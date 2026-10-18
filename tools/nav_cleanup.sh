#!/bin/bash
# 彻底清扫 ROS/仿真进程：按可执行体名逐个杀（ros2 launch 被杀时子进程会孤儿化，
# 不杀本体就会留下多代 map_server/amcl 互相打架——本仓库踩过的最大坑）
pkill -f 'gz sim' 2>/dev/null
pkill -f 'ruby.*gz' 2>/dev/null
pkill -f 'parameter_bridge' 2>/dev/null
pkill -f 'robot_state_publisher' 2>/dev/null
pkill -f 'ultrasonic_node' 2>/dev/null
pkill -f 'waypoint_driver' 2>/dev/null
pkill -f 'slam_toolbox' 2>/dev/null
pkill -f 'map_server' 2>/dev/null
pkill -f 'amcl' 2>/dev/null
pkill -f 'controller_server' 2>/dev/null
pkill -f 'planner_server' 2>/dev/null
pkill -f 'bt_navigator' 2>/dev/null
pkill -f 'lifecycle_manager' 2>/dev/null
pkill -f 'behavior_server' 2>/dev/null
pkill -f 'smoother_server' 2>/dev/null
pkill -f 'velocity_smoother' 2>/dev/null
pkill -f 'collision_monitor' 2>/dev/null
pkill -f 'docking_server' 2>/dev/null
pkill -f 'route_server' 2>/dev/null
pkill -f 'waypoint_follower' 2>/dev/null
pkill -f 'behavior_tree_nav2_bringup' 2>/dev/null
pkill -f 'ros2 launch' 2>/dev/null
pkill -f 'ros2 run' 2>/dev/null
pkill -f 'ros2 topic' 2>/dev/null
pkill -f 'ros2 action' 2>/dev/null
sleep 2
rm -f /dev/shm/fastrtps_* /dev/shm/fast_datasharing* 2>/dev/null
sleep 1
echo "CLEAN; remaining:"
pgrep -af 'map_server|amcl|navigator|controller_server|planner_server|gz sim|parameter_bridge' | wc -l
