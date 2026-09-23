# DataRobot 开发路线图

从当前的底盘驱动到建图导航。包结构参考 oomwoo-one 的分层方式：
描述包 / 硬件驱动包 / 传感器包 / 建图包 / 导航包各自独立，
顶层 bringup launch 逐层组合。

---

## 阶段 0：底盘驱动 — 已完成

`datarobot_base` 可用。cmd_vel 控制前进后退转向已实测通过，
`/odom`、`/joint_states`、TF `odom → base_footprint` 均有数据。
URDF 已修好并接入 RViz，`bringup.launch.py` 一条命令即可启动
驱动 + 模型 + RViz。

已解决的问题记录在 [PROJECT_CONTEXT.md](PROJECT_CONTEXT.md)：
右轮符号翻转、使能时序与重试、Modbus 收发时序、控制频率上限。

<!-- SECTION: remaining -->

### 遗留待办


按优先级排列，都不阻塞下一阶段，但会影响导航精度。

**1. 齿轮比标定（影响所有后续精度，建议最先做）**

`gear_ratio` 现在是假定值 1.0。未标定的话里程计有系统性比例误差，
建图会变形、导航到点会偏。做法：

```bash
ros2 launch datarobot_base bringup.launch.py
# 地面画起点线，发布固定速度让机器人直行
ros2 topic pub --rate 10 /cmd_vel geometry_msgs/msg/Twist "{linear: {x: 0.1}}"
# 停下后量实际距离，与 /odom 的 x 对比
ros2 topic echo /odom --field pose.pose.position.x
```

`gear_ratio = 里程计读数 / 实际距离`。改 `config/base_driver.yaml`。
轮距 `wheel_base` 同理可用原地旋转 360° 标定。

**2. URDF 与 RViz —— 已完成**

修好了 material 缺 name 的报错，并补上了缺失的 `base_footprint`（原先里程计
发布 `odom → base_footprint` 但 URDF 根是 `base_link`，TF 树是断开的两截）。
`bringup.launch.py` 原先加载的是单 link 练习件 `datarobot.urdf`，已改为
真正的 `databot/datarobot.urdf.xacro`，并加了 RViz 一键启动（`rviz:=false` 可关）。
`datarobot_description` 的 CMakeLists 原先没安装 `rviz/` 目录，也已补上。

**3. 偶发 `Failed to set motor speeds`**

已大幅减少（收发改为按截止时间轮询、频率降到 20Hz）。日志现在会带
失败/总次数，例如 `(3 of 1200 writes)`。零星失败无影响；如果比例超过
约 1%，检查 RS485 接线与终端电阻。

**4. 里程计协方差未使用**

`config/base_driver.yaml` 里的 `odom_pose_covariance_diagonal` 等值
声明了但节点未读取，发布的协方差是全零。Nav2 的定位环节会用到，
阶段 3 之前补上。

---

## 阶段 1：传感器接入 — 代码已准备，待硬件测试

建图的前提。激光雷达是必需的，IMU 可选但能显著改善旋转时的里程计。

**已完成的工作**

- ✅ 集成 BlueSeaLidar ROS2 驱动（`bluesea2` 包）
- ✅ 创建雷达配置文件 `config/lidar.yaml`
- ✅ 创建集成 launch 文件 `launch/bringup_with_lidar.launch.py`
  - 支持灵活选择启动模块（`base:=true/false`、`lidar:=true/false`、`rviz:=true/false`）
  - 包含详细的中文注释
  - 可独立测试底盘或雷达
- ✅ TF 链已配置：`odom → base_footprint → base_link → laser_link`
- ✅ 编译通过

**待完成的工作**

1. **连接硬件并测试**
   ```bash
   # 确认雷达串口设备
   ls -l /dev/ttyUSB*
   
   # 赋予串口权限
   sudo chmod 666 /dev/ttyUSB1  # 假设雷达是 ttyUSB1，底盘是 ttyUSB0
   
   # 启动完整系统
   ros2 launch datarobot_base bringup_with_lidar.launch.py
   
   # 或者只测试雷达（不需要底盘）
   ros2 launch datarobot_base bringup_with_lidar.launch.py base:=false
   ```

2. **验证数据**
   ```bash
   # 检查雷达话题
   ros2 topic hz /scan         # 应该有稳定的发布频率（通常 10-20 Hz）
   ros2 topic echo /scan       # 查看扫描数据
   
   # 检查 TF 树完整性
   ros2 run tf2_tools view_frames   # 生成 frames.pdf，检查链条无断裂
   ```

3. **RViz 可视化验证**
   - Fixed Frame 设为 `odom`
   - 添加 `LaserScan` 显示，话题选 `/scan`
   - 手推机器人时，扫描点应与环境轮廓吻合、不随车体漂移
   - 如果扫描点和环境对不上，说明雷达位置 TF 有问题

