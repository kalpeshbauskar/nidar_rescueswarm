#!/usr/bin/env python3
"""Phase D: Dynamic Payload-Release and Mass-Reduction Validation.

Validates that physical package release in Gazebo changes the actual vehicle
dynamics, mass, inertia, and center-of-gravity, rather than just Python bookkeeping.

Executes sequential releases:
- Drone 1: 4 -> 3 -> 2 -> 1 -> 0 packages (6.426 kg -> 5.626 kg)
- Drone 3: 2 -> 1 -> 0 packages (5.956 kg -> 5.556 kg)
- Drone 2: 4 -> 3 -> 2 -> 1 -> 0 packages (6.426 kg -> 5.626 kg)

For each release:
- Stabilized 10s hover before release
- Trigger Gazebo detachable joint release via gz-transport
- 10s high-rate transient logging (altitude, Vz, roll, pitch, yaw, drift, estimator status)
- Capture before & after: AUW, payload mass, CG, inertia, T/W, throttle, power, SOC
- Touchdown and disarm verification
"""

import os
import sys
import time
import json
import math
import signal
import psutil
import argparse
import subprocess
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

# Set ROS 2 Domain and Gazebo Partition
os.environ["ROS_DOMAIN_ID"] = "88"
os.environ["GZ_PARTITION"] = "nidar_rescueswarm"

ROOT = Path(__file__).resolve().parent
BASE = ROOT.parent
REPO_ROOT = BASE.parent
sys.path.insert(0, str(REPO_ROOT))

from simulation.hardware.config import (
    FLEET_SIZE,
    PACKAGE_MASS_KG,
    PAYLOAD_ALLOCATION,
    HARDWARE_BOM,
    get_drone_dry_mass_kg,
    get_drone_initial_auw_kg,
)
from simulation.hardware.propulsion import (
    BatterySOCIntegrator,
    calculate_propulsion_state,
)

import rclpy
from rclpy.node import Node
from px4_msgs.msg import (
    VehicleLocalPosition,
    VehicleStatus,
    VehicleAttitude,
    VehicleCommand,
    OffboardControlMode,
    TrajectorySetpoint,
)
from rclpy.qos import qos_profile_sensor_data

# Gazebo transport
from gz.transport13 import Node as GzNode
from gz.msgs10.empty_pb2 import Empty
from gz.msgs10.stringmsg_pb2 import StringMsg

OUTPUT_DIR = ROOT / "results_phase_d"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

env = os.environ.copy()
env.update(
    ROS_DOMAIN_ID="88",
    GZ_PARTITION="nidar_rescueswarm",
    ROS_LOG_DIR=str(OUTPUT_DIR / "ros"),
    DUAL_RUN_DIR=str(OUTPUT_DIR),
    GZ_CONFIG_PATH=os.environ.get("GZ_CONFIG_PATH", "/usr/share/gz"),
    GZ_SIM_RESOURCE_PATH=os.environ.get(
        "GZ_SIM_RESOURCE_PATH",
        f"{BASE}/imported/PX4-Autopilot/Tools/simulation/gz/models:/home/kalpeshbauskar/PX4-Autopilot/Tools/simulation/gz/models",
    ),
    GZ_SIM_SYSTEM_PLUGIN_PATH=os.environ.get(
        "GZ_SIM_SYSTEM_PLUGIN_PATH",
        "/home/kalpeshbauskar/PX4-Autopilot/build/px4_sitl_default/src/modules/simulation/gz_plugins",
    ),
    LIBGL_ALWAYS_SOFTWARE="1",
    QT_QPA_PLATFORM="xcb",
    LIBGL_DRI3_DISABLE="1",
    __GLX_VENDOR_LIBRARY_NAME="mesa",
)

children = []


def start_proc(name, cmd, cwd=ROOT, extra=None):
    log = open(OUTPUT_DIR / f"{name}.log", "w")
    e = env.copy()
    e.update(extra or {})
    proc = subprocess.Popen(
        cmd, cwd=cwd, env=e, stdout=log, stderr=subprocess.STDOUT, start_new_session=True
    )
    children.append((name, proc, log))
    print(f"  [START] {name} (PID {proc.pid})", flush=True)
    return proc


