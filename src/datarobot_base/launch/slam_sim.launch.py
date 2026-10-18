#!/usr/bin/env python3
"""
SLAM 建图启动文件（Gazebo 仿真专用）
使用 slam_toolbox 进行 2D 激光 SLAM

功能：
- 启动 SLAM Toolbox 并自动激活生命周期节点
- 使用 Gazebo 仿真提供的 /scan 和 /odom 数据
- 适用于 Gazebo 仿真环境测试

使用方法：
    ros2 launch datarobot_base slam_sim.launch.py

建图完成后保存地图：
    mkdir -p ~/maps
    ros2 run nav2_map_server map_saver_cli -f ~/maps/my_map
"""

import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, RegisterEventHandler, EmitEvent
from launch.event_handlers import OnProcessStart
from launch.events import matches_action
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node, LifecycleNode
from launch_ros.events.lifecycle import ChangeState
from launch_ros.event_handlers import OnStateTransition
import lifecycle_msgs.msg


def generate_launch_description():
    # 获取功能包路径
    base_package_path = get_package_share_directory('datarobot_base')

    # SLAM 配置文件路径
    slam_params_file = os.path.join(base_package_path, 'config', 'slam_params.yaml')

    # 启动参数
    use_sim_time_arg = DeclareLaunchArgument(
        'use_sim_time',
        default_value='true',
        choices=['true', 'false'],
        description='使用仿真时间'
    )

    # SLAM Toolbox 生命周期节点（异步模式，适合实时建图）
    slam_toolbox_node = LifecycleNode(
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
        namespace=''
    )

    # 当 SLAM Toolbox 启动后，自动发送 configure 事件
    configure_event = EmitEvent(
        event=ChangeState(
            lifecycle_node_matcher=matches_action(slam_toolbox_node),
            transition_id=lifecycle_msgs.msg.Transition.TRANSITION_CONFIGURE,
        )
    )

    # 注册事件处理器：当节点启动时自动 configure
    slam_configure_handler = RegisterEventHandler(
        OnProcessStart(
            target_action=slam_toolbox_node,
            on_start=[configure_event]
        )
    )

    # 当 configure 成功后，自动发送 activate 事件
    activate_event = EmitEvent(
        event=ChangeState(
            lifecycle_node_matcher=matches_action(slam_toolbox_node),
            transition_id=lifecycle_msgs.msg.Transition.TRANSITION_ACTIVATE,
        )
    )

    # 注册事件处理器：当 configure 成功时自动 activate
    slam_activate_handler = RegisterEventHandler(
        OnStateTransition(
            target_lifecycle_node=slam_toolbox_node,
            start_state='configuring',
            goal_state='inactive',
            entities=[activate_event]
        )
    )

    return LaunchDescription([
        # 声明参数
        use_sim_time_arg,

        # 启动节点和事件处理器
        slam_toolbox_node,
        slam_configure_handler,
        slam_activate_handler,
    ])
