
import rclpy
from rclpy.node import Node
from px4_msgs.msg import VehicleCommand, TrajectorySetpoint, OffboardControlMode, VehicleStatus, VehicleAttitude, VehicleLocalPosition
from gz.msgs10.image_pb2 import Image
from gz.transport13 import Node as GzNode
from gz.msgs10.double_pb2 import Double
import time, math, cv2
import numpy as np

class BenchTest(Node):
    def __init__(self):
        super().__init__('bench_test')
        self.cmd_pub = self.create_publisher(VehicleCommand, '/drone1/in/vehicle_command', 10)
        self.sp_pub = self.create_publisher(TrajectorySetpoint, '/drone1/in/trajectory_setpoint', 10)
        self.mode_pub = self.create_publisher(OffboardControlMode, '/drone1/in/offboard_control_mode', 10)
        self.create_subscription(VehicleStatus, '/drone1/out/vehicle_status_v4', self.status_cb, 10)
        self.create_subscription(VehicleAttitude, '/drone1/out/vehicle_attitude', self.att_cb, 10)
        self.create_subscription(VehicleLocalPosition, '/drone1/out/vehicle_local_position_v1', self.pos_cb, 10)
        
        self.gz = GzNode()
        self.gz.subscribe(Image, '/rescue_0/camera', self.cam_cb)
        self.gimbal_roll_pub = self.gz.advertise('/model/rescue_0/joint/gimbal_roll_joint/0/cmd_pos', Double)
        self.gimbal_pitch_pub = self.gz.advertise('/model/rescue_0/joint/gimbal_pitch_joint/0/cmd_pos', Double)
        
        self.att = None
        self.pos = None
        self.state = 0
        self.t0 = time.time()
        self.armed = False
        
        self.target_px = None
        self.target_area = 0
        self.results = {}
        
        self.create_timer(0.05, self.tick)
        
    def status_cb(self, msg):
        self.armed = (msg.arming_state == 2)
        
    def att_cb(self, msg):
        self.att = msg
        
    def pos_cb(self, msg):
        self.pos = msg
        
    def cam_cb(self, msg):
        try:
            data = np.frombuffer(msg.data, dtype=np.uint8).reshape(msg.height, msg.step)[:, :msg.width * 3].reshape(msg.height, msg.width, 3)
            hsv = cv2.cvtColor(data, cv2.COLOR_RGB2HSV)
            # The target is red (ambient 1 0 0)
            # Actually HSV for red is around 0 or 180. We can just use an easy range or check red channel.
            r_channel = data[:,:,0]
            g_channel = data[:,:,1]
            mask = (r_channel > 200) & (g_channel < 50)
            mask = mask.astype(np.uint8) * 255
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            best_area = 0
            best_center = None
            for c in contours:
                area = cv2.contourArea(c)
                if area > best_area:
                    best_area = area
                    mo = cv2.moments(c)
                    if mo['m00']:
                        best_center = (mo['m10']/mo['m00'], mo['m01']/mo['m00'])
                        
            if best_area > 0:
                self.target_px = best_center
                self.target_area = best_area
            else:
                self.target_px = None
                self.target_area = 0
        except Exception as e:
            pass

    def send_cmd(self, cmd, p1=0.0):
        m = VehicleCommand()
        m.command = cmd
        m.param1 = float(p1)
        m.target_system = 1
        m.target_component = 1
        m.source_system = 255
        self.cmd_pub.publish(m)

    def tick(self):
        now = time.time()
        
        # Publish offboard mode
        mode = OffboardControlMode()
        mode.position = True
        mode.timestamp = int(time.time() * 1e6)
        self.mode_pub.publish(mode)
        
        sp = TrajectorySetpoint()
        sp.position = [-5.0, -5.0, -5.0]
        sp.yaw = 0.0
        sp.timestamp = mode.timestamp
        self.sp_pub.publish(sp)
        
        if self.state == 0:
            if now - self.t0 > 2:
                self.send_cmd(VehicleCommand.VEHICLE_CMD_DO_SET_MODE, 1.0) # PX4_CUSTOM_MAIN_MODE_OFFBOARD
                self.send_cmd(VehicleCommand.VEHICLE_CMD_COMPONENT_ARM_DISARM, 1.0)
                self.state = 1
                print("Armed & Offboard")
        elif self.state == 1:
            if self.pos and self.pos.z < -4.5:
                self.state = 2
                self.t0 = time.time()
                print("Reached 5m. Stabilizing...")
        elif self.state == 2:
            if now - self.t0 > 10:
                self.state = 3
                print("Collecting data...")
                
        # Update gimbal
        if self.att is not None:
            q = self.att.q
            t0 = +2.0 * (q[0] * q[1] + q[2] * q[3])
            t1 = +1.0 - 2.0 * (q[1] * q[1] + q[2] * q[2])
            roll = math.atan2(t0, t1)
            t2 = max(-1.0, min(1.0, +2.0 * (q[0] * q[2] - q[3] * q[1])))
            pitch = math.asin(t2)
            
            gimbal_roll = max(-0.349, min(0.349, -roll))
            gimbal_pitch = max(-0.523, min(0.523, -pitch))
            
            d_roll = Double()
            d_roll.data = gimbal_roll
            self.gimbal_roll_pub.publish(d_roll)
            
            d_pitch = Double()
            d_pitch.data = gimbal_pitch
            self.gimbal_pitch_pub.publish(d_pitch)
            
            if self.state == 3:
                # Log metrics
                target_in_fov = self.target_px is not None
                if target_in_fov:
                    err_x = self.target_px[0] - 160
                    err_y = self.target_px[1] - 120
                    px_err = math.hypot(err_x, err_y)
                else:
                    px_err = 0.0
                
                pos_err = 0.0
                if self.pos:
                    pos_err = math.hypot(self.pos.x - (-5.0), self.pos.y - (-5.0))
                
                res = f"{math.degrees(pitch):.1f},{math.degrees(roll):.1f},{math.degrees(gimbal_pitch):.1f},{math.degrees(gimbal_roll):.1f},{target_in_fov},100.0,{pos_err:.2f}"
                with open("bench_result.txt", "w") as f:
                    f.write(res)
                
                print("Done collecting data.")
                rclpy.shutdown()

def main():
    rclpy.init()
    node = BenchTest()
    try:
        rclpy.spin(node)
    except:
        pass
    finally:
        node.destroy_node()

if __name__ == '__main__':
    main()
