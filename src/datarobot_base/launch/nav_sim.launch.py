#!/usr/bin/env python3
"""
仿真导航启动文件（路线 A：已知地图 + AMCL 定位 + Nav2）

前提：
  1. Gazebo 仿真已经在另一个终端跑着（gazebo_jazzy_sim.launch.py），
     本文件不启动 Gazebo，也不碰串口
  2. slam_toolbox 必须已经停止 —— amcl 和 slam_toolbox 都会发布 map->odom，
     同时跑会互相打架，症状是定位乱跳、路径莫名其妙，很容易误判成参数问题

用法：
    ros2 launch datarobot_base nav_sim.launch.py
    ros2 launch datarobot_base nav_sim.launch.py map_file:=/home/admin/maps/my_map.yaml

跑起来之后，在 RViz 里用 "2D Pose Estimate" 设初始位姿，再用 "Nav2 Goal" 发目标；
或者用命令行发（不需要 RViz）：

    ros2 action send_goal /navigate_to_pose nav2_msgs/action/NavigateToPose \\
      "{pose: {header: {frame_id: map}, pose: {position: {x: 2.0, y: 0.0, z: 0.0},
        orientation: {w: 1.0}}}}"

与 navigation.launch.py 的区别：那个是给**实机**写的，会 include
bringup_with_lidar.launch.py 去打开 /dev/ttyUSB1 和 /dev/ttyUSB0 启动底盘和雷达；
仿真里跑它会去抢串口。本文件只起定位和导航栈。
"""

import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from nav2_common.launch import RewrittenYaml


def generate_launch_description():
    base_pkg = get_package_share_directory("datarobot_base")
    nav2_bringup_dir = get_package_share_directory("nav2_bringup")

    nav2_params_file = os.path.join(base_pkg, "config", "nav2_params.yaml")
    default_map = os.path.join(os.path.expanduser("~"), "maps", "my_map.yaml")

    map_file_arg = DeclareLaunchArgument(
        "map_file",
        default_value=default_map,
        description="地图 yaml 路径（默认 ~/maps/my_map.yaml）"
    )

    use_sim_time_arg = DeclareLaunchArgument(
        "use_sim_time",
        default_value="true",
        choices=["true", "false"],
        description="仿真必须为 true。本文件默认已是 true，"
                    "因为 nav2_params.yaml 里写的是 false，需要在此覆盖掉"
    )

    autostart_arg = DeclareLaunchArgument(
        "autostart",
        default_value="true",
        choices=["true", "false"],
        description="自动激活 Nav2 的生命周期节点（无 GUI 时必须为 true）"
    )

    # 把 use_sim_time 和地图路径注入参数文件
    # nav2_params.yaml 里 13 处 use_sim_time 都写的是 false，仿真必须整体覆盖
    configured_params = RewrittenYaml(
        source_file=nav2_params_file,
        root_key="",
        param_rewrites={
            "use_sim_time": LaunchConfiguration("use_sim_time"),
            "yaml_filename": LaunchConfiguration("map_file"),
        },
        convert_types=True,
    )

    # 1. 定位：map_server（发布 /map）+ amcl（发布 map->odom）
    localization = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(nav2_bringup_dir, "launch", "localization_launch.py")
        ),
        launch_arguments={
            "map": LaunchConfiguration("map_file"),
            "use_sim_time": LaunchConfiguration("use_sim_time"),
            "autostart": LaunchConfiguration("autostart"),
            "params_file": configured_params,
            "use_composition": "False",
        }.items(),
    )

    # 2. 导航栈：planner / controller / bt_navigator / behaviors / smoother ...
    navigation = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(nav2_bringup_dir, "launch", "navigation_launch.py")
        ),
        launch_arguments={
            "use_sim_time": LaunchConfiguration("use_sim_time"),
            "autostart": LaunchConfiguration("autostart"),
            "params_file": configured_params,
            "use_composition": "False",
        }.items(),
    )

    return LaunchDescription([
        map_file_arg,
        use_sim_time_arg,
        autostart_arg,
        localization,
        navigation,
    ])
