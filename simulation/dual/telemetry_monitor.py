import curses
import json
import rclpy
from rclpy.node import Node
from std_msgs.msg import String
from gz.transport13 import Node as GzNode
from gz.msgs10.pose_v_pb2 import Pose_V
from gz.msgs10.actuators_pb2 import Actuators
import time
import math
from collections import deque

class TelemetryMonitor(Node):
    def __init__(self):
        super().__init__('telemetry_monitor')
        self.drones = {1: None, 2: None}
        self.gz_pose_history = {}
        self.locked_release_poses = {}
        
        # Phase 2: Actuators caching
        self.gz_actuators = {1: {"vel": None, "time": 0}, 2: {"vel": None, "time": 0}}
        
        self.create_subscription(String, '/swarm/drone1/state', lambda m: self.update_state(1, m), 10)
        self.create_subscription(String, '/swarm/drone2/state', lambda m: self.update_state(2, m), 10)
        
        self.gz = GzNode()
        self.gz.subscribe(Pose_V, '/world/dual_rescue/dynamic_pose/info', self.gz_pose_cb)
        self.gz.subscribe(Actuators, '/rescue_0/command/motor_speed', lambda m: self.gz_actuator_cb(1, m))
        self.gz.subscribe(Actuators, '/rescue_1/command/motor_speed', lambda m: self.gz_actuator_cb(2, m))
        
    def gz_pose_cb(self, msg):
        now = time.time()
        for p in msg.pose:
            if p.name.startswith('parcel'):
                if p.name not in self.gz_pose_history:
                    self.gz_pose_history[p.name] = deque(maxlen=50)
                self.gz_pose_history[p.name].append((now, p.position.z))

    def gz_actuator_cb(self, idx, msg):
        self.gz_actuators[idx] = {"vel": list(msg.velocity), "time": time.time()}

    def update_state(self, i, msg):
        try:
            d = json.loads(msg.data)
            d['rx_time'] = time.time()
            self.drones[i] = d
            
            lr = d.get('latest_release')
            if lr:
                pkg_id = lr.get('package_id')
                if pkg_id and pkg_id not in self.locked_release_poses:
                    hist = self.gz_pose_history.get(pkg_id, [])
                    if hist:
                        closest = min(hist, key=lambda x: abs(x[0] - d['rx_time']))
                        offset = abs(closest[0] - d['rx_time'])
                        if offset <= 0.2:
                            self.locked_release_poses[pkg_id] = (closest[1], offset)
                        else:
                            self.locked_release_poses[pkg_id] = None
                    else:
                        self.locked_release_poses[pkg_id] = None
        except Exception:
            pass

