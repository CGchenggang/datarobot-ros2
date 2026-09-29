#!/usr/bin/env python3
"""
修改后的启动文件：简化激光雷达数据流
"""

import os
from ament_index_python.packages import get_package_share_path
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess
from launch.conditions import IfCondition
from launch.substitutions import Command, LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    # ========== 路径配置 ==========
    description_package_path = get_package_share_path("datarobot_description")

    xacro_path = os.path.join(description_package_path, "urdf", "databot",
                              "datarobot.urdf.xacro")

    rviz_config_path = os.path.join(description_package_path, "rviz",
                                    "datarobot.rviz")

    # ========== 启动参数 ==========
    rviz_arg = DeclareLaunchArgument(
        "rviz",
        default_value="true",
        choices=["true", "false"],
        description="启动 RViz2 可视化"
    )

    # ========== 机器人描述 ==========
    robot_description = ParameterValue(
        Command(["xacro ", xacro_path, " use_sim_time:=true"]),
        value_type=str
    )

    # ========== 节点配置 ==========
    datarobot_world_path = os.path.join(os.path.expanduser("~"), "xuniceshi_ws", "datarobot_world.sdf")

    # 1. 启动 Gazebo
    gazebo_server = ExecuteProcess(
        cmd=["gz", "sim", "-v", "4", "-r", datarobot_world_path if os.path.exists(datarobot_world_path) else "empty.sdf"],
        output="screen",
        shell=False
    )

    # 2. 机器人状态发布节点
    robot_state_publisher = Node(
        package="robot_state_publisher",
        executable="robot_state_publisher",
        name="robot_state_publisher",
        output="screen",
        parameters=[{
            "use_sim_time": True,
            "robot_description": robot_description
        }]
    )

    # 3. 在 Gazebo 中生成机器人
    spawn_robot = Node(
        package="ros_gz_sim",
        executable="create",
        name="spawn_datarobot",
        output="screen",
        arguments=[
            "-topic", "robot_description",
            "-name", "datarobot",
            "-x", "0.0",
            "-y", "0.0",
            "-z", "0.1",
        ],
        parameters=[{"use_sim_time": True}]
    )

    # 4. 桥接 Gazebo 和 ROS 2 话题（只桥接必要的话题，激光雷达由专门节点处理）
    bridge = Node(
        package="ros_gz_bridge",
        executable="parameter_bridge",
        name="ros_gz_bridge",
        output="screen",
        arguments=[
            # /clock 必须桥接！use_sim_time=true 的节点全靠它走时钟。
            # 不桥接的话 ROS 侧仿真时间永远停在 0，slam_toolbox 因为只用消息
            # 时间戳查 TF 而"恰好"能工作，但 Nav2 充满定时器（控制器频率、
            # 代价地图更新、行为树 tick）—— 时钟不走 = 定时器不触发 = 机器人不动
            "/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock",
            "/cmd_vel@geometry_msgs/msg/Twist]gz.msgs.Twist",
            "/odom@nav_msgs/msg/Odometry[gz.msgs.Odometry",
            "/joint_states@sensor_msgs/msg/JointState[gz.msgs.Model",
            "/world/datarobot_test_world/model/datarobot/link/base_footprint/sensor/laser_sensor/scan@sensor_msgs/msg/LaserScan[gz.msgs.LaserScan",
            "/model/datarobot/tf@tf2_msgs/msg/TFMessage[gz.msgs.Pose_V",
        ],
        parameters=[{"use_sim_time": True}],
        remappings=[
            ("/world/datarobot_test_world/model/datarobot/link/base_footprint/sensor/laser_sensor/scan", "/scan_gazebo_raw"),
            ("/model/datarobot/tf", "/tf"),
        ]
    )

    # 5. Python 节点：修正激光雷达 frame_id（从 /scan_gazebo_raw 到 /scan）
    laser_frame_fixer = Node(
        package="datarobot_base",
        executable="fix_laser_frame.py",
        name="laser_frame_fixer",
        output="screen",
        parameters=[{"use_sim_time": True}],
        remappings=[
            ("/scan_raw", "/scan_gazebo_raw"),
        ]
    )

    # 6. RViz 可视化
    rviz = Node(
        package="rviz2",
        executable="rviz2",
        name="rviz2",
        output="screen",
        arguments=["-d", rviz_config_path],
        parameters=[{"use_sim_time": True}],
        condition=IfCondition(LaunchConfiguration("rviz"))
    )

    return LaunchDescription([
        rviz_arg,
        gazebo_server,
        robot_state_publisher,
        spawn_robot,
        bridge,
        laser_frame_fixer,
        rviz,
    ])
