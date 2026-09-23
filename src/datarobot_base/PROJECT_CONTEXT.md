# DataRobot 项目上下文

达闼（CloudMinds）机器人逆向改造。差速底盘 + 森创 DS20270C 双轴伺服驱动器，
经 RS485 / Modbus RTU 控制。最终目标：Ubuntu 24.04 + ROS 2 Jazzy 上跑通建图与导航。

当前进度与后续路线见 [ROADMAP.md](ROADMAP.md)。

## 硬件

- **驱动器**: 森创 DS20270C（双轴伺服）
- **通信**: RS485, Modbus RTU, 115200bps, 8N1, 从站 ID 0x01
- **设备节点**: /dev/ttyUSB0

## 机器人参数

| 参数 | 值 | 状态 |
|---|---|---|
| 轮子半径 | 0.083 m | 已确认 |
| 轮距 | 0.358 m | 已确认 |
| 齿轮比 | 1.0 | **未实测**，见 ROADMAP 标定项 |
| 最大 RPM | 3000 | 未确认 |

轮子关节名: `left_wheel_joint`, `right_wheel_joint`（continuous）

## TF 树

```
odom → base_footprint → base_link → {left_wheel_link, right_wheel_link,
                                     laser_link, imu_link, camera_link}
```

`odom → base_footprint` 由 base_driver 发布，其余由 robot_state_publisher
按 URDF 发布。`base_footprint` 在 `base.urdf.xacro` 里定义，是模型的根，
位于地面投影处；`base_link` 高出它 0.253m（轮心高 0.17 + 轮半径 0.083）。

轮子几何在 `databot/datarobot.urdf.xacro` 顶部用 xacro property 统一定义，
base 与 wheel 宏共用 —— 改轮径时只需改那一处，否则模型会悬空或陷入地面。

模型文件有两套，**实机用 `urdf/databot/datarobot.urdf.xacro`**（7 个 link，
带轮子和 base_footprint）。同目录下的 `urdf/datarobot.urdf` 与
`urdf/datarobot.xacro` 是早期单 link 练习件，仅存参考，不要加载。

## 电机符号约定（关键）

右轮电机镜像安装，B 轴指令需取反。标准差速运动学输出的是 ROS 约定
（前进两轮同号），代码中由 `invert_right: true` 完成转换：

| 运动 | 运动学输出 | 发给驱动器 |
|---|---|---|
| 前进 | 左+ 右+ | A+ B− |
| 后退 | 左− 右− | A− B+ |
| 原地左转 | 左− 右+ | 两轮同负 |
| 原地右转 | 左+ 右− | 两轮同正 |

参数 `invert_left` / `invert_right` 可调，不要写死。里程计与 joint_states
都会撤销此翻转，回到 ROS 约定。

## Modbus 寄存器

| 寄存器 | 地址 | 用途 |
|---|---|---|
| F0.1.000 | 0x2100 | A 轴使能 |
| F1.1.000 | 0x3100 | B 轴使能 |
| F0.3.018 | 0x2318 | A 轴速度 (RPM) |
| F1.3.018 | 0x3318 | B 轴速度 (RPM) |
| D0.00 | 0x5000 | A 轴实际速度 |
| D1.00 | 0x5100 | B 轴实际速度 |

功能码: 0x03 读、0x06 写单、0x43 双读、0x44 双写。速度为 16 位有符号大端。
CRC-16 标准 Modbus，帧尾小端。

### 实测验证过的帧

```
使能双轴:   01 44 21 00 31 00 00 01 00 01 75 34
失能双轴:   01 44 21 00 31 00 00 00 00 00 E5 34
前进100rpm: 01 44 23 18 33 18 00 64 FF 9C DD 4A
后退100rpm: 01 44 23 18 33 18 FF 9C 00 64 2C DD
速度归零:   01 44 23 18 33 18 00 00 00 00 DD 0C
读双轴速度: 01 43 50 00 51 00 68 95
```

## 时序约束

控制循环每周期两次 Modbus 事务（写速度 + 读速度）。115200bps 下
`publish_rate` 20Hz 稳定；调高会出现应答丢失。`connect()` 后需等 200ms
让 RS485 适配器稳定，否则首帧（使能）会丢 —— `enable_motors()` 因此带 3 次重试。

## WSL2 串口

USB 设备默认不可见，需 usbipd-win 转发。每次重新插拔或重启后，在
**Windows PowerShell（管理员）** 执行：

```powershell
usbipd list                          # 找到 BUSID
usbipd bind --busid <BUSID>          # 首次绑定，只需一次
usbipd attach --wsl --busid <BUSID>  # 每次都要
```

WSL2 内确认: `ls -l /dev/ttyUSB*`，必要时 `sudo chmod 666 /dev/ttyUSB0`。

注意：VSCode 里如果终端是 Git Bash（`uname` 显示 MINGW64），无法运行 ROS 2 命令，
需切到 WSL 终端。

## 常用命令

```bash
cd ~/chapt6/chapt_ws
source /opt/ros/humble/setup.bash
colcon build --packages-select datarobot_base base bluesea2
source install/setup.bash

# 底盘驱动（阶段 0）
ros2 launch datarobot_base bringup.launch.py                     # 驱动 + 模型 + RViz
ros2 launch datarobot_base bringup.launch.py rviz:=false         # 不开 RViz
ros2 launch datarobot_base bringup.launch.py debug_modbus:=true  # 打印 TX/RX

# 完整系统：底盘 + 雷达（阶段 1）
ros2 launch datarobot_base bringup_with_lidar.launch.py          # 启动所有模块
ros2 launch datarobot_base bringup_with_lidar.launch.py base:=false    # 只测试雷达
ros2 launch datarobot_base bringup_with_lidar.launch.py lidar:=false   # 只测试底盘
ros2 launch datarobot_base bringup_with_lidar.launch.py rviz:=false    # 不开 RViz
ros2 launch datarobot_base bringup_with_lidar.launch.py lidar_port:=/dev/ttyUSB2  # 指定雷达串口

# 只看模型, 不需要硬件. 可用 GUI 拖动轮子关节
ros2 launch datarobot_description display.launch.py

# 持续发布速度。必须用 --rate，--once 会被 1 秒超时保护立刻归零
ros2 topic pub --rate 10 /cmd_vel geometry_msgs/msg/Twist "{linear: {x: 0.1}, angular: {z: 0.0}}"

# 查看雷达数据
ros2 topic hz /scan          # 检查雷达发布频率
ros2 topic echo /scan        # 查看雷达原始数据

# 纯软件验证符号约定，不需要硬件
python3 src/datarobot_base/datarobot_base/diff_drive_controller.py
```

启动日志必须出现 `Motors enabled`。失能状态下驱动器仍会正常应答写寄存器
（TX/RX 完全匹配），但电机不转 —— 不要被"通信正常"误导。

## 开发环境

- 当前: WSL2 Ubuntu 22.04 + ROS 2 Humble
- 目标: Ubuntu 24.04 + ROS 2 Jazzy
- 不使用 Humble 特有 API，保持两版本兼容

## 参考

- oomwoo-one (Jazzy): https://github.com/makerspet/oomwoo-one
