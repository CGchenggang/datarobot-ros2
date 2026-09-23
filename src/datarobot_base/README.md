# DataRobot Base Driver

ROS2 base driver for DataRobot with Modbus motor controller.

## Features

- **Modbus RTU communication** with dual-axis servo driver (115200 bps, 8N1)
- **Differential drive kinematics** for velocity command conversion
- **Odometry publishing** with TF transforms (odom → base_footprint)
- **Joint state publishing** for wheel visualization in RViz
- **Safety timeout** - motors stop if no cmd_vel received for 1 second

## Hardware Requirements

- Dual-axis servo motor driver with Modbus RTU interface
- Serial connection (USB-to-RS485 adapter)
- Default settings:
  - Station ID: 0x01
  - Baudrate: 115200 bps
  - Protocol: Modbus RTU, 8N1

## Installation

```bash
cd ~/your_ros2_ws/src
# Copy the datarobot_base package here
cd ~/your_ros2_ws
colcon build --packages-select datarobot_base
source install/setup.bash
```

## Dependencies

```bash
sudo apt install ros-humble-robot-state-publisher
pip3 install pyserial
```

## Usage

### Basic Launch

```bash
ros2 launch datarobot_base bringup.launch.py
```

### With Custom Serial Port

```bash
ros2 launch datarobot_base bringup.launch.py serial_port:=/dev/ttyUSB0
```

### Control the Robot

Use keyboard teleop:
```bash
ros2 run teleop_twist_keyboard teleop_twist_keyboard
```

Or publish velocity commands:
```bash
ros2 topic pub /cmd_vel geometry_msgs/Twist "{linear: {x: 0.2}, angular: {z: 0.0}}"
```

## Topics

### Subscribed
- `/cmd_vel` (geometry_msgs/Twist) - Velocity commands

### Published
- `/odom` (nav_msgs/Odometry) - Odometry information
- `/joint_states` (sensor_msgs/JointState) - Wheel joint angles
- `/tf` - Transform from odom to base_footprint

## Parameters

See `config/base_driver.yaml` for all configurable parameters:

- `serial_port`: Serial device path (default: /dev/ttyUSB0)
- `baudrate`: Communication baudrate (default: 115200)
- `wheel_radius`: Wheel radius in meters (default: 0.083)
- `wheel_base`: Distance between wheels in meters (default: 0.358)
- `max_rpm`: Maximum motor RPM (default: 3000)
- `publish_rate`: Control loop frequency in Hz (default: 50)
- `cmd_vel_timeout`: Safety timeout in seconds (default: 1.0)

## Architecture

```
┌─────────────────┐
│   /cmd_vel      │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────┐
│  base_driver_node.py        │
│  ┌──────────────────────┐   │
│  │ DiffDriveController  │   │  Kinematics
│  └──────────────────────┘   │
│  ┌──────────────────────┐   │
│  │  ModbusController    │   │  Hardware I/O
│  └──────────────────────┘   │
└─────────┬───────────────────┘
          │ Modbus RTU
          ▼
┌─────────────────────────────┐
│  Servo Motor Driver         │
│  (Dual-axis, Station ID=1)  │
└─────────────────────────────┘
```

## Modbus Register Map

### A-axis (Left wheel)
- Enable: 0x2100 (F0.1.000)
- Speed command: 0x2318 (F0.3.018)
- Actual speed: 0x5000 (D0.00)

### B-axis (Right wheel)
- Enable: 0x3100 (F1.1.000)
- Speed command: 0x3318 (F1.3.018)
- Actual speed: 0x5100 (D1.00)

## Testing

### Test Modbus Communication

```bash
cd ~/your_ros2_ws/src/datarobot_base/datarobot_base
python3 modbus_controller.py
```

### Test Kinematics

```bash
cd ~/your_ros2_ws/src/datarobot_base/datarobot_base
python3 diff_drive_controller.py
```

## Troubleshooting

### Cannot open serial port
- Check device permissions: `sudo chmod 666 /dev/ttyUSB0`
- Or add user to dialout group: `sudo usermod -a -G dialout $USER` (logout required)

### Motors not responding
- Verify Modbus station ID matches (default: 1)
- Check baudrate setting (default: 115200)
- Ensure RS485 wiring is correct (A to A, B to B)

### Odometry drifts
- Calibrate wheel radius and wheel base parameters
- Check for wheel slippage
- Verify encoder feedback is working

## License

Apache 2.0
