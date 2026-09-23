# SLAM 建图和导航使用指南

本指南说明如何在**未标定齿轮比**的情况下进行 SLAM 建图和自主导航。

## 前置准备

### 1. 安装依赖包

在机器人板子上执行：

```bash
sudo apt update
sudo apt install -y ros-jazzy-slam-toolbox \
                    ros-jazzy-navigation2 \
                    ros-jazzy-nav2-bringup
```

### 2. 编译工作空间

```bash
cd ~/chapt_ws
source /opt/ros/jazzy/setup.bash
colcon build --packages-select datarobot_base
source install/setup.bash
```

## 第一步：SLAM 建图

### 1.1 启动建图系统

SSH 连接到机器人板子：

```bash
ssh admin@192.168.222.132
cd ~/chapt_ws
source /opt/ros/jazzy/setup.bash
source install/setup.bash

# 启动 SLAM 建图（根据实际串口设备调整）
ros2 launch datarobot_base slam.launch.py \
  serial_port:=/dev/ttyUSB1 \
  lidar_port:=/dev/ttyUSB0
```

**注意**：启动后检查串口设备号是否正确，可能需要用 `ls /dev/ttyUSB*` 确认。

### 1.2 在远程电脑查看建图过程

在同一网络的电脑上：

```bash
# 设置 ROS_DOMAIN_ID（与机器人一致）
export ROS_DOMAIN_ID=0

# 启动 RViz2
rviz2
```

在 RViz2 中添加以下显示：
- **Fixed Frame**: 设置为 `map`
- **Map** (话题: `/map`) - 显示正在构建的地图
- **LaserScan** (话题: `/scan`) - 显示激光扫描数据
- **TF** - 显示坐标变换树
- **RobotModel** - 显示机器人模型

### 1.3 控制机器人建图

在另一个终端控制机器人移动：

```bash
# 慢速前进（建议速度 < 0.3 m/s）
ros2 topic pub /cmd_vel geometry_msgs/msg/Twist \
  "{linear: {x: 0.2}, angular: {z: 0.0}}"

# 左转
ros2 topic pub /cmd_vel geometry_msgs/msg/Twist \
  "{linear: {x: 0.1}, angular: {z: 0.3}}"

# 右转
ros2 topic pub /cmd_vel geometry_msgs/msg/Twist \
  "{linear: {x: 0.1}, angular: {z: -0.3}}"

# 停止
ros2 topic pub /cmd_vel geometry_msgs/msg/Twist \
  "{linear: {x: 0.0}, angular: {z: 0.0}}"
```

**建图技巧**：
- 保持低速移动，避免快速转弯
- 尽量覆盖整个区域，包括房间的四个角
- 让机器人多次经过同一位置，帮助闭环检测
- 在 RViz 中观察地图质量

### 1.4 保存地图

建图完成后，保存地图：

```bash
# 创建地图目录
mkdir -p ~/maps

# 保存地图（会生成 .pgm 和 .yaml 两个文件）
ros2 run nav2_map_server map_saver_cli -f ~/maps/my_map

# 查看生成的文件
ls -lh ~/maps/
```

## 第二步：自主导航

### 2.1 启动导航系统

```bash
cd ~/chapt_ws
source /opt/ros/jazzy/setup.bash
source install/setup.bash

# 启动导航（使用刚才保存的地图）
ros2 launch datarobot_base navigation.launch.py \
  map_file:=/home/admin/maps/my_map.yaml \
  serial_port:=/dev/ttyUSB1 \
  lidar_port:=/dev/ttyUSB0
```

### 2.2 在 RViz 中设置初始位置

在远程电脑的 RViz2 中：

1. 点击工具栏的 **"2D Pose Estimate"**
2. 在地图上点击机器人的**实际位置**
3. 拖动箭头指向机器人的**实际朝向**
4. 观察粒子云（绿色箭头）是否收敛到机器人周围

### 2.3 发送导航目标

1. 点击工具栏的 **"Nav2 Goal"** 或 **"2D Goal Pose"**
2. 在地图上点击目标位置
3. 拖动箭头指向期望的最终朝向
4. 机器人会自动规划路径并导航到目标点

### 2.4 观察导航过程

在 RViz 中可以看到：
- **全局路径**（绿色）：从起点到终点的规划路径
- **局部路径**（红色）：当前正在跟踪的轨迹
- **代价地图**：障碍物和膨胀区域
- **激光扫描**：实时检测的障碍物

## 常见问题

### Q1: 地图扭曲严重，墙壁重叠

**原因**：齿轮比未标定，里程计误差太大。

**解决方案**：
1. 返回标定阶段，完成齿轮比标定（见 `操作手册.md`）
2. 标定后重新建图

### Q2: 定位失败，粒子云分散

**原因**：初始位置设置不准确。

**解决方案**：
1. 重新使用 "2D Pose Estimate" 设置初始位置
2. 确保在地图上选择的位置与机器人实际位置一致
3. 手动控制机器人移动一小段距离，帮助定位收敛

### Q3: 机器人不移动或行为异常

**检查项**：
```bash
# 检查所有话题是否正常
ros2 topic list

# 检查速度命令是否发布
ros2 topic echo /cmd_vel

# 检查导航状态
ros2 topic echo /diagnostics

# 查看 TF 树
ros2 run tf2_tools view_frames
```

### Q4: 串口设备找不到

```bash
# 查看可用的串口设备
ls -l /dev/ttyUSB*

# 根据实际情况调整启动参数
# 底盘通常是 /dev/ttyUSB1，雷达是 /dev/ttyUSB0
# 但可能会变，需要根据实际情况调整
```

### Q5: 导航过程中撞到障碍物

**调整建议**：
- 增大机器人半径：修改 [nav2_params.yaml](src/datarobot_base/config/nav2_params.yaml) 中的 `robot_radius`
- 增大膨胀半径：修改 `inflation_radius` 参数
- 降低最大速度：修改 `max_vel_x` 和 `max_vel_theta`

## 性能优化建议

### 如果地图质量可以接受

当前配置已经针对未标定齿轮比进行了优化：
- SLAM 参数增大了移动阈值，降低对里程计的依赖
- 启用了循环闭合，补偿累积误差
- 导航速度设置为保守值（0.5 m/s）

### 如果地图质量不佳

建议完成齿轮比标定（见 `任务交接说明书.md` 阶段2）：
1. 在地面标记 5 米直线
2. 让机器人前进并测量实际距离
3. 计算并更新 `gear_ratio` 参数
4. 重新建图

## 文件说明

本次更新创建的文件：
- [slam_params.yaml](src/datarobot_base/config/slam_params.yaml) - SLAM 配置参数
- [slam.launch.py](src/datarobot_base/launch/slam.launch.py) - SLAM 启动文件
- [nav2_params.yaml](src/datarobot_base/config/nav2_params.yaml) - Nav2 导航配置
- [navigation.launch.py](src/datarobot_base/launch/navigation.launch.py) - 导航启动文件

## 下一步

成功完成建图和导航后，建议：
1. ✅ 完成齿轮比标定以提高精度
2. ✅ 在更大的环境中测试
3. ✅ 调整 Nav2 参数以优化导航性能
4. ✅ 考虑添加 IMU 传感器改善里程计

---

**最后更新**：2026年9月17日
**状态**：已完成阶段3（SLAM）和阶段4（Nav2）的基础配置