4. **标定雷达实际安装位置（重要！）**
   
   `senser/laser.urdf.xacro` 里的 `laser_link` 安装位置当前是估计值：
   `xyz="0.2375 0.0 0"`
   
   需要**实测**雷达相对于 `base_link` 的位置（x, y, z）与朝向（roll, pitch, yaw）。
   
   测量方法：
   - x：雷达中心到车体中心的前后距离（向前为正）
   - y：雷达中心到车体中心的左右距离（向左为正）
   - z：雷达中心到 base_link 的高度（向上为正）
   
   **这个 TF 错了，建出来的图会是歪的**，且症状很像 SLAM 参数问题，难以排查。
   
   修改位置：`src/datarobot_description/urdf/databot/datarobot.urdf.xacro` 第 20 行：
   ```xml
   <xacro:laser_xacro xyz="实测x 实测y 实测z"/>
   ```
   修改后需重新编译：
   ```bash
   colcon build --packages-select datarobot_description
   ```

5. **调整配置文件（如果需要）**
   
   如果雷达串口不是 `/dev/ttyUSB1`，修改启动命令或配置文件：
   ```bash
   # 方法 1：命令行参数覆盖
   ros2 launch datarobot_base bringup_with_lidar.launch.py lidar_port:=/dev/ttyUSB2
   
   # 方法 2：修改配置文件
   # 编辑 src/datarobot_base/config/lidar.yaml 中的 port 参数
   ```

**IMU（可选）**

若接入，用 `robot_localization` 的 `ekf_node` 融合 `/odom` 与 `/imu/data`，
输出更稳的 `odom → base_footprint`。注意此时要**关掉** base_driver 的 TF 广播，
避免两个节点发布同一个变换。

---

## 阶段 2：建图（SLAM）

用 `slam_toolbox`，Humble 与 Jazzy 都有官方包。

```bash
sudo apt install ros-humble-slam-toolbox   # Jazzy 上换成 ros-jazzy-
```

**新建包 `datarobot_slam`**，结构：

```
datarobot_slam/
├── config/mapper_params_online_async.yaml   # 从 slam_toolbox 拷贝后按本机改
└── launch/slam.launch.py                    # 组合 bringup + slam_toolbox
```

配置要点：`base_frame: base_footprint`、`odom_frame: odom`、`scan_topic: /scan`，
分辨率 `resolution: 0.05` 起步。

流程：

```bash
ros2 launch datarobot_slam slam.launch.py
ros2 run teleop_twist_keyboard teleop_twist_keyboard   # 慢速遥控走一圈
ros2 run nav2_map_server map_saver_cli -f ~/maps/my_map
```

建图时走慢一点、避免原地急转 —— 里程计误差在旋转时最大。
如果闭环时地图错位明显，回头看阶段 0 的齿轮比与轮距标定。

---

## 阶段 3：导航（Nav2）

```bash
sudo apt install ros-humble-navigation2 ros-humble-nav2-bringup
```

**新建包 `datarobot_navigation`**，结构：

```
datarobot_navigation/
├── config/nav2_params.yaml    # 从 nav2_bringup 拷贝后按本机改
├── maps/my_map.yaml           # 阶段 2 保存的地图
└── launch/navigation.launch.py
```

`nav2_params.yaml` 里必须按本机实际改的项：

- `robot_radius` —— 车体半径。URDF 里 base_link 圆柱 r=0.28，据此填
- `max_vel_x` / `max_vel_theta` —— 别超过底盘实际能力
- 局部规划器选 `DWB` 或 `MPPI`
- `robot_base_frame: base_footprint`

流程：

```bash
ros2 launch datarobot_navigation navigation.launch.py
# RViz 里先用 2D Pose Estimate 给初始位姿，再用 Nav2 Goal 发目标点
```

---

## 阶段 4：迁移到 Jazzy

代码已避免 Humble 特有 API，迁移时主要是环境层面：

- 所有 `ros-humble-*` 换成 `ros-jazzy-*`
- Jazzy 的 `cmd_vel` 在部分栈里改用 `geometry_msgs/TwistStamped`，
  若接 Nav2 需确认消息类型是否要适配
- `python3-serial` 依赖照旧
- 重新在目标机上标定齿轮比 —— 换车体或换轮子后必须重做

---

## 目标包结构

```
chapt_ws/src/
├── datarobot_description/     已完成
├── datarobot_base/            已完成 ← 当前位置
├── datarobot_sensors/         阶段 1
├── datarobot_slam/            阶段 2
├── datarobot_navigation/      阶段 3
└── datarobot_bringup/         顶层组合 launch（阶段 1 后建）
```

`datarobot_bringup` 用 `IncludeLaunchDescription` 逐层引入下层 launch，
这样单独调试某一层时不必启动全部节点。