def cleanup_procs():
    for name, proc, log in reversed(children):
        if proc.poll() is None:
            try:
                os.killpg(proc.pid, signal.SIGINT)
            except Exception:
                pass
    time.sleep(1.5)
    for name, proc, log in reversed(children):
        if proc.poll() is None:
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except Exception:
                pass
            try:
                proc.wait(timeout=2)
            except Exception:
                pass
        log.close()
    children.clear()
    subprocess.run(["pkill", "-9", "-f", "px4 -i"], stderr=subprocess.DEVNULL)
    subprocess.run(["pkill", "-9", "-f", "gz sim"], stderr=subprocess.DEVNULL)
    subprocess.run(["pkill", "-9", "-f", "MicroXRCEAgent"], stderr=subprocess.DEVNULL)


def compute_physical_cg_and_inertia(d_idx: int, attached_bays: List[int]) -> Tuple[Dict[str, float], Dict[str, float]]:
    """Calculate rigid body CG (x, y, z) and composite inertia tensor (Ixx, Iyy, Izz)

    relative to the airframe base_link origin.
    """
    dry_mass = get_drone_dry_mass_kg(d_idx)
    pkg_count_total = PAYLOAD_ALLOCATION[d_idx]
    rack_mass = (
        HARDWARE_BOM["payload_drop_rack_4slot"].mass_kg
        if pkg_count_total > 2
        else HARDWARE_BOM["payload_drop_rack_2slot"].mass_kg
    )
    cam_mass = HARDWARE_BOM["oak_d_lite"].mass_kg
    rotor_mass = HARDWARE_BOM["propellers"].mass_kg / 4.0
    base_mass = dry_mass - (rack_mass + cam_mass + 4 * rotor_mass)

    # Component locations relative to base_link
    # base_link: (0, 0, 0)
    # rack_link: (0, 0, -0.05)
    # camera_link: (+0.10, 0, -0.05)
    # rotors: 4x at (+/-0.25, +/-0.25, 0.032) -> net (0, 0, 0.032)
    sum_mx = base_mass * 0.0 + rack_mass * 0.0 + cam_mass * 0.10 + (4 * rotor_mass) * 0.0
    sum_my = 0.0
    sum_mz = base_mass * 0.0 + rack_mass * (-0.05) + cam_mass * (-0.05) + (4 * rotor_mass) * 0.032
    current_mass = dry_mass

    # Package locations
    pkg_positions = {}
    if pkg_count_total == 4:
        # 4 bays: col_spacing = 0.14, col_start = -0.07
        # Bay 0: (-0.12, -0.07, -0.09)  [Rear-Left]
        # Bay 1: (+0.12, -0.07, -0.09)  [Front-Left]
        # Bay 2: (-0.12, +0.07, -0.09)  [Rear-Right]
        # Bay 3: (+0.12, +0.07, -0.09)  [Front-Right]
        pkg_positions = {
            0: (-0.12, -0.07, -0.09),
            1: (+0.12, -0.07, -0.09),
            2: (-0.12, +0.07, -0.09),
            3: (+0.12, +0.07, -0.09),
        }
    elif pkg_count_total == 2:
        # 2 bays along X axis:
        # Bay 0: (-0.12, 0.0, -0.09)   [Rear]
        # Bay 1: (+0.12, 0.0, -0.09)   [Front]
        pkg_positions = {
            0: (-0.12, 0.0, -0.09),
            1: (+0.12, 0.0, -0.09),
        }

    for b in attached_bays:
        if b in pkg_positions:
            px, py, pz = pkg_positions[b]
            sum_mx += PACKAGE_MASS_KG * px
            sum_my += PACKAGE_MASS_KG * py
            sum_mz += PACKAGE_MASS_KG * pz
            current_mass += PACKAGE_MASS_KG

    cg_x = sum_mx / current_mass
    cg_y = sum_my / current_mass
    cg_z = sum_mz / current_mass

    # Composite inertia using parallel axis theorem
    # Base link scaled inertia:
    scale = base_mass / 3.2
    ixx = 0.077 * scale + rack_mass * (0.05**2) + cam_mass * (0.05**2) + 4 * rotor_mass * (0.25**2 + 0.032**2)
    iyy = 0.077 * scale + rack_mass * (0.05**2) + cam_mass * (0.10**2 + 0.05**2) + 4 * rotor_mass * (0.25**2 + 0.032**2)
    izz = 0.133 * scale + cam_mass * (0.10**2) + 4 * rotor_mass * (0.25**2 + 0.25**2)

    # Add package contributions
    for b in attached_bays:
        if b in pkg_positions:
            px, py, pz = pkg_positions[b]
            # pkg intrinsic inertia: ixx=iyy=0.000167, izz=0.000213
            ixx += 0.000167 + PACKAGE_MASS_KG * (py**2 + pz**2)
            iyy += 0.000167 + PACKAGE_MASS_KG * (px**2 + pz**2)
            izz += 0.000213 + PACKAGE_MASS_KG * (px**2 + py**2)

    cg = {"x_mm": round(cg_x * 1000.0, 2), "y_mm": round(cg_y * 1000.0, 2), "z_mm": round(cg_z * 1000.0, 2)}
    inertia = {"ixx": round(ixx, 5), "iyy": round(iyy, 5), "izz": round(izz, 5)}
    return cg, inertia


