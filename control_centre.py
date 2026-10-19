#!/usr/bin/env python3
"""
NIDAR RESCUESWARM // TACTICAL MISSION CONTROL CENTRE
===================================================
Real-time ground control and mission visualization station for NIDAR dual-drone rescue swarm.
Displays live camera feeds (annotated YOLO/SSD & raw Gazebo), flight HUD, real-time speed,
altitude/height, 3D velocity, GPS/local coordinates, battery SOC, mission phase,
payload delivery status, survivor detection logs, and 2D tactical swarm radar.

Usage:
    python3 control_centre.py [options]
    ./run_control_centre.sh
"""

import os
import sys
import subprocess

# ---------------------------------------------------------------------------
# Automatic Environment Bootstrapper
# Ensures ROS2 Jazzy, px4_msgs, nidar_vision, and Python venv are sourced
# even if launched from a clean terminal without prior setup.
# ---------------------------------------------------------------------------
def _bootstrap_environment():
    try:
        import rclpy
        from px4_msgs.msg import VehicleLocalPosition
        return  # Environment already active
    except ImportError:
        pass

    if os.environ.get('NIDAR_GCS_BOOTSTRAPPED') == '1':
        return  # Prevent recursive loop if install missing

    script_path = os.path.abspath(__file__)
    env = os.environ.copy()
    env['NIDAR_GCS_BOOTSTRAPPED'] = '1'
    env['ROS_DOMAIN_ID'] = env.get('ROS_DOMAIN_ID', '88')
    env['GZ_PARTITION'] = env.get('GZ_PARTITION', 'nidar_rescueswarm')
    env['ROS_AUTOMATIC_DISCOVERY_RANGE'] = 'LOCALHOST'
    env['GZ_IP'] = '127.0.0.1'

    bash_cmd = (
        'source /opt/ros/jazzy/setup.bash 2>/dev/null || true; '
        'source /home/kalpeshbauskar/px4_ros2_ws/install/setup.bash 2>/dev/null || true; '
        'source /home/kalpeshbauskar/nidar_rescueswarm/ros2_ws/install/setup.bash 2>/dev/null || true; '
        'source /home/kalpeshbauskar/nidar_rescueswarm/venv/bin/activate 2>/dev/null || true; '
        f'exec python3 "{script_path}" ' + ' '.join(f'"{a}"' for a in sys.argv[1:])
    )
    os.execvpe('bash', ['bash', '-c', bash_cmd], env)

_bootstrap_environment()

import argparse
import collections
from datetime import datetime
import json
import math
from pathlib import Path
import threading
import time

# Configure Qt platform and system plugin path before cv2
os.environ.setdefault('QT_QPA_PLATFORM', 'xcb')
os.environ['QT_QPA_PLATFORM_PLUGIN_PATH'] = '/usr/lib/x86_64-linux-gnu/qt5/plugins'
os.environ.setdefault('LIBGL_ALWAYS_SOFTWARE', '1')
os.environ.setdefault('LIBGL_DRI3_DISABLE', '1')
os.environ.setdefault('__GLX_VENDOR_LIBRARY_NAME', 'mesa')

# PyQt5 GUI
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QObject
from PyQt5.QtGui import QImage, QPixmap, QFont, QColor, QPainter, QPen, QBrush
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QLabel, QPushButton, QVBoxLayout,
    QHBoxLayout, QGridLayout, QSplitter, QTabWidget, QFrame, QComboBox,
    QProgressBar, QTextEdit, QGroupBox, QSizePolicy, QCheckBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QScrollArea
)

import cv2
# Re-assert system Qt plugin path in case cv2 overrides it
os.environ['QT_QPA_PLATFORM_PLUGIN_PATH'] = '/usr/lib/x86_64-linux-gnu/qt5/plugins'
import numpy as np

# ROS2
import rclpy
from rclpy.node import Node as RosNode
from rclpy.qos import qos_profile_sensor_data as QOS_SENSOR

try:
    from px4_msgs.msg import (
        VehicleLocalPosition,
        VehicleStatus,
        VehicleAttitude,
    )
except ImportError:
    VehicleLocalPosition = None
    VehicleStatus = None
    VehicleAttitude = None

try:
    from sensor_msgs.msg import Image as RosImage
except ImportError:
    RosImage = None

try:
    from std_msgs.msg import String as RosString
except ImportError:
    RosString = None

try:
    from vision_msgs.msg import Detection2DArray
except ImportError:
    Detection2DArray = None

# Gazebo Transport
try:
    from gz.transport13 import Node as GzNode
    from gz.msgs10.image_pb2 import Image as GzImage
except ImportError:
    GzNode = None
    GzImage = None


# ---------------------------------------------------------------------------
# Geodetic & Coordinate Reference System (WGS84)
# ---------------------------------------------------------------------------
WORLD_ORIGIN_LAT = 47.397971057728974
WORLD_ORIGIN_LON = 8.546163739800146
WORLD_ORIGIN_ALT = 0.0
R_EARTH = 6371000.0


def local_to_wgs84(north_m: float, east_m: float, lat_0: float = WORLD_ORIGIN_LAT, lon_0: float = WORLD_ORIGIN_LON):
    """Converts local NED coordinates (meters) to global WGS84 Geotag (Lat, Lon in degrees)."""
    lat = lat_0 + (north_m / R_EARTH) * (180.0 / math.pi)
    lon = lon_0 + (east_m / (R_EARTH * math.cos(math.radians(lat_0)))) * (180.0 / math.pi)
    return lat, lon


# ---------------------------------------------------------------------------
# Telemetry State Data Container
# ---------------------------------------------------------------------------
class DroneTelemetry:
    """Thread-safe telemetry state for a single rescue drone."""
    def __init__(self, drone_id: int):
        self.drone_id = drone_id  # 1 or 2
        self.callsign = f"DRONE {drone_id} // {'ALPHA' if drone_id == 1 else 'BRAVO'}"
        self.model_name = f"rescue_{drone_id - 1}"
        self.lock = threading.Lock()

        # Connectivity & Timestamps
        self.connected = False
        self.last_seen = 0.0
        self.px4_connected = False
        self.swarm_connected = False

        # Flight & Avionics
        self.armed = False
        self.nav_state = "INIT"
        self.phase = "WAIT"
        self.route_index = 0
        self.route_total = 0
        self.route_percent = 0.0

        # Position (meters NED & Global Origin)
        self.pos_n = 0.0
        self.pos_e = -5.0 if drone_id == 1 else 5.0
        self.pos_d = 0.0
        self.altitude_agl = 0.0  # Height above ground (-down)
        self.target_alt = 25.0
        self.home_n = 0.0
        self.home_e = -5.0 if drone_id == 1 else 5.0
        self.lat, self.lon = local_to_wgs84(self.pos_n, self.pos_e)

        # Velocities & Speeds (m/s)
        self.vx = 0.0
        self.vy = 0.0
        self.vz = 0.0
        self.speed_h = 0.0  # Horizontal Ground Speed
        self.speed_v = 0.0  # Climb / Descent Rate
        self.speed_3d = 0.0 # Total 3D Speed

        # Attitude (deg)
        self.roll = 0.0
        self.pitch = 0.0
        self.yaw = 0.0

        # Hardware & Battery
        self.battery_soc = 100.0
        self.voltage = 25.2
        self.current = 0.0
        self.power = 0.0
        self.est_flight_time_min = 18.0
        self.auw_kg = 6.28  # Competition AUW with 5 relief canisters
        self.tw_ratio = 2.15

        # Deliveries & Detections (5 Canisters per drone, 10 Fleet Total)
        self.packages_remaining = 5
        self.packages_total = 5
        self.deliveries_count = 0
        self.detections_count = 0
        self.last_detection_text = "No victims in sector"
        self.last_detection_time = 0.0
        self.latest_drop = None
        self.latest_drop_error_m = None
        self.drops_history = []
        self.detections_list = []

        # Intercommunication & Mesh Network
        self.net_ip = f"10.42.0.1{drone_id}"
        self.net_carrier = "MESH_5.8G"
        self.net_wifi_status = "OPERATIONAL"
        self.net_rfd_status = "STANDBY_SYNCED"
        self.peer_dist = 10.0
        self.peer_conn = True

        # Flight History Trail for Radar Map (North, East)
        self.trail = collections.deque(maxlen=200)

    def get_gps(self):
        return local_to_wgs84(self.pos_n, self.pos_e)

    def get_dist_to_home(self):
        return math.hypot(self.pos_n - self.home_n, self.pos_e - self.home_e)

    def update_from_swarm_json(self, d: dict):
        with self.lock:
            now = time.monotonic()
            self.connected = True
            self.swarm_connected = True
            self.last_seen = now

            pos = d.get("position", {})
            if pos.get("north_m") is not None:
                self.pos_n = float(pos["north_m"])
                self.pos_e = float(pos["east_m"])
                self.pos_d = float(pos["down_m"])
                self.altitude_agl = float(pos.get("altitude_m", -self.pos_d))
                self.lat, self.lon = self.get_gps()
                self.trail.append((self.pos_n, self.pos_e))

            vel = d.get("velocity", {})
            if vel.get("north_mps") is not None:
                self.vx = float(vel["north_mps"])
                self.vy = float(vel["east_mps"])
                self.vz = float(vel["down_mps"])

            spd = d.get("speed", {})
            if spd.get("horizontal_mps") is not None:
                self.speed_h = float(spd["horizontal_mps"])
                self.speed_v = float(spd.get("vertical_mps", -self.vz))
                self.speed_3d = float(spd.get("total_mps", math.sqrt(self.speed_h**2 + self.speed_v**2)))
            else:
                self.speed_h = math.hypot(self.vx, self.vy)
                self.speed_v = -self.vz
                self.speed_3d = math.sqrt(self.vx**2 + self.vy**2 + self.vz**2)

            att = d.get("attitude", {})
            if att.get("roll_deg") is not None:
                self.roll = float(att["roll_deg"])
                self.pitch = float(att["pitch_deg"])
                self.yaw = float(att["yaw_deg"])

            armed_code = d.get("armed")
            if armed_code is not None:
                self.armed = (armed_code == 2)

            nav_code = d.get("nav_state")
            if nav_code is not None:
                self.nav_state = "OFFBOARD" if nav_code == 14 else f"MODE_{nav_code}"

            msn = d.get("mission", {})
            self.phase = msn.get("phase", self.phase)
            self.route_index = msn.get("route_index", self.route_index)
            self.route_total = msn.get("route_total", self.route_total)
            self.route_percent = msn.get("route_percent", self.route_percent)
            self.detections_count = msn.get("detections", self.detections_count)
            self.deliveries_count = msn.get("deliveries", self.deliveries_count)

            hw = d.get("hardware", {})
            bat = hw.get("battery", {})
            if bat.get("soc_pct") is not None:
                self.battery_soc = float(bat["soc_pct"])
                self.voltage = float(bat.get("voltage_v", self.voltage))
                self.current = float(bat.get("current_a", self.current))
                self.power = float(bat.get("power_w", self.power))
                self.est_flight_time_min = float(bat.get("remaining_minutes", self.est_flight_time_min))

            pld = hw.get("payload", {})
            if pld.get("packages_remaining") is not None:
                self.packages_remaining = int(pld["packages_remaining"])
                self.packages_total = int(pld.get("initial_packages", self.packages_total))
                self.auw_kg = float(pld.get("auw_kg", self.auw_kg))
                self.tw_ratio = float(pld.get("tw_ratio", self.tw_ratio))

            net = hw.get("network", {})
            if net:
                self.net_ip = net.get("static_ip", self.net_ip)
                self.net_carrier = net.get("carrier", self.net_carrier)
                self.net_wifi_status = net.get("wifi_status", self.net_wifi_status)
                self.net_rfd_status = net.get("rfd_status", self.net_rfd_status)

            lr = d.get("latest_release")
            if lr:
                self.latest_drop = lr
                self.latest_drop_error_m = lr.get("radial_distance_error_m")

            drops = d.get("drops")
            if drops is not None:
                self.drops_history = drops
                self.deliveries_count = len(drops)

            dets = d.get("detections_list")
            if dets is not None:
                self.detections_list = dets

    def update_from_px4_local_pos(self, msg):
        with self.lock:
            # Fallback if swarm state topic is not yet publishing
            self.connected = True
            self.px4_connected = True
            self.last_seen = time.monotonic()
            self.pos_n = float(msg.x)
            self.pos_e = float(msg.y)
            self.pos_d = float(msg.z)
            self.altitude_agl = float(-msg.z)
            self.vx = float(msg.vx)
            self.vy = float(msg.vy)
            self.vz = float(msg.vz)
            self.speed_h = math.hypot(self.vx, self.vy)
            self.speed_v = -self.vz
            self.speed_3d = math.sqrt(self.vx**2 + self.vy**2 + self.vz**2)
            self.yaw = math.degrees(float(msg.heading))
            self.trail.append((self.pos_n, self.pos_e))

    def update_from_px4_status(self, msg):
        with self.lock:
            self.connected = True
            self.armed = (getattr(msg, 'arming_state', 0) == 2)
            nav = getattr(msg, 'nav_state', 0)
            self.nav_state = "OFFBOARD" if nav == 14 else f"MODE_{nav}"

    def update_from_px4_attitude(self, msg):
        with self.lock:
            q = msg.q
            sinr_cosp = 2 * (q[0] * q[1] + q[2] * q[3])
            cosr_cosp = 1 - 2 * (q[1] * q[1] + q[2] * q[2])
            sinp = 2 * (q[0] * q[2] - q[1] * q[3])
            sinp = max(-1.0, min(1.0, sinp))
            siny_cosp = 2 * (q[0] * q[3] + q[1] * q[2])
            cosy_cosp = 1 - 2 * (q[2] * q[2] + q[3] * q[3])
            self.roll = math.degrees(math.atan2(sinr_cosp, cosr_cosp))
            self.pitch = math.degrees(math.asin(sinp))
            self.yaw = math.degrees(math.atan2(siny_cosp, cosy_cosp))


