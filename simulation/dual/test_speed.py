import sys
import time
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy
from px4_msgs.msg import VehicleCommand, OffboardControlMode, TrajectorySetpoint, VehicleStatus, VehicleOdometry, VehicleAttitude, ActuatorMotors, BatteryStatus
from nav_msgs.msg import Odometry

class SpeedTestNode(Node):
    def __init__(self, target_speed):
        super().__init__('speed_test_node')
        self.target_speed = float(target_speed)
        qos = QoSProfile(reliability=ReliabilityPolicy.BEST_EFFORT, durability=DurabilityPolicy.TRANSIENT_LOCAL, depth=1)
        
        self.cmd_pub = self.create_publisher(VehicleCommand, '/drone1/fmu/in/vehicle_command', 10)
        self.mode_pub = self.create_publisher(OffboardControlMode, '/drone1/fmu/in/offboard_control_mode', 10)
        self.sp_pub = self.create_publisher(TrajectorySetpoint, '/drone1/fmu/in/trajectory_setpoint', 10)
        
        self.create_subscription(VehicleStatus, '/drone1/fmu/out/vehicle_status', self.status_cb, qos)
        self.create_subscription(VehicleOdometry, '/drone1/fmu/out/vehicle_odometry', self.odom_cb, qos)
        self.create_subscription(VehicleAttitude, '/drone1/fmu/out/vehicle_attitude', self.att_cb, qos)
        self.create_subscription(ActuatorMotors, '/drone1/fmu/out/actuator_motors', self.motors_cb, qos)
        self.create_subscription(BatteryStatus, '/drone1/fmu/out/battery_status', self.bat_cb, qos)
        
        self.timer = self.create_timer(0.05, self.tick)
        
        self.phase = 'INIT'
        self.start_t = time.time()
        self.last_cmd_t = 0
        
        self.state = None
        self.pos = [0,0,0]
        self.vel = [0,0,0]
        self.pitch = 0
        self.roll = 0
        self.throttle = 0
        self.power_w = 0
        self.current_a = 0
        
        self.max_pitch = 0
        self.max_power = 0
        self.steady_state_pitch = []
        self.steady_state_power = []
        
    def status_cb(self, msg):
        self.state = msg
        
    def odom_cb(self, msg):
        self.pos = msg.position
        self.vel = msg.velocity
        
    def att_cb(self, msg):
        q = msg.q
        self.pitch = -math.asin(2.0 * (q[0]*q[2] - q[3]*q[1]))
        self.roll = math.atan2(2.0 * (q[0]*q[1] + q[2]*q[3]), 1.0 - 2.0 * (q[1]*q[1] + q[2]*q[2]))
        
    def motors_cb(self, msg):
        self.throttle = sum(msg.control[:4]) / 4.0
        
    def bat_cb(self, msg):
        self.current_a = msg.current_a
        self.power_w = msg.voltage_v * msg.current_a
        
    def send_cmd(self, cmd, p1=0.0, p2=0.0):
        msg = VehicleCommand()
        msg.command = cmd
        msg.param1 = float(p1)
        msg.param2 = float(p2)
        msg.target_system = 2 # drone 1 is usually sysid 2 in dual setup
        msg.target_component = 1
        msg.source_system = 255
        msg.timestamp = int(self.get_clock().now().nanoseconds / 1000)
        self.cmd_pub.publish(msg)
        
    def tick(self):
        now = time.time()
        dt = now - self.start_t
        
        # Always publish offboard mode
        mode = OffboardControlMode()
        mode.position = (self.phase in ['TAKEOFF', 'STOP'])
        mode.velocity = (self.phase == 'SPEED')
        mode.acceleration = False
        mode.attitude = False
        mode.body_rate = False
        mode.timestamp = int(self.get_clock().now().nanoseconds / 1000)
        self.mode_pub.publish(mode)
        
        if self.phase == 'INIT':
            if self.state and self.state.nav_state == 14: # Offboard
                self.phase = 'ARM'
            elif now - self.last_cmd_t > 1.0:
                self.send_cmd(VehicleCommand.VEHICLE_CMD_DO_SET_MODE, 1, 6)
                self.last_cmd_t = now
                
        elif self.phase == 'ARM':
            if self.state and self.state.arming_state == 2:
                self.phase = 'TAKEOFF'
                print("Armed. Taking off...")
            elif now - self.last_cmd_t > 1.0:
                self.send_cmd(VehicleCommand.VEHICLE_CMD_COMPONENT_ARM_DISARM, 1)
                self.last_cmd_t = now
                
        elif self.phase == 'TAKEOFF':
            sp = TrajectorySetpoint()
            sp.position = [0.0, 0.0, -25.0]
            sp.yaw = 0.0
            sp.timestamp = int(self.get_clock().now().nanoseconds / 1000)
            self.sp_pub.publish(sp)
            
            if self.pos[2] < -24.0:
                self.phase = 'SPEED'
                self.speed_start_t = now
                print(f"Reached altitude. Accelerating to {self.target_speed} m/s...")
                
        elif self.phase == 'SPEED':
            sp = TrajectorySetpoint()
            sp.position = [float('nan'), float('nan'), -25.0]
            sp.velocity = [self.target_speed, 0.0, 0.0]
            sp.yaw = 0.0
            sp.timestamp = int(self.get_clock().now().nanoseconds / 1000)
            self.sp_pub.publish(sp)
            
            if now - self.speed_start_t > 15.0: # Hold for 15s
                self.phase = 'STOP'
                self.stop_start_t = now
                print("Decelerating...")
                avg_pitch = sum(self.steady_state_pitch)/max(1,len(self.steady_state_pitch))
                avg_power = sum(self.steady_state_power)/max(1,len(self.steady_state_power))
                print(f"RESULTS FOR {self.target_speed} m/s:")
                print(f"  Max Pitch: {math.degrees(self.max_pitch):.1f} deg")
                print(f"  Steady Pitch: {math.degrees(avg_pitch):.1f} deg")
                print(f"  Avg Power: {avg_power:.1f} W")
                print(f"  Achieved Speed: {self.vel[0]:.2f} m/s")
            elif now - self.speed_start_t > 5.0:
                # steady state
                self.max_pitch = max(self.max_pitch, abs(self.pitch))
                self.max_power = max(self.max_power, self.power_w)
                self.steady_state_pitch.append(abs(self.pitch))
                self.steady_state_power.append(self.power_w)
                
        elif self.phase == 'STOP':
            sp = TrajectorySetpoint()
            sp.position = [float('nan'), float('nan'), -25.0]
            sp.velocity = [0.0, 0.0, 0.0]
            sp.yaw = 0.0
            sp.timestamp = int(self.get_clock().now().nanoseconds / 1000)
            self.sp_pub.publish(sp)
            
            if now - self.stop_start_t > 5.0 and abs(self.vel[0]) < 0.5:
                print("Stopped. Test complete.")
                sys.exit(0)

import math
rclpy.init()
node = SpeedTestNode(sys.argv[1])
try:
    rclpy.spin(node)
except SystemExit:
    pass
