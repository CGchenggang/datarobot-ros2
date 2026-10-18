# DataRobot ROS2 机器人（圆柱形 · 多传感器 · 多层建筑仿真）

基于 **ROS 2 Jazzy** 的差速驱动机器人，集成 BlueSea 激光雷达 + **IMU + 顶部相机 + 6 路超声波**。
同一套代码同时支持 **Gazebo（gz Harmonic）仿真** 和 **实机** 两种运行方式。

---

## 当前状态

| 阶段 | 状态 |
|---|---|
| 硬件集成（底盘 Modbus 驱动 + 雷达驱动 + URDF/TF） | ✅ 已完成，连机验证通信正常 |
| Gazebo 仿真：SLAM 建图 + Nav2 导航 | ✅ 已完成（详见《任务完成总结》）|
| **机器人外观美化**（白塔身/蓝饰环/顶盖信标/轮胎毂） | ✅ 已完成并实测渲染 |
| **IMU 传感器**（gz 插件 + /imu/data 桥接） | ✅ 实测 45-47Hz，frame=imu_link |
| **顶部相机**（gz 相机 + /camera/image_raw + RViz 画面） | ✅ 实测 ~5Hz，抓帧成功；`camera_enabled:=false` 可关载 |
| **6 路超声波**（LaserScan→Range+点云，Nav2 代价图融合） | ✅ 实测 8Hz，0.71m 隔墙实测命中；带旋转门控防幻影 |
| **多层建筑仿真世界**（支撑柱×6 + 静止汽车×8 + 二层） | ✅ 建成；一层 SLAM 地图 + 二层 CAD 地图随包 |
| **无头/CI 运行**（gui:=false + EGL 离屏渲染） | ✅ 全程无头验证 |
| **SLAM 建图验证**（building 一层，无头） | ✅ 8/8 航点覆盖建图，地图质量高（见 verify_logs/floor1_map.png）|
| **Nav2 导航闭环验证** | ✅ room 世界 3/3 目标 SUCCEEDED（7/26/32s）；building 一层见 §验证记录 |
| 实机标定（齿轮比） | ⏳ 卡在供电问题，未开始 |
| 实机 IMU/超声波硬件接入 | 📋 接口契约已定，见《实机接入指南》十二节 |

---

## 快速开始

```bash
cd ~/xuniceshi_ws
source /opt/ros/jazzy/setup.bash
source install/setup.bash
```

### 仿真（多层建筑：支撑柱 + 静止汽车 + 二层）

```bash
# 终端 1：Gazebo + RViz + 机器人 + 全传感器桥接
ros2 launch datarobot_base gazebo_jazzy_sim.launch.py

# 终端 2A（导航，用随包地图，无需先建图）：
ros2 launch datarobot_base nav_sim.launch.py                # 一层
ros2 launch datarobot_base nav_sim.launch.py floor:=2       # 二层（配合 spawn_z:=3.55 出生）

# 终端 2B（建图）：
ros2 launch datarobot_base slam_sim.launch.py
# 建图时让机器人自己走覆盖路径：
ros2 run datarobot_base waypoint_driver.py --ros-args -p \
  waypoints:="[[-10.0,0.75,0.0],[10.0,0.75,0.0],[0.0,0.0,0.0]]"
```

发目标（RViz "Nav2 Goal" 或命令行）：

```bash
ros2 action send_goal /navigate_to_pose nav2_msgs/action/NavigateToPose \
  "{pose: {header: {frame_id: map}, pose: {position: {x: 9.0, y: 0.5, z: 0.0}, orientation: {w: 1.0}}}}"
```

### 仿真（10×10 测试房间）

```bash
ros2 launch datarobot_base gazebo_jazzy_sim.launch.py world:=room
ros2 launch datarobot_base nav_sim.launch.py world:=room
```

### 无头运行（SSH / 无显示器 / CI）

```bash
ros2 launch datarobot_base gazebo_jazzy_sim.launch.py gui:=false rviz:=false
# 无显示器时传感器走 EGL 离屏渲染（默认开），有显示器可加 headless_rendering:=false
```

### 出生在二层

```bash
ros2 launch datarobot_base gazebo_jazzy_sim.launch.py spawn_z:=3.55
# 另一终端
ros2 launch datarobot_base nav_sim.launch.py floor:=2
```

### 实机

