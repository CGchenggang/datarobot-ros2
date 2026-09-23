#!/usr/bin/env python3
"""
DataRobot 完整系统启动文件
支持灵活选择启动的模块：底盘驱动、激光雷达、URDF 模型、RViz

使用示例：
    # 启动所有模块（默认）
    ros2 launch datarobot_base bringup_with_lidar.launch.py

    # 只启动底盘和雷达，不开 RViz
    ros2 launch datarobot_base bringup_with_lidar.launch.py rviz:=false

    # 只启动雷达和模型，不启动底盘（调试雷达时）
    ros2 launch datarobot_base bringup_with_lidar.launch.py base:=false

    # 只启动模型查看器，不需要硬件
    ros2 launch datarobot_base bringup_with_lidar.launch.py base:=false lidar:=false
"""

import os
from ament_index_python.packages import get_package_share_path
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition
from launch.substitutions import Command, LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    # ========== 路径配置 ==========
    # 获取功能包路径
    description_package_path = get_package_share_path('datarobot_description')
    base_package_path = get_package_share_path('datarobot_base')
    bluesea_package_path = get_package_share_path('bluesea2')

    # URDF 模型文件路径（使用 xacro 格式，会在启动时动态生成）
    xacro_path = os.path.join(description_package_path, 'urdf', 'databot',
                              'datarobot.urdf.xacro')

    # RViz 配置文件路径
    rviz_config_path = os.path.join(description_package_path, 'rviz',
                                    'datarobot.rviz')

    # 底盘驱动配置文件（暂未使用，参数直接写在 launch 中）
    # base_config_path = os.path.join(base_package_path, 'config', 'base_driver.yaml')

    # 激光雷达配置文件
    lidar_config_path = os.path.join(base_package_path, 'config', 'lidar.yaml')

    # ========== 启动参数声明 ==========
    # 这些参数可以在启动时通过命令行覆盖，例如：rviz:=false

    # 是否使用仿真时间（Gazebo 仿真时需要设为 true）
    use_sim_time_arg = DeclareLaunchArgument(
        'use_sim_time',
        default_value='false',
        choices=['true', 'false'],
        description='使用仿真时钟（Gazebo 仿真时设为 true）'
    )

    # 是否启动底盘驱动节点
    base_arg = DeclareLaunchArgument(
        'base',
        default_value='true',
        choices=['true', 'false'],
        description='启动底盘驱动节点（需要连接底盘硬件）'
    )

    # 是否启动激光雷达节点
    lidar_arg = DeclareLaunchArgument(
        'lidar',
        default_value='true',
        choices=['true', 'false'],
        description='启动激光雷达驱动节点（需要连接雷达硬件）'
    )

    # 是否启动 RViz 可视化
    rviz_arg = DeclareLaunchArgument(
        'rviz',
        default_value='true',
        choices=['true', 'false'],
        description='启动 RViz2 可视化界面'
    )

    # 底盘串口设备路径
    serial_port_arg = DeclareLaunchArgument(
        'serial_port',
        default_value='/dev/ttyUSB0',
        description='底盘驱动器的串口设备路径'
    )

    # 底盘串口波特率
    baudrate_arg = DeclareLaunchArgument(
        'baudrate',
        default_value='115200',
        description='底盘串口通信波特率'
    )

    # 是否打印 Modbus 通信调试信息
    debug_modbus_arg = DeclareLaunchArgument(
        'debug_modbus',
        default_value='false',
        choices=['true', 'false'],
        description='打印 Modbus 收发帧（调试底盘通信时使用）'
    )

    # 激光雷达串口设备路径
    lidar_port_arg = DeclareLaunchArgument(
        'lidar_port',
        default_value='/dev/ttyUSB0',
        description='激光雷达的串口设备路径（通常与底盘不同）'
    )

    # ========== 机器人模型描述 ==========
    # 在启动时动态处理 xacro 文件，生成完整的 URDF
    robot_description = ParameterValue(
        Command(['xacro ', xacro_path]), value_type=str)

    # ========== 节点配置 ==========

    # 1. 底盘驱动节点
    # 功能：通过 Modbus 控制底盘电机，发布里程计和 TF
    base_driver_node = Node(
        package='datarobot_base',
        executable='base_driver_node.py',
        name='base_driver',
        output='screen',
        condition=IfCondition(LaunchConfiguration('base')),  # 仅当 base:=true 时启动
        parameters=[{
            'use_sim_time': LaunchConfiguration('use_sim_time'),
            'serial_port': LaunchConfiguration('serial_port'),
            'baudrate': LaunchConfiguration('baudrate'),
            'debug_modbus': LaunchConfiguration('debug_modbus'),

            # 硬件参数
            'slave_id': 1,              # Modbus 从站 ID
            'wheel_radius': 0.083,      # 轮子半径（米）
            'wheel_base': 0.358,        # 轮距（米）
            'gear_ratio': 1.0,          # 齿轮比（未标定，见 ROADMAP.md）
            'max_rpm': 3000,            # 最大转速

            # 电机方向
            'invert_left': False,       # 左轮是否反向
            'invert_right': True,       # 右轮反向（镜像安装）

            # 控制参数
            'publish_rate': 5.0,       # 控制循环频率（Hz）
            'cmd_vel_timeout': 1.0,     # 速度命令超时时间（秒）

            # 坐标系名称
            'base_frame': 'base_footprint',
            'odom_frame': 'odom',
        }]
    )

    # 2. 激光雷达驱动节点
    # 功能：连接 BlueSeaLidar，发布 LaserScan 消息到 /scan 话题
    lidar_node = Node(
        package='bluesea2',
        executable='bluesea2_node',
        name='bluesea_lidar',
        output='screen',
        condition=IfCondition(LaunchConfiguration('lidar')),  # 仅当 lidar:=true 时启动
        parameters=[
            lidar_config_path,  # 加载配置文件
            {
                'use_sim_time': LaunchConfiguration('use_sim_time'),
                # 覆盖配置文件中的串口路径（允许命令行参数覆盖）
                'port': LaunchConfiguration('lidar_port'),
            }
        ]
    )

    # 3. 机器人状态发布节点
    # 功能：根据 URDF 和 joint_states 发布机器人各部件的 TF 变换
    # 注意：这个节点不需要硬件，只要有模型就能运行
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

    # 4. RViz 可视化节点
    # 功能：显示机器人模型、激光扫描数据、TF 树等
    rviz_node = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        output='screen',
        arguments=['-d', rviz_config_path],
        condition=IfCondition(LaunchConfiguration('rviz')),  # 仅当 rviz:=true 时启动
        parameters=[{'use_sim_time': LaunchConfiguration('use_sim_time')}]
    )

    # ========== 返回 LaunchDescription ==========
    return LaunchDescription([
        # 声明所有启动参数
        use_sim_time_arg,
        base_arg,
        lidar_arg,
        rviz_arg,
        serial_port_arg,
        baudrate_arg,
        debug_modbus_arg,
        lidar_port_arg,

        # 启动所有节点
        base_driver_node,
        lidar_node,
        robot_state_publisher_node,
        rviz_node,
    ])
