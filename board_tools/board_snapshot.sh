#!/usr/bin/env bash
# 在板子上：打快照 + 打 git 检查点（这个脚本是**在板子上运行**的）
# 之后任何改动都能用 git checkout / git reset 或解压快照回退。

TS=$(date +%Y%m%d_%H%M%S)
SNAP=~/ws_snapshots
mkdir -p "$SNAP"

echo "=== 1. 工作区快照（不含 build/install/log/.git）==="
tar czf "$SNAP/ws_$TS.tar.gz" \
    --exclude=./build --exclude=./install --exclude=./log --exclude=./.git \
    -C ~ xuniceshi_ws 2>/dev/null
echo "exit=$?  ->  $SNAP/ws_$TS.tar.gz"

echo
echo "=== 2. udev 规则快照 ==="
echo 12345678 | sudo -S tar czf "$SNAP/udev_$TS.tar.gz" -C /etc udev/rules.d 2>/dev/null
echo "exit=$?  ->  $SNAP/udev_$TS.tar.gz"

echo
echo "=== 3. git 检查点 ==="
cd ~/xuniceshi_ws || exit 1
echo "提交前 HEAD: $(git rev-parse --short HEAD)"
git add -A
git -c user.name='debug' -c user.email='debug@local' commit -q \
    -m "检查点: 桌面工作区已同步 + udev 固定名（实机调试起点）" 2>&1 | tail -3
echo "提交后 HEAD: $(git rev-parse --short HEAD)"

echo
echo "=== 4. 快照清单 ==="
ls -lh "$SNAP" | tail -6

echo
echo "=== 5. 回退提示 ==="
CKPT=$(git rev-parse --short HEAD)
echo "本轮检查点 SHA : $CKPT   （此后任意改动可用 git checkout -- <file> 或 git reset --hard $CKPT 回退）"
echo "彻底回到同步前  : cd ~/xuniceshi_ws && git reset --hard 80a21a4 && git clean -fd"
echo "整包还原        : tar xzf $SNAP/ws_$TS.tar.gz -C ~"
