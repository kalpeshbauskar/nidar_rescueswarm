import re

with open("mission.py", "r") as f:
    data = f.read()

# 1. Add publishers for the gimbal
pub_injection = """        self.mode = self.create_publisher(OffboardControlMode, self.ns + '/in/offboard_control_mode', 10)
        from gz.msgs10.double_pb2 import Double
        self.gimbal_roll_pub = self.gz.advertise(f'/model/rescue_{i}/joint/gimbal_roll_joint/0/cmd_pos', Double)
        self.gimbal_pitch_pub = self.gz.advertise(f'/model/rescue_{i}/joint/gimbal_pitch_joint/0/cmd_pos', Double)"""
data = re.sub(r'        self\.mode = self\.create_publisher\(OffboardControlMode, self\.ns \+ \'/in/offboard_control_mode\', 10\)', pub_injection, data)

# 2. Update self.project to include gimbal angles
project_replacement = """    def project(self, cx, cy, width, height, plane):
        if self.global_p is None or self.att is None:
            return None
        f = width / (2 * math.tan(0.6))
        
        # Calculate aircraft euler angles
        q = self.att.q
        t0 = +2.0 * (q[0] * q[1] + q[2] * q[3])
        t1 = +1.0 - 2.0 * (q[1] * q[1] + q[2] * q[2])
        aircraft_roll = math.atan2(t0, t1)
        t2 = +2.0 * (q[0] * q[2] - q[3] * q[1])
        t2 = max(-1.0, min(1.0, t2))
        aircraft_pitch = math.asin(t2)
        t3 = +2.0 * (q[0] * q[3] + q[1] * q[2])
        t4 = +1.0 - 2.0 * (q[2] * q[2] + q[3] * q[3])
        aircraft_yaw = math.atan2(t3, t4)
        
        # Gimbal compensates for pitch/roll (with limits)
        gimbal_roll = max(-0.349, min(0.349, -aircraft_roll))
        gimbal_pitch = max(-0.523, min(0.523, -aircraft_pitch))
        
        # Camera is pitched by aircraft + gimbal
        cam_roll = aircraft_roll + gimbal_roll
        cam_pitch = aircraft_pitch + gimbal_pitch
        cam_yaw = aircraft_yaw
        
        # New rotation matrix from camera euler
        cx_c = math.cos(cam_roll)
        sx_c = math.sin(cam_roll)
        cy_c = math.cos(cam_pitch)
        sy_c = math.sin(cam_pitch)
        cz_c = math.cos(cam_yaw)
        sz_c = math.sin(cam_yaw)
        
        rot = np.array([
            [cy_c * cz_c, sx_c * sy_c * cz_c - cx_c * sz_c, cx_c * sy_c * cz_c + sx_c * sz_c],
            [cy_c * sz_c, sx_c * sy_c * sz_c + cx_c * cz_c, cx_c * sy_c * sz_c - sx_c * cz_c],
            [-sy_c,       sx_c * cy_c,                      cx_c * cy_c]
        ])
        
        origin = self.global_p + rot @ np.array([0.1, 0, 0.05])
        ray = rot @ np.array([-(cy - (height - 1) / 2) / f, (cx - (width - 1) / 2) / f, 1.0])"""
data = re.sub(r'    def project.*?ray = rot @ np.array\(\[-\(cy - \(height - 1\) / 2\) / f, \(cx - \(width - 1\) / 2\) / f, 1\.0\]\)', project_replacement, data, flags=re.DOTALL)

# 3. Publish to gimbal in tick()
tick_injection = """    def tick(self):
        if self.att is not None:
            from gz.msgs10.double_pb2 import Double
            q = self.att.q
            t0 = +2.0 * (q[0] * q[1] + q[2] * q[3])
            t1 = +1.0 - 2.0 * (q[1] * q[1] + q[2] * q[2])
            roll = math.atan2(t0, t1)
            t2 = +2.0 * (q[0] * q[2] - q[3] * q[1])
            t2 = max(-1.0, min(1.0, t2))
            pitch = math.asin(t2)
            
            gimbal_roll = max(-0.349, min(0.349, -roll))
            gimbal_pitch = max(-0.523, min(0.523, -pitch))
            
            d_roll = Double()
            d_roll.data = gimbal_roll
            self.gimbal_roll_pub.publish(d_roll)
            
            d_pitch = Double()
            d_pitch.data = gimbal_pitch
            self.gimbal_pitch_pub.publish(d_pitch)
        
        now = time.monotonic()"""
data = re.sub(r'    def tick\(self\):\n        now = time\.monotonic\(\)', tick_injection, data)

# 4. Target tracking state machine and bounded prediction
# Instead of `if now - d['last'] > 15: d['rejected'] = True`, we use prediction.
tracking_injection = """            elif self.phase == 'DESCEND':
                if self.arrived(dwell=1.5, speed=0.4):
                    d = self.detections[self.target_id]
                    dt_since_last = now - d['last']
                    
                    if dt_since_last > 1.0:
                        print(f"[TRACKING] Target {self.target_id} TEMPORARILY OCCLUDED (last seen {dt_since_last:.1f}s ago). Confidence: {max(0, 100 - dt_since_last*5):.1f}%")
                    
                    if dt_since_last > 20.0:
                        d['rejected'] = True
                        print(f"[TRACKING] Target {self.target_id} uncertainty exceeds threshold. REACQUISITION FAILED.")
                        self.event('candidate_rejected', target=self.target_id, north=d['n'], east=d['e'], reason='low-altitude confirmation failed')
                        self.set_target(self.global_p[0], self.global_p[1], 25)
                        self.phase_to('ASCEND')
                        return
                        
                    if dt_since_last <= 5.0:
                        # Confirmed!
                        print(f"[TRACKING] Target {self.target_id} CONFIRMED.")
                        self.set_target(d['n'], d['e'] + 0.65, 5)
                        self.phase_to('RELEASE')
                    else:
                        # Wait for reacquisition
                        self.set_target(d['n'], d['e'] + 0.65, 5)"""
data = re.sub(r'            elif self\.phase == \'DESCEND\':\s+if self\.arrived\(dwell=1\.5, speed=0\.4\):\s+d = self\.detections\[self\.target_id\]\s+if now - d\[\'last\'\] > 15:\s+d\[\'rejected\'\] = True\s+self\.event\(\'candidate_rejected\'.*?self\.phase_to\(\'RELEASE\'\)', tracking_injection, data, flags=re.DOTALL)

with open("mission.py", "w") as f:
    f.write(data)
