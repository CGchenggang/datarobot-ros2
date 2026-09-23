#!/usr/bin/env python3
"""
Launch file for DataRobot base driver.

Starts the base_driver_node which controls motors and publishes odometry.
Also starts robot_state_publisher for URDF visualization.
"""

import os
from ament_index_python.packages import get_package_share_path
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition
from launch.substitutions import Command, LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    # Paths. Use the xacro model: the plain datarobot.urdf next to it is an
    # early single-link stub with no wheels and no base_footprint.
    description_package_path = get_package_share_path('datarobot_description')
    xacro_path = os.path.join(description_package_path, 'urdf', 'databot',
                              'datarobot.urdf.xacro')
    rviz_config_path = os.path.join(description_package_path, 'rviz',
                                    'datarobot.rviz')

    # Launch arguments
    use_sim_time_arg = DeclareLaunchArgument(
        'use_sim_time',
        default_value='false',
        choices=['true', 'false'],
        description='Use simulation clock if true'
    )

    serial_port_arg = DeclareLaunchArgument(
        'serial_port',
        default_value='/dev/ttyUSB0',
        description='Serial port for Modbus communication'
    )

    baudrate_arg = DeclareLaunchArgument(
        'baudrate',
        default_value='115200',
        description='Baudrate for serial communication'
    )

    debug_modbus_arg = DeclareLaunchArgument(
        'debug_modbus',
        default_value='false',
        choices=['true', 'false'],
        description='Enable Modbus communication debugging'
    )

    rviz_arg = DeclareLaunchArgument(
        'rviz',
        default_value='true',
        choices=['true', 'false'],
        description='Launch RViz2 with the robot model'
    )

    # Expand the xacro at launch time
    robot_description = ParameterValue(
        Command(['xacro ', xacro_path]), value_type=str)

    # Nodes
    base_driver_node = Node(
        package='datarobot_base',
        executable='base_driver_node.py',
        name='base_driver',
        output='screen',
        parameters=[{
            'use_sim_time': LaunchConfiguration('use_sim_time'),
            'serial_port': LaunchConfiguration('serial_port'),
            'baudrate': LaunchConfiguration('baudrate'),
            'debug_modbus': LaunchConfiguration('debug_modbus'),
            'slave_id': 1,
            'wheel_radius': 0.083,
            'wheel_base': 0.358,
            'gear_ratio': 1.0,
            'max_rpm': 3000,
            'invert_left': False,
            'invert_right': True,
            'publish_rate': 20.0,
            'cmd_vel_timeout': 1.0,
            'base_frame': 'base_footprint',
            'odom_frame': 'odom',
        }]
    )

    robot_state_publisher_node = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        name='robot_state_publisher',
        output='screen',
        parameters=[{
            'use_sim_time': LaunchConfiguration('use_sim_time'),
            'robot_description': robot_description
        }]
    )

    rviz_node = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        output='screen',
        arguments=['-d', rviz_config_path],
        condition=IfCondition(LaunchConfiguration('rviz')),
        parameters=[{'use_sim_time': LaunchConfiguration('use_sim_time')}]
    )

    return LaunchDescription([
        use_sim_time_arg,
        serial_port_arg,
        baudrate_arg,
        debug_modbus_arg,
        rviz_arg,
        base_driver_node,
        robot_state_publisher_node,
        rviz_node,
    ])
