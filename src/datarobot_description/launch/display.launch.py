"""Model-only viewer: robot_state_publisher + joint_state_publisher_gui + RViz.

No hardware needed. Use this to check the URDF geometry and drag the wheel
joints by hand. For the real robot use datarobot_base/bringup.launch.py.
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
    package_path = get_package_share_path('datarobot_description')
    xacro_path = os.path.join(package_path, 'urdf', 'databot',
                              'datarobot.urdf.xacro')
    rviz_config_path = os.path.join(package_path, 'rviz', 'datarobot.rviz')

    rviz_arg = DeclareLaunchArgument(
        'rviz',
        default_value='true',
        choices=['true', 'false'],
        description='Launch RViz2'
    )

    robot_description = ParameterValue(
        Command(['xacro ', xacro_path]), value_type=str)

    return LaunchDescription([
        rviz_arg,

        Node(
            package='robot_state_publisher',
            executable='robot_state_publisher',
            parameters=[{'robot_description': robot_description}],
            output='screen'
        ),

        # Supplies joint_states by hand. Do not run this alongside the base
        # driver, which publishes joint_states from the real encoders.
        Node(
            package='joint_state_publisher_gui',
            executable='joint_state_publisher_gui',
            output='screen'
        ),

        Node(
            package='rviz2',
            executable='rviz2',
            name='rviz2',
            arguments=['-d', rviz_config_path],
            condition=IfCondition(LaunchConfiguration('rviz')),
            output='screen'
        ),
    ])