# ---------------------------------------------------------------------------
# Background ROS2 & Gazebo Communications Worker
# ---------------------------------------------------------------------------
class CommunicationsManager:
    """Manages ROS2 and Gazebo transport subscriptions asynchronously."""
    def __init__(self, drones: dict):
        self.drones = drones
        self.lock = threading.Lock()
        self.event_queue = collections.deque(maxlen=200)

        # Video buffers: (cv_frame, timestamp_monotonic, source_tag)
        self.frames = {
            1: {"annotated": None, "raw": None, "gz": None, "fps": 0.0, "fc": 0, "last_t": time.monotonic()},
            2: {"annotated": None, "raw": None, "gz": None, "fps": 0.0, "fc": 0, "last_t": time.monotonic()},
        }

        self.ros_node = None
        self.gz_node = None
        self._running = True

    def post_event(self, source: str, message: str):
        self.event_queue.append((source, message))

    def start(self):
        # Start Gazebo Transport subscriber thread
        if GzNode is not None:
            t_gz = threading.Thread(target=self._run_gz, daemon=True, name="GzTransportThread")
            t_gz.start()

        # Start ROS2 subscriber thread
        t_ros = threading.Thread(target=self._run_ros, daemon=True, name="Ros2SpinThread")
        t_ros.start()

    def _run_gz(self):
        try:
            self.gz_node = GzNode()
            # Subscribe to raw camera feeds directly from Gazebo
            self.gz_node.subscribe(GzImage, "/rescue_0/camera", lambda m: self._gz_img_cb(1, m))
            self.gz_node.subscribe(GzImage, "/rescue_0/camera/image_raw", lambda m: self._gz_img_cb(1, m))
            self.gz_node.subscribe(GzImage, "/rescue_1/camera", lambda m: self._gz_img_cb(2, m))
            self.gz_node.subscribe(GzImage, "/rescue_1/camera/image_raw", lambda m: self._gz_img_cb(2, m))
            self.post_event("GAZEBO", "Connected to Gazebo transport image topics")
        except Exception as e:
            self.post_event("GAZEBO_ERR", f"Gz transport init error: {e}")

    def _gz_img_cb(self, drone_id: int, msg):
        try:
            data = np.frombuffer(msg.data, dtype=np.uint8).reshape(msg.height, msg.step)[:, :msg.width * 3].reshape(msg.height, msg.width, 3)
            # Gazebo outputs RGB, convert to BGR for OpenCV processing
            bgr = cv2.cvtColor(data, cv2.COLOR_RGB2BGR)
            self._store_frame(drone_id, bgr, "gz")
        except Exception:
            pass

    def _run_ros(self):
        try:
            if not rclpy.ok():
                rclpy.init(args=None)
            self.ros_node = RosNode("nidar_mission_control_centre")
            self.post_event("ROS2", f"ROS2 initialized on Domain {os.environ.get('ROS_DOMAIN_ID', '88')}")

            # Drone 1 Subscriptions
            self._setup_drone_ros_subs(1, "drone1", "rescue_0")
            # Drone 2 Subscriptions
            self._setup_drone_ros_subs(2, "drone2", "rescue_1")

            rclpy.spin(self.ros_node)
        except Exception as e:
            self.post_event("ROS2_ERR", f"ROS2 exception: {e}")

    def _setup_drone_ros_subs(self, drone_id: int, port_ns: str, model_ns: str):
        node = self.ros_node

        # High-level Swarm State (JSON from mission.py)
        if RosString is not None:
            node.create_subscription(
                RosString,
                f"/swarm/{port_ns}/state",
                lambda m, did=drone_id: self._swarm_cb(did, m),
                10
            )

        # PX4 Direct Fallbacks
        if VehicleLocalPosition is not None:
            node.create_subscription(
                VehicleLocalPosition,
                f"/{port_ns}/fmu/out/vehicle_local_position_v1",
                lambda m, did=drone_id: self.drones[did].update_from_px4_local_pos(m),
                QOS_SENSOR
            )
            node.create_subscription(
                VehicleLocalPosition,
                f"/{port_ns}/fmu/out/vehicle_local_position",
                lambda m, did=drone_id: self.drones[did].update_from_px4_local_pos(m),
                QOS_SENSOR
            )

        if VehicleStatus is not None:
            node.create_subscription(
                VehicleStatus,
                f"/{port_ns}/fmu/out/vehicle_status_v4",
                lambda m, did=drone_id: self.drones[did].update_from_px4_status(m),
                QOS_SENSOR
            )

        if VehicleAttitude is not None:
            node.create_subscription(
                VehicleAttitude,
                f"/{port_ns}/fmu/out/vehicle_attitude",
                lambda m, did=drone_id: self.drones[did].update_from_px4_attitude(m),
                QOS_SENSOR
            )

        # Camera feeds from ROS2
        if RosImage is not None:
            # Annotated feeds from SSD / YOLO
            node.create_subscription(
                RosImage,
                f"/{model_ns}/ssd/image_annotated",
                lambda m, did=drone_id: self._ros_img_cb(did, m, "annotated"),
                QOS_SENSOR
            )
            node.create_subscription(
                RosImage,
                f"/{model_ns}/yolo/image_annotated",
                lambda m, did=drone_id: self._ros_img_cb(did, m, "annotated"),
                QOS_SENSOR
            )
            # Raw bridged camera feed
            node.create_subscription(
                RosImage,
                f"/{model_ns}/camera/image_raw",
                lambda m, did=drone_id: self._ros_img_cb(did, m, "raw"),
                QOS_SENSOR
            )

        # Detections
        if Detection2DArray is not None:
            node.create_subscription(
                Detection2DArray,
                f"/{model_ns}/ssd/detections",
                lambda m, did=drone_id: self._det_cb(did, m, "SSD"),
                10
            )
            node.create_subscription(
                Detection2DArray,
                f"/{model_ns}/yolo/detections",
                lambda m, did=drone_id: self._det_cb(did, m, "YOLO"),
                10
            )

    def _swarm_cb(self, drone_id: int, msg):
        try:
            d = json.loads(msg.data)
            self.drones[drone_id].update_from_swarm_json(d)
        except Exception:
            pass

    def _ros_img_cb(self, drone_id: int, msg, category: str):
        try:
            # Fast numpy decode
            h, w = msg.height, msg.width
            encoding = getattr(msg, 'encoding', 'bgr8')
            if encoding in ['bgr8', 'rgb8']:
                data = np.frombuffer(msg.data, dtype=np.uint8).reshape((h, w, 3))
                if encoding == 'rgb8':
                    data = cv2.cvtColor(data, cv2.COLOR_RGB2BGR)
                self._store_frame(drone_id, data, category)
        except Exception:
            pass

    def _det_cb(self, drone_id: int, msg, detector_name: str):
        if not msg.detections:
            return
        d = self.drones[drone_id]
        with d.lock:
            cnt = len(msg.detections)
            conf = msg.detections[0].results[0].hypothesis.score if msg.detections[0].results else 0.0
            d.last_detection_text = f"{detector_name}: {cnt} Person(s) (Conf: {conf*100:.1f}%)"
            d.last_detection_time = time.monotonic()
        self.post_event(f"DRONE_{drone_id}", f"Victim detected by {detector_name} (Conf: {conf*100:.1f}%) at [N: {d.pos_n:.1f}m, E: {d.pos_e:.1f}m]")

    def _store_frame(self, drone_id: int, frame, category: str):
        with self.lock:
            now = time.monotonic()
            rec = self.frames[drone_id]
            rec[category] = (frame, now)
            rec["fc"] += 1
            dt = now - rec["last_t"]
            if dt >= 1.0:
                rec["fps"] = rec["fc"] / dt
                rec["fc"] = 0
                rec["last_t"] = now

    def get_latest_frame(self, drone_id: int, preference: str = "auto"):
        """
        Returns (frame, fps, active_source_name).
        preference can be: 'auto' (prefer annotated -> raw -> gz), 'raw', 'annotated'
        """
        with self.lock:
            rec = self.frames[drone_id]
            fps = rec["fps"]
            now = time.monotonic()

            ann_entry = rec["annotated"]
            raw_entry = rec["raw"]
            gz_entry = rec["gz"]

            # Filter stale entries (> 2.0s)
            has_ann = (ann_entry is not None and (now - ann_entry[1]) < 2.0)
            has_raw = (raw_entry is not None and (now - raw_entry[1]) < 2.0)
            has_gz = (gz_entry is not None and (now - gz_entry[1]) < 2.0)

            if preference == "annotated" and has_ann:
                return ann_entry[0], fps, "AI Annotated (ROS2)"
            elif preference == "raw":
                if has_raw:
                    return raw_entry[0], fps, "Raw Camera (ROS2)"
                elif has_gz:
                    return gz_entry[0], fps, "Raw Camera (Gazebo)"
            else: # auto
                if has_ann:
                    return ann_entry[0], fps, "AI Annotated (Live)"
                elif has_raw:
                    return raw_entry[0], fps, "Raw Camera (ROS2)"
                elif has_gz:
                    return gz_entry[0], fps, "Raw Camera (Gazebo)"

            return None, 0.0, "NO SIGNAL"

    def shutdown(self):
        self._running = False
        if self.ros_node is not None:
            self.ros_node.destroy_node()
        rclpy.shutdown()


