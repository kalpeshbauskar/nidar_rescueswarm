#!/usr/bin/env python3
"""Phase A: 3-Drone Startup and Process Health Test.

Launches Gazebo headless, MicroXRCEAgent, and 3 PX4 SITL instances.
Verifies all 3 instances boot, connect to sensors, expose DDS topics,
and achieve local navigation lock without port collisions or crashes.
"""

import os
import sys
import time
import json
import signal
import psutil
import subprocess
from pathlib import Path

# Force ROS 2 domain ID 88 and Gazebo partition for entire process and children
os.environ["ROS_DOMAIN_ID"] = "88"
os.environ["GZ_PARTITION"] = "nidar_rescueswarm"

ROOT = Path(__file__).resolve().parent
BASE = ROOT.parent
REPO_ROOT = BASE.parent
sys.path.insert(0, str(REPO_ROOT))

from simulation.hardware.config import (
    FLEET_SIZE,
    NETWORK_SPECS,
    get_drone_initial_auw_kg,
    get_drone_dry_mass_kg,
)

OUTPUT_DIR = ROOT / "results_phase_a"
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


def start(name, cmd, cwd=ROOT, extra=None):
    log = open(OUTPUT_DIR / f"{name}.log", "w")
    e = env.copy()
    e.update(extra or {})
    proc = subprocess.Popen(
        cmd, cwd=cwd, env=e, stdout=log, stderr=subprocess.STDOUT, start_new_session=True
    )
    children.append((name, proc, log))
    print(f"  [START] {name} (PID {proc.pid})", flush=True)
    return proc


def cleanup():
    print("\nShutting down child processes...", flush=True)
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
    # Force kill any lingering px4 or gz processes
    subprocess.run(["pkill", "-9", "-f", "px4 -i"], stderr=subprocess.DEVNULL)
    subprocess.run(["pkill", "-9", "-f", "gz sim"], stderr=subprocess.DEVNULL)
    subprocess.run(["pkill", "-9", "-f", "MicroXRCEAgent"], stderr=subprocess.DEVNULL)