def draw_dashboard(stdscr, node):
    curses.curs_set(0)
    stdscr.nodelay(True)
    
    # Motor configuration ordering strictly derived from verified RescueHeavy/PX4 Quad-X
    # This must remain consistent with the physical vehicle geometry.
    MOTOR_NAMES = ["M0 Front Right", "M1 Rear Left", "M2 Front Left", "M3 Rear Right"]
    C_T = 2.5e-5
    
    while True:
        rclpy.spin_once(node, timeout_sec=0.1)
        
        stdscr.erase()
        h, w = stdscr.getmaxyx()
        if h < 51 or w < 90:
            stdscr.addstr(0, 0, f"Terminal too small (need 51x90, have {h}x{w})")
            stdscr.refresh()
            time.sleep(0.1)
            continue
            
        now = time.time()
        
        def safe_get(d, keys, default="--"):
            for k in keys:
                if not isinstance(d, dict) or k not in d: return default
                d = d[k]
                if d is None: return default
            return d

        d1 = node.drones[1] or {}
        d2 = node.drones[2] or {}
        
        # -- HEADER --
        stdscr.addstr(0, 0, "="*85)
        stdscr.addstr(1, 0, f"{'DRONE 1':<41} | {'DRONE 2':<41}")
        stdscr.addstr(2, 0, "-"*85)
        
        # -- FLIGHT --
        stdscr.addstr(3, 0, f"[ FLIGHT ]{' '*31} | [ FLIGHT ]")
        phase1 = safe_get(d1, ['mission', 'phase']); phase2 = safe_get(d2, ['mission', 'phase'])
        stdscr.addstr(4, 0, f"Phase:       {phase1:<28} | Phase:       {phase2}")
        
        wp1 = f"{safe_get(d1, ['mission', 'route_index'])}/{safe_get(d1, ['mission', 'route_total'])} ({safe_get(d1, ['mission', 'route_percent'], 0):.0f}%)"
        wp2 = f"{safe_get(d2, ['mission', 'route_index'])}/{safe_get(d2, ['mission', 'route_total'])} ({safe_get(d2, ['mission', 'route_percent'], 0):.0f}%)"
        stdscr.addstr(5, 0, f"Waypoint:    {wp1:<28} | Waypoint:    {wp2}")
        
        pos1 = f"N:{safe_get(d1, ['position', 'north_m'], 0):.1f} E:{safe_get(d1, ['position', 'east_m'], 0):.1f}"
        pos2 = f"N:{safe_get(d2, ['position', 'north_m'], 0):.1f} E:{safe_get(d2, ['position', 'east_m'], 0):.1f}"
        stdscr.addstr(6, 0, f"Position:    {pos1:<28} | Position:    {pos2}")
        
        alt1 = f"{safe_get(d1, ['position', 'altitude_m'], 0):.2f} m"
        alt2 = f"{safe_get(d2, ['position', 'altitude_m'], 0):.2f} m"
        stdscr.addstr(7, 0, f"Altitude:    {alt1:<28} | Altitude:    {alt2}")
        
        spd1 = f"{safe_get(d1, ['speed', 'total_mps'], 0):.1f} (H:{safe_get(d1, ['speed', 'horizontal_mps'], 0):.1f} V:{safe_get(d1, ['speed', 'vertical_mps'], 0):.1f})"
        spd2 = f"{safe_get(d2, ['speed', 'total_mps'], 0):.1f} (H:{safe_get(d2, ['speed', 'horizontal_mps'], 0):.1f} V:{safe_get(d2, ['speed', 'vertical_mps'], 0):.1f})"
        stdscr.addstr(8, 0, f"Speed (3D):  {spd1:<28} | Speed (3D):  {spd2}")
        
        att1 = f"R:{safe_get(d1, ['attitude', 'roll_deg'], 0):.0f} P:{safe_get(d1, ['attitude', 'pitch_deg'], 0):.0f} Y:{safe_get(d1, ['attitude', 'yaw_deg'], 0):.0f}"
        att2 = f"R:{safe_get(d2, ['attitude', 'roll_deg'], 0):.0f} P:{safe_get(d2, ['attitude', 'pitch_deg'], 0):.0f} Y:{safe_get(d2, ['attitude', 'yaw_deg'], 0):.0f}"
        stdscr.addstr(9, 0, f"Attitude:    {att1:<28} | Attitude:    {att2}")
        
        arm1 = "ARMED" if safe_get(d1, ['armed']) == 2 else "DISARMED"
        arm2 = "ARMED" if safe_get(d2, ['armed']) == 2 else "DISARMED"
        stdscr.addstr(10, 0, f"Armed:       {arm1:<28} | Armed:       {arm2}")
        
        # -- PAYLOAD --
        stdscr.addstr(12, 0, f"[ PAYLOAD ]{' '*30} | [ PAYLOAD ]")
        pkg1 = f"{safe_get(d1, ['payload', 'initial_packages'], 0)} init, {safe_get(d1, ['payload', 'packages_remaining'], 0)} rem"
        pkg2 = f"{safe_get(d2, ['payload', 'initial_packages'], 0)} init, {safe_get(d2, ['payload', 'packages_remaining'], 0)} rem"
        stdscr.addstr(13, 0, f"Packages:    {pkg1:<28} | Packages:    {pkg2}")
        
        mass1 = f"{safe_get(d1, ['payload', 'payload_remaining_kg'], 0):.2f} kg rem"
        mass2 = f"{safe_get(d2, ['payload', 'payload_remaining_kg'], 0):.2f} kg rem"
        stdscr.addstr(14, 0, f"Payload:     {mass1:<28} | Payload:     {mass2}")
        
        del1 = f"{safe_get(d1, ['mission', 'deliveries'])} delivered, {safe_get(d1, ['mission', 'rejected'])} rej"
        del2 = f"{safe_get(d2, ['mission', 'deliveries'])} delivered, {safe_get(d2, ['mission', 'rejected'])} rej"
        stdscr.addstr(15, 0, f"Deliveries:  {del1:<28} | Deliveries:  {del2}")
        
        # -- PROPULSION Phase 2A --
        stdscr.addstr(17, 0, "="*85)
        stdscr.addstr(18, 0, f"[ PROPULSION - COMMAND / ESTIMATE ]       | [ PROPULSION - COMMAND / ESTIMATE ]")
        
        for didx, d_col in [(1, 0), (2, 44)]:
            act = node.gz_actuators[didx]
            auw = 3.65 + float(safe_get(node.drones[didx] or {}, ['payload', 'payload_remaining_kg'], 0))
            weight_N = auw * 9.81
            
            # Theoretical maxes
            stdscr.addstr(19, d_col, f"Theo Max Thrust: 100 N (Max T/W: {100/weight_N:.2f})")
            stdscr.addstr(20, d_col, f"Model AUW: {auw:.2f} kg | Weight: {weight_N:.2f} N")
            
            if act["vel"] is None:
                for i in range(4):
                    stdscr.addstr(22 + i*3, d_col, f"{MOTOR_NAMES[i]}:")
                    stdscr.addstr(23 + i*3, d_col, f"  Cmd Omega: N/A  | Cmd RPM: N/A")
                    stdscr.addstr(24 + i*3, d_col, f"  Est Thrust: N/A")
                stdscr.addstr(35, d_col, "Total Cmd-Est Thrust: N/A")
            else:
                is_stale = (now - act["time"]) > 1.0
                vels = act["vel"]
                total_t = 0.0
                for i in range(min(4, len(vels))):
                    om = vels[i]
                    rpm = om * 60 / (2 * math.pi)
                    t_est = C_T * (om ** 2)
                    total_t += t_est
                    stdscr.addstr(22 + i*3, d_col, f"{MOTOR_NAMES[i]}:")
                    stdscr.addstr(23 + i*3, d_col, f"  Cmd Omega: {om:.1f} rad/s | Cmd RPM: {rpm:.0f}")
                    stdscr.addstr(24 + i*3, d_col, f"  Est Thrust: {t_est:.2f} N")
                
                status_str = " (MOTOR DATA STALE)" if is_stale else ""
                stdscr.addstr(35, d_col, f"Total Cmd-Est Thrust: {total_t:.2f} N{status_str}")
                stdscr.addstr(36, d_col, f"Command-estimated T/W: {total_t / weight_N:.2f}")

        # Params note
        note1 = "Model Params: motorConstant=2.5e-5, maxRotVelocity=1000, rotorVelocitySlowdownSim=10,"
        note2 = "              timeConstantUp=0.0125, timeConstantDown=0.025"
        note3 = "Note: Rotor command is not physical rotor measurement; motor dynamics introduce lag."
        stdscr.addstr(38, 0, note1)
        stdscr.addstr(39, 0, note2)
        stdscr.addstr(40, 0, note3)
        
        # -- COMMUNICATION / LATEST DELIVERY --
        stdscr.addstr(42, 0, "="*85)
        stdscr.addstr(43, 0, f"[ COMMUNICATION ]                       | [ LATEST DELIVERY ]")
        
        a1 = now - d1.get('rx_time', 0) if 'rx_time' in d1 else 999
        a2 = now - d2.get('rx_time', 0) if 'rx_time' in d2 else 999
        s1 = f"ONLINE (Age: {a1:.2f}s)" if a1 < 2 else "OFFLINE"
        s2 = f"ONLINE (Age: {a2:.2f}s)" if a2 < 2 else "OFFLINE"
        
        stdscr.addstr(44, 0, f"D1 -> D2:    {s1:<23} | ")
        stdscr.addstr(45, 0, f"D2 -> D1:    {s2:<23} | ")
        
        lr1 = d1.get('latest_release'); lr2 = d2.get('latest_release')
        lr = lr1; dr = 1
        if lr2 and (not lr1 or lr2.get('runtime_monotonic_s', 0) > lr1.get('runtime_monotonic_s', 0)):
            lr = lr2; dr = 2
        
        if lr:
            pkg_id = lr.get('package_id')
            stdscr.addstr(44, 42, f"Drone:       {dr}")
            stdscr.addstr(45, 42, f"Package ID:  {pkg_id}")
            stdscr.addstr(46, 42, f"Target ID:   {lr.get('target_id')}")
            stdscr.addstr(47, 42, f"Cmd Alt:     {lr.get('commanded_altitude_m')} m")
            stdscr.addstr(48, 42, f"Veh Rel Alt: {lr.get('actual_vehicle_altitude_m', 0):.2f} m")
            
            # Pose policy
            locked = node.locked_release_poses.get(pkg_id, "PENDING")
            if locked and locked != "PENDING":
                alt, offset = locked
                stdscr.addstr(49, 42, f"Pkg pose near obs release: {alt:.2f}m (dt:{offset:.2f}s)")
            else:
                stdscr.addstr(49, 42, f"Pkg pose near release: unavailable")
        else:
            stdscr.addstr(44, 42, f"Drone:       --")
            stdscr.addstr(45, 42, f"Package ID:  --")
                
        # Separation
        if d1 and d2 and a1 < 2 and a2 < 2:
            pn1 = safe_get(d1, ['position', 'north_m']); pe1 = safe_get(d1, ['position', 'east_m']); pd1 = safe_get(d1, ['position', 'down_m'])
            pn2 = safe_get(d2, ['position', 'north_m']); pe2 = safe_get(d2, ['position', 'east_m']); pd2 = safe_get(d2, ['position', 'down_m'])
            if pn1 != "--" and pn2 != "--":
                dh = math.hypot(pn1-pn2, pe1-pe2)
                dv = abs(pd1-pd2)
                d3 = math.sqrt(dh**2 + dv**2)
                stdscr.addstr(46, 0, f"Seq (1/2):   {d1.get('sequence')} / {d2.get('sequence')}")
                stdscr.addstr(47, 0, f"Sep Horiz:   {dh:.1f} m")
                stdscr.addstr(48, 0, f"Sep Vert:    {dv:.1f} m")
                stdscr.addstr(49, 0, f"Sep 3D:      {d3:.1f} m")
        
        stdscr.refresh()
        c = stdscr.getch()
        if c == ord('q'): break

def main():
    rclpy.init()
    node = TelemetryMonitor()
    curses.wrapper(draw_dashboard, node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
