#!/usr/bin/env python3
"""Gazebo (gz Harmonic) 仿真一键启动：机器人 + 世界 + 传感器桥接 + RViz

用法：
    ros2 launch datarobot_base gazebo_jazzy_sim.launch.py                       # 多层建筑世界
    ros2 launch datarobot_base gazebo_jazzy_sim.launch.py world:=room           # 10x10 测试房间
    ros2 launch datarobot_base gazebo_jazzy_sim.launch.py spawn_z:=3.55         # 出生在二层楼板
    ros2 launch datarobot_base gazebo_jazzy_sim.launch.py gui:=false rviz:=false  # 无头（SSH/CI）

桥接话题（world 名由本文件按 world 参数拼接，不再硬编码）：
    /scan            2D 激光 LaserScan   (frame: laser_link)
    /imu/data        IMU Imu             (frame: imu_link)
    /camera/image_raw + /camera/camera_info (frame: camera_link)
    /us/<name>/scan  6 路超声波原始 LaserScan → ultrasonic_node 转 Range + /us/cloud
    /odom /joint_states /tf /clock       底盘与时间

之后可另开终端：
    ros2 launch datarobot_base slam_sim.launch.py                    # 建图
    ros2 launch datarobot_base nav_sim.launch.py                     # 用随包地图直接导航
"""

import os

from ament_index_python.packages import get_package_share_path
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess, OpaqueFunction
from launch.conditions import IfCondition
from launch.substitutions import Command, LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue

# world 别名 → (SDF 文件, world 名)。桥接的作用域话题含 world 名，必须成对维护
WORLDS = {
    "room": ("room_world.sdf", "datarobot_test_world"),
    "building": ("building_world.sdf", "datarobot_building"),
}

# 超声波安装位姿 (x, y, z, yaw)：与 urdf/databot/senser/ultrasonic.urdf.xacro 严格一致
US_MOUNTS = {
    "us_front":       (0.283, 0.0, -0.13, 0.0),
    "us_front_left":  (0.20, 0.20, -0.13, 0.7854),
    "us_front_right": (0.20, -0.20, -0.13, -0.7854),
    "us_left":        (0.0, 0.283, -0.13, 1.5708),
    "us_right":       (0.0, -0.283, -0.13, -1.5708),
    "us_rear":        (-0.283, 0.0, -0.13, 3.14159),
}


