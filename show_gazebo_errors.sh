#!/bin/bash
echo "查看最近的 Gazebo 日志错误..."
echo "=========================================="
# 查找包含 error, warning, sensor 的日志行
journalctl --user -u "*gazebo*" --since "5 minutes ago" 2>/dev/null | grep -i "error\|warn\|sensor" | tail -30
echo ""
echo "如果上面没有输出,请在运行 Gazebo 的终端查找包含以下关键词的信息:"
echo "  - error"
echo "  - warning" 
echo "  - sensor"
echo "  - gpu_lidar"
echo "  - failed"
echo "=========================================="