def run_test():
    print("=" * 70)
    print("PHASE A: 3-DRONE SIMULTANEOUS STARTUP TEST")
    print("=" * 70)

    # Pre-clean
    subprocess.run(["pkill", "-9", "-f", "px4 -i"], stderr=subprocess.DEVNULL)
    subprocess.run(["pkill", "-9", "-f", "gz sim"], stderr=subprocess.DEVNULL)
    subprocess.run(["pkill", "-9", "-f", "MicroXRCEAgent"], stderr=subprocess.DEVNULL)
    time.sleep(1)

    # 1. Start Gazebo Headless
    print("\n1. Launching Gazebo Sim (headless)...")
    gz_proc = start(
        "gazebo",
        [
            "/usr/bin/gz",
            "sim",
            "-r",
            "-s",
            "--render-engine",
            "ogre",
            str(ROOT / "dual_rescue.sdf"),
        ],
    )

    # 2. Start MicroXRCEAgent
    print("2. Launching MicroXRCEAgent (port 8898)...")
    agent_proc = start(
        "agent",
        [
            "/home/kalpeshbauskar/Micro-XRCE-DDS-Agent/build/MicroXRCEAgent",
            "udp4",
            "-p",
            "8898",
        ],
    )

    time.sleep(3)

    # 3. Start 3 PX4 SITL instances
    print("3. Launching 3 PX4 SITL instances simultaneously...")
    px4_procs = {}
    for i in range(3):
        runtime_dir = ROOT / f"runtime_{i}"
        runtime_dir.mkdir(parents=True, exist_ok=True)
        extra = {
            "PX4_SYS_AUTOSTART": "4026",
            "PX4_GZ_STANDALONE": "1",
            "PX4_GZ_WORLD": "dual_rescue",
            "PX4_GZ_MODEL_NAME": f"rescue_{i}",
            "PX4_SIM_MODEL": "gz_rescue_heavy",
            "PX4_UXRCE_DDS_PORT": "8898",
            "PX4_UXRCE_DDS_NS": f"drone{i+1}",
            "PX4_GZ_SIM_RENDER_ENGINE": "ogre",
            "PATH": "/usr/bin:/home/kalpeshbauskar/PX4-Autopilot/build/px4_sitl_default/bin:"
            + env.get("PATH", ""),
        }
        proc = start(
            f"px4-{i+1}",
            [
                "/home/kalpeshbauskar/PX4-Autopilot/build/px4_sitl_default/bin/px4",
                "-i",
                str(i),
                "-s",
                "etc/init.d-posix/rcS",
                ".",
                "-d",
            ],
            runtime_dir,
            extra,
        )
        px4_procs[i] = proc

    # 4. Monitor startup for 30 seconds
    print("\n4. Monitoring startup, sensors, and topic publication (30s)...")
    start_t = time.monotonic()
    all_ready = False
    telemetry_data = {}

    # Import rclpy in-process to listen to topics
    import rclpy
    from rclpy.node import Node
    from px4_msgs.msg import VehicleLocalPosition, VehicleStatus
    from rclpy.qos import qos_profile_sensor_data

    rclpy.init()
    node = Node("phase_a_validator")

    received = {0: False, 1: False, 2: False}
    positions = {}
    arming_states = {}

    def make_pos_cb(idx):
        def cb(msg):
            received[idx] = True
            positions[idx] = {
                "x": round(float(msg.x), 2),
                "y": round(float(msg.y), 2),
                "z": round(float(msg.z), 2),
                "xy_valid": bool(msg.xy_valid),
                "z_valid": bool(msg.z_valid),
            }

        return cb

    def make_stat_cb(idx):
        def cb(msg):
            arming_states[idx] = int(msg.arming_state)

        return cb

    for i in range(3):
        node.create_subscription(
            VehicleLocalPosition,
            f"/drone{i+1}/fmu/out/vehicle_local_position_v1",
            make_pos_cb(i),
            qos_profile_sensor_data,
        )
        node.create_subscription(
            VehicleStatus,
            f"/drone{i+1}/fmu/out/vehicle_status_v4",
            make_stat_cb(i),
            qos_profile_sensor_data,
        )

    cpu_samples = []
    last_print = time.monotonic()

    while time.monotonic() - start_t < 60:
        rclpy.spin_once(node, timeout_sec=0.2)

        # Check process status
        for name, proc, _ in children:
            if proc.poll() is not None:
                raise RuntimeError(
                    f"Process {name} terminated unexpectedly with code {proc.returncode}!"
                )

        # Record CPU usage
        cpu_samples.append(psutil.cpu_percent(interval=None))

        # Periodic progress
        if time.monotonic() - last_print >= 5.0:
            last_print = time.monotonic()
            elapsed = time.monotonic() - start_t
            status_str = ", ".join(
                f"D{i+1}: {'OK' if (received[i] and positions.get(i, {}).get('z_valid')) else ('rx' if received[i] else 'wait')}"
                for i in range(3)
            )
            print(f"  [{elapsed:.1f}s] Drone status: {status_str}", flush=True)

        # Check if all 3 drones have valid local positions
        if all(
            received[i] and positions.get(i, {}).get("z_valid", False) for i in range(3)
        ):
            print(
                f"  All 3 drones reached valid local position lock after {time.monotonic()-start_t:.1f}s!"
            )
            all_ready = True
            break

        time.sleep(0.3)

    node.destroy_node()
    rclpy.shutdown()

    avg_cpu = sum(cpu_samples) / max(len(cpu_samples), 1)
    max_cpu = max(cpu_samples) if cpu_samples else 0.0

    print("\n" + "=" * 70)
    print("PHASE A AUDIT & TELEMETRY REPORT")
    print("=" * 70)

    results = {
        "gazebo_running": gz_proc.poll() is None,
        "agent_running": agent_proc.poll() is None,
        "px4_all_running": all(p.poll() is None for p in px4_procs.values()),
        "lock_achieved_all": all_ready,
        "drones": {},
        "cpu_usage_avg_percent": round(avg_cpu, 1),
        "cpu_usage_max_percent": round(max_cpu, 1),
    }

    for i in range(3):
        pos = positions.get(i, {})
        results["drones"][f"drone{i+1}"] = {
            "instance": i,
            "topic": f"/drone{i+1}/fmu/out/vehicle_local_position_v1",
            "received": received.get(i, False),
            "position": pos,
            "arming_state": arming_states.get(i, None),
            "configured_initial_auw_kg": get_drone_initial_auw_kg(i),
            "configured_dry_mass_kg": get_drone_dry_mass_kg(i),
        }
        print(f"Drone {i+1} (rescue_{i}):")
        print(f"  Topic received: {received.get(i, False)}")
        print(f"  Local position: x={pos.get('x')}, y={pos.get('y')}, z={pos.get('z')}")
        print(
            f"  Navigation valid: xy_valid={pos.get('xy_valid')}, z_valid={pos.get('z_valid')}"
        )
        print(f"  Initial AUW: {get_drone_initial_auw_kg(i)} kg")

    print(f"\nSystem Performance:")
    print(f"  CPU Load (avg): {avg_cpu:.1f}%, (peak): {max_cpu:.1f}%")

    passed = (
        results["gazebo_running"]
        and results["agent_running"]
        and results["px4_all_running"]
        and all_ready
    )

    print(f"\nPHASE A RESULT: {'PASSED' if passed else 'FAILED'}")
    (OUTPUT_DIR / "phase_a_results.json").write_text(json.dumps(results, indent=2))
    return passed


if __name__ == "__main__":
    try:
        ok = run_test()
        sys.exit(0 if ok else 1)
    finally:
        cleanup()
