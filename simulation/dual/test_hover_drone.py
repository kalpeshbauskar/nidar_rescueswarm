#!/usr/bin/env python3
"""Phase B: Individual Drone Hover Test (60-second Hover).

Tests Drone 1, Drone 2, or Drone 3 through:
1. Arming
2. Takeoff and climb to 5.0 m
3. Stable hover for 60 seconds
4. Controlled descent and landing
5. Disarm

Measures altitude error, roll/pitch/yaw, vertical velocity, battery/SOC,
and touchdown behavior against explicit PASS criteria.
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

# Force ROS 2 domain ID 88 and Gazebo partition
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

p = argparse.ArgumentParser()
p.add_argument("--drone", type=int, default=1, choices=[1, 2, 3], help="Drone number to test (1, 2, or 3)")
p.add_argument("--hover-time", type=float, default=60.0, help="Hover duration in seconds (default: 60s)")
p.add_argument("--target-alt", type=float, default=5.0, help="Target hover altitude in meters (default: 5.0m)")
args, unknown = p.parse_known_args()

drone_num = args.drone
drone_idx = drone_num - 1
target_alt = args.target_alt
hover_duration = args.hover_time

OUTPUT_DIR = ROOT / f"results_phase_b_drone{drone_num}"
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
    print("\nCleaning up processes...", flush=True)
    for name, proc, log in reversed(children):
        if proc.poll() is None:
            try:
                os.killpg(proc.pid, signal.SIGINT)
            except Exception:
                pass
    time.sleep(2)
    for name, proc, log in reversed(children):
        if proc.poll() is None:
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except Exception:
                pass
            try:
                proc.wait(timeout=3)
            except Exception:
                pass
        log.close()
    subprocess.run(["pkill", "-9", "-f", "px4 -i"], stderr=subprocess.DEVNULL)
    subprocess.run(["pkill", "-9", "-f", "gz sim"], stderr=subprocess.DEVNULL)
    subprocess.run(["pkill", "-9", "-f", "MicroXRCEAgent"], stderr=subprocess.DEVNULL)


class IndividualHoverController(Node):
    def __init__(self, d_num: int, d_idx: int, t_alt: float, h_dur: float):
        super().__init__(f"hover_tester_drone{d_num}")
        self.d_num = d_num
        self.d_idx = d_idx
        self.target_alt = t_alt
        self.hover_dur = h_dur
        self.ns = f"/drone{d_num}/fmu"

        self.initial_auw = get_drone_initial_auw_kg(d_idx)
        self.dry_mass = get_drone_dry_mass_kg(d_idx)
        self.packages_count = PAYLOAD_ALLOCATION[d_idx]

        self.prop_state = calculate_propulsion_state(self.initial_auw)
        self.battery = BatterySOCIntegrator(drone_id=d_idx)

        self.pos = None
        self.stat = None
        self.att = None

        self.create_subscription(VehicleLocalPosition, f"{self.ns}/out/vehicle_local_position_v1", self.pos_cb, qos_profile_sensor_data)
        self.create_subscription(VehicleStatus, f"{self.ns}/out/vehicle_status_v4", self.stat_cb, qos_profile_sensor_data)
        self.create_subscription(VehicleAttitude, f"{self.ns}/out/vehicle_attitude", self.att_cb, qos_profile_sensor_data)

        self.mode_pub = self.create_publisher(OffboardControlMode, f"{self.ns}/in/offboard_control_mode", 10)
        self.sp_pub = self.create_publisher(TrajectorySetpoint, f"{self.ns}/in/trajectory_setpoint", 10)
        self.cmd_pub = self.create_publisher(VehicleCommand, f"{self.ns}/in/vehicle_command", 10)

        self.phase = "INIT"
        self.phase_t0 = time.monotonic()
        self.last_cmd_t = 0.0
        self.test_t0 = time.monotonic()

        self.hover_samples = []
        self.climb_samples = []
        self.land_samples = []

        self.timer = self.create_timer(0.05, self.control_loop)
        print(f"Controller initialized for Drone {d_num} (AUW={self.initial_auw}kg, pkgs={self.packages_count})")

    def pos_cb(self, msg):
        self.pos = msg

    def stat_cb(self, msg):
        self.stat = msg

    def att_cb(self, msg):
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
        m.source_component = 1
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

    def set_phase(self, new_phase: str):
        elapsed = time.monotonic() - self.test_t0
        print(f"  [{elapsed:6.1f}s] Phase transition: {self.phase} -> {new_phase}", flush=True)
        self.phase = new_phase
        self.phase_t0 = time.monotonic()

    def control_loop(self):
        now = time.monotonic()
        total_elapsed = now - self.test_t0

        # Safety timeout: 150 seconds max
        if total_elapsed > 150.0:
            print("ERROR: Test exceeded maximum safety timeout (150s)!")
            rclpy.shutdown()
            return

        if not self.pos or not self.stat:
            return

        alt = -float(self.pos.z)
        vz = -float(self.pos.vz)
        roll, pitch, yaw = self.get_euler()

        # Update battery model based on flight phase
        dt = 0.05
        if self.phase in ("CLIMB", "HOVER", "DESCEND", "LAND"):
            self.battery.update(self.phase, self.initial_auw, dt)

        # Offboard setpoint stream (must stream continuously)
        # Offboard setpoint stream (must stream continuously during offboard flight)
        if self.phase not in ("INIT", "LAND", "TOUCHDOWN", "FINISHED"):
            mode_msg = OffboardControlMode()
            mode_msg.timestamp = self.get_clock().now().nanoseconds // 1000
            mode_msg.position = True
            self.mode_pub.publish(mode_msg)

            sp_msg = TrajectorySetpoint()
            sp_msg.timestamp = mode_msg.timestamp
            hx = getattr(self, "home_x", 0.0)
            hy = getattr(self, "home_y", 0.0)
            if self.phase in ("OFFBOARD", "ARM", "CLIMB", "HOVER"):
                sp_msg.position = [hx, hy, -self.target_alt]
            elif self.phase == "DESCEND":
                sp_msg.position = [hx, hy, -1.0]
            sp_msg.velocity = [math.nan] * 3
            sp_msg.acceleration = [math.nan] * 3
            sp_msg.yaw = 0.0
            sp_msg.yawspeed = math.nan
            self.sp_pub.publish(sp_msg)

        # State machine
        if self.phase == "INIT":
            if int(now - self.test_t0) % 5 == 0:
                print(f"Waiting for STANDBY... current state: {self.stat.arming_state if self.stat else None}")
            if self.pos.xy_valid and self.pos.z_valid:
                self.home_x = float(self.pos.x)
                self.home_y = float(self.pos.y)
                self.set_phase("OFFBOARD")

        elif self.phase == "OFFBOARD":
            if self.stat.nav_state == 14:  # Offboard active
                self.set_phase("ARM")
            elif now - self.last_cmd_t > 0.5:
                self.send_cmd(VehicleCommand.VEHICLE_CMD_DO_SET_MODE, 1, 6)

        elif self.phase == "ARM":
            if self.stat.arming_state == 2:  # Armed
                self.set_phase("CLIMB")
            elif now - self.last_cmd_t > 0.5:
                self.send_cmd(VehicleCommand.VEHICLE_CMD_COMPONENT_ARM_DISARM, 1)

        elif self.phase == "CLIMB":
            self.climb_samples.append({"t": round(now - self.test_t0, 2), "alt": round(alt, 3), "vz": round(vz, 3)})
            if int((now - self.phase_t0) * 10) % 20 == 0:
                print(f"    [Climb] Alt: {alt:.2f}m / {self.target_alt:.2f}m, Vz: {vz:.2f}m/s", flush=True)
            if alt >= (self.target_alt - 0.20):
                self.set_phase("HOVER")

        elif self.phase == "HOVER":
            hover_t = now - self.phase_t0
            alt_err = abs(alt - self.target_alt)
            sample = {
                "t_hover": round(hover_t, 2),
                "alt": round(alt, 3),
                "alt_err": round(alt_err, 3),
                "vz": round(vz, 3),
                "roll": round(roll, 2),
                "pitch": round(pitch, 2),
                "yaw": round(yaw, 2),
                "energy_wh": round(self.battery.energy_consumed_wh, 3),
                "soc_percent": round(self.battery.soc * 100, 2),
            }
            self.hover_samples.append(sample)

            if int(hover_t * 10) % 50 == 0:  # Every 5 seconds
                print(
                    f"    [Hover {hover_t:4.1f}s/{self.hover_dur:.0f}s] Alt: {alt:5.2f}m (err: {alt_err:4.2f}m), "
                    f"Roll: {roll:4.1f}°, Pitch: {pitch:4.1f}°, Vz: {vz:5.2f}m/s, SOC: {self.battery.soc*100:4.1f}%",
                    flush=True,
                )

            if hover_t >= self.hover_dur:
                self.set_phase("DESCEND")

        elif self.phase == "DESCEND":
            if alt <= 1.5:
                self.set_phase("LAND")

        elif self.phase == "LAND":
            self.land_samples.append({"t": round(now - self.test_t0, 2), "alt": round(alt, 3), "vz": round(vz, 3)})
            if now - self.last_cmd_t > 1.5:
                self.send_cmd(VehicleCommand.VEHICLE_CMD_NAV_LAND)

            if self.stat.arming_state != 2:
                print("  Vehicle touchdown and disarm confirmed!")
                self.set_phase("FINISHED")
                rclpy.shutdown()
            elif alt < 0.20 and abs(vz) < 0.15 and (now - self.phase_t0 > 3.0):
                # Touchdown reached, disarm if auto-disarm has not fired yet
                if now - self.last_cmd_t > 0.5:
                    self.send_cmd(VehicleCommand.VEHICLE_CMD_COMPONENT_ARM_DISARM, 0)


def run_single_drone_hover(d_num: int, h_dur: float = 60.0):
    print("=" * 70)
    print(f"PHASE B: INDIVIDUAL HOVER TEST — DRONE {d_num}")
    print("=" * 70)

    # Pre-clean
    subprocess.run(["pkill", "-9", "-f", "px4 -i"], stderr=subprocess.DEVNULL)
    subprocess.run(["pkill", "-9", "-f", "gz sim"], stderr=subprocess.DEVNULL)
    subprocess.run(["pkill", "-9", "-f", "MicroXRCEAgent"], stderr=subprocess.DEVNULL)
    time.sleep(1)

    # Start Gazebo
    print("1. Launching Gazebo Sim (headless)...")
    start_proc(
        "gazebo",
        ["/usr/bin/gz", "sim", "-r", "-s", "--render-engine", "ogre", str(ROOT / "dual_rescue.sdf")],
    )

    # Start MicroXRCEAgent
    print("2. Launching MicroXRCEAgent (port 8898)...")
    start_proc("agent", ["/home/kalpeshbauskar/Micro-XRCE-DDS-Agent/build/MicroXRCEAgent", "udp4", "-p", "8898"])
    time.sleep(3)

    # Start ONLY the drone under test
    d_idx = d_num - 1
    print(f"3. Launching PX4 SITL instance for Drone {d_num} (index {d_idx})...")
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
    start_proc(
        f"px4-{d_num}",
        ["/home/kalpeshbauskar/PX4-Autopilot/build/px4_sitl_default/bin/px4", "-i", str(d_idx), "-s", "etc/init.d-posix/rcS", ".", "-d"],
        runtime_dir,
        extra,
    )

    # Wait 8s for PX4 to boot
    time.sleep(8)

    print("4. Executing Hover Flight Cycle...")
    rclpy.init()
    tester = IndividualHoverController(d_num=d_num, d_idx=d_idx, t_alt=5.0, h_dur=h_dur)

    try:
        rclpy.spin(tester)
    except Exception as exc:
        print(f"Controller exception: {exc}")

    # Analyze samples
    samples = tester.hover_samples
    if not samples:
        print("FAILED: No hover samples recorded!")
        return False, {}

    alts = [s["alt"] for s in samples]
    alt_errs = [s["alt_err"] for s in samples]
    rolls = [s["roll"] for s in samples]
    pitches = [s["pitch"] for s in samples]
    vzs = [s["vz"] for s in samples]

    mean_alt = sum(alts) / len(alts)
    mean_err = sum(alt_errs) / len(alt_errs)
    max_err = max(alt_errs)

    std_roll = math.sqrt(sum(r**2 for r in rolls) / len(rolls))
    std_pitch = math.sqrt(sum(p**2 for p in pitches) / len(pitches))
    max_roll = max(abs(r) for r in rolls)
    max_pitch = max(abs(p) for p in pitches)
    std_vz = math.sqrt(sum(v**2 for v in vzs) / len(vzs))

    final_energy = tester.battery.energy_consumed_wh
    final_soc = tester.battery.soc * 100.0

    print("\n" + "=" * 70)
    print(f"HOVER PERFORMANCE METRICS — DRONE {d_num}")
    print("=" * 70)
    print(f"  AUW: {tester.initial_auw:.3f} kg (Packages: {tester.packages_count} x 0.200kg)")
    print(f"  Hover Duration: {len(samples)*0.05:.1f} s ({len(samples)} samples)")
    print(f"  Commanded Altitude: {tester.target_alt:.2f} m")
    print(f"  Mean Altitude: {mean_alt:.3f} m (Error: {mean_err:.3f} m, Max: {max_err:.3f} m)")
    print(f"  Attitude Stability: Roll RMS={std_roll:.2f}° (max {max_roll:.2f}°), Pitch RMS={std_pitch:.2f}° (max {max_pitch:.2f}°)")
    print(f"  Vertical Velocity RMS: {std_vz:.3f} m/s")
    print(f"  Energy Consumed: {final_energy:.2f} Wh ({final_energy*3600:.0f} J)")
    print(f"  Remaining SOC: {final_soc:.1f}% (Reserve intact: {final_soc >= 20.0})")

    # Explicit PASS Criteria:
    # 1. Steady hover alt error mean <= 0.25 m, max <= 0.60 m
    # 2. Roll & pitch RMS <= 2.5 deg, max tilt <= 8.0 deg
    # 3. Vertical velocity RMS <= 0.30 m/s
    # 4. Successful landing & disarm (phase == FINISHED)
    pass_alt = mean_err <= 0.25 and max_err <= 0.60
    pass_att = std_roll <= 2.5 and std_pitch <= 2.5 and max_roll <= 8.0 and max_pitch <= 8.0
    pass_vz = std_vz <= 0.30
    pass_land = tester.phase == "FINISHED"

    passed = pass_alt and pass_att and pass_vz and pass_land

    print(f"\n  CRITERIA CHECK:")
    print(f"    Altitude Tracking:  {'PASS' if pass_alt else 'FAIL'} (mean={mean_err:.2f}m <= 0.25m, max={max_err:.2f}m <= 0.60m)")
    print(f"    Attitude Stability: {'PASS' if pass_att else 'FAIL'} (roll_rms={std_roll:.2f}°, pitch_rms={std_pitch:.2f}° <= 2.5°)")
    print(f"    Vertical Velocity:  {'PASS' if pass_vz else 'FAIL'} (vz_rms={std_vz:.2f}m/s <= 0.30m/s)")
    print(f"    Touchdown & Disarm: {'PASS' if pass_land else 'FAIL'} (final_state={tester.phase})")
    print(f"\nOVERALL RESULT FOR DRONE {d_num}: {'PASSED' if passed else 'FAILED'}")

    res = {
        "drone_num": d_num,
        "drone_idx": d_idx,
        "initial_auw_kg": tester.initial_auw,
        "packages": tester.packages_count,
        "hover_duration_sec": round(len(samples)*0.05, 2),
        "mean_altitude_m": round(mean_alt, 3),
        "mean_alt_error_m": round(mean_err, 3),
        "max_alt_error_m": round(max_err, 3),
        "roll_rms_deg": round(std_roll, 2),
        "pitch_rms_deg": round(std_pitch, 2),
        "max_roll_deg": round(max_roll, 2),
        "max_pitch_deg": round(max_pitch, 2),
        "vz_rms_ms": round(std_vz, 3),
        "energy_consumed_wh": round(final_energy, 2),
        "remaining_soc_percent": round(final_soc, 1),
        "reserve_intact": final_soc >= 20.0,
        "final_phase": tester.phase,
        "passed": passed,
    }
    (OUTPUT_DIR / f"phase_b_drone{d_num}_results.json").write_text(json.dumps(res, indent=2))
    return passed, res


if __name__ == "__main__":
    try:
        ok, _ = run_single_drone_hover(args.drone, args.hover_time)
        sys.exit(0 if ok else 1)
    finally:
        cleanup_procs()
