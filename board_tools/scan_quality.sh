#!/usr/bin/env bash
# Step 1: 重测雷达点云质量（在板子上运行；只上雷达，不碰电机）
# 上一轮"点云大多无效"的结论是被 head 截断导致的误判，这里抓**完整一帧**再统计。

source /opt/ros/jazzy/setup.bash
source /home/admin/xuniceshi_ws/install/setup.bash

LOG=/tmp/scan_q.log
: > "$LOG"
setsid ros2 launch datarobot_base bringup_with_lidar.launch.py \
    base:=false lidar:=true rviz:=false >"$LOG" 2>&1 &
sleep 12

echo "=== 抓取完整一帧 /scan ==="
rm -f /tmp/scan.txt
timeout 15 ros2 topic echo /scan --once > /tmp/scan.txt 2>&1
echo "抓到 $(wc -l < /tmp/scan.txt) 行"

echo
echo "=== 统计 ==="
python3 /tmp/scan.txt <<'PY'
import sys, math
lines = open(sys.argv[1], encoding='utf-8', errors='replace').read().splitlines()
vals, inr = [], False
for ln in lines:
    s = ln.strip()
    if s == 'ranges:':
        inr = True
        continue
    if inr:
        if s.startswith('- '):
            t = s[2:].strip()
            try:
                vals.append(float('inf') if 'inf' in t else float(t))
            except ValueError:
                pass
        elif s:
            break

if not vals:
    print("!! 没解析到 ranges，原始输出前 20 行：")
    print('\n'.join(lines[:20]))
    sys.exit()

finite = [v for v in vals if math.isfinite(v) and v > 0]
print("总点数          : %d" % len(vals))
print("有效点(有限且>0): %d  (%.1f%%)" % (len(finite), 100.0 * len(finite) / len(vals)))
print("inf/无效点数    : %d" % (len(vals) - len(finite)))

if finite:
    fs = sorted(finite)
    print("距离范围        : %.3f m ~ %.3f m" % (fs[0], fs[-1]))
    for p in (10, 25, 50, 75, 90):
        print("  %2d%% 分位      : %.3f m" % (p, fs[min(len(fs) - 1, len(fs) * p // 100)]))

n = len(vals)
print("\n各扇区有效点数（每 45 度一档）:")
for k in range(8):
    a, b = n * k // 8, n * (k + 1) // 8
    seg = [v for v in vals[a:b] if math.isfinite(v) and v > 0]
    print("  %5d°~%5d° : %4d / %4d" % (-180 + 45 * k, -180 + 45 * (k + 1), len(seg), b - a))
PY

echo
echo "=== 清理 ==="
pkill -INT -f "bringup_with_lidar.launch.py" 2>/dev/null
sleep 1
pkill -f bluesea2_node 2>/dev/null
pkill -f robot_state_publisher 2>/dev/null
sleep 1
echo "已清理"

echo
echo "=== 雷达日志异常行 ==="
grep -iE "error|fail|unknown" "$LOG" | head -8
echo "(无输出=没有异常)"