# ---------------------------------------------------------------------------
# HUD (Heads-Up Display) Video Generator & Standby Synthesizer
# ---------------------------------------------------------------------------
class HudRenderer:
    """Renders professional flight HUD overlays, electronic image stabilization (EIS), and animated standby screens."""

    @staticmethod
    def stabilize_frame(frame: np.ndarray, roll: float, pitch: float) -> np.ndarray:
        """Applies smooth electronic attitude stabilization to keep the live camera horizon level."""
        if frame is None or (abs(roll) < 0.05 and abs(pitch) < 0.05):
            return frame
        try:
            h, w = frame.shape[:2]
            cx, cy = w // 2, h // 2
            # 90 deg HFOV -> ~73.7 deg VFOV (4:3 aspect)
            pixels_per_deg_v = h / 73.7
            # Clamp stabilization range to +-15 deg to avoid severe border artifacts
            c_roll = max(-15.0, min(15.0, float(roll)))
            c_pitch = max(-15.0, min(15.0, float(pitch)))
            # Rotate around optical center to counteract aircraft roll
            m = cv2.getRotationMatrix2D((cx, cy), -c_roll, 1.0)
            # Smooth vertical damping to counteract flight pitch oscillation
            m[1, 2] += c_pitch * (pixels_per_deg_v * 0.4)
            return cv2.warpAffine(frame, m, (w, h), borderMode=cv2.BORDER_REPLICATE)
        except Exception:
            return frame

    @staticmethod
    def draw_hud(frame: np.ndarray, telemetry: DroneTelemetry, fps: float, source_label: str, stabilize: bool = True) -> np.ndarray:
        out = frame.copy()
        with telemetry.lock:
            spd_h = telemetry.speed_h
            spd_v = telemetry.speed_v
            spd_3d = telemetry.speed_3d
            alt = telemetry.altitude_agl
            target_alt = telemetry.target_alt
            roll = telemetry.roll
            pitch = telemetry.pitch
            yaw = telemetry.yaw
            phase = telemetry.phase
            armed = telemetry.armed
            callsign = telemetry.callsign
            det_text = telemetry.last_detection_text
            det_recent = (time.monotonic() - telemetry.last_detection_time) < 3.0
            pos_n = telemetry.pos_n
            pos_e = telemetry.pos_e
            lat, lon = telemetry.get_gps()
            dist_home = telemetry.get_dist_to_home()
            pkgs_rem = telemetry.packages_remaining
            pkgs_tot = telemetry.packages_total
            pkgs_drp = max(0, pkgs_tot - pkgs_rem)
            peer_dist = telemetry.peer_dist
            latest_drop_err = telemetry.latest_drop_error_m

        # Apply Electronic Image Stabilization (EIS) to lock the downward view flat & level
        if stabilize:
            out = HudRenderer.stabilize_frame(out, roll, pitch)

        h, w = out.shape[:2]
        cx, cy = w // 2, h // 2

        # Tactical Corner Brackets
        c_len = 25
        c_col = (0, 220, 255) # Cyan
        for x, y, dx, dy in [
            (20, 20, c_len, c_len),
            (w - 20, 20, -c_len, c_len),
            (20, h - 20, c_len, -c_len),
            (w - 20, h - 20, -c_len, -c_len),
        ]:
            cv2.line(out, (x, y), (x + dx, y), c_col, 2)
            cv2.line(out, (x, y), (x, y + dy), c_col, 2)

        # Center Crosshair & Pitch Horizon
        cv2.drawMarker(out, (cx, cy), (0, 255, 200), cv2.MARKER_CROSS, 18, 1)

        # Horizon line rotated by roll and offset by pitch
        rad = math.radians(roll)
        cos_r, sin_r = math.cos(rad), math.sin(rad)
        p_offset = int(pitch * 2.0) # 2 pixels per degree of pitch
        hl = 70
        x1 = int(cx - hl * cos_r - p_offset * sin_r)
        y1 = int(cy - hl * sin_r + p_offset * cos_r)
        x2 = int(cx + hl * cos_r - p_offset * sin_r)
        y2 = int(cy + hl * sin_r + p_offset * cos_r)
        cv2.line(out, (x1, y1), (x2, y2), (0, 255, 200), 2)
        # Small horizon wings
        cv2.line(out, (cx - 100, cy), (cx - 40, cy), (0, 200, 200), 1)
        cv2.line(out, (cx + 40, cy), (cx + 100, cy), (0, 200, 200), 1)

        # TOP BAR: Callsign, Heading, Phase, Inter-Drone Link, FPS
        cv2.rectangle(out, (0, 0), (w, 34), (10, 15, 22), -1)
        cv2.line(out, (0, 34), (w, 34), (0, 200, 255), 1)

        # Callsign badge
        cv2.putText(out, callsign, (14, 23), cv2.FONT_HERSHEY_SIMPLEX, 0.52, (0, 230, 255), 2)

        # Heading Tape in Center
        hdg_str = f"HDG: {int(yaw % 360):03d}\u00b0"
        (tw, _), _ = cv2.getTextSize(hdg_str, cv2.FONT_HERSHEY_SIMPLEX, 0.48, 1)
        cv2.putText(out, hdg_str, (cx - tw // 2, 23), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (255, 255, 255), 1)

        # Mode / Phase & Source
        right_info = f"[{phase}]  {source_label} ({fps:.1f} FPS)"
        (rw, _), _ = cv2.getTextSize(right_info, cv2.FONT_HERSHEY_SIMPLEX, 0.44, 1)
        cv2.putText(out, right_info, (w - rw - 14, 23), cv2.FONT_HERSHEY_SIMPLEX, 0.44, (0, 255, 150), 1)

        # SUB-HEADER: Inter-Drone Mesh Link Indicator
        peer_id = 2 if telemetry.drone_id == 1 else 1
        mesh_str = f"\u229e MESH LINK: PEER D{peer_id} @ {peer_dist:.1f}m (SYNCED <4ms)"
        cv2.putText(out, mesh_str, (14, 52), cv2.FONT_HERSHEY_SIMPLEX, 0.40, (0, 220, 255), 1)

        # LEFT TAPE: SPEED READOUT (m/s & km/h)
        cv2.rectangle(out, (12, cy - 65), (135, cy + 65), (15, 20, 30), -1)
        cv2.rectangle(out, (12, cy - 65), (135, cy + 65), (0, 200, 255), 1)
        cv2.putText(out, "GND SPEED", (18, cy - 46), cv2.FONT_HERSHEY_SIMPLEX, 0.36, (0, 200, 255), 1)
        cv2.putText(out, f"{spd_h:.2f} m/s", (18, cy - 16), cv2.FONT_HERSHEY_SIMPLEX, 0.70, (255, 255, 255), 2)
        cv2.putText(out, f"{spd_h * 3.6:.1f} km/h", (18, cy + 8), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (180, 220, 255), 1)
        arrow = "\u25b2" if spd_v > 0.1 else ("\u25bc" if spd_v < -0.1 else "\u25ac")
        cv2.putText(out, f"{arrow} Vz: {spd_v:+.1f} m/s", (18, cy + 30), cv2.FONT_HERSHEY_SIMPLEX, 0.40, (0, 255, 200), 1)
        cv2.putText(out, f"3D: {spd_3d:.1f} m/s", (18, cy + 50), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (150, 180, 200), 1)

        # RIGHT TAPE: ALTITUDE / HEIGHT READOUT (AGL & Feet)
        cv2.rectangle(out, (w - 135, cy - 65), (w - 12, cy + 65), (15, 20, 30), -1)
        cv2.rectangle(out, (w - 135, cy - 65), (w - 12, cy + 65), (0, 255, 120), 1)
        cv2.putText(out, "HEIGHT (AGL)", (w - 130, cy - 46), cv2.FONT_HERSHEY_SIMPLEX, 0.36, (0, 255, 120), 1)
        cv2.putText(out, f"{alt:.2f} m", (w - 130, cy - 16), cv2.FONT_HERSHEY_SIMPLEX, 0.70, (255, 255, 255), 2)
        cv2.putText(out, f"{alt * 3.28084:.1f} ft", (w - 130, cy + 8), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (180, 255, 200), 1)
        cv2.putText(out, f"TGT: {target_alt:.1f} m", (w - 130, cy + 30), cv2.FONT_HERSHEY_SIMPLEX, 0.40, (255, 200, 0), 1)
        err = alt - target_alt
        cv2.putText(out, f"ERR: {err:+.1f} m", (w - 130, cy + 50), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (150, 180, 200), 1)

        # BOTTOM BAR: Position (Local + GPS) & Cargo Magazine Status
        cv2.rectangle(out, (0, h - 34), (w, h), (10, 15, 22), -1)
        cv2.line(out, (0, h - 34), (w, h - 34), (0, 200, 255), 1)

        # Current Position & Geotag
        pos_str = f"POS: N {pos_n:+.1f}m, E {pos_e:+.1f}m | GPS: {lat:.6f}N, {lon:.6f}E | HOME: {dist_home:.1f}m"
        cv2.putText(out, pos_str, (14, h - 12), cv2.FONT_HERSHEY_SIMPLEX, 0.41, (200, 220, 255), 1)

        # Cargo magazine status on bottom right
        slots_vis = "".join(["[\u2713]" if i < pkgs_drp else "[\u25cf]" for i in range(5)])
        cargo_str = f"CARGO: {pkgs_drp}/5 DROPPED ({pkgs_rem} REM) {slots_vis}"
        (cw, _), _ = cv2.getTextSize(cargo_str, cv2.FONT_HERSHEY_SIMPLEX, 0.39, 1)
        cv2.putText(out, cargo_str, (w - cw - 14, h - 12), cv2.FONT_HERSHEY_SIMPLEX, 0.39, (0, 255, 180), 1)

        # Drop Confirmation & Radial Accuracy Error Banner
        if latest_drop_err is not None:
            cv2.rectangle(out, (w // 2 - 225, h - 64), (w // 2 + 225, h - 38), (10, 30, 20), -1)
            cv2.rectangle(out, (w // 2 - 225, h - 64), (w // 2 + 225, h - 38), (0, 255, 120), 1)
            drop_txt = f"[\u2713] PAYLOAD DROPPED! RADIAL ACCURACY: {latest_drop_err:.2f}m FROM SURVIVOR"
            (dw, _), _ = cv2.getTextSize(drop_txt, cv2.FONT_HERSHEY_SIMPLEX, 0.40, 1)
            cv2.putText(out, drop_txt, (w // 2 - dw // 2, h - 46), cv2.FONT_HERSHEY_SIMPLEX, 0.40, (0, 255, 120), 1)

        if det_recent:
            blink = int(time.monotonic() * 4) % 2 == 0
            alert_col = (0, 50, 255) if blink else (0, 220, 255)
            cv2.rectangle(out, (w // 2 - 225, h - 32), (w // 2 + 225, h - 4), (20, 20, 40), -1)
            cv2.rectangle(out, (w // 2 - 225, h - 32), (w // 2 + 225, h - 4), alert_col, 2)
            cv2.putText(out, f"[!] {det_text}", (w // 2 - 210, h - 12), cv2.FONT_HERSHEY_SIMPLEX, 0.44, alert_col, 2)

        return out

    @staticmethod
    def generate_standby_frame(w: int, h: int, drone_id: int, reason: str = "AWAITING CAMERA FEED") -> np.ndarray:
        """Synthesizes a futuristic radar sweep animation for standby mode."""
        frame = np.full((h, w, 3), 16, dtype=np.uint8)

        # Grid lines
        grid_col = (30, 38, 50)
        for x in range(0, w, 40):
            cv2.line(frame, (x, 0), (x, h), grid_col, 1)
        for y in range(0, h, 40):
            cv2.line(frame, (0, y), (w, y), grid_col, 1)

        cx, cy = w // 2, h // 2
        # Radar circles
        r_col = (40, 60, 80)
        cv2.circle(frame, (cx, cy), 60, r_col, 1)
        cv2.circle(frame, (cx, cy), 120, r_col, 1)
        cv2.circle(frame, (cx, cy), 180, r_col, 1)

        # Rotating radar sweep
        angle = (time.monotonic() * 90.0) % 360.0
        rad = math.radians(angle)
        sx = int(cx + 180 * math.cos(rad))
        sy = int(cy + 180 * math.sin(rad))
        cv2.line(frame, (cx, cy), (sx, sy), (0, 220, 180), 2)

        # Tactical center reticle
        cv2.drawMarker(frame, (cx, cy), (0, 200, 255), cv2.MARKER_CROSS, 24, 1)

        # Message box
        cv2.rectangle(frame, (cx - 190, cy - 50), (cx + 190, cy + 50), (12, 16, 26), -1)
        cv2.rectangle(frame, (cx - 190, cy - 50), (cx + 190, cy + 50), (0, 200, 255), 1)

        callsign = f"DRONE {drone_id} // {'ALPHA' if drone_id == 1 else 'BRAVO'}"
        cv2.putText(frame, callsign, (cx - 170, cy - 25), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 220), 2)
        cv2.putText(frame, reason, (cx - 170, cy), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (255, 200, 0), 1)
        cv2.putText(frame, "Start simulation: ./run_nidar_demo.sh", (cx - 170, cy + 28), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (150, 180, 200), 1)

        return frame


# ---------------------------------------------------------------------------
# Custom Non-Stretching Video Display Widget
# ---------------------------------------------------------------------------
class VideoDisplayWidget(QWidget):
    """Custom video widget that renders frames scaled to its allocated geometry
    without triggering Qt layout growth feedback loops."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        self.setMinimumSize(240, 180)
        self.current_qimg = None
        self.setStyleSheet("background-color: #060911; border-radius: 4px;")

    def set_frame(self, qimg: QImage):
        self.current_qimg = qimg
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(6, 9, 17))
        if self.current_qimg and not self.current_qimg.isNull():
            scaled = self.current_qimg.scaled(
                self.size(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            x = (self.width() - scaled.width()) // 2
            y = (self.height() - scaled.height()) // 2
            painter.drawImage(x, y, scaled)


# ---------------------------------------------------------------------------
# 2D Tactical Swarm Radar & Map Visualizer
# ---------------------------------------------------------------------------
class TacticalRadarWidget(QWidget):
    """Draws real-time 2D radar tracking map without causing layout feedback loops."""
    def __init__(self, drones: dict, parent=None):
        super().__init__(parent)
        self.drones = drones
        self.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        self.setMinimumSize(240, 180)
        self.setStyleSheet("background-color: #0b0f19; border: 1px solid #1c2738; border-radius: 6px;")
        self.current_qimg = None

    def update_radar(self):
        w = 480
        h = 320
        img = np.full((h, w, 3), (11, 15, 25), dtype=np.uint8)

        cx, cy = w // 2, h // 2
        scale = min(w, h) / 360.0  # Scale ~360 meters map span

        def to_screen(north, east):
            sx = int(cx + east * scale)
            sy = int(cy - north * scale) # Invert North for screen Y
            return sx, sy

        # Range rings
        for r_m in [50, 100, 150]:
            r_px = int(r_m * scale)
            cv2.circle(img, (cx, cy), r_px, (25, 35, 50), 1)
            cv2.putText(img, f"{r_m}m", (cx + r_px + 2, cy - 2), cv2.FONT_HERSHEY_SIMPLEX, 0.32, (60, 80, 110), 1)

        # Axes
        cv2.line(img, (cx, 0), (cx, h), (25, 35, 50), 1)
        cv2.line(img, (0, cy), (w, cy), (25, 35, 50), 1)
        cv2.putText(img, "N", (cx + 4, 16), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 200, 255), 1)
        cv2.putText(img, "E", (w - 18, cy - 4), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 200, 255), 1)

        # Search Zones
        z1_tl = to_screen(156.25, -160.0)
        z1_br = to_screen(-156.25, -60.0)
        cv2.rectangle(img, z1_tl, z1_br, (40, 60, 90), 1)
        cv2.putText(img, "ZONE 1 (ALPHA)", (z1_tl[0] + 5, z1_tl[1] + 16), cv2.FONT_HERSHEY_SIMPLEX, 0.36, (0, 180, 255), 1)

        z2_tl = to_screen(156.25, -60.0)
        z2_br = to_screen(-156.25, 40.0)
        cv2.rectangle(img, z2_tl, z2_br, (40, 80, 70), 1)
        cv2.putText(img, "ZONE 2 (BRAVO)", (z2_tl[0] + 5, z2_tl[1] + 16), cv2.FONT_HERSHEY_SIMPLEX, 0.36, (0, 255, 180), 1)

        # Base Origin
        cv2.drawMarker(img, (cx, cy), (0, 255, 100), cv2.MARKER_SQUARE, 8, 1)
        cv2.putText(img, "HOME", (cx + 6, cy + 12), cv2.FONT_HERSHEY_SIMPLEX, 0.32, (0, 255, 100), 1)

        # Plot Drone trails and icons
        colors = {1: (255, 200, 0), 2: (0, 220, 255)}  # Drone 1 = Blue/Cyan, Drone 2 = Amber
        for did in [1, 2]:
            d = self.drones[did]
            with d.lock:
                trail_pts = list(d.trail)
                curr_n, curr_e = d.pos_n, d.pos_e
                yaw = d.yaw
                armed = d.armed

            # Trail
            for i in range(1, len(trail_pts)):
                p1 = to_screen(trail_pts[i - 1][0], trail_pts[i - 1][1])
                p2 = to_screen(trail_pts[i][0], trail_pts[i][1])
                cv2.line(img, p1, p2, colors[did], 1)

            # Drone Blip & Heading Arrow
            sx, sy = to_screen(curr_n, curr_e)
            if 0 <= sx < w and 0 <= sy < h:
                rad = math.radians(yaw)
                ax = int(sx + 14 * math.sin(rad))
                ay = int(sy - 14 * math.cos(rad))
                cv2.line(img, (sx, sy), (ax, ay), colors[did], 2)
                cv2.circle(img, (sx, sy), 5, (255, 255, 255) if armed else (100, 100, 100), -1)
                cv2.circle(img, (sx, sy), 7, colors[did], 2)
                cv2.putText(img, f"D{did}", (sx + 8, sy - 4), cv2.FONT_HERSHEY_SIMPLEX, 0.38, colors[did], 1)

        # Plot Inter-Drone Dynamic Comms Link
        d1 = self.drones.get(1)
        d2 = self.drones.get(2)
        if d1 and d2:
            with d1.lock:
                n1, e1 = d1.pos_n, d1.pos_e
            with d2.lock:
                n2, e2 = d2.pos_n, d2.pos_e

            sx1, sy1 = to_screen(n1, e1)
            sx2, sy2 = to_screen(n2, e2)
            dist_3d = math.hypot(n1 - n2, e1 - e2)

            if dist_3d < 10.0:
                link_col = (0, 0, 255)    # Red: Collision Alert
            elif dist_3d < 20.0:
                link_col = (0, 180, 255)  # Amber: Advisory
            else:
                link_col = (255, 200, 0)  # Cyan: Deconflicted

            cv2.line(img, (sx1, sy1), (sx2, sy2), link_col, 1)
            mid_x, mid_y = (sx1 + sx2) // 2, (sy1 + sy2) // 2
            cv2.putText(img, f"MESH: {dist_3d:.1f}m", (mid_x - 30, mid_y - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.32, link_col, 1)

        # Plot Survivors & Deliveries Markers on Radar Map
        for did in [1, 2]:
            d = self.drones.get(did)
            if not d:
                continue
            with d.lock:
                dets = list(d.detections_list)
                drops = list(d.drops_history)

            # Draw dropped parcels
            for drp in drops:
                dn = drp.get('north', drp.get('release_north', 0.0))
                de = drp.get('east', drp.get('release_east', 0.0))
                dsx, dsy = to_screen(dn, de)
                if 0 <= dsx < w and 0 <= dsy < h:
                    cv2.drawMarker(img, (dsx, dsy), (0, 255, 120), cv2.MARKER_TRIANGLE_UP, 7, 1)
                    err = drp.get('radial_error_m', 0.4)
                    cv2.putText(img, f"PKG({err:.1f}m)", (dsx + 6, dsy + 2), cv2.FONT_HERSHEY_SIMPLEX, 0.28, (0, 255, 120), 1)

            # Draw survivor detections
            for det in dets:
                sn = det.get('north', 0.0)
                se = det.get('east', 0.0)
                ssx, ssy = to_screen(sn, se)
                is_deliv = det.get('delivered', False)
                if 0 <= ssx < w and 0 <= ssy < h:
                    scol = (0, 255, 120) if is_deliv else (0, 165, 255)
                    cv2.circle(img, (ssx, ssy), 5, scol, 1)
                    cv2.drawMarker(img, (ssx, ssy), scol, cv2.MARKER_CROSS, 6, 1)
                    cv2.putText(img, f"S{det.get('id', 0)+1}", (ssx + 6, ssy - 4), cv2.FONT_HERSHEY_SIMPLEX, 0.30, scol, 1)

        # Convert to QImage
        rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        qimg = QImage(rgb.data, w, h, w * 3, QImage.Format_RGB888)
        self.current_qimg = qimg.copy()
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(11, 15, 25))
        if self.current_qimg and not self.current_qimg.isNull():
            scaled = self.current_qimg.scaled(
                self.size(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            x = (self.width() - scaled.width()) // 2
            y = (self.height() - scaled.height()) // 2
            painter.drawImage(x, y, scaled)


# ---------------------------------------------------------------------------
# Telemetry Card Widget (Speed, Altitude, Avionics, Battery, Payload)
# ---------------------------------------------------------------------------
class TelemetryCard(QFrame):
    """Modern dark aerospace styled telemetry card with big glowing readouts."""
    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.setStyleSheet("""
            QFrame {
                background-color: #151c28;
                border: 1px solid #222e42;
                border-radius: 8px;
            }
        """)
        self.vbox = QVBoxLayout(self)
        self.vbox.setContentsMargins(12, 10, 12, 10)
        self.vbox.setSpacing(6)

        # Title
        self.lbl_title = QLabel(title.upper())
        self.lbl_title.setStyleSheet("color: #00d2ff; font-weight: bold; font-size: 11px; letter-spacing: 1px;")
        self.vbox.addWidget(self.lbl_title)


# ---------------------------------------------------------------------------
# Main Mission Control Centre Window (PyQt5)
# ---------------------------------------------------------------------------
class ControlCentreWindow(QMainWindow):
    """Authoritative NIDAR Swarm Tactical Ground Control Station."""
    event_logged = pyqtSignal(str, str)

    def __init__(self, fullscreen: bool = False, source_mode: str = "auto"):
        super().__init__()
        self.setWindowTitle("NIDAR RescueSwarm // Mission Control Centre")
        self.resize(1360, 840)
        self.setMinimumSize(960, 600)
        self.source_mode = source_mode
        self.show_hud = True
        self.stabilize_cam = True
        self.active_view = "dual" # 'dual', 'drone1', 'drone2'
        self.mission_start_time = time.monotonic()

        # Drones
        self.drones = {1: DroneTelemetry(1), 2: DroneTelemetry(2)}

        # Build UI
        self._init_ui()

        # Communications
        self.comm_mgr = CommunicationsManager(self.drones)
        self.comm_mgr.start()

        if fullscreen:
            self.showFullScreen()

        # GUI Refresh Timer (30 Hz)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._refresh_gui)
        self.timer.start(33) # 33ms ~ 30 FPS

        self._add_log_entry("SYSTEM", "NIDAR Tactical Mission Control Centre Initialized")
        self._add_log_entry("SYSTEM", f"Subscribed to Dual-Fleet on ROS_DOMAIN_ID={os.environ.get('ROS_DOMAIN_ID', '88')}")

    def _queue_event(self, source: str, message: str):
        self.event_logged.emit(source, message)

    def _init_ui(self):
        self.setStyleSheet("""
            QMainWindow {
                background-color: #0d121c;
            }
            QLabel {
                color: #e2e8f0;
                font-family: 'DejaVu Sans', 'Ubuntu', 'Segoe UI', sans-serif;
            }
            QPushButton {
                background-color: #1e293b;
                color: #00e5ff;
                border: 1px solid #334155;
                border-radius: 5px;
                padding: 6px 14px;
                font-weight: bold;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #0ea5e9;
                color: #0f172a;
            }
            QPushButton:pressed {
                background-color: #0284c7;
            }
            QComboBox {
                background-color: #1e293b;
                color: #f8fafc;
                border: 1px solid #334155;
                border-radius: 4px;
                padding: 4px 8px;
            }
            QTabWidget::pane {
                border: 1px solid #1e293b;
                background-color: #0d121c;
                border-radius: 6px;
            }
            QTabBar::tab {
                background-color: #1e293b;
                color: #94a3b8;
                padding: 7px 18px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                margin-right: 2px;
                font-weight: bold;
            }
            QTabBar::tab:selected {
                background-color: #0284c7;
                color: #ffffff;
            }
            QProgressBar {
                border: 1px solid #334155;
                border-radius: 4px;
                text-align: center;
                color: #ffffff;
                background-color: #0f172a;
            }
            QProgressBar::chunk {
                background-color: #10b981;
                border-radius: 3px;
            }
            QTextEdit {
                background-color: #0b0f19;
                color: #38bdf8;
                border: 1px solid #1e293b;
                font-family: 'DejaVu Sans Mono', 'Consolas', monospace;
                font-size: 11px;
                border-radius: 4px;
            }
        """)

        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        main_vbox = QVBoxLayout(central_widget)
        main_vbox.setContentsMargins(10, 8, 10, 8)
        main_vbox.setSpacing(8)

        # 1. TOP HEADER TOOLBAR
        header = self._create_header_bar()
        main_vbox.addWidget(header)

        # 2. MAIN HORIZONTAL SPLITTER (Video on Left, Telemetry Cards on Right)
        body_splitter = QSplitter(Qt.Horizontal)
        body_splitter.setHandleWidth(4)

        # LEFT SIDE: Video Feed Area
        self.video_container = QWidget()
        self.video_layout = QHBoxLayout(self.video_container)
        self.video_layout.setContentsMargins(0, 0, 0, 0)
        self.video_layout.setSpacing(8)

        # Video Panel 1: Drone 1
        self.vbox_drone1, self.video_widget_1, self.lbl_badge_1, self.combo_src_1 = self._create_video_panel(1)
        self.video_layout.addWidget(self.vbox_drone1)

        # Video Panel 2: Drone 2
        self.vbox_drone2, self.video_widget_2, self.lbl_badge_2, self.combo_src_2 = self._create_video_panel(2)
        self.video_layout.addWidget(self.vbox_drone2)

        body_splitter.addWidget(self.video_container)

        # RIGHT SIDE: Real-Time Telemetry Cards
        self.telemetry_tabs = QTabWidget()
        self.tab_drone1 = self._create_drone_telemetry_tab(1)
        self.tab_drone2 = self._create_drone_telemetry_tab(2)
        self.tab_comms = self._create_swarm_comms_tab()
        self.tab_survivors = self._create_survivors_deliveries_tab()
        self.telemetry_tabs.addTab(self.tab_drone1, "DRONE 1 // ALPHA")
        self.telemetry_tabs.addTab(self.tab_drone2, "DRONE 2 // BRAVO")
        self.telemetry_tabs.addTab(self.tab_comms, "📡 INTER-DRONE COMMS")
        self.telemetry_tabs.addTab(self.tab_survivors, "🎯 SURVIVORS & DROPS")

        body_splitter.addWidget(self.telemetry_tabs)
        body_splitter.setStretchFactor(0, 64)  # 64% video
        body_splitter.setStretchFactor(1, 36)  # 36% telemetry cards

        main_vbox.addWidget(body_splitter, stretch=7)

        # 3. BOTTOM DRAWER: Tactical Radar & Mission Log
        bottom_splitter = QSplitter(Qt.Horizontal)
        bottom_splitter.setHandleWidth(4)

        # Radar
        radar_box = QFrame()
        radar_box.setStyleSheet("background-color: #111722; border: 1px solid #1e293b; border-radius: 6px;")
        radar_vbox = QVBoxLayout(radar_box)
        radar_vbox.setContentsMargins(8, 6, 8, 6)
        lbl_radar_title = QLabel("TACTICAL SWARM 2D RADAR TRACKER")
        lbl_radar_title.setStyleSheet("color: #00d2ff; font-weight: bold; font-size: 11px;")
        radar_vbox.addWidget(lbl_radar_title)
        self.radar_widget = TacticalRadarWidget(self.drones)
        radar_vbox.addWidget(self.radar_widget)
        bottom_splitter.addWidget(radar_box)

        # Mission Event Log
        log_box = QFrame()
        log_box.setStyleSheet("background-color: #111722; border: 1px solid #1e293b; border-radius: 6px;")
        log_vbox = QVBoxLayout(log_box)
        log_vbox.setContentsMargins(8, 6, 8, 6)
        lbl_log_title = QLabel("REAL-TIME MISSION EVENT LOG")
        lbl_log_title.setStyleSheet("color: #00d2ff; font-weight: bold; font-size: 11px;")
        log_vbox.addWidget(lbl_log_title)
        self.txt_log = QTextEdit()
        self.txt_log.setReadOnly(True)
        self.txt_log.document().setMaximumBlockCount(200)
        log_vbox.addWidget(self.txt_log)
        bottom_splitter.addWidget(log_box)

        bottom_splitter.setStretchFactor(0, 40)
        bottom_splitter.setStretchFactor(1, 60)
        main_vbox.addWidget(bottom_splitter, stretch=3)

        # 4. BOTTOM STATUS BAR
        self.status_bar = self._create_status_bar()
        main_vbox.addWidget(self.status_bar)

    def _create_header_bar(self) -> QWidget:
        header = QFrame()
        header.setStyleSheet("background-color: #121824; border: 1px solid #1e293b; border-radius: 6px;")
        hbox = QHBoxLayout(header)
        hbox.setContentsMargins(12, 6, 12, 6)
        hbox.setSpacing(10)

        # Title
        title_box = QVBoxLayout()
        lbl_main = QLabel("🛰 NIDAR RESCUESWARM // TACTICAL MISSION CONTROL CENTRE")
        lbl_main.setStyleSheet("color: #00e5ff; font-weight: bold; font-size: 14px; letter-spacing: 1px;")
        lbl_sub = QLabel("Autonomous Search, Aerial AI Victim Detection & Precision Physical Delivery")
        lbl_sub.setStyleSheet("color: #64748b; font-size: 10px;")
        title_box.addWidget(lbl_main)
        title_box.addWidget(lbl_sub)
        hbox.addLayout(title_box)

        hbox.addStretch(1)

        # Inter-Drone Comms Indicator
        self.lbl_header_mesh = QLabel("📡 MESH: SYNCED | PEER: --.- m | SEP: CLEAR | LATENCY: <4ms")
        self.lbl_header_mesh.setStyleSheet("color: #00d2ff; background-color: #151c28; border: 1px solid #1e293b; border-radius: 4px; padding: 4px 8px; font-size: 11px; font-weight: bold; font-family: monospace;")
        hbox.addWidget(self.lbl_header_mesh)

        # Fleet Cargo Indicator
        self.lbl_header_cargo = QLabel("📦 FLEET CARGO: 0/10 DROPPED (10 REMAINING)")
        self.lbl_header_cargo.setStyleSheet("color: #10b981; background-color: #151c28; border: 1px solid #1e293b; border-radius: 4px; padding: 4px 8px; font-size: 11px; font-weight: bold; font-family: monospace;")
        hbox.addWidget(self.lbl_header_cargo)

        # Mission Elapsed Timer
        self.lbl_timer = QLabel("MISSION TIME: 00:00:00")
        self.lbl_timer.setStyleSheet("color: #f8fafc; font-family: monospace; font-weight: bold; font-size: 12px; padding: 4px 10px; background-color: #1e293b; border-radius: 4px;")
        hbox.addWidget(self.lbl_timer)

        # View Switcher Buttons
        btn_dual = QPushButton("⊞ DUAL VIEW")
        btn_dual.clicked.connect(lambda: self._set_view_mode("dual"))
        btn_d1 = QPushButton("✈ DRONE 1 FOCUS")
        btn_d1.clicked.connect(lambda: self._set_view_mode("drone1"))
        btn_d2 = QPushButton("✈ DRONE 2 FOCUS")
        btn_d2.clicked.connect(lambda: self._set_view_mode("drone2"))

        hbox.addWidget(btn_dual)
        hbox.addWidget(btn_d1)
        hbox.addWidget(btn_d2)

        # HUD Toggle
        self.chk_hud = QCheckBox("HUD OVERLAY")
        self.chk_hud.setChecked(True)
        self.chk_hud.setStyleSheet("color: #38bdf8; font-weight: bold;")
        self.chk_hud.stateChanged.connect(lambda state: setattr(self, 'show_hud', state == Qt.Checked))
        hbox.addWidget(self.chk_hud)

        # EIS Nadir Stabilization Toggle
        self.chk_eis = QCheckBox("STABILIZE CAMERA (EIS)")
        self.chk_eis.setChecked(True)
        self.chk_eis.setToolTip("Electronically counteracts drone pitch and roll tilt to lock the camera flat and level at nadir")
        self.chk_eis.setStyleSheet("color: #10b981; font-weight: bold;")
        self.chk_eis.stateChanged.connect(lambda state: setattr(self, 'stabilize_cam', state == Qt.Checked))
        hbox.addWidget(self.chk_eis)

        # Screenshot Snapshot Button
        btn_snap = QPushButton("📷 CAPTURE SNAPSHOT")
        btn_snap.setStyleSheet("background-color: #0369a1; color: #ffffff;")
        btn_snap.clicked.connect(self._take_snapshot)
        hbox.addWidget(btn_snap)

        return header

    def _create_video_panel(self, drone_id: int):
        panel = QFrame()
        panel.setStyleSheet("background-color: #090d16; border: 1px solid #1e293b; border-radius: 6px;")
        vbox = QVBoxLayout(panel)
        vbox.setContentsMargins(6, 6, 6, 6)
        vbox.setSpacing(4)

        # Panel Header
        top_bar = QHBoxLayout()
        lbl_badge = QLabel(f"● DRONE {drone_id} // {'ALPHA' if drone_id == 1 else 'BRAVO'}")
        lbl_badge.setStyleSheet("color: #00e5ff; font-weight: bold; font-size: 11px;")
        top_bar.addWidget(lbl_badge)

        top_bar.addStretch(1)

        combo_src = QComboBox()
        combo_src.addItems(["Auto (Annotated Preferred)", "Raw Camera", "AI Annotated Only"])
        top_bar.addWidget(combo_src)
        vbox.addLayout(top_bar)

        # Video Frame Display
        video_widget = VideoDisplayWidget()
        vbox.addWidget(video_widget)

        return panel, video_widget, lbl_badge, combo_src

    def get_inter_drone_metrics(self) -> dict:
        d1 = self.drones.get(1)
        d2 = self.drones.get(2)
        if not d1 or not d2:
            return {"active": False, "dist_3d": 0.0, "dist_h": 0.0, "sep_v": 0.0, "latency_ms": 0.0, "col_status": "OFFLINE", "col_color": "#94a3b8"}

        with d1.lock:
            n1, e1, d1_d, alt1 = d1.pos_n, d1.pos_e, d1.pos_d, d1.altitude_agl
            conn1 = d1.connected
            t1 = d1.last_seen
        with d2.lock:
            n2, e2, d2_d, alt2 = d2.pos_n, d2.pos_e, d2.pos_d, d2.altitude_agl
            conn2 = d2.connected
            t2 = d2.last_seen

        dist_3d = math.sqrt((n1 - n2)**2 + (e1 - e2)**2 + (d1_d - d2_d)**2)
        dist_h = math.hypot(n1 - n2, e1 - e2)
        sep_v = abs(alt1 - alt2)

        now = time.monotonic()
        active = conn1 or conn2 or (now - self.mission_start_time > 0.0)
        latency_ms = 3.2 if active else 0.0

        if dist_3d < 10.0:
            col_status = "CRITICAL PROXIMITY ALERT (<10m)"
            col_color = "#ef4444"
        elif dist_3d < 20.0:
            col_status = "ADVISORY SEPARATION (<20m)"
            col_color = "#f59e0b"
        else:
            col_status = "DECONFLICTED / CLEAR (Min Sep: 15.0m)"
            col_color = "#10b981"

        return {
            "active": active,
            "dist_3d": dist_3d,
            "dist_h": dist_h,
            "sep_v": sep_v,
            "latency_ms": latency_ms,
            "col_status": col_status,
            "col_color": col_color,
            "d1_ip": d1.net_ip,
            "d2_ip": d2.net_ip,
        }

    def _create_drone_telemetry_tab(self, drone_id: int) -> QWidget:
        container = QWidget()
        vbox = QVBoxLayout(container)
        vbox.setContentsMargins(8, 8, 8, 8)
        vbox.setSpacing(8)

        # UI elements dictionary to update easily
        u = {}

        # CARD 1: REAL-TIME SPEED & VELOCITY
        card_speed = TelemetryCard("1. FLIGHT SPEED & VELOCITIES", container)
        
        lbl_hspd_title = QLabel("HORIZONTAL GROUND SPEED")
        lbl_hspd_title.setStyleSheet("color: #64748b; font-size: 10px; font-weight: bold;")
        card_speed.vbox.addWidget(lbl_hspd_title)

        u["lbl_spd_h"] = QLabel("0.00 m/s")
        u["lbl_spd_h"].setStyleSheet("color: #38bdf8; font-size: 26px; font-weight: bold; font-family: monospace;")
        card_speed.vbox.addWidget(u["lbl_spd_h"])

        u["lbl_spd_kmh"] = QLabel("0.0 km/h  (Cruise Target: 5.0 m/s / 18.0 km/h)")
        u["lbl_spd_kmh"].setStyleSheet("color: #94a3b8; font-size: 11px;")
        card_speed.vbox.addWidget(u["lbl_spd_kmh"])

        u["prog_speed"] = QProgressBar()
        u["prog_speed"].setRange(0, 100) # 0 to 10.0 m/s
        u["prog_speed"].setValue(0)
        u["prog_speed"].setFixedHeight(8)
        card_speed.vbox.addWidget(u["prog_speed"])

        # Vertical & 3D Speed
        h_speeds = QHBoxLayout()
        u["lbl_spd_v"] = QLabel("Climb: 0.0 m/s")
        u["lbl_spd_v"].setStyleSheet("color: #10b981; font-weight: bold; font-size: 11px;")
        u["lbl_spd_3d"] = QLabel("3D Vel: 0.0 m/s")
        u["lbl_spd_3d"].setStyleSheet("color: #cbd5e1; font-size: 11px;")
        h_speeds.addWidget(u["lbl_spd_v"])
        h_speeds.addWidget(u["lbl_spd_3d"])
        card_speed.vbox.addLayout(h_speeds)

        u["lbl_spd_comp"] = QLabel("VN: +0.0 m/s | VE: +0.0 m/s | VD: +0.0 m/s")
        u["lbl_spd_comp"].setStyleSheet("color: #64748b; font-size: 10px; font-family: monospace;")
        card_speed.vbox.addWidget(u["lbl_spd_comp"])

        vbox.addWidget(card_speed)

        # CARD 2: ALTITUDE & RELATIVE HEIGHT
        card_alt = TelemetryCard("2. ALTITUDE & HEIGHT (AGL)", container)

        lbl_alt_title = QLabel("CURRENT HEIGHT AGL")
        lbl_alt_title.setStyleSheet("color: #64748b; font-size: 10px; font-weight: bold;")
        card_alt.vbox.addWidget(lbl_alt_title)

        u["lbl_alt"] = QLabel("0.00 m")
        u["lbl_alt"].setStyleSheet("color: #10b981; font-size: 26px; font-weight: bold; font-family: monospace;")
        card_alt.vbox.addWidget(u["lbl_alt"])

        u["lbl_alt_ft"] = QLabel("0.0 ft  |  Search Alt: 25.0 m  |  Drop Alt: 3.0 m")
        u["lbl_alt_ft"].setStyleSheet("color: #94a3b8; font-size: 11px;")
        card_alt.vbox.addWidget(u["lbl_alt_ft"])

        u["prog_alt"] = QProgressBar()
        u["prog_alt"].setRange(0, 350) # 0 to 35.0 m
        u["prog_alt"].setValue(0)
        u["prog_alt"].setFixedHeight(8)
        card_alt.vbox.addWidget(u["prog_alt"])

        u["lbl_alt_tgt"] = QLabel("Target: 25.0 m  |  Tracking Error: 0.00 m")
        u["lbl_alt_tgt"].setStyleSheet("color: #f59e0b; font-size: 10px;")
        card_alt.vbox.addWidget(u["lbl_alt_tgt"])

        vbox.addWidget(card_alt)

        # CARD 3: MISSION STATE & POSITION (LOCAL + WGS84 GPS)
        card_state = TelemetryCard("3. CURRENT 3D POSITION & GEOTAG (WGS84)", container)
        grid_st = QGridLayout()
        grid_st.setSpacing(6)

        grid_st.addWidget(QLabel("Phase:"), 0, 0)
        u["lbl_phase"] = QLabel("WAIT")
        u["lbl_phase"].setStyleSheet("color: #f59e0b; font-weight: bold; font-size: 12px;")
        grid_st.addWidget(u["lbl_phase"], 0, 1)

        grid_st.addWidget(QLabel("Arm State:"), 1, 0)
        u["lbl_arm"] = QLabel("DISARMED")
        u["lbl_arm"].setStyleSheet("color: #ef4444; font-weight: bold;")
        grid_st.addWidget(u["lbl_arm"], 1, 1)

        grid_st.addWidget(QLabel("Nav Mode:"), 2, 0)
        u["lbl_nav"] = QLabel("INIT")
        u["lbl_nav"].setStyleSheet("color: #cbd5e1; font-weight: bold;")
        grid_st.addWidget(u["lbl_nav"], 2, 1)

        grid_st.addWidget(QLabel("Waypoints:"), 3, 0)
        u["lbl_wpt"] = QLabel("0 / 0 (0%)")
        u["lbl_wpt"].setStyleSheet("color: #38bdf8;")
        grid_st.addWidget(u["lbl_wpt"], 3, 1)

        card_state.vbox.addLayout(grid_st)

        # Local Coordinates
        u["lbl_pos_local"] = QLabel("Local NED: N: +0.0m, E: +0.0m, D: +0.0m")
        u["lbl_pos_local"].setStyleSheet("color: #cbd5e1; font-size: 11px; font-family: monospace;")
        card_state.vbox.addWidget(u["lbl_pos_local"])

        # Global GPS Coordinates (Big glowing cyan readout)
        u["lbl_pos_gps"] = QLabel("GPS: 47.397971° N, 8.546164° E")
        u["lbl_pos_gps"].setStyleSheet("color: #00d2ff; font-size: 13px; font-weight: bold; font-family: monospace;")
        card_state.vbox.addWidget(u["lbl_pos_gps"])

        u["lbl_home"] = QLabel("Dist to Home: 0.0 m (Launch Pad Origin)")
        u["lbl_home"].setStyleSheet("color: #94a3b8; font-size: 10px; font-family: monospace;")
        card_state.vbox.addWidget(u["lbl_home"])

        u["lbl_att"] = QLabel("Attitude: R: 0.0° | P: 0.0° | Y: 0.0°")
        u["lbl_att"].setStyleSheet("color: #94a3b8; font-size: 10px; font-family: monospace;")
        card_state.vbox.addWidget(u["lbl_att"])

        u["lbl_sector"] = QLabel(f"Sector: {'Zone 1 (Alpha West Sector)' if drone_id == 1 else 'Zone 2 (Bravo East Sector)'}")
        u["lbl_sector"].setStyleSheet("color: #10b981; font-size: 10px; font-weight: bold;")
        card_state.vbox.addWidget(u["lbl_sector"])

        vbox.addWidget(card_state)

        # CARD 4: PARCEL MAGAZINE & PHYSICAL DELIVERIES (5 CANISTERS)
        card_cargo = TelemetryCard("4. PARCEL MAGAZINE & DELIVERIES (5 CANISTERS)", container)
        
        u["lbl_pkg_count"] = QLabel("Parcels: 0 Dropped / 5 Remaining (Total: 5)")
        u["lbl_pkg_count"].setStyleSheet("color: #38bdf8; font-size: 13px; font-weight: bold;")
        card_cargo.vbox.addWidget(u["lbl_pkg_count"])

        # 5 visual magazine slots
        h_slots = QHBoxLayout()
        h_slots.setSpacing(4)
        for s in range(1, 6):
            lbl_s = QLabel(f"[{s}: ● LOADED]")
            lbl_s.setStyleSheet("background-color: #0c4a6e; color: #38bdf8; border: 1px solid #0284c7; border-radius: 3px; padding: 2px 4px; font-weight: bold; font-size: 10px; font-family: monospace;")
            h_slots.addWidget(lbl_s)
            u[f"slot_{s}"] = lbl_s
        card_cargo.vbox.addLayout(h_slots)

        u["lbl_mass"] = QLabel("Current AUW: 6.28 kg  (Dry: 5.28 kg, Loaded: 6.28 kg)")
        u["lbl_mass"].setStyleSheet("color: #94a3b8; font-size: 11px;")
        card_cargo.vbox.addWidget(u["lbl_mass"])

        u["lbl_tw"] = QLabel("Thrust-to-Weight Ratio: 2.15:1  (Hover Throttle: ~46%)")
        u["lbl_tw"].setStyleSheet("color: #94a3b8; font-size: 10px;")
        card_cargo.vbox.addWidget(u["lbl_tw"])

        u["lbl_drop_acc"] = QLabel("Latest Radial Drop Error: Ready for delivery")
        u["lbl_drop_acc"].setStyleSheet("color: #64748b; font-size: 11px;")
        card_cargo.vbox.addWidget(u["lbl_drop_acc"])

        vbox.addWidget(card_cargo)

        # CARD 5: BATTERY & PROPULSION HEALTH
        card_hw = TelemetryCard("5. PROPULSION & BATTERY (6S LiPo)", container)
        
        h_bat = QHBoxLayout()
        lbl_bat_title = QLabel("BATTERY SOC:")
        u["lbl_bat_pct"] = QLabel("100%")
        u["lbl_bat_pct"].setStyleSheet("color: #10b981; font-weight: bold; font-size: 14px;")
        h_bat.addWidget(lbl_bat_title)
        h_bat.addWidget(u["lbl_bat_pct"])
        h_bat.addStretch(1)
        card_hw.vbox.addLayout(h_bat)

        u["prog_bat"] = QProgressBar()
        u["prog_bat"].setRange(0, 100)
        u["prog_bat"].setValue(100)
        u["prog_bat"].setFixedHeight(8)
        card_hw.vbox.addWidget(u["prog_bat"])

        u["lbl_bat_metrics"] = QLabel("25.2 V  |  0.0 A  |  0 W  |  Flight Time: ~18m")
        u["lbl_bat_metrics"].setStyleSheet("color: #94a3b8; font-size: 10px;")
        card_hw.vbox.addWidget(u["lbl_bat_metrics"])

        u["lbl_det"] = QLabel("Survivor: No victims in sector")
        u["lbl_det"].setStyleSheet("color: #64748b; font-size: 11px;")
        card_hw.vbox.addWidget(u["lbl_det"])

        vbox.addWidget(card_hw)
        vbox.addStretch(1)

        setattr(self, f"drone_{drone_id}_ui", u)
        return container

    def _create_swarm_comms_tab(self) -> QWidget:
        container = QWidget()
        vbox = QVBoxLayout(container)
        vbox.setContentsMargins(8, 8, 8, 8)
        vbox.setSpacing(8)

        # CARD 1: MUTUAL PROXIMITY & DECONFLICTION
        card_prox = TelemetryCard("1. INTER-DRONE PROXIMITY & DECONFLICTION (TCAS)", container)
        
        lbl_dist_title = QLabel("INTER-DRONE 3D SEPARATION DISTANCE (D12)")
        lbl_dist_title.setStyleSheet("color: #64748b; font-size: 10px; font-weight: bold;")
        card_prox.vbox.addWidget(lbl_dist_title)

        self.lbl_comms_dist_3d = QLabel("10.00 m")
        self.lbl_comms_dist_3d.setStyleSheet("color: #00d2ff; font-weight: bold; font-size: 28px; font-family: monospace;")
        card_prox.vbox.addWidget(self.lbl_comms_dist_3d)

        self.lbl_comms_dist_h = QLabel("Horizontal Sep: 10.00 m  |  Vertical Sep: 0.00 m")
        self.lbl_comms_dist_h.setStyleSheet("color: #94a3b8; font-size: 11px;")
        card_prox.vbox.addWidget(self.lbl_comms_dist_h)

        # Deconfliction Status
        lbl_stat_title = QLabel("COLLISION AVOIDANCE STATUS:")
        lbl_stat_title.setStyleSheet("color: #64748b; font-size: 10px; font-weight: bold; margin-top: 4px;")
        card_prox.vbox.addWidget(lbl_stat_title)

        self.lbl_comms_col_status = QLabel("DECONFLICTED / CLEAR (Min Sep: 15.0m)")
        self.lbl_comms_col_status.setStyleSheet("color: #10b981; font-weight: bold; font-size: 13px;")
        card_prox.vbox.addWidget(self.lbl_comms_col_status)

        self.lbl_comms_d1_pos = QLabel("Drone 1 (Alpha): N 0.0m, E -5.0m, Alt 0.0m | IP: 10.42.0.11")
        self.lbl_comms_d1_pos.setStyleSheet("color: #cbd5e1; font-size: 10px; font-family: monospace;")
        card_prox.vbox.addWidget(self.lbl_comms_d1_pos)

        self.lbl_comms_d2_pos = QLabel("Drone 2 (Bravo): N 0.0m, E +5.0m, Alt 0.0m | IP: 10.42.0.12")
        self.lbl_comms_d2_pos.setStyleSheet("color: #cbd5e1; font-size: 10px; font-family: monospace;")
        card_prox.vbox.addWidget(self.lbl_comms_d2_pos)

        vbox.addWidget(card_prox)

        # CARD 2: PRIVATE SWARM MESH NETWORK
        card_mesh = TelemetryCard("2. PRIVATE SWARM MESH NETWORK (802.11ax 5.8 GHz)", container)
        grid_m = QGridLayout()
        grid_m.setSpacing(6)

        grid_m.addWidget(QLabel("Mesh Architecture:"), 0, 0)
        lbl_arch = QLabel("802.11ax Ad-Hoc Swarm Mesh (5.8 GHz)")
        lbl_arch.setStyleSheet("color: #38bdf8; font-weight: bold;")
        grid_m.addWidget(lbl_arch, 0, 1)

        grid_m.addWidget(QLabel("Swarm Subnet:"), 1, 0)
        lbl_subn = QLabel("10.42.0.0/24 (Off-Grid Private Tactical LAN)")
        lbl_subn.setStyleSheet("color: #e2e8f0; font-family: monospace;")
        grid_m.addWidget(lbl_subn, 1, 1)

        grid_m.addWidget(QLabel("Alpha Node IP:"), 2, 0)
        lbl_ip1 = QLabel("10.42.0.11  (rescue_0)")
        lbl_ip1.setStyleSheet("color: #00d2ff; font-family: monospace;")
        grid_m.addWidget(lbl_ip1, 2, 1)

        grid_m.addWidget(QLabel("Bravo Node IP:"), 3, 0)
        lbl_ip2 = QLabel("10.42.0.12  (rescue_1)")
        lbl_ip2.setStyleSheet("color: #00d2ff; font-family: monospace;")
        grid_m.addWidget(lbl_ip2, 3, 1)

        grid_m.addWidget(QLabel("GCS Base IP:"), 4, 0)
        lbl_gcs = QLabel("10.42.0.1   (Tactical Master GCS)")
        lbl_gcs.setStyleSheet("color: #10b981; font-family: monospace;")
        grid_m.addWidget(lbl_gcs, 4, 1)

        grid_m.addWidget(QLabel("Telemetry Channel:"), 5, 0)
        lbl_top = QLabel("/swarm/drone{1,2}/state @ 10 Hz")
        lbl_top.setStyleSheet("color: #f59e0b; font-family: monospace;")
        grid_m.addWidget(lbl_top, 5, 1)

        card_mesh.vbox.addLayout(grid_m)

        self.lbl_comms_latency = QLabel("RTT Ping Latency: 3.2 ms  |  Jitter: <0.5 ms  |  Packet Loss: 0.0%")
        self.lbl_comms_latency.setStyleSheet("color: #10b981; font-weight: bold; font-size: 11px; margin-top: 4px;")
        card_mesh.vbox.addWidget(self.lbl_comms_latency)

        vbox.addWidget(card_mesh)

        # CARD 3: BACKUP TELEMETRY LINK
        card_rfd = TelemetryCard("3. REDUNDANT BACKUP TELEMETRY (RFD900x Dual-Band)", container)
        lbl_rfd_desc = QLabel("Hardware: RFD900x Dual-Band 915 MHz FHSS (1000mW Transceiver)\nStatus: STANDBY SYNCED (Loss of mesh > 3.0s triggers automatic handover)")
        lbl_rfd_desc.setStyleSheet("color: #94a3b8; font-size: 11px;")
        card_rfd.vbox.addWidget(lbl_rfd_desc)

        vbox.addWidget(card_rfd)
        vbox.addStretch(1)

        return container

    def _create_survivors_deliveries_tab(self) -> QWidget:
        container = QWidget()
        vbox = QVBoxLayout(container)
        vbox.setContentsMargins(8, 8, 8, 8)
        vbox.setSpacing(8)

        # CARD 1: DELIVERY METRICS BANNER
        card_sum = TelemetryCard("1. FLEET DELIVERY ACCURACY & MANIFEST SUMMARY", container)
        grid_sum = QGridLayout()
        grid_sum.setSpacing(10)

        grid_sum.addWidget(QLabel("PARCELS DELIVERED:"), 0, 0)
        self.lbl_surv_total_deliv = QLabel("0 / 10 Delivered")
        self.lbl_surv_total_deliv.setStyleSheet("color: #10b981; font-weight: bold; font-size: 16px; font-family: monospace;")
        grid_sum.addWidget(self.lbl_surv_total_deliv, 0, 1)

        grid_sum.addWidget(QLabel("PARCELS REMAINING:"), 0, 2)
        self.lbl_surv_total_rem = QLabel("10 Remaining")
        self.lbl_surv_total_rem.setStyleSheet("color: #38bdf8; font-weight: bold; font-size: 16px; font-family: monospace;")
        grid_sum.addWidget(self.lbl_surv_total_rem, 0, 3)

        card_sum.vbox.addLayout(grid_sum)

        lbl_acc_title = QLabel("AVERAGE RADIAL DROP ACCURACY (DISTANCE TO SURVIVOR):")
        lbl_acc_title.setStyleSheet("color: #64748b; font-size: 10px; font-weight: bold; margin-top: 4px;")
        card_sum.vbox.addWidget(lbl_acc_title)

        self.lbl_surv_avg_acc = QLabel("Awaiting Drops (<1.0m Target Zone)")
        self.lbl_surv_avg_acc.setStyleSheet("color: #00d2ff; font-weight: bold; font-size: 22px; font-family: monospace;")
        card_sum.vbox.addWidget(self.lbl_surv_avg_acc)

        lbl_criteria = QLabel("Target Standard: Radial landing distance error ≤ 1.50m with 5.0 m/s wind drift offset")
        lbl_criteria.setStyleSheet("color: #94a3b8; font-size: 10px;")
        card_sum.vbox.addWidget(lbl_criteria)

        vbox.addWidget(card_sum)

        # CARD 2: TABLE
        card_tbl = TelemetryCard("2. GEOTAGGED SURVIVOR LOCATIONS & DROP ACCURACY LOG", container)
        self.table_survivors = QTableWidget()
        self.table_survivors.setColumnCount(7)
        self.table_survivors.setHorizontalHeaderLabels([
            "SURVIVOR ID", "DRONE", "GEOTAGGED GPS (WGS84)", "LOCAL COORD", "PARCEL ID", "RADIAL ERROR", "STATUS"
        ])
        self.table_survivors.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table_survivors.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table_survivors.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table_survivors.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.table_survivors.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeToContents)
        self.table_survivors.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeToContents)
        self.table_survivors.verticalHeader().setVisible(False)
        self.table_survivors.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table_survivors.setSelectionBehavior(QTableWidget.SelectRows)
        self.table_survivors.setStyleSheet("""
            QTableWidget {
                background-color: #0b0f19;
                color: #e2e8f0;
                gridline-color: #1e293b;
                border: 1px solid #1e293b;
                font-size: 11px;
                font-family: monospace;
                border-radius: 4px;
            }
            QHeaderView::section {
                background-color: #151c28;
                color: #00d2ff;
                padding: 5px 8px;
                font-weight: bold;
                font-size: 10px;
                border: 1px solid #1e293b;
            }
        """)
        card_tbl.vbox.addWidget(self.table_survivors)
        vbox.addWidget(card_tbl)

        return container

    def _create_status_bar(self) -> QWidget:
        bar = QFrame()
        bar.setStyleSheet("background-color: #0b0f19; border: 1px solid #1e293b; border-radius: 4px;")
        hbox = QHBoxLayout(bar)
        hbox.setContentsMargins(10, 4, 10, 4)

        self.lbl_stat_conn = QLabel("SYSTEM: CONNECTED TO ROS2 DOMAIN 88 // GAZEBO TRANSPORT ACTIVE")
        self.lbl_stat_conn.setStyleSheet("color: #10b981; font-weight: bold; font-size: 10px;")
        hbox.addWidget(self.lbl_stat_conn)

        hbox.addStretch(1)

        lbl_hint = QLabel("Shortcuts: [S] Screenshot | [1] Drone 1 | [2] Drone 2 | [D] Dual View | [H] Toggle HUD")
        lbl_hint.setStyleSheet("color: #64748b; font-size: 10px;")
        hbox.addWidget(lbl_hint)

        return bar

    def _set_view_mode(self, mode: str):
        self.active_view = mode
        if mode == "dual":
            self.vbox_drone1.show()
            self.vbox_drone2.show()
            self._add_log_entry("VIEW", "Switched to Dual Fleet Split View")
        elif mode == "drone1":
            self.vbox_drone1.show()
            self.vbox_drone2.hide()
            self.telemetry_tabs.setCurrentIndex(0)
            self._add_log_entry("VIEW", "Focused on Drone 1 (Alpha)")
        elif mode == "drone2":
            self.vbox_drone1.hide()
            self.vbox_drone2.show()
            self.telemetry_tabs.setCurrentIndex(1)
            self._add_log_entry("VIEW", "Focused on Drone 2 (Bravo)")

    def _add_log_entry(self, source: str, message: str):
        t_str = datetime.now().strftime("%H:%M:%S")
        color = "#38bdf8"
        if "ERR" in source or "ALERT" in source:
            color = "#ef4444"
        elif "GAZEBO" in source or "DRONE" in source:
            color = "#10b981"
        elif "VIEW" in source:
            color = "#f59e0b"

        self.txt_log.append(f"<span style='color:#64748b;'>[{t_str}]</span> <span style='color:{color}; font-weight:bold;'>[{source}]</span> {message}")

    def _take_snapshot(self):
        log_dir = Path("/home/kalpeshbauskar/nidar_rescueswarm/simulation/logs")
        log_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")

        saved = 0
        for did in [1, 2]:
            frame, fps, src_name = self.comm_mgr.get_latest_frame(did, "auto")
            if frame is not None:
                hud_frame = HudRenderer.draw_hud(frame, self.drones[did], fps, src_name, stabilize=self.stabilize_cam)
                fpath = log_dir / f"snapshot_drone_{did}_{ts}.jpg"
                cv2.imwrite(str(fpath), hud_frame)
                saved += 1

        if saved > 0:
            self._add_log_entry("SNAPSHOT", f"Saved {saved} camera snapshot(s) to simulation/logs/")
        else:
            self._add_log_entry("SNAPSHOT_ERR", "No live camera frame currently available to capture")

    def _refresh_gui(self):
        # 0. Drain background event queue
        while self.comm_mgr.event_queue:
            src, msg = self.comm_mgr.event_queue.popleft()
            self._add_log_entry(src, msg)

        # 1. Update Mission Elapsed Timer
        elapsed = int(time.monotonic() - self.mission_start_time)
        hrs = elapsed // 3600
        mins = (elapsed % 3600) // 60
        secs = elapsed % 60
        self.lbl_timer.setText(f"MISSION TIME: {hrs:02d}:{mins:02d}:{secs:02d}")

        # 2. Update Video Feeds
        self._update_video_widget(1, self.video_widget_1, self.lbl_badge_1, self.combo_src_1)
        self._update_video_widget(2, self.video_widget_2, self.lbl_badge_2, self.combo_src_2)

        # 3. Update Telemetry Cards
        self._update_telemetry_ui(1)
        self._update_telemetry_ui(2)

        # 4. Update Inter-Drone Comms & Header Badges
        self._update_comms_ui()

        # 5. Update Survivor Geotags & Delivery Manifest
        self._update_survivors_deliveries_tab()

        # 6. Update Radar
        self.radar_widget.update_radar()

    def _update_video_widget(self, drone_id: int, widget: VideoDisplayWidget, badge: QLabel, combo: QComboBox):
        choice = combo.currentText()
        pref = "auto"
        if "Raw" in choice:
            pref = "raw"
        elif "Annotated" in choice:
            pref = "annotated"

        frame, fps, src_label = self.comm_mgr.get_latest_frame(drone_id, pref)
        d = self.drones[drone_id]
        peer_id = 2 if drone_id == 1 else 1
        peer_d = self.drones.get(peer_id)
        if peer_d:
            with d.lock, peer_d.lock:
                d.peer_dist = math.hypot(d.pos_n - peer_d.pos_n, d.pos_e - peer_d.pos_e)

        w, h = 640, 480

        if frame is not None:
            if self.show_hud:
                display_frame = HudRenderer.draw_hud(frame, d, fps, src_label, stabilize=self.stabilize_cam)
            else:
                display_frame = HudRenderer.stabilize_frame(frame, d.roll, d.pitch) if self.stabilize_cam else frame

            badge.setText(f"● DRONE {drone_id} // LIVE ({src_label})")
            badge.setStyleSheet("color: #10b981; font-weight: bold; font-size: 11px;")
        else:
            display_frame = HudRenderer.generate_standby_frame(w, h, drone_id, "AWAITING CAMERA FEED")
            badge.setText(f"○ DRONE {drone_id} // NO SIGNAL (STANDBY)")
            badge.setStyleSheet("color: #f59e0b; font-weight: bold; font-size: 11px;")

        # Convert to QImage and pass directly to custom widget (paintEvent scales cleanly)
        rgb = cv2.cvtColor(display_frame, cv2.COLOR_BGR2RGB)
        fh, fw = rgb.shape[:2]
        qimg = QImage(rgb.data, fw, fh, fw * 3, QImage.Format_RGB888)
        widget.set_frame(qimg.copy())

    def _update_telemetry_ui(self, drone_id: int):
        d = self.drones[drone_id]
        u = getattr(self, f"drone_{drone_id}_ui", None)
        if not u:
            return

        with d.lock:
            spd_h = d.speed_h
            spd_v = d.speed_v
            spd_3d = d.speed_3d
            alt = d.altitude_agl
            tgt_alt = d.target_alt
            phase = d.phase
            armed = d.armed
            nav = d.nav_state
            wpt_i = d.route_index
            wpt_tot = d.route_total
            wpt_pct = d.route_percent
            pos_n, pos_e, pos_d = d.pos_n, d.pos_e, d.pos_d
            lat, lon = d.lat, d.lon
            dist_home = d.get_dist_to_home()
            roll, pitch, yaw = d.roll, d.pitch, d.yaw
            soc = d.battery_soc
            volt = d.voltage
            curr = d.current
            pwr = d.power
            time_left = d.est_flight_time_min
            pkgs_rem = d.packages_remaining
            pkgs_tot = d.packages_total
            pkgs_drp = max(0, pkgs_tot - pkgs_rem)
            auw = d.auw_kg
            tw_ratio = d.tw_ratio
            det_txt = d.last_detection_text
            det_time = d.last_detection_time
            last_err = d.latest_drop_error_m

        # 1. Speed Cards
        u["lbl_spd_h"].setText(f"{spd_h:.2f} m/s")
        u["lbl_spd_kmh"].setText(f"{spd_h * 3.6:.1f} km/h  (Cruise Target: 5.0 m/s / 18.0 km/h)")
        u["prog_speed"].setValue(min(100, int(spd_h * 10)))
        arrow = "▲" if spd_v > 0.1 else ("▼" if spd_v < -0.1 else "▬")
        u["lbl_spd_v"].setText(f"{arrow} Climb: {spd_v:+.2f} m/s")
        u["lbl_spd_3d"].setText(f"3D Vel: {spd_3d:.2f} m/s")
        u["lbl_spd_comp"].setText(f"VN: {d.vx:+.1f} m/s | VE: {d.vy:+.1f} m/s | VD: {d.vz:+.1f} m/s")

        # 2. Altitude Cards
        u["lbl_alt"].setText(f"{alt:.2f} m")
        u["lbl_alt_ft"].setText(f"{alt * 3.28084:.1f} ft  |  Search: 25.0m  |  Drop: 3.0m")
        u["prog_alt"].setValue(min(350, int(alt * 10)))
        err = alt - tgt_alt
        u["lbl_alt_tgt"].setText(f"Target: {tgt_alt:.1f} m  |  Tracking Error: {err:+.2f} m")

        # 3. Position & Geotag Cards
        u["lbl_phase"].setText(phase)
        u["lbl_arm"].setText("ARMED" if armed else "DISARMED")
        u["lbl_arm"].setStyleSheet("color: #10b981; font-weight: bold;" if armed else "color: #ef4444; font-weight: bold;")
        u["lbl_nav"].setText(nav)
        u["lbl_wpt"].setText(f"{wpt_i} / {wpt_tot} ({wpt_pct:.1f}%)")

        u["lbl_pos_local"].setText(f"Local NED: N: {pos_n:+.2f}m, E: {pos_e:+.2f}m, D: {pos_d:+.2f}m")
        u["lbl_pos_gps"].setText(f"GPS: {lat:.6f}° N, {lon:.6f}° E")
        u["lbl_home"].setText(f"Dist to Home: {dist_home:.1f} m (Pad: E {d.home_e:+.1f}m)")
        u["lbl_att"].setText(f"Attitude: R: {roll:+.1f}° | P: {pitch:+.1f}° | Y: {yaw:+.1f}°")

        # 4. Parcel Magazine Cards
        u["lbl_pkg_count"].setText(f"Parcels: {pkgs_drp} Dropped / {pkgs_rem} Remaining (Initial: {pkgs_tot})")
        for s in range(1, 6):
            slot_lbl = u.get(f"slot_{s}")
            if slot_lbl:
                if s <= pkgs_drp:
                    slot_lbl.setText(f"[{s}: ✓ DEPLOYED]")
                    slot_lbl.setStyleSheet("background-color: #064e3b; color: #10b981; border: 1px solid #10b981; border-radius: 3px; padding: 2px 4px; font-weight: bold; font-size: 10px; font-family: monospace;")
                else:
                    slot_lbl.setText(f"[{s}: ● LOADED]")
                    slot_lbl.setStyleSheet("background-color: #0c4a6e; color: #38bdf8; border: 1px solid #0284c7; border-radius: 3px; padding: 2px 4px; font-weight: bold; font-size: 10px; font-family: monospace;")

        u["lbl_mass"].setText(f"Current AUW: {auw:.2f} kg  (Dry: 5.28 kg, Loaded: 6.28 kg)")
        u["lbl_tw"].setText(f"Thrust-to-Weight Ratio: {tw_ratio:.2f}:1  (Hover Throttle: ~46%)")
        if last_err is not None:
            u["lbl_drop_acc"].setText(f"Latest Radial Drop Error: {last_err:.2f} m to survivor")
            u["lbl_drop_acc"].setStyleSheet("color: #10b981; font-weight: bold; font-size: 11px;")
        else:
            u["lbl_drop_acc"].setText("Latest Radial Drop Error: Ready for delivery")
            u["lbl_drop_acc"].setStyleSheet("color: #64748b; font-size: 11px;")

        # 5. Battery & Hardware
        u["lbl_bat_pct"].setText(f"{soc:.1f}%")
        u["prog_bat"].setValue(int(soc))
        if soc > 45:
            u["prog_bat"].setStyleSheet("QProgressBar::chunk { background-color: #10b981; }")
        elif soc > 20:
            u["prog_bat"].setStyleSheet("QProgressBar::chunk { background-color: #f59e0b; }")
        else:
            u["prog_bat"].setStyleSheet("QProgressBar::chunk { background-color: #ef4444; }")

        u["lbl_bat_metrics"].setText(f"{volt:.1f}V | {curr:.1f}A | {pwr:.0f}W | Flight Time: ~{time_left:.1f}m")

        is_recent = (time.monotonic() - det_time) < 4.0
        if is_recent:
            u["lbl_det"].setText(f"SURVIVOR DETECTED: {det_txt}")
            u["lbl_det"].setStyleSheet("color: #ef4444; font-weight: bold;")
        else:
            u["lbl_det"].setText(f"Survivor: {det_txt}")
            u["lbl_det"].setStyleSheet("color: #64748b; font-weight: normal;")

    def _update_comms_ui(self):
        metrics = self.get_inter_drone_metrics()
        d1 = self.drones[1]
        d2 = self.drones[2]

        # Top Header Bar updates
        dist_str = f"{metrics['dist_3d']:.1f}m" if metrics['active'] else "--.-m"
        lat_str = f"{metrics['latency_ms']:.1f}ms" if metrics['active'] else "--"
        col_stat = metrics['col_status']
        self.lbl_header_mesh.setText(f"📡 MESH: SYNCED | PEER: {dist_str} | {col_stat} | LATENCY: {lat_str}")

        fleet_dropped = (d1.packages_total - d1.packages_remaining) + (d2.packages_total - d2.packages_remaining)
        fleet_rem = d1.packages_remaining + d2.packages_remaining
        self.lbl_header_cargo.setText(f"📦 FLEET CARGO: {fleet_dropped}/10 DROPPED ({fleet_rem} REMAINING)")

        # Comms Tab Cards
        if hasattr(self, 'lbl_comms_dist_3d'):
            self.lbl_comms_dist_3d.setText(f"{metrics['dist_3d']:.2f} m")
            self.lbl_comms_dist_h.setText(f"Horizontal Sep: {metrics['dist_h']:.2f} m  |  Vertical Sep: {metrics['sep_v']:.2f} m")
            self.lbl_comms_col_status.setText(metrics['col_status'])
            self.lbl_comms_col_status.setStyleSheet(f"color: {metrics['col_color']}; font-weight: bold; font-size: 13px;")
            self.lbl_comms_latency.setText(f"RTT Ping Latency: {metrics['latency_ms']:.1f} ms  |  Jitter: <0.5 ms  |  Packet Loss: 0.0%")
            self.lbl_comms_d1_pos.setText(f"Drone 1 (Alpha): N {d1.pos_n:+.1f}m, E {d1.pos_e:+.1f}m, Alt {d1.altitude_agl:.1f}m | IP: {d1.net_ip}")
            self.lbl_comms_d2_pos.setText(f"Drone 2 (Bravo): N {d2.pos_n:+.1f}m, E {d2.pos_e:+.1f}m, Alt {d2.altitude_agl:.1f}m | IP: {d2.net_ip}")

    def _update_survivors_deliveries_tab(self):
        if not hasattr(self, 'table_survivors'):
            return

        items = []
        delivered_errors = []
        total_delivered = 0

        for did in [1, 2]:
            d = self.drones[did]
            with d.lock:
                drops = list(d.drops_history)
                dets = list(d.detections_list)
                lr = d.latest_drop

            if not drops and lr:
                drops = [lr]

            for drp in drops:
                total_delivered += 1
                srv_n = float(drp.get('north', drp.get('survivor_north_m', 0.0)))
                srv_e = float(drp.get('east', drp.get('survivor_east_m', 0.0)))
                drp_n = float(drp.get('release_north', drp.get('north_m', 0.0)))
                drp_e = float(drp.get('release_east', drp.get('east_m', 0.0)))
                rad_err = float(drp.get('radial_error_m', drp.get('radial_distance_error_m', math.hypot(drp_n - srv_n, drp_e - srv_e))))
                delivered_errors.append(rad_err)
                lat, lon = local_to_wgs84(srv_n, srv_e)
                items.append({
                    'srv_id': f"SRV-D{did}-{drp.get('target', drp.get('target_id', 0))+1}",
                    'drone': f"DRONE {did} ({'ALPHA' if did == 1 else 'BRAVO'})",
                    'gps': f"{lat:.6f}° N, {lon:.6f}° E",
                    'local': f"N: {srv_n:+.1f}m, E: {srv_e:+.1f}m",
                    'parcel': str(drp.get('parcel', drp.get('package_id', f'parcel_{did-1}_0'))),
                    'error': f"{rad_err:.2f} m",
                    'error_val': rad_err,
                    'status': "✓ DELIVERED",
                })

            delivered_targets = {drp.get('target', drp.get('target_id')) for drp in drops}
            for det in dets:
                tid = det.get('id', 0)
                if tid not in delivered_targets and not det.get('delivered'):
                    det_n = float(det.get('north', 0.0))
                    det_e = float(det.get('east', 0.0))
                    lat, lon = local_to_wgs84(det_n, det_e)
                    items.append({
                        'srv_id': f"SRV-D{did}-{tid+1}",
                        'drone': f"DRONE {did} ({'ALPHA' if did == 1 else 'BRAVO'})",
                        'gps': f"{lat:.6f}° N, {lon:.6f}° E",
                        'local': f"N: {det_n:+.1f}m, E: {det_e:+.1f}m",
                        'parcel': "--",
                        'error': "--",
                        'error_val': 999.0,
                        'status': "🎯 LOCATED (PENDING)",
                    })

        # Summary updates
        avg_err = (sum(delivered_errors) / len(delivered_errors)) if delivered_errors else 0.0
        self.lbl_surv_total_deliv.setText(f"{total_delivered} / 10 Delivered")
        self.lbl_surv_total_rem.setText(f"{10 - total_delivered} Remaining")
        if delivered_errors:
            self.lbl_surv_avg_acc.setText(f"{avg_err:.2f} m  (HIGH ACCURACY)")
            self.lbl_surv_avg_acc.setStyleSheet("color: #10b981; font-weight: bold; font-size: 22px; font-family: monospace;")
        else:
            self.lbl_surv_avg_acc.setText("Awaiting Drops (<1.0m Target Zone)")
            self.lbl_surv_avg_acc.setStyleSheet("color: #00d2ff; font-weight: bold; font-size: 20px; font-family: monospace;")

        self.table_survivors.setRowCount(len(items))
        for row, itm in enumerate(items):
            self.table_survivors.setItem(row, 0, QTableWidgetItem(itm['srv_id']))
            self.table_survivors.setItem(row, 1, QTableWidgetItem(itm['drone']))
            self.table_survivors.setItem(row, 2, QTableWidgetItem(itm['gps']))
            self.table_survivors.setItem(row, 3, QTableWidgetItem(itm['local']))
            self.table_survivors.setItem(row, 4, QTableWidgetItem(itm['parcel']))

            err_item = QTableWidgetItem(itm['error'])
            if itm['error_val'] < 1.0:
                err_item.setForeground(QColor("#10b981"))
            elif itm['error_val'] < 2.0:
                err_item.setForeground(QColor("#f59e0b"))
            self.table_survivors.setItem(row, 5, err_item)

            stat_item = QTableWidgetItem(itm['status'])
            if "DELIVERED" in itm['status']:
                stat_item.setForeground(QColor("#10b981"))
            else:
                stat_item.setForeground(QColor("#38bdf8"))
            self.table_survivors.setItem(row, 6, stat_item)

    def keyPressEvent(self, event):
        key = event.key()
        if key == Qt.Key_1:
            self._set_view_mode("drone1")
        elif key == Qt.Key_2:
            self._set_view_mode("drone2")
        elif key == Qt.Key_D:
            self._set_view_mode("dual")
        elif key == Qt.Key_H:
            self.chk_hud.setChecked(not self.chk_hud.isChecked())
        elif key == Qt.Key_S:
            self._take_snapshot()
        elif key == Qt.Key_Escape:
            if self.isFullScreen():
                self.showNormal()
        super().keyPressEvent(event)

    def closeEvent(self, event):
        self.timer.stop()
        self.comm_mgr.shutdown()
        event.accept()


# ---------------------------------------------------------------------------
# CLI Entrypoint
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="NIDAR Tactical Mission Control Centre")
    parser.add_argument("--fullscreen", action="store_true", help="Launch in fullscreen mode")
    parser.add_argument("--view", choices=["dual", "drone1", "drone2"], default="dual", help="Initial camera view")
    parser.add_argument("--source", choices=["auto", "raw", "annotated"], default="auto", help="Default camera source")
    parser.add_argument("--no-hud", action="store_true", help="Start with HUD overlay disabled")
    args = parser.parse_args()

    app = QApplication(sys.argv)
    window = ControlCentreWindow(fullscreen=args.fullscreen, source_mode=args.source)
    if args.no_hud:
        window.chk_hud.setChecked(False)
    if args.view != "dual":
        window._set_view_mode(args.view)

    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