def _setup(context, *args, **kwargs):
    base_share = get_package_share_path("datarobot_base")
    desc_share = get_package_share_path("datarobot_description")

    world = LaunchConfiguration("world").perform(context)
    gui = LaunchConfiguration("gui").perform(context) == "true"
    rviz = LaunchConfiguration("rviz").perform(context) == "true"
    headless_rendering = LaunchConfiguration("headless_rendering").perform(context)

    world_file, world_name = WORLDS[world]
    world_path = str(base_share / "worlds" / world_file)

    # world 名校验：SDF 里的 <world name> 与这里不一致时，桥接作用域话题全部静默断流
    with open(world_path, "r", encoding="utf-8") as f:
        if f'<world name="{world_name}">' not in f.read():
            raise RuntimeError(
                f"{world_path} 里没有 <world name=\"{world_name}\">，"
                "world 文件与 WORLDS 表不一致，桥接必然断流")

    xacro_path = str(desc_share / "urdf" / "databot" / "datarobot.urdf.xacro")
    rviz_config_path = str(desc_share / "rviz" / "datarobot.rviz")

    # ---- Gazebo：gui:=true 开完整 GUI；false 只跑 server（SSH/CI 用），
    #      传感器渲染需要 --headless-rendering（EGL），有显示器时可关掉省事
    gz_cmd = ["gz", "sim", "-v", "3", "-r"]
    if not gui:
        gz_cmd += ["-s"]
        if headless_rendering == "true":
            gz_cmd += ["--headless-rendering"]
    gz_cmd.append(world_path)
    gazebo = ExecuteProcess(cmd=gz_cmd, output="screen")

    robot_description = ParameterValue(
        Command(["xacro ", xacro_path, " use_sim_time:=true",
                 " camera_enabled:=", LaunchConfiguration("camera_enabled")]),
        value_type=str)

    robot_state_publisher = Node(
        package="robot_state_publisher", executable="robot_state_publisher",
        name="robot_state_publisher", output="screen",
        parameters=[{"use_sim_time": True,
                     "robot_description": robot_description}])

    spawn_robot = Node(
        package="ros_gz_sim", executable="create", name="spawn_datarobot",
        output="screen",
        arguments=["-topic", "robot_description", "-name", "datarobot",
                   "-x", LaunchConfiguration("spawn_x"),
                   "-y", LaunchConfiguration("spawn_y"),
                   "-z", LaunchConfiguration("spawn_z"),
                   "-Y", LaunchConfiguration("spawn_yaw")],
        parameters=[{"use_sim_time": True}])

    # ---- 桥接。作用域话题的 link 段是 base_footprint：URDF 固定关节在 gz 里
    #      被合并（lump），所有车载传感器都挂到规范化后的根连杆名下。
    scope = f"/world/{world_name}/model/datarobot/link/base_footprint/sensor"
    bridge_args = [
        # /clock 必须桥接：use_sim_time=true 的节点全靠它走时钟，不桥接 Nav2 定时器不触发
        "/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock",
        "/cmd_vel@geometry_msgs/msg/Twist]gz.msgs.Twist",
        "/odom@nav_msgs/msg/Odometry[gz.msgs.Odometry",
        "/joint_states@sensor_msgs/msg/JointState[gz.msgs.Model",
        "/model/datarobot/tf@tf2_msgs/msg/TFMessage[gz.msgs.Pose_V",
        f"{scope}/laser_sensor/scan@sensor_msgs/msg/LaserScan[gz.msgs.LaserScan",
        f"{scope}/imu_sensor/imu@sensor_msgs/msg/Imu[gz.msgs.IMU",
        f"{scope}/camera_sensor/image@sensor_msgs/msg/Image[gz.msgs.Image",
        f"{scope}/camera_sensor/camera_info@sensor_msgs/msg/CameraInfo[gz.msgs.CameraInfo",
    ]
    bridge_remaps = [
        ("/model/datarobot/tf", "/tf"),
        (f"{scope}/laser_sensor/scan", "/scan"),
        (f"{scope}/imu_sensor/imu", "/imu/data"),
        (f"{scope}/camera_sensor/image", "/camera/image_raw"),
        (f"{scope}/camera_sensor/camera_info", "/camera/camera_info"),
    ]
    for us_name in US_MOUNTS:
        bridge_args.append(
            f"{scope}/{us_name}/scan@sensor_msgs/msg/LaserScan[gz.msgs.LaserScan")
        bridge_remaps.append((f"{scope}/{us_name}/scan", f"/us/{us_name}/scan"))

    bridge = Node(
        package="ros_gz_bridge", executable="parameter_bridge",
        name="ros_gz_bridge", output="screen",
        arguments=bridge_args,
        remappings=bridge_remaps,
        parameters=[{"use_sim_time": True}])

    # ---- 超声波接口节点：LaserScan → Range + 融合点云（挂载位姿与 URDF 一致）
    us_params = [{"use_sim_time": True,
                  "base_frame": "base_link",
                  "sensor_names": list(US_MOUNTS.keys())}]
    for name, (x, y, z, yaw) in US_MOUNTS.items():
        us_params.append({f"{name}.x": x, f"{name}.y": y,
                          f"{name}.z": z, f"{name}.yaw": yaw})
    ultrasonic = Node(
        package="datarobot_base", executable="ultrasonic_node.py",
        name="ultrasonic_node", output="screen", parameters=us_params)

    rviz_node = Node(
        package="rviz2", executable="rviz2", name="rviz2", output="screen",
        arguments=["-d", rviz_config_path],
        parameters=[{"use_sim_time": True}],
        condition=IfCondition(LaunchConfiguration("rviz")))

    return [gazebo, robot_state_publisher, spawn_robot, bridge, ultrasonic, rviz_node]


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument(
            "world", default_value="building", choices=["room", "building"],
            description="仿真世界：building=多层建筑(柱+汽车+二层) / room=10x10测试房间"),
        DeclareLaunchArgument(
            "gui", default_value="true", choices=["true", "false"],
            description="是否启动 Gazebo GUI（false 只跑 server，配合 rviz:=false 可无头运行）"),
        DeclareLaunchArgument(
            "headless_rendering", default_value="true", choices=["true", "false"],
            description="gui:=false 时传感器是否用 EGL 离屏渲染（SSH 无显示器必须 true）"),
        DeclareLaunchArgument(
            "rviz", default_value="true", choices=["true", "false"],
            description="启动 RViz2 可视化"),
        DeclareLaunchArgument("spawn_x", default_value="0.0"),
        DeclareLaunchArgument("spawn_y", default_value="0.0"),
        DeclareLaunchArgument(
            "spawn_z", default_value="0.05",
            description="出生高度：一层 0.05；二层楼板(顶面3.5m)用 3.55"),
        DeclareLaunchArgument("spawn_yaw", default_value="0.0"),
        DeclareLaunchArgument(
            "camera_enabled", default_value="true", choices=["true", "false"],
            description="是否挂载 gz 相机传感器（CPU 紧张时 false 可省一路渲染）"),
        OpaqueFunction(function=_setup),
    ])
