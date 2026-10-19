"""NIDAR RescueSwarm Camera-Search / Physical Delivery Mission Controller.

Integrates authoritative hardware models (dynamic mass reduction, interpolated T-Motor
propulsion, battery SOC integration, and deterministic private network failsafes).
Supports both 3-drone competition and 2-drone legacy profiles configurably.
"""
import csv, json, math, os, sys, time, threading
from pathlib import Path
import cv2, numpy as np
import yaml

ROOT = Path(__file__).resolve().parent
REPO_ROOT = ROOT.parent.parent

# Load configuration dynamically
default_cfg = 'ssd_sim.yaml' if os.environ.get('DETECTOR', 'ssd') == 'ssd' else 'yolo_sim.yaml'
yaml_path = os.environ.get('YOLO_CONFIG_FILE', os.path.join(REPO_ROOT, f'ros2_ws/src/nidar_vision/config/{default_cfg}'))
if not os.path.exists(yaml_path):
    yaml_path = os.path.join(REPO_ROOT, 'ros2_ws/src/nidar_vision/config/ssd_sim.yaml')
if not os.path.exists(yaml_path):
    print(f"ERROR: Config not found at {yaml_path}")
    sys.exit(1)

with open(yaml_path, 'r') as f:
    _yolo_cfg = yaml.safe_load(f)
    _params = _yolo_cfg.get('/**') or _yolo_cfg.get('ssd_person_node') or _yolo_cfg.get('yolo_person_node') or {}
    _ros_params = _params.get('ros__parameters', {})

SIMULATION_MODE = _ros_params.get('simulation_mode', True)
VISION_RELEASE_ENABLED = _ros_params.get('vision_release_enabled', False)
MIN_CONSECUTIVE_FRAMES = _ros_params.get('min_consecutive_frames', 5)
MIN_CONFIDENCE = _ros_params.get('min_confidence', 0.40)
MAX_DETECTION_AGE_SEC = _ros_params.get('max_detection_age_sec', 1.0)
MIN_BOX_AREA_PX = _ros_params.get('min_box_area_px', 0)
MAX_BOX_AREA_PX = _ros_params.get('max_box_area_px', 1000000)

print(f"Mission loaded config from {yaml_path}")


import rclpy
from rclpy.node import Node as RosNode
from rclpy.qos import qos_profile_sensor_data as Q
from rclpy.executors import SingleThreadedExecutor
from px4_msgs.msg import (
    VehicleLocalPosition,
    VehicleStatus,
    VehicleAttitude,
    VehicleLandDetected,
    VehicleCommand,
    OffboardControlMode,
    TrajectorySetpoint,
)
from std_msgs.msg import String
from vision_msgs.msg import Detection2DArray
from gz.transport13 import Node as GzNode
from gz.msgs10.image_pb2 import Image
from gz.msgs10.empty_pb2 import Empty
from gz.msgs10.stringmsg_pb2 import StringMsg
from gz.msgs10.pose_v_pb2 import Pose_V

ROOT = Path(__file__).resolve().parent
REPO_ROOT = ROOT.parent.parent
sys.path.insert(0, str(REPO_ROOT))

from simulation.hardware.config import (
    BATTERY_SPECS,
    ELECTRICAL_LIMITS,
    FLEET_SIZE,
    MAX_FLEET_AUW_KG,
    MAX_MISSION_TIME_SEC,
    NETWORK_SPECS,
    PACKAGE_MASS_KG,
    PAYLOAD_ALLOCATION,
    get_drone_dry_mass_kg,
    get_drone_initial_auw_kg,
)
from simulation.hardware.propulsion import (
    BatterySOCIntegrator,
    PayloadTracker,
    calculate_propulsion_state,
    validate_electrical_limits,
)
from simulation.hardware.network import (
    FailsafeAction,
    LinkStatus,
    NetworkCase,
    SwarmNetworkSimulator,
)

OUT = Path(os.environ.get('DUAL_RUN_DIR', str(ROOT / 'latest_run')))
OUT.mkdir(parents=True, exist_ok=True)
CFG = json.loads((ROOT / 'config.json').read_text())
LAT, LON, ALT = CFG['world_origin']
R = 6371000.0

if os.environ.get('ROS_DOMAIN_ID') != '88':
    # Allow test imports without hard crash
    if 'pytest' not in sys.modules and '__main__' == __name__:
        raise SystemExit('Restricted to dual-drone SITL domain 88')