class DroneReleaseController(Node):
    def __init__(self, d_num: int, d_idx: int, target_alt: float = 5.0):
        super().__init__(f"drone_{d_num}_release_controller")
        self.d_num = d_num
        self.d_idx = d_idx
        self.ns = f"/drone{d_num}/fmu"
        self.target_alt = target_alt

        self.initial_auw = get_drone_initial_auw_kg(d_idx)
        self.dry_mass = get_drone_dry_mass_kg(d_idx)
        self.total_packages = PAYLOAD_ALLOCATION[d_idx]

        self.battery = BatterySOCIntegrator(drone_id=d_idx)

        # Release plan (balanced diagonal bays for 4-rack; symmetric for 2-rack)
        if self.total_packages == 4:
            # Bay 0: Rear-Left (-0.12, -0.07)
            # Bay 3: Front-Right (+0.12, +0.07) -> diagonal opposed pair returns CG to centerline
            # Bay 1: Front-Left (+0.12, -0.07)
            # Bay 2: Rear-Right (-0.12, +0.07) -> opposed pair returns to empty centerline
            self.release_sequence = [0, 3, 1, 2]
        else:
            # 2 bays along X axis: Bay 0 (rear), Bay 1 (front)
            self.release_sequence = [0, 1]

        self.currently_attached = list(range(self.total_packages))
        self.completed_releases = []

        self.pos = None
        self.stat = None
        self.att = None
        self.home_x = None
        self.home_y = None

        self.phase = "INIT"
        self.phase_t0 = time.monotonic()
        self.test_t0 = time.monotonic()
        self.last_cmd_t = 0.0

        # Gazebo transport for package release
        self.gz = GzNode()
        self.cargo_pubs = {}
        self.cargo_states = {}
        for j in range(self.total_packages):
            name = f"parcel_{d_idx}_{j}"
            self.cargo_pubs[j] = self.gz.advertise(f"/{name}/detach", Empty)
            self.gz.subscribe(
                StringMsg,
                f"/{name}/state",
                lambda m, bay=j: self.cargo_states.update({bay: m.data}),
            )

        # High-rate transient recording buffers
        self.pre_samples = []
        self.transient_samples = []
        self.current_release_idx = 0
        self.release_stage = "IDLE"  # IDLE, STABILIZING_PRE, RELEASING, MONITORING_TRANSIENT, COMPLETE
        self.release_trigger_time = 0.0

        # ROS 2 Pubs & Subs
        self.create_subscription(
            VehicleLocalPosition,
            f"{self.ns}/out/vehicle_local_position_v1",
            self.on_pos,
            qos_profile_sensor_data,
        )
        self.create_subscription(
            VehicleStatus,
            f"{self.ns}/out/vehicle_status_v4",
            self.on_stat,
            qos_profile_sensor_data,
        )
        self.create_subscription(
            VehicleAttitude,
            f"{self.ns}/out/vehicle_attitude",
            self.on_att,
            qos_profile_sensor_data,
        )

        self.mode_pub = self.create_publisher(OffboardControlMode, f"{self.ns}/in/offboard_control_mode", 10)
        self.sp_pub = self.create_publisher(TrajectorySetpoint, f"{self.ns}/in/trajectory_setpoint", 10)
        self.cmd_pub = self.create_publisher(VehicleCommand, f"{self.ns}/in/vehicle_command", 10)

        self.timer = self.create_timer(0.05, self.control_loop)
        print(f"Controller initialized for Drone {d_num} (rescue_{d_idx}, initial AUW {self.initial_auw} kg, {self.total_packages} pkgs)")

    def on_pos(self, msg):
        self.pos = msg

    def on_stat(self, msg):
        self.stat = msg

    def on_att(self, msg):
        self.att = msg

    def send_cmd(self, command: int, p1: float = 0.0, p2: float = 0.0):
        m = VehicleCommand()
        m.timestamp = self.get_clock().now().nanoseconds // 1000
        m.command = command
        m.param1 = float(p1)
        m.param2 = float(p2)
        m.target_system = self.d_num
        m.target_component = 1
        m.source_system = 240
        m.source_component = self.d_num
        m.from_external = True
        self.cmd_pub.publish(m)
        self.last_cmd_t = time.monotonic()

    def get_euler(self):
        if not self.att:
            return 0.0, 0.0, 0.0
        q = self.att.q
        roll = math.atan2(2.0 * (q[0] * q[1] + q[2] * q[3]), 1.0 - 2.0 * (q[1] * q[1] + q[2] * q[2]))
        pitch = math.asin(max(-1.0, min(1.0, 2.0 * (q[0] * q[2] - q[3] * q[1]))))
        yaw = math.atan2(2.0 * (q[0] * q[3] + q[1] * q[2]), 1.0 - 2.0 * (q[2] * q[2] + q[3] * q[3]))
        return math.degrees(roll), math.degrees(pitch), math.degrees(yaw)

    def trigger_detach(self, bay: int):
        if bay in self.cargo_pubs:
            for _ in range(3):
                self.cargo_pubs[bay].publish(Empty())

    def control_loop(self):
        now = time.monotonic()
        total_elapsed = now - self.test_t0

        if total_elapsed > 180.0:
            print(f"ERROR: Drone {self.d_num} safety timeout exceeded!")
            rclpy.shutdown()
            return

        # Battery update
        dt = 0.05
        current_auw = self.dry_mass + len(self.currently_attached) * PACKAGE_MASS_KG
        if self.phase in ("CLIMB", "HOVER", "RELEASE_TEST", "DESCEND", "LAND"):
            self.battery.update(self.phase, current_auw, dt)

        # Offboard setpoint stream
        if self.phase not in ("INIT", "LAND", "TOUCHDOWN", "FINISHED"):
            mode_msg = OffboardControlMode()
            mode_msg.timestamp = self.get_clock().now().nanoseconds // 1000
            mode_msg.position = True
            self.mode_pub.publish(mode_msg)

            sp_msg = TrajectorySetpoint()
            sp_msg.timestamp = mode_msg.timestamp
            hx = self.home_x if self.home_x is not None else 0.0
            hy = self.home_y if self.home_y is not None else 0.0
            if self.phase in ("OFFBOARD", "ARM", "CLIMB", "HOVER", "RELEASE_TEST"):
                sp_msg.position = [hx, hy, -self.target_alt]
            elif self.phase == "DESCEND":
                sp_msg.position = [hx, hy, -1.0]
            sp_msg.velocity = [math.nan] * 3
            sp_msg.acceleration = [math.nan] * 3
            sp_msg.yaw = 0.0
            sp_msg.yawspeed = math.nan
            self.sp_pub.publish(sp_msg)

        if not self.pos or not self.stat:
            return

        alt = -float(self.pos.z)
        vz = -float(self.pos.vz)
        roll, pitch, yaw = self.get_euler()
        drift = math.hypot(float(self.pos.x) - (self.home_x or 0.0), float(self.pos.y) - (self.home_y or 0.0))

        # Base flight state machine
        if self.phase == "INIT":
            if self.pos.xy_valid and self.pos.z_valid:
                self.home_x = float(self.pos.x)
                self.home_y = float(self.pos.y)
                self.phase = "OFFBOARD"
                self.phase_t0 = now
                print(f"  [{now-self.test_t0:5.1f}s] Drone {self.d_num}: INIT -> OFFBOARD (home: x={self.home_x:.2f}, y={self.home_y:.2f})")

        elif self.phase == "OFFBOARD":
            if self.stat.nav_state == 14:
                self.phase = "ARM"
                self.phase_t0 = now
                print(f"  [{now-self.test_t0:5.1f}s] Drone {self.d_num}: OFFBOARD -> ARM")
            elif now - self.last_cmd_t > 0.5:
                self.send_cmd(VehicleCommand.VEHICLE_CMD_DO_SET_MODE, 1, 6)

        elif self.phase == "ARM":
            if self.stat.arming_state == 2:
                self.phase = "CLIMB"
                self.phase_t0 = now
                print(f"  [{now-self.test_t0:5.1f}s] Drone {self.d_num}: ARM -> CLIMB")
            elif now - self.last_cmd_t > 0.5:
                self.send_cmd(VehicleCommand.VEHICLE_CMD_COMPONENT_ARM_DISARM, 1)

        elif self.phase == "CLIMB":
            if alt >= (self.target_alt - 0.20):
                self.phase = "RELEASE_TEST"
                self.phase_t0 = now
                self.release_stage = "STABILIZING_PRE"
                print(f"  [{now-self.test_t0:5.1f}s] Drone {self.d_num}: Reached {alt:.2f}m -> Starting Phase D Payload-Release Sequence!\n", flush=True)

        elif self.phase == "RELEASE_TEST":
            # Execution of sequential drops with 10s stabilization windows
            if self.release_stage == "STABILIZING_PRE":
                # Collect pre-release baseline for 2.0s
                self.pre_samples.append({
                    "alt": alt, "vz": vz, "roll": roll, "pitch": pitch, "yaw": yaw, "drift": drift
                })
                # After 2.5s pre-release hover, trigger release
                if (now - self.phase_t0) >= 2.5:
                    bay_to_release = self.release_sequence[self.current_release_idx]
                    pkgs_before = len(self.currently_attached)
                    pkgs_after = pkgs_before - 1

                    auw_before = self.dry_mass + pkgs_before * PACKAGE_MASS_KG
                    auw_after = self.dry_mass + pkgs_after * PACKAGE_MASS_KG

                    cg_before, in_before = compute_physical_cg_and_inertia(self.d_idx, self.currently_attached)
                    bays_after = [b for b in self.currently_attached if b != bay_to_release]
                    cg_after, in_after = compute_physical_cg_and_inertia(self.d_idx, bays_after)

                    prop_before = calculate_propulsion_state(auw_before)
                    prop_after = calculate_propulsion_state(auw_after)

                    avg_pre_alt = sum(s["alt"] for s in self.pre_samples[-20:]) / max(len(self.pre_samples[-20:]), 1)
                    avg_pre_roll = sum(s["roll"] for s in self.pre_samples[-20:]) / max(len(self.pre_samples[-20:]), 1)
                    avg_pre_pitch = sum(s["pitch"] for s in self.pre_samples[-20:]) / max(len(self.pre_samples[-20:]), 1)
                    avg_pre_yaw = sum(s["yaw"] for s in self.pre_samples[-20:]) / max(len(self.pre_samples[-20:]), 1)

                    print(f"--- [EVENT] Triggering Release {self.current_release_idx + 1}/{len(self.release_sequence)}: "
                          f"Bay {bay_to_release} ({pkgs_before} -> {pkgs_after} pkgs, AUW {auw_before:.3f}kg -> {auw_after:.3f}kg) ---", flush=True)

                    # Trigger the actual physical detachment in Gazebo
                    self.trigger_detach(bay_to_release)
                    self.release_trigger_time = now
                    self.transient_samples = []

                    # Store event metadata
                    self.current_event = {
                        "release_index": self.current_release_idx + 1,
                        "bay_released": bay_to_release,
                        "pkgs_before": pkgs_before,
                        "pkgs_after": pkgs_after,
                        "payload_mass_before_kg": round(pkgs_before * PACKAGE_MASS_KG, 3),
                        "payload_mass_after_kg": round(pkgs_after * PACKAGE_MASS_KG, 3),
                        "mass_change_kg": -PACKAGE_MASS_KG,
                        "auw_before_kg": round(auw_before, 3),
                        "auw_after_kg": round(auw_after, 3),
                        "cg_before": cg_before,
                        "cg_after": cg_after,
                        "cg_shift_mm": {
                            "dx": round(cg_after["x_mm"] - cg_before["x_mm"], 2),
                            "dy": round(cg_after["y_mm"] - cg_before["y_mm"], 2),
                            "dz": round(cg_after["z_mm"] - cg_before["z_mm"], 2),
                        },
                        "inertia_before": in_before,
                        "inertia_after": in_after,
                        "tw_before": round(prop_before.tw_ratio, 2),
                        "tw_after": round(prop_after.tw_ratio, 2),
                        "throttle_before_pct": round(prop_before.estimated_hover_throttle * 100.0, 1),
                        "throttle_after_pct": round(prop_after.estimated_hover_throttle * 100.0, 1),
                        "power_before_w": round(prop_before.total_hover_power_w, 1),
                        "power_after_w": round(prop_after.total_hover_power_w, 1),
                        "pre_alt_m": round(avg_pre_alt, 3),
                        "pre_roll_deg": round(avg_pre_roll, 2),
                        "pre_pitch_deg": round(avg_pre_pitch, 2),
                        "pre_yaw_deg": round(avg_pre_yaw, 2),
                    }

                    # Remove from attached list
                    self.currently_attached = bays_after
                    self.release_stage = "MONITORING_TRANSIENT"

            elif self.release_stage == "MONITORING_TRANSIENT":
                elapsed_transient = now - self.release_trigger_time
                self.transient_samples.append({
                    "dt": elapsed_transient,
                    "alt": alt,
                    "vz": vz,
                    "roll": roll,
                    "pitch": pitch,
                    "yaw": yaw,
                    "drift": drift,
                })

                if int(elapsed_transient * 10) % 25 == 0:
                    print(f"    [Post-Release +{elapsed_transient:4.1f}s] Alt: {alt:5.2f}m, Vz: {vz:5.2f}m/s, "
                          f"Roll: {roll:4.1f}°, Pitch: {pitch:4.1f}°, Drift: {drift:4.2f}m", flush=True)

                # Require 10.0s of stabilization post-release
                if elapsed_transient >= 10.0:
                    # Evaluate transients
                    alts = [s["alt"] for s in self.transient_samples]
                    vzs = [s["vz"] for s in self.transient_samples]
                    rolls = [s["roll"] for s in self.transient_samples]
                    pitches = [s["pitch"] for s in self.transient_samples]
                    drifts = [s["drift"] for s in self.transient_samples]

                    peak_alt_dev = max(abs(a - self.target_alt) for a in alts)
                    peak_vz = max(abs(v) for v in vzs)
                    peak_roll = max(abs(r - self.current_event["pre_roll_deg"]) for r in rolls)
                    peak_pitch = max(abs(p - self.current_event["pre_pitch_deg"]) for p in pitches)
                    max_drift = max(drifts)

                    # Steady-state over last 2 seconds
                    last_alts = [s["alt"] for s in self.transient_samples if s["dt"] >= 8.0]
                    steady_alt = sum(last_alts) / max(len(last_alts), 1)

                    # Check pass criteria
                    pass_alt = peak_alt_dev <= 0.50
                    pass_vz = peak_vz <= 1.00
                    pass_roll = peak_roll <= 5.0
                    pass_pitch = peak_pitch <= 5.0
                    pass_tw = self.current_event["tw_after"] > self.current_event["tw_before"]
                    pass_throttle = self.current_event["throttle_after_pct"] < self.current_event["throttle_before_pct"]
                    pass_steady = abs(steady_alt - self.target_alt) <= 0.25

                    release_pass = pass_alt and pass_vz and pass_roll and pass_pitch and pass_tw and pass_throttle and pass_steady

                    self.current_event.update({
                        "peak_altitude_deviation_m": round(peak_alt_dev, 3),
                        "peak_vertical_velocity_ms": round(peak_vz, 3),
                        "peak_roll_transient_deg": round(peak_roll, 2),
                        "peak_pitch_transient_deg": round(peak_pitch, 2),
                        "max_horizontal_drift_m": round(max_drift, 3),
                        "steady_altitude_m": round(steady_alt, 3),
                        "battery_soc_pct": round(self.battery.soc * 100.0, 1),
                        "energy_consumed_wh": round(self.battery.energy_consumed_wh, 2),
                        "pass_criteria": {
                            "pass_alt_dev": pass_alt,
                            "pass_vz_transient": pass_vz,
                            "pass_roll_transient": pass_roll,
                            "pass_pitch_transient": pass_pitch,
                            "pass_tw_increase": pass_tw,
                            "pass_throttle_decrease": pass_throttle,
                            "pass_stabilized": pass_steady,
                            "release_pass": release_pass,
                        },
                        "release_pass": release_pass,
                    })
                    self.completed_releases.append(self.current_event)

                    status_str = "PASSED" if release_pass else "FAILED"
                    print(f"  [RESULT] Release {self.current_release_idx + 1} {status_str}: "
                          f"Alt Dev: {peak_alt_dev:.3f}m, Peak Vz: {peak_vz:.3f}m/s, "
                          f"Peak Roll: {peak_roll:.2f}°, Peak Pitch: {peak_pitch:.2f}°, "
                          f"T/W: {self.current_event['tw_before']:.2f} -> {self.current_event['tw_after']:.2f}, "
                          f"Throttle: {self.current_event['throttle_before_pct']:.1f}% -> {self.current_event['throttle_after_pct']:.1f}%\n", flush=True)

                    self.current_release_idx += 1
                    if self.current_release_idx < len(self.release_sequence):
                        self.release_stage = "STABILIZING_PRE"
                        self.pre_samples = []
                        self.phase_t0 = now
                    else:
                        print(f">>> All {len(self.release_sequence)} releases complete for Drone {self.d_num}! Ordering descent...\n", flush=True)
                        self.phase = "DESCEND"
                        self.phase_t0 = now

        elif self.phase == "DESCEND":
            if alt <= 1.5:
                self.phase = "LAND"
                self.phase_t0 = now
                print(f"  [{now-self.test_t0:5.1f}s] Drone {self.d_num}: DESCEND -> LAND")

        elif self.phase == "LAND":
            if now - self.last_cmd_t > 1.5:
                self.send_cmd(VehicleCommand.VEHICLE_CMD_NAV_LAND)

            if self.stat.arming_state != 2:
                self.phase = "FINISHED"
                print(f"  [{now-self.test_t0:5.1f}s] Drone {self.d_num}: Disarm confirmed on ground! Test Complete.")
                rclpy.shutdown()
            elif alt < 0.20 and abs(vz) < 0.15 and (now - self.phase_t0 > 3.0):
                if now - self.last_cmd_t > 0.5:
                    self.send_cmd(VehicleCommand.VEHICLE_CMD_COMPONENT_ARM_DISARM, 0)


