# board_tools —— 实机调试脚本

这些脚本**不是双击运行的**。它们要在 **WSL 里**执行，通过 ssh 管道把脚本送到板子上跑。

## 统一调用方式

脚本都在 Windows 桌面的工作区里，WSL 里通过 `/mnt/c/...` 访问：

```bash
wsl -d Ubuntu-22.04 -- bash -lc 'bash /mnt/c/Users/yinbaofeng/Desktop/xuniceshi_ws/board_tools/<脚本名>.sh'
```

需要密码的（走 sshpass）脚本内部已带 `SSHPASS`。

## 脚本清单

| 脚本 | 作用 | 何时用 |
|---|---|---|
| `board_snapshot.sh` | 在板子上打 tar 快照 + 打 git 检查点 | **改动板子之前必跑**（可回退机制） |
| `sync_board.sh` | 桌面工作区 → 板子（rsync） | ⚠️ 见下方警告 |
| `build_board.sh` | 在板子上 `colcon build` | 改了 `config/*.yaml` 或 `launch/*.py` 后 |
| `udev_install.sh` | 装 udev 固定名规则、停用厂商规则 | 换机器 / 换 USB 插口后 |
| `test_lidar.sh` | 只上雷达，验证 `/scan` 有数据 | 排查雷达 |
| `scan_quality2.sh` | 抓**完整一帧** `/scan`，统计有效点/距离分布/扇区分布 | 判断雷达视野是否正常 |
| `motor_test.sh` | 架空电机测试（默认开环）：使能、前进、转向、里程计累积 | 验证电机与里程计 |
| `motor_test_actual.sh` | 同上，但用 `read_actual_speed:=true` 回读**真实转速** | 客观证明电机真的在转 |
| `motor_direction.sh` | 放慢拉长的转向确认（前进5s×2 + 左转5s） | 肉眼确认轮子转向 |
| `scan_quality.sh` | 雷达统计（第一版） | ❌ **已被 `scan_quality2.sh` 取代**，可删 |

## ⚠️ 关于 `sync_board.sh`

它内部用的是 **`rsync --delete`** —— 会删掉板子上多余的**未跟踪**文件，
且那些文件**无法用 git 还原**。2026-09-29 就这么一次删掉了 53 项。

**用它之前先跑 `board_snapshot.sh`**，或者改用 `--backup --backup-dir`。
（`bash sync_board.sh` 不带参数是**预演**，只列清单不改动板子。）

## 几个踩过的坑（写脚本时记住）

1. **别用 `set -u`** —— 会破坏 ROS 的 `setup.bash`（`AMENT_TRACE_SETUP_FILES: unbound variable`）。
2. **`ros2 topic echo` 会截断长数组**（`ranges` 只打印前一小段，末尾给个 `- '...'`）。
   要完整数据用 `--full-length`，或用 rclpy 直接订阅（`scan_quality2.sh` 就是这么做的）。
3. **`ros2 topic pub` 测底盘必须带 `-r 10`**（或 `--rate`）：`cmd_vel_timeout: 1.0` 会把
   `--once` 的指令立刻归零，看起来像"发了指令但不动"。
4. **rclpy 测试脚本收尾时别在 spin 线程还活着时调 `rclpy.shutdown()`** ——
   会 `terminate called without an active exception` + core dump（功能无影响，但很难看）。
5. 通过 MINGW(Git Bash) 嵌套调用 WSL 时，**shell 变量 `$VAR` 可能被吃掉**，
   脚本里尽量写字面路径。

## 相关文档

- **[git速查.md](git速查.md)** —— 常用 git 命令、回退决策表、危险命令、本项目的两个仓库说明
- 《实机接入指南》—— 从供电到建图的完整流程
- 《技术手册》—— 硬件规格、Modbus 帧、udev 实测结论
- 《操作指南》—— 日常操作命令与排查手册
- 《实机调试交接.md》—— 当前进度、回退点、待办（在上一级目录）
