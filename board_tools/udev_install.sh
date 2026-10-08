#!/usr/bin/env bash
# 在板子上安装 DataRobot udev 固定名规则，并停用厂商的只按 VID/PID 的规则
# 这个脚本是**在板子上运行**的（通过 ssh 'bash -s' 管道送入）
set -u

PW='12345678'
S() { echo "$PW" | sudo -S "$@" 2>/dev/null; }

cd ~/xuniceshi_ws || exit 1

echo "=== 1. 安装规则文件 ==="
S cp src/datarobot_base/config/udev/99-datarobot.rules /etc/udev/rules.d/
echo "cp exit=$?"

echo
echo "=== 2. 停用厂商规则（它会同时命中底盘适配器）==="
if [ -f /etc/udev/rules.d/99-bluesea-lidar.rules ]; then
  S mv /etc/udev/rules.d/99-bluesea-lidar.rules /etc/udev/rules.d/99-bluesea-lidar.rules.disabled
  echo "已停用 -> .disabled"
else
  echo "（已不存在，跳过）"
fi

echo
echo "=== 3. 重新加载规则 ==="
S udevadm control --reload-rules
S udevadm trigger
sleep 3

echo
echo "=== 4. /etc/udev/rules.d/ 现状 ==="
ls -1 /etc/udev/rules.d/ | grep -iE 'datarobot|bluesea' || echo "(无匹配)"

echo
echo "=== 5. 符号链接是否生成 ==="
ls -l /dev/datarobot_base /dev/LHLiDAR 2>&1

echo
echo "=== 6. 指向校验（期望 datarobot_base->ttyUSB0, LHLiDAR->ttyUSB1）==="
for n in datarobot_base LHLiDAR; do
  if [ -L "/dev/$n" ]; then
    echo "$n -> $(readlink -f /dev/$n)"
  else
    echo "$n -> 不存在"
  fi
done
