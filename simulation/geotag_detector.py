#!/usr/bin/env python3
"""
RescueSwarm geotagging detector.

Runs two subscriptions in one process:
  - gz.transport13: camera frames, direct from Gazebo (bypasses broken ros_gz_bridge)
  - rclpy: PX4 vehicle_local_position / vehicle_gps_position, for geotagging

On each frame, does HSV color thresholding for the orange survivor markers.
When a detection is confirmed (large enough contour, debounced), logs a
geotag entry: timestamp, pixel location, and the vehicle's GPS position at
that instant.

NOTE: on PX4 `main`, the vehicle_gps_position DDS topic publishes type
px4_msgs::msg::SensorGps (VehicleGpsPosition was renamed/replaced upstream).
Field names changed too: latitude_deg / longitude_deg / altitude_msl_m are
already in real-world units (degrees, meters) - no 1e-7 / 1e-3 scaling needed.
Before running, confirm on your machine with:
    ros2 topic list | grep gps
    ros2 interface show px4_msgs/msg/SensorGps
"""

import time
import threading
import csv
import os
from pathlib import Path
from datetime import datetime

import numpy as np
import cv2

from gz.transport13 import Node as GzNode
from gz.msgs10.image_pb2 import Image as GzImage

import rclpy
from rclpy.node import Node as RclNode
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy
from px4_msgs.msg import SensorGps, VehicleLocalPosition

# ---- config ----
CAMERA_TOPIC = "/x500_claw/camera"
LOG_PATH = str(Path(__file__).resolve().parent / "logs" / "geotags.csv")
# Orange in HSV (OpenCV: H 0-179, S/V 0-255)
HSV_LOWER = np.array([5, 150, 150])
HSV_UPPER = np.array([26, 255, 255])
MIN_CONTOUR_AREA = 150       # pixels, filters noise
DETECTION_COOLDOWN_SEC = 5.0  # don't re-log the same survivor repeatedly while hovering


class PositionListener(RclNode):
    """Keeps the latest GPS + local position, updated by PX4 over the XRCE-DDS bridge."""

    def __init__(self):
        super().__init__('geotag_position_listener')
        qos = QoSProfile(
            reliability=ReliabilityPolicy.BEST_EFFORT,
            history=HistoryPolicy.KEEP_LAST,
            depth=1,
        )
        self.lat = None
        self.lon = None
        self.alt = None
        self.local_x = None
        self.local_y = None
        self.local_z = None
        self.gps_at = 0.0
        self.local_at = 0.0

        self.create_subscription(
            SensorGps, '/fmu/out/vehicle_gps_position', self._gps_cb, qos)
        self.create_subscription(
            VehicleLocalPosition, '/fmu/out/vehicle_local_position_v1', self._local_cb, qos)

    def _gps_cb(self, msg):
        # SensorGps reports lat/lon/alt already in real-world units
        # (degrees, meters) - unlike the old VehicleGpsPosition int32*1e7 scaling.
        self.gps_at = time.monotonic()
        self.lat = msg.latitude_deg
        self.lon = msg.longitude_deg
        self.alt = msg.altitude_msl_m

    def _local_cb(self, msg):
        self.local_at = time.monotonic()
        self.local_x = msg.x
        self.local_y = msg.y
        self.local_z = msg.z

    def snapshot(self):
        return {
            'lat': self.lat, 'lon': self.lon, 'alt': self.alt,
            'local_x': self.local_x, 'local_y': self.local_y, 'local_z': self.local_z,
        }


def ensure_log_header():
    if not os.path.exists(LOG_PATH):
        with open(LOG_PATH, 'w', newline='') as f:
            w = csv.writer(f)
            w.writerow(['timestamp', 'lat', 'lon', 'alt_m',
                        'local_x', 'local_y', 'local_z',
                        'pixel_cx', 'pixel_cy', 'contour_area'])


def log_detection(pos, cx, cy, area):
    with open(LOG_PATH, 'a', newline='') as f:
        w = csv.writer(f)
        w.writerow([
            datetime.utcnow().isoformat(),
            pos['lat'], pos['lon'], pos['alt'],
            pos['local_x'], pos['local_y'], pos['local_z'],
            cx, cy, area,
        ])
    print(f"[GEOTAG] survivor at pixel ({cx},{cy}) area={area} "
          f"-> lat={pos['lat']} lon={pos['lon']} local=({pos['local_x']},{pos['local_y']},{pos['local_z']})")


def main():
    ensure_log_header()

    rclpy.init()
    pos_node = PositionListener()

    # spin rclpy in a background thread so the main thread can stay free
    # for the gz-transport event loop / idle wait
    spin_thread = threading.Thread(target=rclpy.spin, args=(pos_node,), daemon=True)
    spin_thread.start()

    frame_count = 0
    last_detection_time = 0.0

    def camera_cb(msg):
        nonlocal frame_count, last_detection_time
        frame_count += 1
        w, h = msg.width, msg.height
        arr = np.frombuffer(msg.data, dtype=np.uint8)
        try:
            frame = arr.reshape((h, w, 3))
        except ValueError:
            return

        hsv = cv2.cvtColor(frame, cv2.COLOR_RGB2HSV)
        mask = cv2.inRange(hsv, HSV_LOWER, HSV_UPPER)
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        for c in contours:
            area = cv2.contourArea(c)
            if area < MIN_CONTOUR_AREA:
                continue
            now = time.time()
            if now - last_detection_time < DETECTION_COOLDOWN_SEC:
                continue
            M = cv2.moments(c)
            if M['m00'] == 0:
                continue
            cx = int(M['m10'] / M['m00'])
            cy = int(M['m01'] / M['m00'])
            pos = pos_node.snapshot()
            if pos['lat'] is None or time.monotonic()-pos_node.gps_at>2 or time.monotonic()-pos_node.local_at>2:
                print("[GEOTAG] detection seen but no GPS fix yet, skipping log")
                continue
            cv2.imwrite(LOG_PATH.replace('.csv', '-latest.png'), cv2.cvtColor(frame, cv2.COLOR_RGB2BGR))
            log_detection(pos, cx, cy, area)
            last_detection_time = now

        if frame_count % 50 == 0:
            print(f"Processed {frame_count} frames so far")

    gz_node = GzNode()
    ok = gz_node.subscribe(GzImage, CAMERA_TOPIC, camera_cb)
    if not ok:
        print(f"Error subscribing to {CAMERA_TOPIC}")
        return
    print(f"Subscribed to {CAMERA_TOPIC}, waiting for frames...")
    print(f"Logging drone-position geotags to {LOG_PATH}", flush=True)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        pos_node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()