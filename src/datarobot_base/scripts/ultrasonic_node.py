#!/usr/bin/env python3
"""超声波接口节点：把仿真/实机的超声波测距统一成标准 ROS 接口。

输入：每个超声波一路 LaserScan（仿真 = 窄波束 gpu_lidar 桥接；
      实机 = 单片机采集 HC-SR04 后由串口驱动发布的单点 LaserScan，接口一致）
输出：每个超声波一路 sensor_msgs/Range（/us/<name>，辐射类型=ULTRASOUND，
      视场角/量程与器件一致）+ 一路融合 PointCloud2（/us/cloud，base_link 系）

PointCloud2 供 Nav2 代价地图做障碍标记：单束测距按安装位姿投影成
base_link 系下的一个点，六个探头合成一帧。安装位姿通过参数下发，
与 URDF 中 ultrasonic_xacro 的 xyz/yaw 一一对应（见 gazebo_jazzy_sim.launch.py）。
"""

import math

import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from nav_msgs.msg import Odometry
from sensor_msgs.msg import LaserScan, PointCloud2, PointField, Range
from std_msgs.msg import Header

try:  # Humble/Jazzy 都带 sensor_msgs.point_cloud2；Kilted 起移到 sensor_msgs_py
    from sensor_msgs.point_cloud2 import create_cloud
except ImportError:  # pragma: no cover
    from sensor_msgs_py.point_cloud2 import create_cloud

_XYZ_FIELDS = [
    PointField(name='x', offset=0, datatype=PointField.FLOAT32, count=1),
    PointField(name='y', offset=4, datatype=PointField.FLOAT32, count=1),
    PointField(name='z', offset=8, datatype=PointField.FLOAT32, count=1),
]


class UltrasonicNode(Node):
    def __init__(self):
        super().__init__('ultrasonic_node')

        self.declare_parameter('base_frame', 'base_link')
        self.declare_parameter('cloud_topic', '/us/cloud')
        self.declare_parameter('field_of_view', 0.26)  # HC-SR04 有效角度 ~15°
        self.declare_parameter('range_min', 0.03)
        self.declare_parameter('range_max', 4.0)
        self.declare_parameter(
            'sensor_names',
            ['us_front', 'us_front_left', 'us_front_right',
             'us_left', 'us_right', 'us_rear'])

        self.base_frame = self.get_parameter('base_frame').value
        self.fov = float(self.get_parameter('field_of_view').value)
        self.range_min = float(self.get_parameter('range_min').value)
        self.range_max = float(self.get_parameter('range_max').value)

        self.sensors = {}
        for name in self.get_parameter('sensor_names').value:
            self.declare_parameter(f'{name}.topic', f'/us/{name}/scan')
            self.declare_parameter(f'{name}.frame', f'{name}_link')
            self.declare_parameter(f'{name}.x', 0.0)
            self.declare_parameter(f'{name}.y', 0.0)
            self.declare_parameter(f'{name}.z', -0.13)
            self.declare_parameter(f'{name}.yaw', 0.0)
            cfg = {
                'topic': self.get_parameter(f'{name}.topic').value,
                'frame': self.get_parameter(f'{name}.frame').value,
                'x': float(self.get_parameter(f'{name}.x').value),
                'y': float(self.get_parameter(f'{name}.y').value),
                'z': float(self.get_parameter(f'{name}.z').value),
                'yaw': float(self.get_parameter(f'{name}.yaw').value),
                'range': None,
                'pub': self.create_publisher(Range, f'/us/{name}', 10),
            }
            self.sensors[name] = cfg
            self.create_subscription(
                LaserScan, cfg['topic'],
                (lambda n: lambda msg: self.scan_cb(n, msg))(name),
                qos_profile_sensor_data)

        self.cloud_pub = self.create_publisher(
            PointCloud2, self.get_parameter('cloud_topic').value, 10)
        # 10 Hz 与探头同拍发布融合点云
        self.cloud_timer = self.create_timer(0.1, self.cloud_cb)
        # 角速度门控：转身时位姿时间戳滞后会把测距点涂成弧形幻影墙
        # （代价图上表现为障碍物"发福"/扇形污染），旋转期间不出点
        self.declare_parameter('max_mark_ang_vel', 0.25)
        self.max_mark_ang_vel = float(self.get_parameter('max_mark_ang_vel').value)
        self.ang_vel = 0.0
        self.create_subscription(Odometry, '/odom', self.odom_cb, qos_profile_sensor_data)

        names = ', '.join(self.sensors)
        self.get_logger().info(f'超声波接口节点就绪: {names} → /us/<name> + /us/cloud')

    def scan_cb(self, name, msg):
        cfg = self.sensors[name]
        # 取波束内最近的有效回波；inf/nan = 无回波
        valid = [r for r in msg.ranges
                 if math.isfinite(r) and self.range_min <= r <= self.range_max]
        rng = min(valid) if valid else float('inf')
        cfg['range'] = rng

        out = Range()
        out.header.stamp = msg.header.stamp
        out.header.frame_id = cfg['frame']
        out.radiation_type = Range.ULTRASOUND
        out.field_of_view = self.fov
        out.min_range = self.range_min
        out.max_range = self.range_max
        out.range = rng if math.isfinite(rng) else self.range_max
        cfg['pub'].publish(out)

    def odom_cb(self, msg):
        self.ang_vel = abs(msg.twist.twist.angular.z)

    def cloud_cb(self):
        header = Header()
        header.stamp = self.get_clock().now().to_msg()
        header.frame_id = self.base_frame
        if self.ang_vel > self.max_mark_ang_vel:
            self.cloud_pub.publish(create_cloud(header, _XYZ_FIELDS, []))
            return
        points = []
        for cfg in self.sensors.values():
            rng = cfg['range']
            if rng is None or not math.isfinite(rng):
                continue  # 无回波：不出点（不标记、也不清除）
            points.append((
                float(cfg['x'] + rng * math.cos(cfg['yaw'])),
                float(cfg['y'] + rng * math.sin(cfg['yaw'])),
                float(cfg['z'])))
        # Jazzy 的 sensor_msgs_py.create_cloud 接受 (x, y, z) 元组序列
        self.cloud_pub.publish(create_cloud(header, _XYZ_FIELDS, points))


def main(args=None):
    rclpy.init(args=args)
    node = UltrasonicNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
