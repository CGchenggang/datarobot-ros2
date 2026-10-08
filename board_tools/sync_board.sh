#!/usr/bin/env bash
# 把桌面 xuniceshi_ws 同步到板子（默认预演，传 --go 才真改）
set -u

SRC=/mnt/c/Users/yinbaofeng/Desktop/xuniceshi_ws/
DST=admin@192.168.222.132:/home/admin/xuniceshi_ws/
export SSHPASS=12345678

SSH_OPTS="-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null"
RSYNC_OPTS=(-a --delete --exclude 'build/' --exclude 'install/' --exclude 'log/' --exclude '.git/'
            --exclude '__pycache__/'
            -e "sshpass -e ssh $SSH_OPTS")

if [ "${1:-}" = "--go" ]; then
  echo "===== 实际执行同步 ====="
  rsync "${RSYNC_OPTS[@]}" "$SRC" "$DST"
  echo "exit=$?"
else
  echo "===== 预演（不会改动板子）====="
  rsync -n --itemize-changes "${RSYNC_OPTS[@]}" "$SRC" "$DST"
  echo
  echo "===== 统计 ====="
  rsync -n --itemize-changes "${RSYNC_OPTS[@]}" "$SRC" "$DST" 2>/dev/null \
    | awk '{c[substr($0,1,2)]++} END {for (k in c) printf "%s : %d\n", k, c[k]}' | sort
fi
