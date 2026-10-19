import re

with open("mission.py", "r") as f:
    data = f.read()

# Add gz actuator subscription
gz_sub = """        self.gz.subscribe(Image, f'/rescue_{i}/camera', self.image)
        
        self.motor_speeds = []
        # Subscribe to gazebo motor speed commands
        from gz.msgs10.actuators_pb2 import Actuators
        self.gz.subscribe(Actuators, f'/rescue_{i}/command/motor_speed', lambda m: setattr(self, "motor_speeds", list(m.velocity)))
"""
data = re.sub(r"self\.gz\.subscribe\(Image,\s*f'/rescue_\{i\}/camera',\s*self\.image\)", gz_sub, data)

# Replace CSV header
new_header = """        self.csv.writerow([
            'elapsed', 'phase', 'north', 'east', 'altitude',
            'route_index', 'armed', 'nav_state', 'frames',
            'auw_kg', 'tw_ratio', 'battery_soc_pct', 'power_w',
            'target_n', 'target_e', 'target_alt', 'pos_err_h', 'alt_err',
            'roll', 'pitch', 'yaw', 'vx', 'vy', 'vz',
            'throttle'
        ])"""
data = re.sub(r'self\.csv\.writerow\(\[\s*\'elapsed\',.*?\'power_w\',\s*\]\)', new_header, data, flags=re.DOTALL)

# Replace CSV writing block
new_write = """                target_n, target_e, target_alt = 'N/A', 'N/A', 'N/A'
                pos_err_h, alt_err = 'N/A', 'N/A'
                if self.target_n is not None:
                    target_n, target_e, target_alt = self.target_n, self.target_e, -self.target_d
                    pos_err_h = math.hypot(n - target_n, e - target_e)
                    alt_err = -z - target_alt
                
                roll, pitch, yaw = 'N/A', 'N/A', 'N/A'
                if self.att is not None:
                    q = self.att.q
                    t0 = +2.0 * (q[0] * q[1] + q[2] * q[3])
                    t1 = +1.0 - 2.0 * (q[1] * q[1] + q[2] * q[2])
                    roll = math.atan2(t0, t1)
                    t2 = +2.0 * (q[0] * q[2] - q[3] * q[1])
                    t2 = max(-1.0, min(1.0, t2))
                    pitch = math.asin(t2)
                    t3 = +2.0 * (q[0] * q[3] + q[1] * q[2])
                    t4 = +1.0 - 2.0 * (q[2] * q[2] + q[3] * q[3])
                    yaw = math.atan2(t3, t4)
                
                vx, vy, vz = 'N/A', 'N/A', 'N/A'
                if self.p is not None:
                    vx, vy, vz = self.p.vx, self.p.vy, self.p.vz
                    
                throttle = 'N/A'
                if hasattr(self, 'motor_speeds') and self.motor_speeds:
                    # In SITL: omega = 150 + u * (1000 - 150) = 150 + 850 * u
                    # => u = (omega - 150) / 850
                    avg_omega = sum(self.motor_speeds) / len(self.motor_speeds)
                    throttle = (avg_omega - 150) / 850.0
                    
                self.csv.writerow([
                    round(now - self.start, 2), self.phase, n, e, -z,
                    self.index, self.s.arming_state, self.s.nav_state, self.frames,
                    auw, prop.tw_ratio, round(self.battery_integrator.soc * 100, 1),
                    prop.total_hover_power_w,
                    target_n, target_e, target_alt, pos_err_h, alt_err,
                    roll, pitch, yaw, vx, vy, vz, throttle
                ])"""
data = re.sub(r'self\.csv\.writerow\(\[\s*round\(now - self\.start.*?\]\)', new_write, data, flags=re.DOTALL)

with open("mission.py", "w") as f:
    f.write(data)