```bash
ros2 launch datarobot_base bringup_with_lidar.launch.py      # 底盘 + 雷达
ros2 launch datarobot_base slam.launch.py                    # 建图
ros2 launch datarobot_base navigation.launch.py map_file:=/home/admin/maps/my_map.yaml
```

> ⚠️ 参数名是 **`rviz`**，不是 `use_rviz`。
> ⚠️ 首次上电务必把驱动轮**架空**，详见《实机接入指南》安全须知。
> ⚠️ `slam_toolbox` 与 `amcl` 不能同时跑（都发布 `map→odom`）；`teleop`/`waypoint_driver` 与 Nav2 不能同时跑（都抢 `/cmd_vel`）。

---

## 本轮改造（2026-10-17）要点

1. **外观**：白塔身 + 上下蓝色饰环 + 深灰裙边/顶盖 + 橙色信标 + 前脸面板；轮胎深灰+银毂。
   碰撞体/惯性**保持原验证参数不动**（重心、倾覆与雷达遮挡特性都依赖它）。
2. **IMU**：`imu_link` 加 gz IMU 传感器（50Hz），桥接 `/imu/data`（frame=imu_link）；
   world 侧需 `gz-sim-imu-system` 插件（两个世界都已加）。
3. **相机**：顶盖云台位（下俯 10°），320×240@5Hz，桥接 `/camera/image_raw` + `/camera/camera_info`。
4. **超声波 ×6**（前×3/左/右/后）：仿真用窄波束 gpu_lidar 模拟 HC-SR04（0.03~4m，10Hz），
   `ultrasonic_node.py` 统一转成 `sensor_msgs/Range`（`/us/<name>`，实机驱动同接口）
   + 融合点云 `/us/cloud`；**局部与全局代价图都挂了 us_cloud**——低矮障碍（绿化岛/挡轮杆）
   不在静态地图里，只挡局部不挡全局会造成"全局反复穿、局部反复停"的振荡。
5. **多层建筑世界** `building_world.sdf`（24×16m）：一层车库层（6 根支撑柱 r=0.3、
   8 辆静止汽车、4 个 0.12m 绿化岛=超声波专属目标）、二层办公层（隔断+工位），
   反对称特征防 AMCL 镜像跳变。原 10×10 房间保留为 `room_world.sdf`。
6. **整理**：删除早期练习件（`urdf/datarobot.urdf`、`urdf/datarobot.xacro`）与雷达 xacro 备份；
   world 随包安装（不再依赖 `~/xuniceshi_ws/` 硬编码路径+静默回退 empty.sdf）；
   激光 frame 用 `<gz_frame_id>` 在源头修正，删除 `fix_laser_frame.py` 补丁节点。
7. **地图随包**：`maps/building_floor1.yaml`、`maps/building_floor2.yaml`、`maps/room.yaml`
   由无头 SLAM 实测生成，`nav_sim.launch.py` 直接可用，无需先建图。

## ROS 2 话题

| 话题 | 方向 | 说明 |
|---|---|---|
| `/cmd_vel` | 订阅 | 速度指令（实机由 velocity_smoother 输出） |
| `/scan` | 发布 | 2D 激光（10 Hz，frame=laser_link） |
| `/imu/data` | 发布 | IMU（50 Hz，frame=imu_link） |
| `/us/<name>` | 发布 | 6 路超声波 Range（10 Hz，frame=各 us_*_link） |
| `/us/cloud` | 发布 | 超声波融合点云（base_link 系，供代价图） |
| `/camera/image_raw`、`/camera/camera_info` | 发布 | 顶部相机（5 Hz） |
| `/odom` | 发布 | 里程计（50 Hz） |
| `/tf`、`/tf_static`、`/joint_states`、`/robot_description` | 发布 | 坐标变换/关节/模型 |

坐标系：`odom → base_footprint → base_link → laser_link / imu_link / camera_link / us_*_link`

---

## 导航算法选型

为什么选 Nav2 而不是 SCAN-Planner / ego-planner，多层建筑怎么处理，
见 **[导航算法选型分析.md](导航算法选型分析.md)**。一句话：Nav2 一期跑通全栈，
SCAN（圆柱障碍最佳适配）列二期局部规划器旁路，ego-planner 只借鉴思想不搬代码。

---

## 硬件速查