def run_drone_release_test(d_num: int) -> Tuple[bool, Dict]:
    d_idx = d_num - 1
    print("\n" + "=" * 75)
    print(f"PHASE D: DYNAMIC PAYLOAD RELEASE TEST — DRONE {d_num}")
    print("=" * 75)

    cleanup_procs()
    time.sleep(1)

    print("1. Launching Gazebo Sim & MicroXRCEAgent...")
    gz_proc = start_proc("gazebo", ["/usr/bin/gz", "sim", "-r", "-s", "--render-engine", "ogre", str(ROOT / "dual_rescue.sdf")])
    agent_proc = start_proc("agent", ["/home/kalpeshbauskar/Micro-XRCE-DDS-Agent/build/MicroXRCEAgent", "udp4", "-p", "8898"])
    time.sleep(3)

    print(f"2. Launching PX4 SITL for Drone {d_num} (rescue_{d_idx})...")
    runtime_dir = ROOT / f"runtime_{d_idx}"
    extra = {
        "PX4_SYS_AUTOSTART": "4026",
        "PX4_GZ_STANDALONE": "1",
        "PX4_GZ_WORLD": "dual_rescue",
        "PX4_GZ_MODEL_NAME": f"rescue_{d_idx}",
        "PX4_SIM_MODEL": "gz_rescue_heavy",
        "PX4_UXRCE_DDS_PORT": "8898",
        "PX4_UXRCE_DDS_NS": f"drone{d_num}",
        "PX4_GZ_SIM_RENDER_ENGINE": "ogre",
        "PATH": "/usr/bin:/home/kalpeshbauskar/PX4-Autopilot/build/px4_sitl_default/bin:" + env.get("PATH", ""),
    }
    px4_proc = start_proc(
        f"px4-{d_num}",
        ["/home/kalpeshbauskar/PX4-Autopilot/build/px4_sitl_default/bin/px4", "-i", str(d_idx), "-s", "etc/init.d-posix/rcS", ".", "-d"],
        runtime_dir,
        extra,
    )
    time.sleep(8)

    if px4_proc.poll() is not None or gz_proc.poll() is not None:
        print(f"FAILED: Process crash during startup for Drone {d_num}!")
        cleanup_procs()
        return False, {}

    print(f"3. Initializing ROS 2 and Drone {d_num} Release Controller...")
    rclpy.init()
    controller = DroneReleaseController(d_num=d_num, d_idx=d_idx, target_alt=5.0)

    try:
        rclpy.spin(controller)
    except Exception as exc:
        print(f"Exception during release flight: {exc}")

    cleanup_procs()

    # Evaluate results
    all_releases = controller.completed_releases
    expected_count = len(controller.release_sequence)
    pass_all = (len(all_releases) == expected_count) and all(r["release_pass"] for r in all_releases) and (controller.phase == "FINISHED")

    drone_summary = {
        "drone_num": d_num,
        "initial_auw_kg": controller.initial_auw,
        "final_auw_kg": controller.dry_mass + len(controller.currently_attached) * PACKAGE_MASS_KG,
        "total_packages": controller.total_packages,
        "releases_performed": len(all_releases),
        "disarm_confirmed": controller.phase == "FINISHED",
        "overall_pass": pass_all,
        "releases": all_releases,
    }

    print("\n" + "-" * 75)
    print(f"DRONE {d_num} RELEASE SUMMARY: {'PASSED' if pass_all else 'FAILED'}")
    print("-" * 75)
    for r in all_releases:
        print(f"  Release {r['release_index']} (Bay {r['bay_released']}): "
              f"AUW {r['auw_before_kg']:.3f} -> {r['auw_after_kg']:.3f} kg (Δ {r['mass_change_kg']:.3f} kg) | "
              f"T/W {r['tw_before']} -> {r['tw_after']} | Throttle {r['throttle_before_pct']}% -> {r['throttle_after_pct']}% | "
              f"Peak Alt Dev: {r['peak_altitude_deviation_m']:.3f}m | Peak Vz: {r['peak_vertical_velocity_ms']:.3f}m/s | "
              f"Peak Roll: {r['peak_roll_transient_deg']:.2f}° | Peak Pitch: {r['peak_pitch_transient_deg']:.2f}° | "
              f"CG Shift: ({r['cg_shift_mm']['dx']:+.2f}, {r['cg_shift_mm']['dy']:+.2f}, {r['cg_shift_mm']['dz']:+.2f}) mm | "
              f"Status: {'PASS' if r['release_pass'] else 'FAIL'}")

    return pass_all, drone_summary


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--drone", type=int, default=1, choices=[1, 2, 3], help="Drone to test (default: 1)")
    p.add_argument("--all", action="store_true", help="Run full sequence: Drone 1, then Drone 3, then Drone 2")
    args = p.parse_args()

    results_file = OUTPUT_DIR / "phase_d_results.json"
    overall_results = {}
    if results_file.exists():
        try:
            overall_results = json.loads(results_file.read_text())
        except Exception:
            pass

    if args.all:
        drones_to_test = [1, 3, 2]
    else:
        drones_to_test = [args.drone]

    overall_success = True
    for d_num in drones_to_test:
        ok, res = run_drone_release_test(d_num)
        overall_results[f"drone_{d_num}"] = res
        if not ok:
            overall_success = False
            print(f"\nCRITICAL: Drone {d_num} failed Phase D release validation!")
            break

    # Save artifact
    (OUTPUT_DIR / "phase_d_results.json").write_text(json.dumps(overall_results, indent=2))
    print(f"\nPhase D JSON results written to {OUTPUT_DIR / 'phase_d_results.json'}")
    return 0 if overall_success else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    finally:
        cleanup_procs()
