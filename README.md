# DataRobot ROS2 机器人

基于 **ROS 2 Jazzy** 的差速驱动机器人，集成 BlueSea 激光雷达。
同一套代码同时支持 **Gazebo 仿真** 和 **实机** 两种运行方式。

---

## 当前状态

| 阶段 | 状态 |
|---|---|
| 硬件集成（底盘 Modbus 驱动 + 雷达驱动 + URDF/TF） | ✅ 已完成，连机验证通信正常 |
| Gazebo 仿真：SLAM 建图 | ✅ 已完成（地图已知区域 96.3%） |
| Gazebo 仿真：Nav2 导航 | ✅ 已完成（直线到达误差 5.6 cm，能绕障、能干净失败） |
| 实机标定（齿轮比 / 轮距） | ⏳ **卡在供电问题**，未开始 |
| 实机建图 / 导航 | ⏳ 待标定完成 |

> **下一步**：解决供电 → 按《实机接入指南》做标定 → 落地建图。

---

## 快速开始

```bash
cd ~/xuniceshi_ws
source /opt/ros/jazzy/setup.bash
source install/setup.bash
```

### 仿真

```bash
# 终端 1：Gazebo + RViz + 机器人 + 桥接
ros2 launch datarobot_base gazebo_jazzy_sim.launch.py

# 终端 2（建图）：SLAM
ros2 launch datarobot_base slam_sim.launch.py
# 终端 2（导航）：地图 + AMCL + Nav2
ros2 launch datarobot_base nav_sim.launch.py
```

⚠️ `slam_toolbox` 与 `amcl` 不能同时跑（都发布 `map→odom`）；
`teleop` 与 Nav2 不能同时跑（都抢 `/cmd_vel`）。

### 实机

```bash
# 底盘 + 雷达（串口默认走 udev 固定名，见下）
ros2 launch datarobot_base bringup_with_lidar.launch.py

# 只调雷达 / 只调底盘
ros2 launch datarobot_base bringup_with_lidar.launch.py base:=false
ros2 launch datarobot_base bringup_with_lidar.launch.py lidar:=false rviz:=false

# 建图 / 导航
ros2 launch datarobot_base slam.launch.py
ros2 launch datarobot_base navigation.launch.py map_file:=/home/admin/maps/my_map.yaml
```

> ⚠️ 参数名是 **`rviz`**，不是 `use_rviz`。
> ⚠️ 首次上电务必把驱动轮**架空**，详见《实机接入指南》的安全须知。

### 测试底盘

```bash
ros2 topic pub -r 10 /cmd_vel geometry_msgs/msg/Twist "{linear: {x: 0.2}}"
ros2 topic pub -r 10 /cmd_vel geometry_msgs/msg/Twist "{angular: {z: 0.5}}"
```

---

## 硬件速查

| 项目 | 值 |
|---|---|
| 底盘接口 | Modbus RTU over RS485，115200 bps，8N1，从站 0x01 |
| 底盘串口 | `/dev/datarobot_base`（udev 固定名） |
| 雷达型号 | BlueSea LDS，UART 接口 |
| 雷达串口 | `/dev/LHLiDAR`（udev 固定名），**波特率 1000000**，10 Hz，0.1–50 m |
| 轮半径 / 轮距 | 0.083 m（待卡尺复核）/ **0.358 m** ✅ 已实测确认 |
| 齿轮比 | **1.0，未标定** |
| 最大转速 | 3000 RPM |
| 控制频率 | 20 Hz（115200 bps 下稳定；50 Hz 会丢应答） |
| 坐标帧 | `odom` → `base_footprint` → `base_link` → `laser_link` |

⚠️ 串口**必须**用 udev 固定名，不要用 `/dev/ttyUSB*` ——
底盘和雷达按插入顺序抢号，且**抢的时候不报错，只静默失灵**。
规则文件：`src/datarobot_base/config/udev/99-datarobot.rules`（含安装步骤）。

---

## ROS 2 话题

| 话题 | 方向 | 说明 |
|---|---|---|
| `/cmd_vel` | 订阅 | 速度指令（`geometry_msgs/msg/Twist`） |
| `/scan` | 发布 | 激光扫描（10 Hz） |
| `/odom` | 发布 | 里程计（20 Hz） |
| `/tf`、`/tf_static` | 发布 | 坐标变换 |
| `/joint_states` | 发布 | 车轮关节位置 |
| `/robot_description` | 发布 | URDF 模型 |

---

## 文档

| 文档 | 内容 |
|---|---|
| **[实机接入指南.md](实机接入指南.md)** | ⭐ 从仿真过渡到真机的完整流程：udev 串口、接线复核、标定、建图、安全须知、供电排查 |
| **[技术手册.md](技术手册.md)** | 硬件规格、Modbus 寄存器映射与实测帧、电机符号约定、时序约束、串口转发 |
| **[操作指南.md](操作指南.md)** | 日常操作命令、仿真与实机的建图/导航步骤、完整排查手册 |
| **[项目结构说明.md](项目结构说明.md)** | 目录结构、每个文件的作用、快速定位表、TF 树 |
| **[任务完成总结.md](任务完成总结.md)** | 仿真阶段的成果与踩坑记录（DDS 共享内存退化、TF 问题、Nav2 配置等） |

---

## 目录结构

```
xuniceshi_ws/
├── src/
│   ├── datarobot_base/          底盘驱动、雷达集成、所有 launch
│   │   ├── datarobot_base/      modbus_controller.py（RS485 驱动）
│   │   │                        diff_drive_controller.py（运动学与里程计）
│   │   ├── scripts/             base_driver_node.py（ROS2 节点入口）
│   │   ├── launch/              仿真 + 实机的全部启动文件
│   │   ├── config/              底盘/雷达/SLAM/Nav2 参数 + udev 规则
│   │   └── ...
│   ├── datarobot_description/   URDF 模型
│   │   └── urdf/databot/datarobot.urdf.xacro   ← 使用这个
│   ├── bluesea2/                激光雷达厂商驱动（含 SDK）
│   └── base/                    早期练习件（雷达服务定义），当前未使用
├── 实机接入指南.md  技术手册.md  操作指南.md
├── 项目结构说明.md  任务完成总结.md  README.md
└── build/  install/  log/       colcon 产物（已 gitignore）
```

⚠️ **URDF 只能用一个**：`urdf/databot/datarobot.urdf.xacro`。
同目录下的 `urdf/datarobot.urdf` 和 `urdf/datarobot.xacro` 是早期单 link 练习件，
**没有轮子也没有 `base_footprint`**，用了会出怪问题。

---

## 从源码编译

```bash
cd ~/xuniceshi_ws
source /opt/ros/jazzy/setup.bash

# 依赖
sudo apt install ros-jazzy-desktop python3-colcon-common-extensions
sudo apt install python3-serial python3-pymodbus

# 编译
colcon build
source install/setup.bash
```

改了 `config/*.yaml` 或 `launch/*.py` 后需要重新 `colcon build` 才会生效
（config 和 launch 是随包安装的）。

---

## 系统要求

- ROS 2 Jazzy（官方对应 Ubuntu 24.04）
- Python 3.10+
- 硬件：DataRobot 底盘 + BlueSea 激光雷达

> WSL2 里跑需要先用 `usbipd` 转发 USB 串口，见《技术手册》。