| 项目 | 值 |
|---|---|
| 底盘接口 | Modbus RTU over RS485，115200 bps，8N1，从站 0x01 |
| 底盘串口 | `/dev/datarobot_base`（udev 固定名） |
| 雷达型号 | BlueSea LDS，UART 接口，**波特率 1000000**，10 Hz |
| 雷达串口 | `/dev/LHLiDAR`（udev 固定名） |
| IMU / 超声波 | 📋 待装：接口契约见《实机接入指南》十二节 |
| 轮半径 / 轮距 | 0.083 m（待卡尺复核）/ **0.358 m** ✅ 已实测确认 |
| 控制频率 | 20 Hz（115200 bps 下稳定；50 Hz 会丢应答） |

⚠️ 串口**必须**用 udev 固定名，规则文件：`src/datarobot_base/config/udev/99-datarobot.rules`。

---

## 文档

| 文档 | 内容 |
|---|---|
| **[导航算法选型分析.md](导航算法选型分析.md)** | ⭐ oomwoo/SCAN/ego-planner 分析与选型结论、多层系统设计 |
| **[实机接入指南.md](实机接入指南.md)** | 仿真→真机全流程 + 十二节：IMU/超声波实机接入 |
| [技术手册.md](技术手册.md) | 硬件规格、Modbus 寄存器映射与实测帧 |
| [操作指南.md](操作指南.md) | 日常操作命令、建图/导航步骤、排查手册 |
| [项目结构说明.md](项目结构说明.md) | 目录结构、每个文件的作用、TF 树 |
| [任务完成总结.md](任务完成总结.md) | 上一阶段（基础仿真）成果与踩坑 |

---

## 目录结构

```
xuniceshi_ws/
├── src/
│   ├── datarobot_base/          底盘驱动、传感器节点、launch、参数、世界、地图
│   │   ├── datarobot_base/      modbus_controller.py + diff_drive_controller.py
│   │   ├── scripts/             base_driver_node / ultrasonic_node / waypoint_driver
│   │   ├── launch/              仿真 + 实机全部启动文件
│   │   ├── config/              底盘/雷达/SLAM/Nav2 参数 + udev
│   │   ├── worlds/              room_world.sdf + building_world.sdf（随包安装）
│   │   └── maps/                building_floor1/2 + room（随包安装）
│   ├── datarobot_description/   URDF 模型
│   │   └── urdf/databot/        datarobot.urdf.xacro ← 唯一入口
│   │       ├── base.urdf.xacro       车体+全局材质调色板
│   │       ├── gazebo.urdf.xacro     差速/关节状态插件
│   │       ├── actuator/             wheel / caster
│   │       └── senser/               laser / imu / camera / ultrasonic
│   ├── bluesea2/                激光雷达厂商驱动（含 SDK）
│   └── base/                    早期练习件（未使用）
├── 导航算法选型分析.md  实机接入指南.md  技术手册.md  操作指南.md
├── 项目结构说明.md  任务完成总结.md  README.md
└── build/ install/ log/         colcon 产物（已 gitignore）
```

⚠️ **URDF 只能用一个**：`urdf/databot/datarobot.urdf.xacro`（历史遗留练习件已删除）。

---

## 从源码编译

```bash
cd ~/xuniceshi_ws
source /opt/ros/jazzy/setup.bash

# 依赖
sudo apt install ros-jazzy-desktop python3-colcon-common-extensions \
  ros-jazzy-ros-gz ros-jazzy-nav2-bringup ros-jazzy-slam-toolbox
sudo apt install python3-serial python3-pymodbus

# 编译（改动 config/*.yaml 与 launch/*.py 后必须重新编译才生效）
colcon build --packages-select datarobot_description datarobot_base
source install/setup.bash
```

## 系统要求

- ROS 2 Jazzy（Ubuntu 24.04）+ gz Harmonic
- 硬件：DataRobot 底盘 + BlueSea 激光雷达（+ 待装 IMU/超声波）

> WSL2 里跑需要 `usbipd` 转发 USB 串口（实机），见《技术手册》；纯仿真无需串口。
>
> ⚠️ **WSL2 mirrored 网络模式注意**：镜像模式下 distro 内 eth0 等是 DOWN 的占位镜像，
> FastDDS 默认的 UDP 组播发现会全灭（症状：话题都列得出但收不到数据、进程间几分钟才互相发现）。
> 单机仿真加一个环境变量即可（纯共享内存传输，与网卡无关）：
> ```bash
> export FASTRTPS_DEFAULT_PROFILES_FILE=<仓库>/.agent/local/fastdds_shm.xml
> ```
> （实机/跨机部署不要用这个配置，删掉该环境变量即恢复默认 UDP。）
