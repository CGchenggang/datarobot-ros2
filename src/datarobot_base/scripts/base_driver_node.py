#!/usr/bin/env python3
"""
ROS2 base driver node for DataRobot.

Subscribes to /cmd_vel and controls motors via Modbus.
Publishes /odom and /tf (odom -> base_footprint).
"""

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy
from geometry_msgs.msg import Twist, TransformStamped, Quaternion
from nav_msgs.msg import Odometry
from sensor_msgs.msg import JointState
from tf2_ros import TransformBroadcaster
import math
import time

from datarobot_base.modbus_controller import ModbusController
from datarobot_base.diff_drive_controller import DiffDriveController


class BaseDriverNode(Node):
    """ROS2 node for DataRobot base control."""

    def __init__(self):
        super().__init__('base_driver')

        # Declare parameters
        self.declare_parameter('serial_port', '/dev/ttyUSB0')
        self.declare_parameter('baudrate', 115200)
        self.declare_parameter('slave_id', 1)
        self.declare_parameter('wheel_radius', 0.083)  # meters
        self.declare_parameter('wheel_base', 0.358)    # meters
        self.declare_parameter('gear_ratio', 1.0)
        self.declare_parameter('max_rpm', 3000)
        self.declare_parameter('publish_rate', 20.0)   # Hz - bounded by serial link
        self.declare_parameter('cmd_vel_timeout', 1.0)  # seconds
        self.declare_parameter('base_frame', 'base_footprint')
        self.declare_parameter('odom_frame', 'odom')
        self.declare_parameter('debug_modbus', False)  # Enable Modbus debug output
        self.declare_parameter('invert_left', False)   # Negate A axis command
        self.declare_parameter('invert_right', True)   # Negate B axis (mirror-mounted)

        # Get parameters
        serial_port = self.get_parameter('serial_port').value
        baudrate = self.get_parameter('baudrate').value
        slave_id = self.get_parameter('slave_id').value
        wheel_radius = self.get_parameter('wheel_radius').value
        wheel_base = self.get_parameter('wheel_base').value
        gear_ratio = self.get_parameter('gear_ratio').value
        max_rpm = self.get_parameter('max_rpm').value
        self.publish_rate = self.get_parameter('publish_rate').value
        self.cmd_vel_timeout = self.get_parameter('cmd_vel_timeout').value
        self.base_frame = self.get_parameter('base_frame').value
        self.odom_frame = self.get_parameter('odom_frame').value
        self.debug_modbus = self.get_parameter('debug_modbus').value
        invert_left = self.get_parameter('invert_left').value
        invert_right = self.get_parameter('invert_right').value

        # Initialize controllers
        self.modbus = ModbusController(serial_port, baudrate, slave_id, logger=self.get_logger())
        self.diff_drive = DiffDriveController(wheel_radius, wheel_base,
                                              gear_ratio, max_rpm,
                                              invert_left, invert_right)

        # Connect to hardware
        if not self.modbus.connect():
            self.get_logger().error(f'Failed to connect to {serial_port}')
            raise RuntimeError('Cannot connect to motor controller')

        self.get_logger().info(f'Connected to motor controller on {serial_port}')
        # Enable write-only mode (skip reading responses due to communication issues)
        self.modbus.set_write_only(True)

        # Enable motors
        if self.modbus.enable_motors(True, debug=self.debug_modbus):
            self.get_logger().info('Motors enabled')
        else:
            self.modbus.disconnect()
            raise RuntimeError(
                'Failed to enable motors - check RS485 wiring, driver power '
                'and slave_id')

        # QoS profile for cmd_vel (match default for teleop)
        cmd_vel_qos = QoSProfile(
            reliability=ReliabilityPolicy.RELIABLE,
            history=HistoryPolicy.KEEP_LAST,
            depth=10
        )

        # Publishers
        self.odom_pub = self.create_publisher(Odometry, 'odom', 10)
        self.joint_state_pub = self.create_publisher(JointState, 'joint_states', 10)
        self.tf_broadcaster = TransformBroadcaster(self)

        # Subscriber
        self.cmd_vel_sub = self.create_subscription(
            Twist, 'cmd_vel', self.cmd_vel_callback, cmd_vel_qos)

        # State variables
        self.last_cmd_vel_time = self.get_clock().now()
        self.target_linear = 0.0
        self.target_angular = 0.0
        self.last_update_time = time.time()

        # Joint angles for visualization (fake spinning wheels)
        self.left_wheel_angle = 0.0
        self.right_wheel_angle = 0.0

        # Modbus write statistics, reported with the failure warning
        self.write_ok = 0
        self.write_fail = 0

        # Create timer for control loop
        timer_period = 1.0 / self.publish_rate
        self.timer = self.create_timer(timer_period, self.control_loop)

        self.get_logger().info('Base driver node started')

    def cmd_vel_callback(self, msg: Twist):
        """Handle incoming velocity commands."""
        self.target_linear = msg.linear.x
        self.target_angular = msg.angular.z
        self.last_cmd_vel_time = self.get_clock().now()

    def control_loop(self):
        """Main control loop - runs at publish_rate Hz."""
        current_time = self.get_clock().now()
        dt = time.time() - self.last_update_time
        self.last_update_time = time.time()

        # Check for cmd_vel timeout
        time_since_cmd = (current_time - self.last_cmd_vel_time).nanoseconds / 1e9
        if time_since_cmd > self.cmd_vel_timeout:
            self.target_linear = 0.0
            self.target_angular = 0.0

        # Convert cmd_vel to wheel speeds
        left_rpm, right_rpm = self.diff_drive.cmd_vel_to_wheel_speeds(
            self.target_linear, self.target_angular)

        # Send speed command to motors
        if self.modbus.set_motor_speeds(left_rpm, right_rpm, debug=self.debug_modbus):
            self.write_ok += 1
        else:
            self.write_fail += 1
            self.get_logger().warn(
                f'Failed to set motor speeds '
                f'({self.write_fail} of {self.write_ok + self.write_fail} writes)',
                throttle_duration_sec=5.0)

        # Read actual speeds from motors
        speeds = self.modbus.get_motor_speeds()
        if speeds:
            actual_left_rpm, actual_right_rpm = speeds

            # Update odometry
            linear_vel, angular_vel = self.diff_drive.update_odometry(
                actual_left_rpm, actual_right_rpm, dt)

            # Get current pose
            x, y, theta = self.diff_drive.get_pose()

            # Update wheel angles for joint_states (visualization only).
            # Use the wheel RPM in ROS convention that update_odometry stored,
            # not the raw driver values, so the right wheel spins the right way.
            left_wheel_omega = self.diff_drive.last_left_rpm * (2.0 * math.pi) / 60.0
            right_wheel_omega = self.diff_drive.last_right_rpm * (2.0 * math.pi) / 60.0
            self.left_wheel_angle += left_wheel_omega * dt
            self.right_wheel_angle += right_wheel_omega * dt

            # Publish odometry
            self.publish_odometry(x, y, theta, linear_vel, angular_vel, current_time)

            # Publish TF
            self.publish_tf(x, y, theta, current_time)

            # Publish joint states
            self.publish_joint_states(current_time)

    def publish_odometry(self, x: float, y: float, theta: float,
                        vx: float, vth: float, timestamp):
        """Publish odometry message."""
        odom = Odometry()
        odom.header.stamp = timestamp.to_msg()
        odom.header.frame_id = self.odom_frame
        odom.child_frame_id = self.base_frame

        # Position
        odom.pose.pose.position.x = x
        odom.pose.pose.position.y = y
        odom.pose.pose.position.z = 0.0

        # Orientation (quaternion from yaw)
        quat = self.quaternion_from_yaw(theta)
        odom.pose.pose.orientation = quat

        # Velocity
        odom.twist.twist.linear.x = vx
        odom.twist.twist.linear.y = 0.0
        odom.twist.twist.angular.z = vth

        # Covariance (simple diagonal values)
        odom.pose.covariance[0] = 0.01   # x
        odom.pose.covariance[7] = 0.01   # y
        odom.pose.covariance[35] = 0.05  # theta

        odom.twist.covariance[0] = 0.01   # vx
        odom.twist.covariance[7] = 0.01   # vy
        odom.twist.covariance[35] = 0.05  # vth

        self.odom_pub.publish(odom)

    def publish_tf(self, x: float, y: float, theta: float, timestamp):
        """Publish odom -> base_footprint transform."""
        t = TransformStamped()
        t.header.stamp = timestamp.to_msg()
        t.header.frame_id = self.odom_frame
        t.child_frame_id = self.base_frame

        t.transform.translation.x = x
        t.transform.translation.y = y
        t.transform.translation.z = 0.0

        quat = self.quaternion_from_yaw(theta)
        t.transform.rotation = quat

        self.tf_broadcaster.sendTransform(t)

    def publish_joint_states(self, timestamp):
        """Publish joint states for wheel visualization."""
        joint_state = JointState()
        joint_state.header.stamp = timestamp.to_msg()
        joint_state.name = ['left_wheel_joint', 'right_wheel_joint']
        joint_state.position = [self.left_wheel_angle, self.right_wheel_angle]
        joint_state.velocity = []
        joint_state.effort = []

        self.joint_state_pub.publish(joint_state)

    def quaternion_from_yaw(self, yaw: float) -> Quaternion:
        """Convert yaw angle to quaternion."""
        quat = Quaternion()
        quat.x = 0.0
        quat.y = 0.0
        quat.z = math.sin(yaw / 2.0)
        quat.w = math.cos(yaw / 2.0)
        return quat

    def shutdown(self):
        """Clean shutdown - stop motors and close serial port."""
        self.get_logger().info('Shutting down base driver...')
        self.modbus.set_motor_speeds(0, 0)
        time.sleep(0.1)
        self.modbus.enable_motors(False)
        self.modbus.disconnect()


def main(args=None):
    rclpy.init(args=args)

    node = None
    try:
        node = BaseDriverNode()
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f'Error: {e}')
    finally:
        if node is not None:
            node.shutdown()
            node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
