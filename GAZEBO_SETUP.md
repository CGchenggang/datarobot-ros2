# Gazebo 仿真依赖包安装指南

## 需要在板子上安装的包

在板子上通过 SSH 执行以下命令,安装 Gazebo 仿真所需的 ROS 2 包:

```bash
# 安装新版 Gazebo 与 ROS 2 的桥接包
sudo apt install ros-jazzy-ros-gz

# 安装 Gazebo 仿真包
sudo apt install ros-jazzy-ros-gz-sim

# 安装 ROS 2 与 Gazebo 话题桥接包
sudo apt install ros-jazzy-ros-gz-bridge
```

## 可选:安装额外的 Gazebo 插件

如果需要更多的传感器或功能,可以安装:

```bash
# 安装 Gazebo 图像桥接(如果需要相机仿真)
sudo apt install ros-jazzy-ros-gz-image

# 安装完整的 Gazebo 工具集
sudo apt install gz-harmonic
```

## 安装后验证

安装完成后,执行以下命令验证:

```bash
# 验证 Gazebo 命令可用
which gz

# 验证 ROS 2 包已安装
ros2 pkg list | grep ros_gz
```

应该看到类似输出:
```
ros_gz
ros_gz_bridge
ros_gz_image
ros_gz_sim
ros_gz_sim_demos
```

## 下一步

安装完依赖包后:

1. 将桌面上修改好的 `chapt_ws` 文件夹复制到板子上
2. 在板子上进入工作空间并重新编译:
   ```bash
   cd ~/chapt_ws
   colcon build
   source install/setup.bash
   ```
3. 启动 Gazebo 仿真测试:
   ```bash
   ros2 launch datarobot_base gazebo_jazzy_sim.launch.py
   ```

## 常见问题

**Q: 安装时提示找不到包怎么办?**

A: 先更新软件源:
```bash
sudo apt update
```

**Q: Gazebo 启动很慢或者卡住?**

A: 第一次启动 Gazebo 会下载模型,可能需要几分钟。如果一直卡住,可以按 Ctrl+C 终止后重新启动。

**Q: 如何确认仿真是否正常工作?**

A: 仿真启动后,在另一个终端执行:
```bash
ros2 topic list
```

应该能看到 `/scan`、`/odom`、`/cmd_vel` 等话题。
