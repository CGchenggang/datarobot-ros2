#!/usr/bin/env python3
"""
修正激光雷达 frame_id 的节点
从 /scan_raw 读取数据，修正 frame_id 后发布到 /scan
"""

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import LaserScan


class LaserFrameFixer(Node):
    def __init__(self):
        super().__init__('laser_frame_fixer')
        
        # 订阅原始扫描数据
        self.subscription = self.create_subscription(
            LaserScan,
            '/scan_raw',
            self.scan_callback,
            10
        )
        
        # 发布修正后的扫描数据
        self.publisher = self.create_publisher(LaserScan, '/scan', 10)
        
        self.get_logger().info('激光雷达 frame_id 修正节点已启动')
    
    def scan_callback(self, msg):
        # 创建新消息，修正 frame_id
        fixed_msg = LaserScan()
        fixed_msg.header.stamp = msg.header.stamp
        fixed_msg.header.frame_id = 'laser_link'  # 修正为正确的 frame_id
        fixed_msg.angle_min = msg.angle_min
        fixed_msg.angle_max = msg.angle_max
        fixed_msg.angle_increment = msg.angle_increment
        fixed_msg.time_increment = msg.time_increment
        fixed_msg.scan_time = msg.scan_time
        fixed_msg.range_min = msg.range_min
        fixed_msg.range_max = msg.range_max
        fixed_msg.ranges = msg.ranges
        fixed_msg.intensities = msg.intensities
        
        # 发布修正后的消息
        self.publisher.publish(fixed_msg)


def main(args=None):
    rclpy.init(args=args)
    node = LaserFrameFixer()
    
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