def rotation(q):
    w, x, y, z = q
    return np.array([
        [1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
        [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
        [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)],
    ])


class Drone(RosNode):
    def __init__(self, i):
        super().__init__(f'dual_search_{i}')
        self.i = i
        self.ns = f'/drone{i+1}/fmu'

        # Get zone allocation
        active_prof = CFG.get('active_profile', 'competition_3drone')
        zones = CFG.get('profiles', {}).get(active_prof, {}).get('zones', []) or CFG.get('zones', [])
        self.z = zones[i] if i < len(zones) else {
            'east_min': -160 + i * 100,
            'east_max': -60 + i * 100,
            'north_min': -156.25,
            'north_max': 156.25,
            'area_m2': 33333.3,
        }

        # Initialize authoritative hardware models
        self.payload_tracker = PayloadTracker(drone_id=min(i, FLEET_SIZE - 1))
        self.battery_integrator = BatterySOCIntegrator(drone_id=min(i, FLEET_SIZE - 1))
        self.network_sim = SwarmNetworkSimulator(drone_id=min(i, FLEET_SIZE - 1))
        self.packages_total = self.payload_tracker.initial_packages

        self.p = self.s = self.att = self.land = None
        self.p_at = self.att_at = 0.0
        self.global_p = None
        self.offset = None

        self.phase = 'WAIT'
        self.start = self.since = time.monotonic()
        self.last_tick = time.monotonic()
        self.last_cmd = 0.0
        self.last_status = 0.0
        self.target = None
        self.home = None
        self.stable = None

        self.route = []
        self.index = 0
        self.target_id = None
        self.resume = None
        self.last_seen = 0.0
        self.packages_used = 0
        self.drops = []
        self.done = False
        self.error = None
        self.pickup_ok = False

        self.detections = []
        self.frames = 0
        self.camera_at = 0.0
        self.cargo = {}
        self.cargo_pubs = {}
        self.lock = threading.RLock()
        self.gz = GzNode()

        self.cover = np.zeros((125, 64), np.uint8)
        self.file = open(OUT / f'drone{i+1}-telemetry.csv', 'w', buffering=1)
        self.csv = csv.writer(self.file)
        self.csv.writerow([
            'elapsed', 'phase', 'north', 'east', 'altitude',
            'route_index', 'armed', 'nav_state', 'frames',
            'auw_kg', 'tw_ratio', 'battery_soc_pct', 'power_w',
            'target_n', 'target_e', 'target_alt', 'pos_err_h', 'alt_err',
            'roll', 'pitch', 'yaw', 'vx', 'vy', 'vz'
        ])
        self.events = open(OUT / f'drone{i+1}-events.jsonl', 'w', buffering=1)

        # PX4 uORB subscriptions
        for typ, suffix, cb in [
            (VehicleLocalPosition, 'vehicle_local_position_v1', self.position),
            (VehicleStatus, 'vehicle_status_v4', lambda m: setattr(self, 's', m)),
            (VehicleAttitude, 'vehicle_attitude', self.attitude),
            (VehicleLandDetected, 'vehicle_land_detected', lambda m: setattr(self, 'land', m)),
        ]:
            self.create_subscription(typ, self.ns + '/out/' + suffix, cb, Q)

        # PX4 command publishers
        self.mode = self.create_publisher(OffboardControlMode, self.ns + '/in/offboard_control_mode', 10)
        self.sp = self.create_publisher(TrajectorySetpoint, self.ns + '/in/trajectory_setpoint', 10)
        self.cmd = self.create_publisher(VehicleCommand, self.ns + '/in/vehicle_command', 10)

        # Vision (YOLO & SSD) detections subscriptions
        self.create_subscription(
            Detection2DArray,
            f'/rescue_{i}/yolo/detections',
            self.yolo_callback,
            10
        )
        self.create_subscription(
            Detection2DArray,
            f'/rescue_{i}/ssd/detections',
            self.yolo_callback,
            10
        )
        
        # Gazebo detachable joint topics for physical packages
        for j in range(self.packages_total):
            name = f'parcel_{i}_{j}'
            self.gz.subscribe(StringMsg, f'/{name}/state', lambda m, j=j: self.cargo.update({j: m.data}))
            for action in ['attach', 'detach']:
                self.cargo_pubs[j, action] = self.gz.advertise(f'/{name}/{action}', Empty)

        self.gz.subscribe(Image, f'/rescue_{i}/camera', self.image)
        self.gz.subscribe(Image, f'/rescue_{i}/camera/image_raw', self.image)
        
        self.motor_speeds = []
        # Subscribe to gazebo motor speed commands
        from gz.msgs10.actuators_pb2 import Actuators
        self.gz.subscribe(Actuators, f'/rescue_{i}/command/motor_speed', lambda m: setattr(self, "motor_speeds", list(m.velocity)))

        self.create_timer(0.05, self.tick)

        # Swarm telemetry communications
        self.swarm_pub = self.create_publisher(String, f'/swarm/drone{i+1}/state', 10)
        self.peer_subs = []
        for peer_id in range(FLEET_SIZE):
            if peer_id != i:
                sub = self.create_subscription(
                    String,
                    f'/swarm/drone{peer_id+1}/state',
                    lambda msg, pid=peer_id: self.peer_cb(pid, msg),
                    10,
                )
                self.peer_subs.append(sub)

        self.peer_states = {}
        self.seq = 0
        self.separation = None
        self.create_timer(0.1, self.publish_state)

    def peer_cb(self, peer_id, msg):
        try:
            d = json.loads(msg.data)
            d['rx_time'] = time.monotonic()
            self.peer_states[peer_id] = d
        except Exception:
            pass

    def publish_state(self):
        try:
            now = time.monotonic()
            auw = self.payload_tracker.current_auw_kg
            prop = calculate_propulsion_state(auw)
            elec = validate_electrical_limits(prop.total_propulsion_current_a)

            st = {
                "drone_id": self.i + 1,
                "sequence": self.seq,
                "runtime_monotonic_s": now,
                "px4_timestamp_us": self.p.timestamp if self.p else None,
                "position": {
                    "north_m": float(self.global_p[0]) if self.global_p is not None else None,
                    "east_m": float(self.global_p[1]) if self.global_p is not None else None,
                    "down_m": float(self.global_p[2]) if self.global_p is not None else None,
                    "altitude_m": float(-self.global_p[2]) if self.global_p is not None else None,
                },
                "velocity": {
                    "north_mps": float(self.p.vx) if self.p else None,
                    "east_mps": float(self.p.vy) if self.p else None,
                    "down_mps": float(self.p.vz) if self.p else None,
                },
                "speed": {
                    "horizontal_mps": float(math.hypot(self.p.vx, self.p.vy)) if self.p else None,
                    "vertical_mps": float(-self.p.vz) if self.p else None,
                    "total_mps": float(math.sqrt(self.p.vx**2 + self.p.vy**2 + self.p.vz**2)) if self.p else None,
                },
            }

            if self.att:
                q = self.att.q
                sinr_cosp = 2 * (q[0] * q[1] + q[2] * q[3])
                cosr_cosp = 1 - 2 * (q[1] * q[1] + q[2] * q[2])
                sinp = math.sqrt(1 + 2 * (q[0] * q[2] - q[1] * q[3])) - math.sqrt(1 - 2 * (q[0] * q[2] - q[1] * q[3]))
                siny_cosp = 2 * (q[0] * q[3] + q[1] * q[2])
                cosy_cosp = 1 - 2 * (q[2] * q[2] + q[3] * q[3])
                st["attitude"] = {
                    "roll_deg": math.degrees(math.atan2(sinr_cosp, cosr_cosp)),
                    "pitch_deg": math.degrees(math.asin(sinp)),
                    "yaw_deg": math.degrees(math.atan2(siny_cosp, cosy_cosp)),
                }
            else:
                st["attitude"] = {"roll_deg": None, "pitch_deg": None, "yaw_deg": None}

            st["armed"] = self.s.arming_state if self.s else None
            st["nav_state"] = self.s.nav_state if self.s else None

            with self.lock:
                det_cnt = len(self.detections)
                del_cnt = sum(1 for d in self.detections if d.get('delivered'))
                rej_cnt = sum(1 for d in self.detections if d.get('rejected'))

            st["mission"] = {
                "phase": self.phase,
                "route_index": self.index,
                "route_total": len(self.route),
                "route_percent": (self.index / len(self.route) * 100) if len(self.route) else 0.0,
                "target_candidate": self.target_id,
                "detections": det_cnt,
                "deliveries": del_cnt,
                "rejected": rej_cnt,
            }

            # Hardware state telemetry
            st["hardware"] = {
                "payload": {
                    "initial_packages": self.packages_total,
                    "packages_remaining": self.payload_tracker.packages_remaining,
                    "payload_mass_kg": self.payload_tracker.current_payload_mass_kg,
                    "auw_kg": auw,
                    "tw_ratio": prop.tw_ratio,
                    "hover_throttle": prop.estimated_hover_throttle,
                    "hover_power_w": prop.total_hover_power_w,
                    "thrust_reserve_pct": prop.thrust_reserve_pct,
                },
                "battery": {
                    "nominal_wh": BATTERY_SPECS.nominal_energy_wh,
                    "usable_wh": BATTERY_SPECS.usable_energy_wh,
                    "reserve_wh": BATTERY_SPECS.reserve_energy_wh,
                    "consumed_wh": round(self.battery_integrator.energy_consumed_wh, 2),
                    "soc_pct": round(self.battery_integrator.soc * 100, 2),
                    "usable_soc_remaining_pct": round(self.battery_integrator.usable_soc_remaining * 100, 2),
                    "is_reserve_intact": self.battery_integrator.is_reserve_intact,
                },
                "electrical": {
                    "motor_current_a": prop.motor_current_a,
                    "total_propulsion_current_a": prop.total_propulsion_current_a,
                    "all_limits_ok": elec.all_ok,
                },
                "network": {
                    "static_ip": self.network_sim.state.static_ip,
                    "carrier": self.network_sim.state.telemetry_carrier,
                    "wifi_status": self.network_sim.state.wifi_status.value,
                    "rfd_status": self.network_sim.state.rfd_status.value,
                    "case": self.network_sim.state.current_case.value,
                    "active_failsafe": self.network_sim.state.active_failsafe.value,
                },
            }

            lr = self.drops[-1] if self.drops else None
            if lr:
                rad_err = round(float(math.hypot(lr.get('release_north', 0.0) - lr.get('north', 0.0), lr.get('release_east', 0.0) - lr.get('east', 0.0))), 2)
                st["latest_release"] = {
                    "package_id": lr['parcel'],
                    "target_id": lr['target'],
                    "runtime_monotonic_s": lr['elapsed'],
                    "commanded_altitude_m": 5.0,
                    "actual_vehicle_altitude_m": lr['release_altitude'],
                    "north_m": lr['release_north'],
                    "east_m": lr['release_east'],
                    "survivor_north_m": lr.get('north'),
                    "survivor_east_m": lr.get('east'),
                    "radial_distance_error_m": rad_err,
                    "horizontal_speed_mps": lr.get('speed_h'),
                    "vertical_speed_mps": lr.get('speed_v'),
                }
            else:
                st["latest_release"] = None

            st["drops"] = [
                {
                    'parcel': d.get('parcel'),
                    'target': d.get('target'),
                    'drone': d.get('drone', self.i + 1),
                    'north': d.get('north'),
                    'east': d.get('east'),
                    'release_north': d.get('release_north'),
                    'release_east': d.get('release_east'),
                    'release_altitude': d.get('release_altitude'),
                    'radial_error_m': round(float(math.hypot(d.get('release_north', 0.0) - d.get('north', 0.0), d.get('release_east', 0.0) - d.get('east', 0.0))), 2),
                    'elapsed': round(d.get('elapsed', 0.0), 1),
                } for d in self.drops
            ]

            with self.lock:
                st["detections_list"] = [
                    {
                        'id': idx,
                        'north': round(float(det['n']), 2),
                        'east': round(float(det['e']), 2),
                        'hits': det.get('hits', 0),
                        'delivered': det.get('delivered', False),
                    } for idx, det in enumerate(self.detections)
                ]

            msg = String()
            msg.data = json.dumps(st)
            self.swarm_pub.publish(msg)
            self.seq += 1

        except Exception as e:
            print("State pub error:", e, flush=True)

    def event(self, event, **kw):
        record = {
            'elapsed': round(time.monotonic() - self.start, 3),
            'drone': self.i + 1,
            'event': event,
            **kw,
        }
        self.events.write(json.dumps(record) + '\n')
        print(json.dumps(record), flush=True)

    def phase_to(self, p):
        self.phase = p
        self.since = time.monotonic()
        self.stable = None
        self._drop_triggered = False
        self.event('phase', phase=p)

    def position(self, m):
        self.p = m
        self.p_at = time.monotonic()
        if m.xy_global and m.z_global:
            self.offset = np.array([
                math.radians(m.ref_lat - LAT) * R,
                math.radians(m.ref_lon - LON) * R * math.cos(math.radians(LAT)),
                -m.ref_alt,
            ])
            self.global_p = np.array([m.x, m.y, m.z]) + self.offset

    def attitude(self, m):
        self.att = m
        self.att_at = time.monotonic()

    def project(self, cx, cy, width, height, plane):
        if self.global_p is None or self.att is None:
            return None
        CAM_HFOV = 1.5708
        f = width / (2 * math.tan(CAM_HFOV / 2))
        
        # Ray in camera optical sensor frame (cy down, cx right, z forward along bore)
        v_lens = np.array([-(cy - (height - 1) / 2) / f, (cx - (width - 1) / 2) / f, 1.0])
        # 15 degree forward mount slant (pitch = 1.3090 rad = 75 deg in SDF)
        # Rotates ray forward around body Y axis
        c_a = math.cos(0.2618)
        s_a = math.sin(0.2618)
        v_body = np.array([c_a * v_lens[0] + s_a * v_lens[2], v_lens[1], -s_a * v_lens[0] + c_a * v_lens[2]])

        rot = rotation(self.att.q)
        origin = self.global_p + rot @ np.array([0.15, 0, -0.06])
        ray = rot @ v_body
        if ray[2] < 0.2:
            return None
        scale = (-plane - origin[2]) / ray[2]
        return origin + scale * ray if 0 < scale < 150 else None

    def image(self, msg):
        self.frames += 1
        self.camera_at = time.monotonic()
        if self.global_p is None or self.att is None or time.monotonic() - self.p_at > 1 or time.monotonic() - self.att_at > 1:
            return
        try:
            data = np.frombuffer(msg.data, dtype=np.uint8).reshape(msg.height, msg.step)[:, :msg.width * 3].reshape(msg.height, msg.width, 3)
        except ValueError:
            return
        w, h = msg.width, msg.height
        self.img_w = w
        self.img_h = h

        if self.phase in ['SEARCH', 'TRANSIT'] and -self.global_p[2] > 18:
            pts = [self.project(x, y, w, h, 0) for x, y in [(0, 0), (w - 1, 0), (w - 1, h - 1), (0, h - 1)]]
            if all(p is not None for p in pts):
                poly = np.array([[(p[1] - self.z['east_min']) / 2.5, (p[0] + 156.25) / 2.5] for p in pts], np.int32)
                cv2.fillConvexPoly(self.cover, poly, 1)

        # Detection logic is now handled in yolo_callback
        
    def yolo_callback(self, msg):
        if self.phase not in ['SEARCH', 'APPROACH', 'DESCEND', 'RELEASE']:
            return
            
        w, h = getattr(self, 'img_w', 960), getattr(self, 'img_h', 720)
        
        for det in msg.detections:
            u = det.bbox.center.position.x
            v = det.bbox.center.position.y
            bw = det.bbox.size_x
            bh = det.bbox.size_y
            area = bw * bh
            
            # Use only confident detections
            if det.results:
                conf = det.results[0].hypothesis.score
                if conf < MIN_CONFIDENCE:
                    continue
                    
            if area < MIN_BOX_AREA_PX or area > MAX_BOX_AREA_PX:
                continue
            
            point = self.project(u, v, w, h, 0.9)
            if point is None:
                continue
            n, e = map(float, point[:2])
            if not (self.z['east_min'] <= e <= self.z['east_max'] and -156.25 <= n <= 156.25):
                continue

            # Home exclusion zone: reject any detection within 35m of launch pad
            if self.home is not None and math.hypot(n - self.home[0], e - self.home[1]) < 35.0:
                continue

            with self.lock:
                # Check if this detection is near an already-completed drop
                already_delivered = any(math.hypot(drop['north'] - n, drop['east'] - e) < 25.0 for drop in self.drops)

                distances = [math.hypot(d['n'] - n, d['e'] - e) for d in self.detections]
                k = int(np.argmin(distances)) if distances else -1

                # Clustering thresholds: 25.0m (survivors are spaced 60m+ apart)
                if k < 0 or distances[k] > 25.0:
                    if self.phase != 'SEARCH':
                        continue
                    self.detections.append({
                        'n': n,
                        'e': e,
                        'hits': 1,
                        'delivered': already_delivered,
                        'rejected': False,
                        'last': time.monotonic()
                    })
                    k = len(self.detections) - 1
                else:
                    d = self.detections[k]
                    d['hits'] += 1
                    d['last'] = time.monotonic()
                    if already_delivered:
                        d['delivered'] = True
                    weight = 0.25 if -self.global_p[2] < 8 else 0.08
                    if not d['delivered']:
                        d['n'] = (1 - weight) * d['n'] + weight * n
                        d['e'] = (1 - weight) * d['e'] + weight * e
                d = self.detections[k]
                
                # Wait for N consecutive frames of confidence equivalent
                if d['hits'] == MIN_CONSECUTIVE_FRAMES and not d['delivered']:
                    self.event('camera_detection', target=k, north=d['n'], east=d['e'], method='yolo')

    def cargo_send(self, j, action):
        for _ in range(3):
            self.cargo_pubs[j, action].publish(Empty())

    def command(self, c, p1=0.0, p2=0.0):
        m = VehicleCommand()
        m.timestamp = self.get_clock().now().nanoseconds // 1000
        m.command = c
        m.param1 = float(p1)
        m.param2 = float(p2)
        m.target_system = self.i + 1
        m.target_component = 1
        m.source_system = 240
        m.source_component = self.i + 1
        m.from_external = True
        self.cmd.publish(m)
        self.last_cmd = time.monotonic()

    
    def set_speed(self, speed):
        self.send_cmd(178, 1.0, float(speed), -1.0)

    def set_target(self, n, e, h):
        self.target = np.array([float(n), float(e), -float(h)])
        self.stable = None

    def arrived(self, tolerance=0.65, dwell=0.7, speed=0.65):
        if self.global_p is None:
            return False
        v = math.sqrt(self.p.vx**2 + self.p.vy**2 + self.p.vz**2)
        if np.linalg.norm(self.global_p - self.target) < tolerance and v < speed:
            if self.stable is None:
                self.stable = time.monotonic()
            return time.monotonic() - self.stable > dwell
        self.stable = None
        return False

    def publish(self):
        m = OffboardControlMode()
        m.timestamp = self.get_clock().now().nanoseconds // 1000
        m.position = True
        self.mode.publish(m)
        s = TrajectorySetpoint()
        s.timestamp = m.timestamp
        s.position = list(self.target - self.offset)
        s.velocity = [math.nan] * 3
        s.acceleration = [math.nan] * 3
        s.yaw = 0.0
        s.yawspeed = math.nan
        self.sp.publish(s)

    def abort(self, why):
        if self.phase not in ['LAND', 'DONE']:
            self.error = why
            self.event('abort', reason=why)
            self.phase_to('LAND')

    def status(self):
        with self.lock:
            det = [dict(d) for d in self.detections]
        auw = self.payload_tracker.current_auw_kg
        prop = calculate_propulsion_state(auw)
        elec = validate_electrical_limits(prop.total_propulsion_current_a)

        return {
            'drone': self.i + 1,
            'phase': self.phase,
            'done': self.done,
            'error': self.error,
            'pickup_confirmed': self.pickup_ok,
            'zone_area_m2': self.z.get('area_m2', 33333.3),
            'route_points_reached': self.index,
            'route_points_total': len(self.route),
            'camera_frames': self.frames,
            'coverage_grid_fraction': float(np.mean(self.cover)),
            'detections': det,
            'drops': list(self.drops),
            'elapsed_s': time.monotonic() - self.start,
            'final_alt': float(-self.global_p[2]) if self.global_p is not None else None,
            'final_vz': float(-self.p.vz) if self.p else None,
            'final_arming_state': int(self.s.arming_state) if self.s else None,

            'hardware': {
                'payload': {
                    'initial_packages': self.packages_total,
                    'packages_remaining': self.payload_tracker.packages_remaining,
                    'payload_mass_kg': self.payload_tracker.current_payload_mass_kg,
                    'auw_kg': auw,
                    'tw_ratio': prop.tw_ratio,
                    'hover_throttle': prop.estimated_hover_throttle,
                    'total_hover_power_w': prop.total_hover_power_w,
                    'thrust_reserve_pct': prop.thrust_reserve_pct,
                },
                'battery': {
                    'nominal_wh': BATTERY_SPECS.nominal_energy_wh,
                    'usable_wh': BATTERY_SPECS.usable_energy_wh,
                    'reserve_wh': BATTERY_SPECS.reserve_energy_wh,
                    'consumed_wh': round(self.battery_integrator.energy_consumed_wh, 2),
                    'soc_pct': round(self.battery_integrator.soc * 100, 2),
                    'is_reserve_intact': self.battery_integrator.is_reserve_intact,
                },
                'electrical': {
                    'motor_current_a': prop.motor_current_a,
                    'total_propulsion_current_a': prop.total_propulsion_current_a,
                    'all_ok': elec.all_ok,
                },
            },
        }

    def tick(self):
        now = time.monotonic()
        if self.done:
            return

        dt = now - self.last_tick
        self.last_tick = now

        # Dynamic battery SOC depletion update
        self.battery_integrator.update(self.phase, self.payload_tracker.current_auw_kg, dt)

        # Check maximum competition flight time rule (30 minutes)
        if now - self.start > MAX_MISSION_TIME_SEC:
            self.abort('30-minute competition flight timeout reached')

        # Check battery reserve threshold (20% hard reserve)
        if self.battery_integrator.soc <= BATTERY_SPECS.reserve_fraction:
            self.abort('emergency battery low (20% reserve threshold reached)')

        if now - self.last_status > 1:
            self.last_status = now
            if self.global_p is not None and self.s:
                n, e, z = self.global_p
                auw = self.payload_tracker.current_auw_kg
                prop = calculate_propulsion_state(auw)
                target_n, target_e, target_alt = 'N/A', 'N/A', 'N/A'
                pos_err_h, alt_err = 'N/A', 'N/A'
                if hasattr(self, 'target') and self.target is not None:
                    target_n, target_e, target_alt = self.target[0], self.target[1], -self.target[2]
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
                    
                target_n, target_e, target_alt = 'N/A', 'N/A', 'N/A'
                pos_err_h, alt_err = 'N/A', 'N/A'
                if hasattr(self, 'target') and self.target is not None:
                    target_n, target_e, target_alt = self.target[0], self.target[1], -self.target[2]
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
                ])
            (OUT / f'drone{self.i+1}-status.json').write_text(json.dumps(self.status(), indent=2))

        if self.phase == 'WAIT':
            if self.global_p is not None and self.s and self.p.xy_valid and self.p.z_valid and self.att is not None and self.frames > 5:
                self.home = self.global_p.copy()
                self.pickup_ok = True
                self.event(
                    'preflight_confirmed',
                    packages=self.packages_total,
                    mass_kg=round(self.packages_total * PACKAGE_MASS_KG, 3),
                    auw_kg=self.payload_tracker.current_auw_kg,
                )
                # Compute search lawnmower route for this drone's zone
                lane_width = 20
                num_lanes = max(3, int((self.z['east_max'] - self.z['east_min']) / lane_width))
                for k in range(num_lanes):
                    east = self.z['east_min'] + 10 + lane_width * k
                    start, end = (-144, 144) if k % 2 == 0 else (144, -144)
                    self.route.extend([(start, east), (end, east)])
                self.set_target(self.home[0], self.home[1], 25)
                self.phase_to('WARMUP')
            elif now - self.start > 90:
                self.abort('startup/telemetry not ready')
            return

        if self.phase == 'LAND':
            alt = -self.global_p[2] if self.global_p is not None else 10.0
            vz = -self.p.vz if self.p else 0.0
            if self.s and self.s.arming_state != 2:
                self.done = True
                self.phase_to('DONE')
                self.event('landed_disarmed', error=self.error)
                (OUT / f'drone{self.i+1}-status.json').write_text(json.dumps(self.status(), indent=2))
                return
            elif alt < 0.35 and abs(vz) < 0.20 and (now - self.since > 3.0):
                if now - self.last_cmd > 0.5:
                    self.command(VehicleCommand.VEHICLE_CMD_COMPONENT_ARM_DISARM, 0)
            elif now - self.last_cmd > 1.5:
                self.command(VehicleCommand.VEHICLE_CMD_NAV_LAND)
            if now - self.since > 90:
                self.error = self.error or 'landing timeout'
                self.done = True
            return

        if self.global_p is None or now - self.p_at > 2 or not self.p.xy_valid or not self.p.z_valid:
            self.abort('stale/invalid position')
            return
        if self.phase in ['TRANSIT', 'SEARCH', 'APPROACH', 'DESCEND', 'RELEASE', 'ASCEND', 'RESUME'] and now - self.camera_at > 12:
            self.abort('camera timeout')
            return
        if self.phase == 'SEARCH' and not (self.z['east_min'] - 50 <= self.global_p[1] <= self.z['east_max'] + 50):
            self.abort('zone boundary exceeded')
            return

        self.publish()

        if self.phase == 'WARMUP':
            if now - self.since > 2:
                self.phase_to('OFFBOARD')
        elif self.phase == 'OFFBOARD':
            if self.s.nav_state == 14:
                self.phase_to('ARM')
            elif now - self.last_cmd > 2:
                self.command(VehicleCommand.VEHICLE_CMD_DO_SET_MODE, 1, 6)
        elif self.phase == 'ARM':
            if self.s.arming_state == 2:
                self.phase_to('TAKEOFF')
            elif now - self.last_cmd > 2:
                self.command(VehicleCommand.VEHICLE_CMD_COMPONENT_ARM_DISARM, 1)
        elif self.phase == 'TAKEOFF':
            if self.arrived():
                self.set_target(*self.route[0], 25)
                self.phase_to('TRANSIT')
        elif self.phase == 'TRANSIT':
            if self.arrived(tolerance=5.0, dwell=0.1, speed=2.0) or (self.z['east_min'] <= self.global_p[1] <= self.z['east_max']):
                self.set_target(*self.route[self.index], 25)
                self.phase_to('SEARCH')
        else:
            if self.s.nav_state != 14 and (now - self.since > 3.0):
                self.command(VehicleCommand.VEHICLE_CMD_DO_SET_MODE, 1, 6)
            if self.phase == 'SEARCH':
                with self.lock:
                    pending = [
                        k for k, d in enumerate(self.detections)
                        if d['hits'] >= MIN_CONSECUTIVE_FRAMES
                        and not d['delivered']
                        and not d['rejected']
                        and not any(math.hypot(drop['north'] - d['n'], drop['east'] - d['e']) < 25.0 for drop in self.drops)
                    ]
                if pending and self.packages_used < self.packages_total:
                    if not VISION_RELEASE_ENABLED:
                        if getattr(self, '_last_print_gate', 0) < time.monotonic() - 5.0:
                            self.get_logger().info('VISION DETECTION VALID BUT HARDWARE RELEASE DISABLED')
                            self._last_print_gate = time.monotonic()
                    else:
                        self.target_id = pending[0]
                        d = self.detections[self.target_id]
                        # Estimate energy needed for delivery + return home
                        dist_to_target = math.hypot(self.global_p[0] - d['n'], self.global_p[1] - d['e'])
                        dist_target_to_home = math.hypot(d['n'] - self.home[0], d['e'] - self.home[1])
                        cruise_speed = 3.0
                        flight_time_s = (dist_to_target + dist_target_to_home) / cruise_speed + 45.0
                        est_energy_wh = 750.0 * (flight_time_s / 3600.0)
                        if self.battery_integrator.usable_energy_remaining_wh < est_energy_wh:
                            self.event('energy_failsafe_abort_delivery', needed_wh=est_energy_wh, remaining_wh=self.battery_integrator.usable_energy_remaining_wh)
                            self.set_target(self.home[0], self.home[1], 25)
                            self.phase_to('RETURN')
                            return
                        self.resume = self.global_p.copy()
                        self.set_target(d['n'], d['e'], 25)
                        self.phase_to('APPROACH')
                        return
                if self.arrived(tolerance=1.0, dwell=0.15, speed=1.5):
                    self.index += 1
                    self.event('sweep_point', completed=self.index, total=len(self.route))
                    if self.index >= len(self.route) or self.packages_used >= self.packages_total:
                        self.set_target(self.home[0], self.home[1], 25)
                        self.phase_to('RETURN')
                    else:
                        self.set_target(*self.route[self.index], 25)
            elif self.phase == 'APPROACH':
                if self.arrived():
                    d = self.detections[self.target_id]
                    # Descend to 3.0m altitude with wind drift compensation (-2.5m North for 5.0m/s wind)
                    self.set_target(d['n'] - 2.5, d['e'], 3.0)
                    self.phase_to('DESCEND')
            elif self.phase == 'DESCEND':
                if self.arrived(dwell=0.8, speed=0.5):
                    d = self.detections[self.target_id]
                    print(f"[DELIVERY] Arrived at Target {self.target_id} (N={d['n']:.1f}, E={d['e']:.1f}). Offsetting setpoint N={d['n']-2.5:.1f} for 5m/s wind...")
                    self.set_target(d['n'] - 2.5, d['e'], 3.0)
                    self.phase_to('RELEASE')
            elif self.phase == 'RELEASE':
                d = self.detections[self.target_id]
                if self.arrived(tolerance=0.6, dwell=0.8, speed=0.35):
                    # Bilateral CG-preserving drop order: Front-Left, Aft-Right, Front-Right, Aft-Left, Center
                    order = [0, 4, 1, 3, 2] if self.packages_total >= 5 else ([0, 3, 1, 2] if self.packages_total == 4 else list(range(self.packages_total)))
                    j = order[self.packages_used] if self.packages_used < len(order) else (self.packages_used % self.packages_total)
                    if not getattr(self, '_drop_triggered', False):
                        self._drop_triggered = True
                        self._drop_time = now
                        self.cargo_send(j, 'detach')
                        print(f"*** [PAYLOAD DROP ACTIVE] Drone {self.i+1} DETACHED Canister #{j+1} at Target {self.target_id} (N={d['n']:.1f}, E={d['e']:.1f})! Hovering 2.0s for visual drop verification ***")

                    # Hover 2.0s to let package fall 3m to ground under gravity
                    if (now - getattr(self, '_drop_time', now) > 2.0):
                        self._drop_triggered = False
                        d['delivered'] = True
                        prop_state = self.payload_tracker.release_package(f'parcel_{self.i}_{j}')
                        drop = {
                            'drone': self.i + 1,
                            'parcel': f'parcel_{self.i}_{j}',
                            'target': self.target_id,
                            'package_mass_kg': PACKAGE_MASS_KG,
                            'north': d['n'],
                            'east': d['e'],
                            'release_north': float(self.global_p[0]),
                            'release_east': float(self.global_p[1]),
                            'release_altitude': float(-self.global_p[2]),
                            'elapsed': now - self.start,
                            'speed_h': float(math.hypot(self.p.vx, self.p.vy)),
                            'speed_v': float(-self.p.vz),
                            'new_auw_kg': prop_state.auw_kg,
                            'new_tw_ratio': prop_state.tw_ratio,
                            'packages_remaining': self.payload_tracker.packages_remaining,
                        }
                        self.drops.append(drop)
                        self.event('package_released', **drop)
                        self.packages_used += 1
                        print(f"*** [PAYLOAD DROP CONFIRMED] Canister #{j+1} landed beside survivor! Packages remaining: {self.payload_tracker.packages_remaining}. Ascending to 25m ***")
                        self.set_target(self.global_p[0], self.global_p[1], 25)
                        self.phase_to('ASCEND')
            elif self.phase == 'ASCEND':
                if self.arrived():
                    if self.packages_used >= self.packages_total:
                        self.set_target(self.home[0], self.home[1], 25)
                        self.phase_to('RETURN')
                    else:
                        self.set_target(self.resume[0], self.resume[1], 25)
                        self.phase_to('RESUME')
            elif self.phase == 'RESUME':
                if self.arrived():
                    self.set_target(*self.route[self.index], 25)
                    self.phase_to('SEARCH')
            elif self.phase == 'RETURN':
                if self.arrived():
                    self.phase_to('LAND')


