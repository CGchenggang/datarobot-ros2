#!/usr/bin/env python3
"""
Nav2 导航系统启动文件
使用已保存的地图进行自主导航

功能：
- 启动底盘驱动和激光雷达
- 加载已保存的地图
- 启动 AMCL 定位
- 启动完整的 Nav2 导航栈

使用方法：
    # 基本启动（需要先指定地图文件）
    ros2 launch datarobot_base navigation.launch.py map_file:=/home/admin/maps/my_map.yaml

    # 串口默认走 udev 固定名（/dev/datarobot_base、/dev/LHLiDAR），
    # 若还没建 udev 规则，用命令行覆盖成实际设备：
    ros2 launch datarobot_base navigation.launch.py \
      map_file:=/home/admin/maps/my_map.yaml \
      serial_port:=/dev/ttyUSB1 \
      lidar_port:=/dev/ttyUSB0

在 RViz 中操作：
    1. 使用 "2D Pose Estimate" 设置机器人初始位置
    2. 使用 "Nav2 Goal" 设置目标点
    3. 观察机器人自主导航
"""

import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (
    IncludeLaunchDescription,
    DeclareLaunchArgument,
    GroupAction,
)
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node, PushRosNamespace
from nav2_common.launch import RewrittenYaml


def generate_launch_description():
    # 获取功能包路径
    base_package_path = get_package_share_directory('datarobot_base')
    nav2_bringup_dir = get_package_share_directory('nav2_bringup')

    # Nav2 配置文件路径
    nav2_params_file = os.path.join(base_package_path, 'config', 'nav2_params.yaml')

    # 启动参数
    namespace_arg = DeclareLaunchArgument(
        'namespace',
        default_value='',
        description='命名空间'
    )

    use_sim_time_arg = DeclareLaunchArgument(
        'use_sim_time',
        default_value='false',
        choices=['true', 'false'],
        description='使用仿真时间'
    )

    map_file_arg = DeclareLaunchArgument(
        'map_file',
        default_value='',
        description='地图文件路径（必需，例如：/home/admin/maps/my_map.yaml）'
    )

    autostart_arg = DeclareLaunchArgument(
        'autostart',
        default_value='true',
        choices=['true', 'false'],
        description='自动启动生命周期节点'
    )

    # 端口默认值用 udev 固定名（见 config/udev/99-datarobot.rules）
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

    use_composition_arg = DeclareLaunchArgument(
        'use_composition',
        default_value='false',
        description='使用组合节点'
    )

    use_respawn_arg = DeclareLaunchArgument(
        'use_respawn',
        default_value='false',
        description='节点崩溃后自动重启'
    )

    # 配置变量
    namespace = LaunchConfiguration('namespace')
    use_sim_time = LaunchConfiguration('use_sim_time')
    map_yaml_file = LaunchConfiguration('map_file')
    autostart = LaunchConfiguration('autostart')
    use_composition = LaunchConfiguration('use_composition')
    use_respawn = LaunchConfiguration('use_respawn')

    # 重写参数文件（注入运行时配置）
    param_substitutions = {
        'use_sim_time': use_sim_time,
        'yaml_filename': map_yaml_file,
    }

    configured_params = RewrittenYaml(
        source_file=nav2_params_file,
        root_key=namespace,
        param_rewrites=param_substitutions,
        convert_types=True
    )

    # 1. 启动底盘和雷达
    base_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            PathJoinSubstitution([
                base_package_path,
                'launch',
                'bringup_with_lidar.launch.py'
            ])
        ]),
        launch_arguments={
            'use_sim_time': use_sim_time,
            'rviz': 'false',  # 导航时不自动启动 RViz
            'serial_port': LaunchConfiguration('serial_port'),
            'lidar_port': LaunchConfiguration('lidar_port'),
        }.items()
    )

    # 2. Nav2 定位和导航栈
    # 使用 nav2_bringup 的标准启动文件
    nav2_bringup_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            PathJoinSubstitution([
                nav2_bringup_dir,
                'launch',
                'localization_launch.py'
            ])
        ]),
        launch_arguments={
            'namespace': namespace,
            'map': map_yaml_file,
            'use_sim_time': use_sim_time,
            'autostart': autostart,
            'params_file': configured_params,
            'use_composition': use_composition,
            'use_respawn': use_respawn,
        }.items()
    )

    nav2_navigation_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            PathJoinSubstitution([
                nav2_bringup_dir,
                'launch',
                'navigation_launch.py'
            ])
        ]),
        launch_arguments={
            'namespace': namespace,
            'use_sim_time': use_sim_time,
            'autostart': autostart,
            'params_file': configured_params,
            'use_composition': use_composition,
            'use_respawn': use_respawn,
        }.items()
    )

    return LaunchDescription([
        # 声明参数
        namespace_arg,
        use_sim_time_arg,
        map_file_arg,
        autostart_arg,
        serial_port_arg,
        lidar_port_arg,
        use_composition_arg,
        use_respawn_arg,

        # 启动节点
        base_launch,
        nav2_bringup_launch,
        nav2_navigation_launch,
    ])
