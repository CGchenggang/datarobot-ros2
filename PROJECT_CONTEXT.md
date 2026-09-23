# DataRobot ROS2 Project Context

## Overview
ROS2 Jazzy based differential drive robot with lidar and base controller.

## Hardware

### Base Controller (DataRobot)
- Interface: Modbus RTU over RS485
- Port: /dev/ttyUSB1
- Baudrate: 115200
- Address: 0x01
- Mode: Write-only (no read to avoid port conflict)
- Control frequency: 50 Hz

### Lidar (Bluesea2)
- Model: Bluesea2
- Interface: UART
- Port: /dev/ttyUSB0
- Baudrate: 1000000
- Scan frequency: 10 Hz
- Range: 0.1m - 50m
- Version: V1.1

### Robot Parameters
- Wheel base: 0.46m
- Wheel diameter: 0.17m
- Gear ratio: needs calibration (default 1.0)
- Drive type: Differential drive

## Software Architecture

### ROS2 Nodes

1. base_driver_node (datarobot_base)
   - Subscribe: /cmd_vel
   - Publish: /odom, /tf (odom -> base_footprint)
   - Frequency: 50 Hz

2. bluesea_lidar (bluesea2)
   - Publish: /scan
   - Frequency: 10 Hz

3. robot_state_publisher
   - Publish: /robot_description, /tf_static

### TF Tree
odom -> base_footprint -> base_link -> {laser_link, left_wheel_link, right_wheel_link}

## Key Configurations

### Base Config (config/base_params.yaml)
- Serial port, baudrate
- Wheel base, diameter, gear ratio
- Control frequency
- Write-only mode enabled

### Lidar Config (config/lidar.yaml)
- IMPORTANT: namespace must be "bluesea_lidar:" (match node name)
- baudrate must be 1000000
- frame_id: "laser_link"

### URDF Model (datarobot_description)
- USE: databot/urdf/databot.urdf.xacro
- DO NOT USE: datarobot/ directory models

## Known Issues

1. DataRobot Modbus still responds when disabled
   - Solution: write-only mode

2. Right wheel speed sign inverted
   - Solution: negate right wheel speed in base_driver.py

3. Serial port is bottleneck at 115200
   - Solution: write-only mode, no read wait

4. Gear ratio not calibrated
   - Solution: calibrate before mapping

5. WSL2 serial forwarding
   - Solution: use usbipd

6. Two URDF models exist
   - Solution: only use databot/ directory

7. Lidar parameter namespace mismatch
   - Solution: config namespace must match launch node name

## Launch Commands

### Full system (base + lidar + URDF)
ros2 launch datarobot_base bringup_with_lidar.launch.py use_rviz:=false serial_port:=/dev/ttyUSB1 lidar_port:=/dev/ttyUSB0

### Base only
ros2 launch datarobot_base bringup.launch.py serial_port:=/dev/ttyUSB1

### Test motor
ros2 topic pub /cmd_vel geometry_msgs/msg/Twist "{linear: {x: 0.2}, angular: {z: 0.0}}"

## Next Steps

1. Calibrate gear ratio
2. Build map with slam_toolbox or cartographer
3. Setup navigation with nav2
4. Tune PID and odometry covariance
