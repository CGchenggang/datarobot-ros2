"""
Differential drive base controller for DataRobot.

Converts cmd_vel (linear.x, angular.z) to wheel speeds,
controls motors via Modbus, and publishes odometry.
"""

import math
from typing import Tuple


class DiffDriveController:
    """Differential drive kinematics and odometry."""

    def __init__(self, wheel_radius: float, wheel_base: float,
                 gear_ratio: float = 1.0, max_rpm: int = 3000,
                 invert_left: bool = False, invert_right: bool = True):
        """
        Initialize differential drive controller.

        Args:
            wheel_radius: Wheel radius in meters
            wheel_base: Distance between wheels in meters
            gear_ratio: Motor gear ratio (motor_rpm / wheel_rpm)
            max_rpm: Maximum motor RPM
            invert_left: Negate left (A axis) motor command
            invert_right: Negate right (B axis) motor command. True by default
                because the right motor is mirror-mounted: forward motion needs
                A positive and B negative.
        """
        self.wheel_radius = wheel_radius
        self.wheel_base = wheel_base
        self.gear_ratio = gear_ratio
        self.max_rpm = max_rpm
        self.left_sign = -1 if invert_left else 1
        self.right_sign = -1 if invert_right else 1

        # Odometry state
        self.x = 0.0
        self.y = 0.0
        self.theta = 0.0
        self.last_left_rpm = 0
        self.last_right_rpm = 0

    def cmd_vel_to_wheel_speeds(self, linear_x: float, angular_z: float) -> Tuple[int, int]:
        """
        Convert cmd_vel to motor RPM.

        Returns motor commands in the driver's own sign convention (see
        invert_left / invert_right), not in the ROS wheel convention.

        Args:
            linear_x: Linear velocity in m/s
            angular_z: Angular velocity in rad/s

        Returns:
            (left_rpm, right_rpm): Motor speeds in RPM, ready to send
        """
        # Calculate wheel velocities in m/s
        # v_left = linear_x - (angular_z * wheel_base / 2)
        # v_right = linear_x + (angular_z * wheel_base / 2)
        v_left = linear_x - (angular_z * self.wheel_base / 2.0)
        v_right = linear_x + (angular_z * self.wheel_base / 2.0)

        # Convert to wheel angular velocity (rad/s)
        omega_left = v_left / self.wheel_radius
        omega_right = v_right / self.wheel_radius

        # Convert to RPM (revolutions per minute)
        # RPM = (rad/s) * (60 / 2π)
        left_wheel_rpm = omega_left * 60.0 / (2.0 * math.pi)
        right_wheel_rpm = omega_right * 60.0 / (2.0 * math.pi)

        # Apply gear ratio (motor RPM = wheel RPM * gear_ratio) and the
        # per-axis sign convention of the driver
        left_motor_rpm = int(left_wheel_rpm * self.gear_ratio) * self.left_sign
        right_motor_rpm = int(right_wheel_rpm * self.gear_ratio) * self.right_sign

        # Clamp to max RPM
        left_motor_rpm = max(-self.max_rpm, min(self.max_rpm, left_motor_rpm))
        right_motor_rpm = max(-self.max_rpm, min(self.max_rpm, right_motor_rpm))

        return (left_motor_rpm, right_motor_rpm)

    def update_odometry(self, left_rpm: int, right_rpm: int, dt: float):
        """
        Update odometry based on motor speeds.

        Args:
            left_rpm: Left (A axis) motor RPM, in driver sign convention
            right_rpm: Right (B axis) motor RPM, in driver sign convention
            dt: Time step in seconds
        """
        # Undo the driver sign convention to get ROS wheel rotation, then
        # convert motor RPM to wheel RPM
        left_wheel_rpm = (left_rpm * self.left_sign) / self.gear_ratio
        right_wheel_rpm = (right_rpm * self.right_sign) / self.gear_ratio

        # Convert RPM to rad/s
        omega_left = left_wheel_rpm * (2.0 * math.pi) / 60.0
        omega_right = right_wheel_rpm * (2.0 * math.pi) / 60.0

        # Calculate wheel velocities
        v_left = omega_left * self.wheel_radius
        v_right = omega_right * self.wheel_radius

        # Calculate robot velocities
        linear_x = (v_left + v_right) / 2.0
        angular_z = (v_right - v_left) / self.wheel_base

        # Update pose (using simple Euler integration)
        delta_x = linear_x * math.cos(self.theta) * dt
        delta_y = linear_x * math.sin(self.theta) * dt
        delta_theta = angular_z * dt

        self.x += delta_x
        self.y += delta_y
        self.theta += delta_theta

        # Normalize theta to [-pi, pi]
        self.theta = math.atan2(math.sin(self.theta), math.cos(self.theta))

        self.last_left_rpm = left_wheel_rpm
        self.last_right_rpm = right_wheel_rpm

        return (linear_x, angular_z)

    def get_pose(self) -> Tuple[float, float, float]:
        """Get current pose (x, y, theta)."""
        return (self.x, self.y, self.theta)

    def reset_odometry(self):
        """Reset odometry to origin."""
        self.x = 0.0
        self.y = 0.0
        self.theta = 0.0


if __name__ == '__main__':
    # Verify sign convention against the frames captured from the real driver:
    #   forward  -> A positive, B negative
    #   backward -> A negative, B positive
    #   turn left  -> both negative
    #   turn right -> both positive
    controller = DiffDriveController(
        wheel_radius=0.083,  # 8.3 cm
        wheel_base=0.358,    # 35.8 cm
        gear_ratio=1.0,
        max_rpm=3000
    )

    cases = [
        ('forward  0.2 m/s', 0.2, 0.0, 'A+ B-'),
        ('backward 0.2 m/s', -0.2, 0.0, 'A- B+'),
        ('turn left  0.5 rad/s', 0.0, 0.5, 'both -'),
        ('turn right 0.5 rad/s', 0.0, -0.5, 'both +'),
        ('arc (0.2 m/s, 0.3 rad/s)', 0.2, 0.3, ''),
    ]

    for label, lin, ang, expected in cases:
        left_rpm, right_rpm = controller.cmd_vel_to_wheel_speeds(lin, ang)
        note = f'  (expect {expected})' if expected else ''
        print(f'{label:26s}: A={left_rpm:5d} RPM, B={right_rpm:5d} RPM{note}')