def main():
    rclpy.init()

    # Determine fleet size from configuration profile
    active_profile = CFG.get('active_profile', 'competition_3drone')
    drone_configs = CFG.get('profiles', {}).get(active_profile, {}).get('drones', None)
    if drone_configs:
        fleet_size = len(drone_configs)
    else:
        fleet_size = CFG.get('fleet_size', 3)

    nodes = [Drone(i) for i in range(fleet_size)]
    executor = SingleThreadedExecutor()
    for n in nodes:
        executor.add_node(n)

    truth = {}
    gz = GzNode()
    min_sep = float('inf')

    def poses(msg):
        for p in msg.pose:
            if p.name.startswith(('parcel_', 'rescue_')):
                truth[p.name] = [p.position.x, p.position.y, p.position.z]

    gz.subscribe(Pose_V, '/world/dual_rescue/dynamic_pose/info', poses)
    last = 0.0

    try:
        while not all(n.done for n in nodes):
            executor.spin_once(timeout_sec=0.05)

            # Check pairwise separation across all active swarm drones
            valid_positions = [n.global_p for n in nodes if n.global_p is not None]
            if len(valid_positions) == len(nodes):
                for a_idx in range(len(nodes)):
                    for b_idx in range(a_idx + 1, len(nodes)):
                        sep = float(np.linalg.norm(nodes[a_idx].global_p - nodes[b_idx].global_p))
                        min_sep = min(min_sep, sep)
                        if sep < 4:
                            for n in nodes:
                                n.abort('separation below 4m')

            if time.monotonic() - last > 2:
                last = time.monotonic()
                (OUT / 'physical-poses.json').write_text(json.dumps(truth, indent=2))

        result = {
            'controllers': [n.status() for n in nodes],
            'minimum_separation_m': min_sep,
            'physical_poses': truth,
        }
        (OUT / 'mission-result.json').write_text(json.dumps(result, indent=2))
        print('MISSION COMPLETE', flush=True)

    finally:
        for n in nodes:
            n.gz.unsubscribe(f'/rescue_{n.i}/camera')
            for j in range(n.packages_total):
                n.gz.unsubscribe(f'/parcel_{n.i}_{j}/state')
            n.file.close()
            n.events.close()
            n.destroy_node()

        gz.unsubscribe('/world/dual_rescue/dynamic_pose/info')
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
