# DataRobot Project Structure

## Directory Layout

```
chapt_ws/
├── src/
│   ├── datarobot_base/           # Base controller driver package
│   │   ├── config/
│   │   │   ├── base_params.yaml  # Base controller configuration
│   │   │   └── lidar.yaml        # Lidar configuration
│   │   ├── launch/
│   │   │   ├── bringup.launch.py           # Base only
│   │   │   └── bringup_with_lidar.launch.py # Full system
│   │   ├── datarobot_base/
│   │   │   ├── base_driver.py    # Main ROS2 node
│   │   │   └── modbus_controller.py # Low-level Modbus driver
│   │   ├── package.xml
│   │   └── setup.py
│   │
│   ├── datarobot_description/    # Robot URDF models
│   │   ├── urdf/
│   │   │   ├── databot/          # CORRECT MODEL (use this)
│   │   │   │   ├── urdf/
│   │   │   │   │   └── databot.urdf.xacro
│   │   │   │   └── launch/
│   │   │   │       └── display.launch.py
│   │   │   └── datarobot/        # OLD MODEL (do not use)
│   │   ├── meshes/               # 3D models for visualization
│   │   ├── rviz/
│   │   │   └── datarobot.rviz    # RViz configuration
│   │   ├── package.xml
│   │   └── CMakeLists.txt
│   │
│   └── bluesea2/                 # Lidar driver (binary)
│       ├── sdk/                  # Lidar SDK
│       ├── src/
│       │   └── node.cpp          # Lidar ROS2 node
│       ├── params/
│       │   └── params.yaml       # Default parameters
│       ├── launch/
│       ├── package.xml
│       └── CMakeLists.txt
│
├── build/                        # Build artifacts (auto-generated)
├── install/                      # Installed packages (auto-generated)
├── log/                          # Build and runtime logs
├── PROJECT_CONTEXT.md            # This file
├── ROADMAP.md                    # Development roadmap
└── PROJECT_STRUCTURE.md          # You are here

```

## Key Files Explained

### Configuration Files

**src/datarobot_base/config/base_params.yaml**
- Base controller parameters
- Serial port, baudrate
- Robot dimensions (wheel_base, wheel_diameter)
- Gear ratio (needs calibration)
- Control frequency

**src/datarobot_base/config/lidar.yaml**
- Lidar parameters
- MUST use namespace "bluesea_lidar:" (match node name in launch)
- Baudrate MUST be 1000000
- Frame ID must match URDF (laser_link)

### Source Code

**src/datarobot_base/datarobot_base/base_driver.py**
- Main ROS2 node
- Subscribes to /cmd_vel
- Publishes /odom and /tf
- Converts twist to wheel velocities
- Performs odometry calculation
- NOTE: Right wheel speed is negated here

**src/datarobot_base/datarobot_base/modbus_controller.py**
- Low-level Modbus RTU driver
- Handles serial communication
- Write-only mode to avoid port conflicts
- Register definitions:
  - 0x0000: Left wheel speed (RPM * 10)
  - 0x0001: Right wheel speed (RPM * 10, inverted)
  - 0x0010: Motor enable/disable

### Launch Files

**src/datarobot_base/launch/bringup.launch.py**
- Launches base_driver_node only
- Launches robot_state_publisher with URDF
- Arguments:
  - serial_port (default: /dev/ttyUSB0)
  - use_sim_time (default: false)

**src/datarobot_base/launch/bringup_with_lidar.launch.py**
- Launches full system (base + lidar + URDF)
- Arguments:
  - serial_port (default: /dev/ttyUSB0)
  - lidar_port (default: /dev/ttyUSB1)
  - lidar (default: true)
  - use_rviz (default: true)
  - use_sim_time (default: false)

### URDF Models

**src/datarobot_description/urdf/databot/urdf/databot.urdf.xacro**
- Correct URDF model (use this!)
- Defines robot geometry
- Defines coordinate frames
- Links for base, wheels, lidar

**DO NOT USE: src/datarobot_description/urdf/datarobot/**
- This is an old/alternative model
- Not compatible with current setup

## Build System

### Colcon Commands

```bash
# Build all packages
colcon build

# Build specific package
colcon build --packages-select datarobot_base

# Build with symlink (Python only, no rebuild needed)
colcon build --symlink-install

# Clean build
rm -rf build/ install/ log/
colcon build
```

### Source Setup

```bash
# Source ROS2
source /opt/ros/jazzy/setup.bash

# Source workspace
source install/setup.bash

# Or combined
source /opt/ros/jazzy/setup.bash && source install/setup.bash
```

## Dependencies

### System Packages
- ros-jazzy-desktop
- python3-colcon-common-extensions
- python3-serial
- python3-pymodbus

### ROS2 Packages
- geometry_msgs
- nav_msgs
- sensor_msgs
- tf2_ros
- robot_state_publisher
- xacro

### Custom Packages (included)
- bluesea2 (lidar driver binary)

## Device Mapping

```
/dev/ttyUSB0 -> Bluesea2 Lidar (1000000 baud)
/dev/ttyUSB1 -> DataRobot Base (115200 baud)
```

Note: USB device numbers may change on reboot. Consider using udev rules for persistent naming.

## ROS2 Topics

```
Published:
  /odom              (nav_msgs/Odometry)          - Odometry from base
  /scan              (sensor_msgs/LaserScan)      - Lidar scans
  /tf                (tf2_msgs/TFMessage)         - Dynamic transforms
  /tf_static         (tf2_msgs/TFMessage)         - Static transforms
  /joint_states      (sensor_msgs/JointState)     - Wheel positions
  /robot_description (std_msgs/String)            - URDF model

Subscribed:
  /cmd_vel           (geometry_msgs/Twist)        - Velocity commands
```

## Debugging Tips

### Check USB devices
```bash
ls -l /dev/ttyUSB*
dmesg | grep tty
```

### Monitor topics
```bash
ros2 topic list
ros2 topic hz /scan
ros2 topic echo /odom --once
```

### View TF tree
```bash
ros2 run tf2_tools view_frames
evince frames.pdf
```

### Check node status
```bash
ros2 node list
ros2 node info /base_driver
```

### View logs
```bash
# Runtime logs
tail -f ~/.ros/log/latest/base_driver_node/stdout.log

# Build logs
cat log/latest_build/datarobot_base/stdout.log
```

## Common Issues

1. **Permission denied on serial port**
   ```bash
   sudo chmod 666 /dev/ttyUSB0 /dev/ttyUSB1
   ```

2. **Port already in use**
   ```bash
   # Find process using port
   lsof /dev/ttyUSB0
   # Kill it
   kill -9 <PID>
   ```

3. **Parameters not loading**
   - Check namespace in YAML matches node name in launch file
   - Verify YAML syntax (spaces, not tabs)
   - Check file path in launch file

4. **URDF not loading**
   - Make sure using databot/ not datarobot/
   - Run: ros2 topic echo /robot_description --once
   - Check for xacro errors

5. **Lidar not working**
   - Check baudrate is 1000000
   - Check namespace is bluesea_lidar
   - Verify /dev/ttyUSB0 is the lidar (not base)
