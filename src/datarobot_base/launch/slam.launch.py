#!/usr/bin/env python3
"""
SLAM 建图启动文件
使用 slam_toolbox 进行 2D 激光 SLAM

功能：
- 启动底盘驱动和激光雷达
- 启动 slam_toolbox 进行实时建图
- 适用于未标定齿轮比的初步建图测试

使用方法：
    # 基本启动
    ros2 launch datarobot_base slam.launch.py

    # 串口默认走 udev 固定名（/dev/datarobot_base、/dev/LHLiDAR），
    # 若还没建 udev 规则，用命令行覆盖成实际设备：
    ros2 launch datarobot_base slam.launch.py \
      serial_port:=/dev/ttyUSB1 lidar_port:=/dev/ttyUSB0

建图完成后保存地图：
    mkdir -p ~/maps
    ros2 run nav2_map_server map_saver_cli -f ~/maps/my_map
"""

import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, DeclareLaunchArgument
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node


def generate_launch_description():
    # 获取功能包路径
    base_package_path = get_package_share_directory('datarobot_base')

    # SLAM 配置文件路径
    slam_params_file = os.path.join(base_package_path, 'config', 'slam_params.yaml')

    # 启动参数
    use_sim_time_arg = DeclareLaunchArgument(
        'use_sim_time',
        default_value='false',
        choices=['true', 'false'],
        description='使用仿真时间'
    )

    # 端口默认值用 udev 固定名，不用按插入顺序分配的 /dev/ttyUSB*。
    # 安装规则见 config/udev/99-datarobot.rules。
    serial_port_arg = DeclareLaunchArgument(
        'serial_port',
        default_value='/dev/datarobot_base',
        description='底盘串口设备（udev 固定名）'
    )

    lidar_port_arg = DeclareLaunchArgument(
        'lidar_port',
        default_value='/dev/LHLiDAR',
        description='激光雷达串口设备（udev 固定名）'
    )

    # 1. 启动底盘和雷达（不启动 RViz，用远程电脑查看）
    base_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            PathJoinSubstitution([
                base_package_path,
                'launch',
                'bringup_with_lidar.launch.py'
            ])
        ]),
        launch_arguments={
            'use_sim_time': LaunchConfiguration('use_sim_time'),
            'rviz': 'false',  # SLAM 建图时不启动 RViz，避免板载计算机负载过高
            'serial_port': LaunchConfiguration('serial_port'),
            'lidar_port': LaunchConfiguration('lidar_port'),
        }.items()
    )

    # 2. SLAM Toolbox 节点（异步模式，适合实时建图）
    slam_toolbox_node = Node(
        package='slam_toolbox',
        executable='async_slam_toolbox_node',
        name='slam_toolbox',
        output='screen',
        parameters=[
            slam_params_file,
            {
                'use_sim_time': LaunchConfiguration('use_sim_time'),
            }
        ],
    )

    return LaunchDescription([
        # 声明参数
        use_sim_time_arg,
        serial_port_arg,
        lidar_port_arg,

        # 启动节点
        base_launch,
        slam_toolbox_node,
    ])
