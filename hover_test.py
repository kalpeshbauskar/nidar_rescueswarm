import rclpy, sys, time, json, math
from rclpy.node import Node
from px4_msgs.msg import VehicleLocalPosition, VehicleCommand, OffboardControlMode, TrajectorySetpoint, VehicleStatus, VehicleAttitude
from rclpy.qos import qos_profile_sensor_data
from gz.transport13 import Node as GzNode
from gz.msgs10.stringmsg_pb2 import StringMsg

class HoverTester(Node):
    def __init__(self):
        super().__init__('hover_test')
        self.ns = '/drone1/fmu'
        self.p = self.s = self.att = None
        self.create_subscription(VehicleLocalPosition, self.ns+'/out/vehicle_local_position_v1', self.pos_cb, qos_profile_sensor_data)
        self.create_subscription(VehicleStatus, self.ns+'/out/vehicle_status_v4', self.stat_cb, qos_profile_sensor_data)
        self.create_subscription(VehicleAttitude, self.ns+'/out/vehicle_attitude', self.att_cb, qos_profile_sensor_data)
        self.mode_pub = self.create_publisher(OffboardControlMode, self.ns+'/in/offboard_control_mode', 10)
        self.sp_pub = self.create_publisher(TrajectorySetpoint, self.ns+'/in/trajectory_setpoint', 10)
        self.cmd_pub = self.create_publisher(VehicleCommand, self.ns+'/in/vehicle_command', 10)
        
        self.gz = GzNode()
        self.cargo = {}
        self.cargo_pubs = {}
        for j in range(10):
            name = f'parcel_0_{j}'
            self.gz.subscribe(StringMsg, f'/{name}/state', lambda m, j=j: self.cargo.update({j:m.data}))
            self.cargo_pubs[j, 'attach'] = self.gz.advertise(f'/{name}/attach', __import__('gz.msgs10.empty_pb2', fromlist=['Empty']).Empty)
            self.cargo_pubs[j, 'detach'] = self.gz.advertise(f'/{name}/detach', __import__('gz.msgs10.empty_pb2', fromlist=['Empty']).Empty)
            
        self.timer = self.create_timer(0.05, self.tick)
        self.start_time = time.monotonic()
        self.phase = 'WAIT'
        self.last_cmd = 0
        self.phase_start = 0
        self.target = [0.0, 0.0, -5.0]
        
        self.log = []
        self.max_alt = 0.0

    def pos_cb(self, msg): self.p = msg
    def stat_cb(self, msg): self.s = msg
    def att_cb(self, msg): self.att = msg

    def cmd(self, c, p1=0., p2=0.):
        m = VehicleCommand(); m.timestamp = self.get_clock().now().nanoseconds // 1000
        m.command = c; m.param1 = float(p1); m.param2 = float(p2)
        m.target_system = 1; m.target_component = 1; m.source_system = 240; m.source_component = 1
        m.from_external = True; self.cmd_pub.publish(m); self.last_cmd = time.monotonic()

    def phase_to(self, new_phase):
        self.phase = new_phase
        self.phase_start = time.monotonic()
        print(f"[{time.monotonic()-self.start_time:.1f}s] Phase -> {self.phase}")

    def get_rpy(self):
        if not self.att: return 0,0,0
        q = self.att.q
        roll = math.atan2(2.0 * (q[0] * q[1] + q[2] * q[3]), 1.0 - 2.0 * (q[1] * q[1] + q[2] * q[2]))
        pitch = math.asin(2.0 * (q[0] * q[2] - q[3] * q[1]))
        yaw = math.atan2(2.0 * (q[0] * q[3] + q[1] * q[2]), 1.0 - 2.0 * (q[2] * q[2] + q[3] * q[3]))
        return roll, pitch, yaw

    def tick(self):
        now = time.monotonic()
        if now - self.start_time > 120:
            print("FAILED: Global timeout reached.")
            sys.exit(1)
            
        if self.p and self.s and self.p.xy_valid and self.p.z_valid:
            if -self.p.z > self.max_alt: self.max_alt = -self.p.z
            
            if self.phase == 'WAIT':
                if now - self.start_time > 2:
                    self.phase_to('DETACH')
                    
            elif self.phase == 'DETACH':
                for j in range(10):
                    if self.cargo.get(j) != 'detached':
                        self.cargo_pubs[j, 'detach'].publish(__import__('gz.msgs10.empty_pb2', fromlist=['Empty']).Empty())
                if all(self.cargo.get(j) == 'detached' for j in range(10)):
                    self.phase_to('ATTACH')
                elif now - self.phase_start > 5:
                    print(f"FAILED: Could not detach. States: {self.cargo}")
                    sys.exit(1)
                    
            elif self.phase == 'ATTACH':
                for j in range(10):
                    if self.cargo.get(j) != 'attached':
                        self.cargo_pubs[j, 'attach'].publish(__import__('gz.msgs10.empty_pb2', fromlist=['Empty']).Empty())
                if all(self.cargo.get(j) == 'attached' for j in range(10)):
                    print(f"VERIFIED: All 10 packages attached. Payload=2.0kg.")
                    self.phase_to('OFFBOARD')
                elif now - self.phase_start > 10:
                    print(f"FAILED: Packages not attached. States: {self.cargo}")
                    sys.exit(1)
            elif self.phase == 'OFFBOARD':
                if self.s.nav_state == 14: self.phase_to('ARM')
                elif now - self.last_cmd > 1: self.cmd(VehicleCommand.VEHICLE_CMD_DO_SET_MODE, 1, 6)
                
            elif self.phase == 'ARM':
                if self.s.arming_state == 2:
                    print("VERIFIED: Armed successfully.")
                    self.phase_to('TAKEOFF')
                elif now - self.last_cmd > 1: self.cmd(VehicleCommand.VEHICLE_CMD_COMPONENT_ARM_DISARM, 1)
                
            elif self.phase == 'TAKEOFF':
                if -self.p.z > 4.5:
                    print(f"VERIFIED: Reached takeoff altitude. Z: {-self.p.z:.2f}")
                    self.phase_to('HOLD')
                    
            elif self.phase == 'HOLD':
                if now - self.phase_start > 10:
                    self.target = [5.0, 5.0, -5.0]
                    self.phase_to('MOVE')
                    
            elif self.phase == 'MOVE':
                if math.hypot(self.p.x - 5.0, self.p.y - 5.0) < 0.5:
                    self.phase_to('STABILIZE')
                    
            elif self.phase == 'STABILIZE':
                if now - self.phase_start > 5:
                    self.target = [0.0, 0.0, -5.0]
                    self.phase_to('RETURN')
                    
            elif self.phase == 'RETURN':
                if math.hypot(self.p.x, self.p.y) < 0.5:
                    self.phase_to('LAND')
                    
            elif self.phase == 'LAND':
                if self.s.arming_state != 2:
                    print(f"VERIFIED: Disarmed successfully.")
                    print(f"Max altitude: {self.max_alt:.2f}")
                    sys.exit(0)
                elif now - self.last_cmd > 2:
                    self.cmd(VehicleCommand.VEHICLE_CMD_NAV_LAND)

            # Publish setpoint for position phases
            if self.phase not in ['WAIT', 'LAND']:
                m = OffboardControlMode(); m.timestamp = self.get_clock().now().nanoseconds // 1000
                m.position = True; self.mode_pub.publish(m)
                
                s = TrajectorySetpoint(); s.timestamp = m.timestamp
                s.position = self.target
                s.yaw = 0.0; self.sp_pub.publish(s)
                
            # Log data every second for review
            if int(now * 10) % 10 == 0:
                r, p, y = self.get_rpy()
                self.log.append({
                    't': round(now - self.start_time, 1),
                    'phase': self.phase,
                    'x': round(self.p.x, 2), 'y': round(self.p.y, 2), 'z': round(-self.p.z, 2),
                    'roll': round(math.degrees(r), 1), 'pitch': round(math.degrees(p), 1)
                })

rclpy.init()
node = HoverTester()
try: rclpy.spin(node)
except SystemExit as e:
    with open('hover_log.json', 'w') as f:
        json.dump(node.log, f, indent=2)
    sys.exit(e.code)
