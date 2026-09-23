# DataRobot ROS2 机器人项目

基于 ROS2 Jazzy 的完整差速驱动机器人系统，集成激光雷达。

## 快速开始

### 在机器人板子上运行（Ubuntu 22.04 + ROS2 Jazzy）

```bash
cd ~/chapt_ws
source /opt/ros/jazzy/setup.bash
source install/setup.bash

# 启动完整系统（底盘 + 雷达 + URDF）
ros2 launch datarobot_base bringup_with_lidar.launch.py \
  use_rviz:=false \
  serial_port:=/dev/ttyUSB1 \
  lidar_port:=/dev/ttyUSB0
```

### 测试机器人

```bash
# 前进
ros2 topic pub /cmd_vel geometry_msgs/msg/Twist \
  "{linear: {x: 0.2}, angular: {z: 0.0}}"

# 旋转
ros2 topic pub /cmd_vel geometry_msgs/msg/Twist \
  "{linear: {x: 0.0}, angular: {z: 0.5}}"

# 检查话题
ros2 topic list
ros2 topic hz /scan
ros2 topic echo /odom --once
```

## 项目进度

✅ **阶段 1：硬件集成 - 已完成**
- 底盘控制器（Modbus RTU，只写模式）
- 激光雷达（Bluesea2，1M 波特率）
- URDF 模型和 TF 树
- 所有话题正常发布

⏳ **阶段 2：标定 - 下一步**
- 需要标定齿轮比
- 里程计调优

📋 **阶段 3：建图 - 待办**
- SLAM 配置
- 地图构建

📋 **阶段 4：导航 - 待办**
- Nav2 配置
- 自主导航

## 文档说明

- **[项目背景.md](项目背景.md)** - 硬件规格、软件架构、已知问题
- **[项目结构说明.md](项目结构说明.md)** - 目录结构、文件说明、调试技巧
- **[开发路线图.md](开发路线图.md)** - 开发规划和未来功能

## 项目统计

- **源代码**：约 6,900 行（Python + C++）
- **配置文件**：12 个
- **文档**：7 个 markdown 文件
- **ROS2 功能包**：3 个（datarobot_base、datarobot_description、bluesea2）

## 硬件配置

```
/dev/ttyUSB0 -> Bluesea2 激光雷达（1000000 波特率）
/dev/ttyUSB1 -> DataRobot 底盘（115200 波特率）
```

## ROS2 话题

```
发布话题：
  /scan         (10 Hz)  - 激光扫描数据
  /odom         (40 Hz)  - 里程计
  /tf           (52 Hz)  - 坐标变换
  /tf_static           - 静态坐标变换
  /joint_states        - 车轮位置
  /robot_description   - URDF 模型

订阅话题：
  /cmd_vel             - 速度控制指令
```

## 系统要求

- Ubuntu 22.04 LTS
- ROS2 Jazzy Jalisco
- Python 3.10+
- 硬件：DataRobot 底盘 + Bluesea2 激光雷达

## 从源码编译

```bash
# 安装依赖
sudo apt update
sudo apt install ros-jazzy-desktop python3-colcon-common-extensions
sudo apt install python3-serial python3-pymodbus

# 构建
source /opt/ros/jazzy/setup.bash
colcon build

# 加载工作空间
source install/setup.bash
```

## 故障排查

详见 [项目结构说明.md](项目结构说明.md) 中的常见问题和解决方案。

## 最后更新

2026年9月16日 - 阶段 1 硬件集成完成
