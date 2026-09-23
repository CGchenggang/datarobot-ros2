#!/usr/bin/env python3
"""
DataRobot Gazebo 仿真启动文件
用于在没有实际硬件的情况下测试系统

功能：
- 在 Gazebo 中生成机器人模型
- 启动差速驱动控制器（模拟底盘）
- 启动激光雷达仿真（模拟扫描数据）
- 可以用 /cmd_vel 控制，发布 /odom 和 /scan

使用方法：
    ros2 launch datarobot_base gazebo_sim.launch.py

    # 在另一个终端控制机器人
    ros2 topic pub --rate 10 /cmd_vel geometry_msgs/msg/Twist \
      "{linear: {x: 0.2}, angular: {z: 0.0}}"
"""

import os
from ament_index_python.packages import get_package_share_path
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import Command, LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    # ========== 路径配置 ==========
    description_package_path = get_package_share_path('datarobot_description')

    # URDF 模型文件
    xacro_path = os.path.join(description_package_path, 'urdf', 'databot',
                              'datarobot.urdf.xacro')

    # RViz 配置文件
    rviz_config_path = os.path.join(description_package_path, 'rviz',
                                    'datarobot.rviz')

    # ========== 启动参数 ==========

    # Gazebo 仿真世界文件（可选，默认空世界）
    world_arg = DeclareLaunchArgument(
        'world',
        default_value='',
        description='Gazebo world 文件路径（为空则使用默认空世界）'
    )

    # 是否启动 RViz
    rviz_arg = DeclareLaunchArgument(
        'rviz',
        default_value='true',
        choices=['true', 'false'],
        description='启动 RViz2 可视化'
    )

    # ========== 机器人描述 ==========
    # 仿真模式下使用仿真时间
    robot_description = ParameterValue(
        Command(['xacro ', xacro_path, ' use_sim_time:=true']),
        value_type=str
    )

    # ========== 节点配置 ==========

    # 1. 启动 Gazebo 仿真器
    # 注意：需要先安装 ros-humble-gazebo-ros-pkgs
    gazebo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            PathJoinSubstitution([
                get_package_share_path('gazebo_ros'),
                'launch',
                'gazebo.launch.py'
            ])
        ]),
        launch_arguments={
            'world': LaunchConfiguration('world'),
            'verbose': 'false'
        }.items()
    )

    # 2. 在 Gazebo 中生成机器人
    spawn_robot = Node(
        package='gazebo_ros',
        executable='spawn_entity.py',
        name='spawn_datarobot',
        output='screen',
        arguments=[
            '-topic', 'robot_description',
            '-entity', 'datarobot',
            '-x', '0.0',
            '-y', '0.0',
            '-z', '0.1',
        ]
    )

    # 3. 机器人状态发布节点
    robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        name='robot_state_publisher',
        output='screen',
        parameters=[{
            'use_sim_time': True,
            'robot_description': robot_description
        }]
    )

    # 4. 关节状态发布节点（Gazebo 会通过插件发布，这里可能不需要）
    # 如果 URDF 中配置了 gazebo_ros_joint_state_publisher 插件就不需要这个节点

    # 5. RViz 可视化
    rviz = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        output='screen',
        arguments=['-d', rviz_config_path],
        parameters=[{'use_sim_time': True}],
        condition=IfCondition(LaunchConfiguration('rviz'))
    )

    return LaunchDescription([
        # 声明参数
        world_arg,
        rviz_arg,

        # 启动节点
        gazebo,
        robot_state_publisher,
        spawn_robot,
        rviz,
    ])
