# DataRobot Project Roadmap

## Phase 1: Hardware Integration (COMPLETED)

### 1.1 Base Controller
- [x] Identify Modbus protocol and registers
- [x] Implement Python Modbus driver
- [x] Fix right wheel speed inversion
- [x] Enable write-only mode to avoid port conflicts
- [x] Integrate with ROS2 (cmd_vel subscriber, odom publisher)
- [x] Publish TF transforms (odom -> base_footprint)

### 1.2 Lidar Integration
- [x] Install bluesea2 driver
- [x] Fix baudrate configuration (500000 -> 1000000)
- [x] Fix parameter namespace mismatch
- [x] Verify scan data publishing
- [x] Integrate with launch file

### 1.3 Robot Description
- [x] Create URDF model with correct dimensions
- [x] Add laser_link for lidar mounting
- [x] Setup robot_state_publisher
- [x] Verify TF tree structure

## Phase 2: Calibration (CURRENT)

### 2.1 Gear Ratio Calibration
- [ ] Mark starting position
- [ ] Command robot to move forward 5 meters
- [ ] Measure actual distance traveled
- [ ] Calculate gear_ratio = commanded / actual
- [ ] Update base_params.yaml
- [ ] Verify with multiple test runs

### 2.2 Odometry Tuning
- [ ] Test straight line motion accuracy
- [ ] Test rotation accuracy (360 degree turn)
- [ ] Adjust wheel_base if rotation is off
- [ ] Adjust wheel_diameter if linear motion is off
- [ ] Set appropriate odometry covariance values

## Phase 3: Mapping (NEXT)

### 3.1 SLAM Setup
- [ ] Install slam_toolbox or cartographer
- [ ] Configure SLAM parameters
- [ ] Create mapping launch file
- [ ] Test in controlled environment

### 3.2 Map Building
- [ ] Drive robot to scan environment
- [ ] Save generated map
- [ ] Verify map quality
- [ ] Adjust SLAM parameters if needed

## Phase 4: Navigation

### 4.1 Nav2 Setup
- [ ] Install nav2 packages
- [ ] Configure costmap parameters
- [ ] Configure planner parameters
- [ ] Configure controller parameters
- [ ] Setup recovery behaviors

### 4.2 Navigation Testing
- [ ] Test static obstacle avoidance
- [ ] Test dynamic obstacle avoidance
- [ ] Test path planning to waypoints
- [ ] Tune parameters for performance

## Phase 5: Advanced Features (FUTURE)

### 5.1 Sensor Fusion
- [ ] Consider adding IMU for better odometry
- [ ] Implement EKF or UKF fusion
- [ ] Test on uneven terrain

### 5.2 Autonomous Behaviors
- [ ] Waypoint following
- [ ] Patrol mode
- [ ] Docking/charging station
- [ ] Multi-robot coordination

### 5.3 User Interface
- [ ] Web dashboard for monitoring
- [ ] Mobile app for control
- [ ] Voice commands
- [ ] Gesture control

## Known Technical Debt

1. PID controller not implemented
   - Currently open-loop velocity control
   - Should add closed-loop control for better accuracy

2. Error handling needs improvement
   - Add retry logic for Modbus failures
   - Better error messages for debugging

3. Parameter validation missing
   - Add checks for valid wheel_base, wheel_diameter ranges
   - Validate serial port exists before opening

4. No unit tests
   - Add pytest tests for modbus_controller
   - Add tests for coordinate transforms
   - Add integration tests

5. Documentation incomplete
   - Add API documentation
   - Add more code comments
   - Create user manual

## Performance Optimization Ideas

1. Reduce CPU usage
   - Profile code to find bottlenecks
   - Consider C++ rewrite for performance-critical parts

2. Improve real-time performance
   - Use RT kernel if needed
   - Tune thread priorities

3. Battery optimization
   - Implement power management
   - Sleep modes when idle

## Hardware Upgrades to Consider

1. Better lidar (higher resolution, longer range)
2. IMU for sensor fusion
3. RGB-D camera for 3D perception
4. Encoders for wheel odometry
5. Better motors with built-in encoders
6. Faster onboard computer

## Community Contributions Welcome

- Bug reports and fixes
- Documentation improvements
- New feature implementations
- Testing on different hardware
- Performance optimizations
