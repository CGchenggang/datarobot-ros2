#!/usr/bin/env bash
# 在板子上重新编译工作区（这个脚本是**在板子上运行**的）
# 注意：不要用 set -u，会破坏 ROS 的 setup.bash

source /opt/ros/jazzy/setup.bash
cd ~/xuniceshi_ws || exit 1

echo "=== ROS 环境 ==="
echo "ROS_DISTRO=$ROS_DISTRO"

echo
echo "=== 开始编译（全量，4 个包）==="
colcon build 2>&1 | tail -25

echo
echo "=== 编译结果 ==="
if [ -f install/setup.bash ]; then
  echo "install/setup.bash 存在"
fi
echo
echo "=== 确认新代码已进 install（应能找到 read_actual_speed）==="
grep -c read_actual_speed install/datarobot_base/lib/datarobot_base/base_driver_node.py 2>/dev/null \
  || grep -rc read_actual_speed install/datarobot_base/ 2>/dev/null | grep -v ':0' | head -3

echo
echo "=== 确认 udev 规则随包安装 ==="
ls -l install/datarobot_base/share/datarobot_base/config/udev/ 2>&1 | tail -3
