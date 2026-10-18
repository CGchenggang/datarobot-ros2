#!/usr/bin/env python3
"""
仿真导航启动文件（路线 A：已知地图 + AMCL 定位 + Nav2）

前提：
  1. Gazebo 仿真已经在另一个终端跑着（gazebo_jazzy_sim.launch.py），
     本文件不启动 Gazebo，也不碰串口
  2. slam_toolbox 必须已经停止 —— amcl 和 slam_toolbox 都会发布 map->odom，
     同时跑会互相打架，症状是定位乱跳、路径莫名其妙，很容易误判成参数问题

用法（world 参数决定默认地图，与 gazebo_jazzy_sim.launch.py 的 world 对应）：
    ros2 launch datarobot_base nav_sim.launch.py                       # 建筑一层地图
    ros2 launch datarobot_base nav_sim.launch.py world:=room           # 测试房间地图
    ros2 launch datarobot_base nav_sim.launch.py world:=building floor:=2
    ros2 launch datarobot_base nav_sim.launch.py map_file:=/path/x.yaml

跑起来之后，在 RViz 里用 "Nav2 Goal" 发目标；或者用命令行发（不需要 RViz）：

    ros2 action send_goal /navigate_to_pose nav2_msgs/action/NavigateToPose \\
      "{pose: {header: {frame_id: map}, pose: {position: {x: -7.0, y: 0.0, z: 0.0},
        orientation: {w: 1.0}}}}"

与 navigation.launch.py 的区别：那个是给**实机**写的，会 include
bringup_with_lidar.launch.py 去打开 /dev/datarobot_base 和 /dev/LHLiDAR 启动底盘和雷达；
仿真里跑它会去抢串口。本文件只起定位和导航栈。
"""

import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, OpaqueFunction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from nav2_common.launch import RewrittenYaml


def _setup(context, *args, **kwargs):
    base_pkg = get_package_share_directory("datarobot_base")
    nav2_bringup_dir = get_package_share_directory("nav2_bringup")

    nav2_params_file = os.path.join(base_pkg, "config", "nav2_params.yaml")

    world = LaunchConfiguration("world").perform(context)
    floor = LaunchConfiguration("floor").perform(context)
    map_file = LaunchConfiguration("map_file").perform(context)

    # 默认地图 = 随包预建地图（建图产物存 src/datarobot_base/maps/）
    if map_file == "":
        default_map = os.path.join(
            base_pkg, "maps",
            "room.yaml" if world == "room" else f"building_floor{floor}.yaml")
        if not os.path.exists(default_map):
            raise RuntimeError(
                f"随包地图不存在: {default_map}\n"
                "先用 slam_sim.launch.py 建图并 map_saver 保存，"
                "或显式传 map_file:=/path/to/map.yaml")
    else:
        default_map = map_file

    configured_params = RewrittenYaml(
        source_file=nav2_params_file,
        root_key="",
        param_rewrites={
            "use_sim_time": LaunchConfiguration("use_sim_time"),
            "yaml_filename": default_map,
        },
        convert_types=True,
    )

    localization = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(nav2_bringup_dir, "launch", "localization_launch.py")
        ),
        launch_arguments={
            "map": default_map,
            "use_sim_time": LaunchConfiguration("use_sim_time"),
            "autostart": LaunchConfiguration("autostart"),
            "params_file": configured_params,
            "use_composition": "False",
        }.items(),
    )

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

    return [localization, navigation]


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument(
            "world", default_value="building", choices=["room", "building"],
            description="与 gazebo_jazzy_sim.launch.py 的 world 对应，决定默认地图"),
        DeclareLaunchArgument(
            "floor", default_value="1", choices=["1", "2"],
            description="建筑楼层（决定默认地图 building_floorN.yaml）"),
        DeclareLaunchArgument(
            "map_file", default_value="",
            description="地图 yaml 路径；留空则用随包地图"),
        DeclareLaunchArgument(
            "use_sim_time", default_value="true", choices=["true", "false"],
            description="仿真必须为 true。nav2_params.yaml 里默认 false，在此整体覆盖"),
        DeclareLaunchArgument(
            "autostart", default_value="true", choices=["true", "false"],
            description="自动激活 Nav2 的生命周期节点（无 GUI 时必须为 true）"),
        OpaqueFunction(function=_setup),
    ])
