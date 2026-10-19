#!/usr/bin/env python3
"""Phase E: Complete 3-Drone RescueSwarm Mission Validation Supervisor.

Validates the full simultaneous autonomous mission from takeoff through final
landing and disarm across all 3 drones:
- Drone 1: 4 packages, initial AUW 6.426 kg
- Drone 2: 4 packages, initial AUW 6.426 kg
- Drone 3: 2 packages, initial AUW 5.956 kg
- Total payload: 10 packages = 2.000 kg

Executes:
1. Simultaneous launch of Gazebo, MicroXRCEAgent, and 3 PX4 instances
2. Autonomous lawnmower search across 3 non-overlapping zones (100,000 m² total)
3. Vision-based orange cylinder (survivor) detection via nadir cameras
4. Physical delivery of all 10 packages at 5m hover via DetachableJoint
5. Dynamic mass, inertia, and CG adaptation in flight
6. Continuous battery SOC and usable energy tracking (protecting 20% hard reserve)
7. Coordinated Return-to-Launch (RTL), precision landing, and ground disarm
8. Detailed performance metric compilation (search coverage, drops, transients, health)
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
from typing import Dict, List, Optional, Tuple

os.environ["ROS_DOMAIN_ID"] = "88"
os.environ["GZ_PARTITION"] = "nidar_rescueswarm"

ROOT = Path(__file__).resolve().parent
BASE = ROOT.parent
REPO_ROOT = BASE.parent
sys.path.insert(0, str(REPO_ROOT))

from simulation.hardware.config import (
    BATTERY_SPECS,
    FLEET_SIZE,
    MAX_MISSION_TIME_SEC,
    PACKAGE_MASS_KG,
    PAYLOAD_ALLOCATION,
    HARDWARE_BOM,
    get_drone_dry_mass_kg,
    get_drone_initial_auw_kg,
    get_fleet_initial_auw_kg,
)
from simulation.hardware.propulsion import (
    BatterySOCIntegrator,
    calculate_propulsion_state,
)

OUTPUT_DIR = ROOT / "results_phase_e"
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
    print("STEP 1 cleanup starting", flush=True)
    for name, proc, log in reversed(children):
        if proc.poll() is None:
            try:
                os.killpg(proc.pid, signal.SIGINT)
            except Exception:
                pass
    if children:
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

    # Safely terminate stale simulator processes without touching own PID or parent
    my_pid = os.getpid()
    my_ppid = os.getppid()
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            pid = proc.info['pid']
            if pid in (my_pid, my_ppid):
                continue
            name = proc.info.get('name') or ''
            cmdline = proc.info.get('cmdline') or []
            cmd_str = ' '.join(cmdline)

            # Match Gazebo, PX4 SITL, MicroXRCEAgent
            if name in ('gz-sim-server', 'MicroXRCEAgent', 'px4') or any(k in cmd_str for k in ('gz sim', 'px4 -i', 'MicroXRCEAgent')):
                try:
                    os.kill(pid, signal.SIGKILL)
                except Exception:
                    pass
            # Match mission.py ONLY if it is not test_phase_e
            elif any(c.endswith('simulation/dual/mission.py') or c == 'mission.py' for c in cmdline):
                if not any('test_phase_e' in c for c in cmdline):
                    try:
                        os.kill(pid, signal.SIGKILL)
                    except Exception:
                        pass
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

    print("STEP 2 cleanup complete", flush=True)


def scan_log(path: Path) -> Dict:
    if not path.exists():
        return {"error_count": 0, "warn_count": 0, "errors": [], "warnings": []}
    errs, warns = [], []
    with open(path, "r", errors="ignore") as f:
        for line in f:
            l = line.strip()
            if not l:
                continue
            ll = l.lower()
            if "error" in ll or "fatal" in ll or "critical" in ll:
                errs.append(l)
            elif "warn" in ll:
                warns.append(l)
    return {
        "error_count": len(errs),
        "warn_count": len(warns),
        "errors": errs[:5],
        "warnings": warns[:5],
    }


def parse_telemetry_csv(csv_path: Path) -> Dict:
    if not csv_path.exists():
        return {}
    import csv
    rows = []
    with open(csv_path, "r") as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append(r)
    if not rows:
        return {}

    alts = [float(r["altitude"]) for r in rows if r.get("altitude")]
    phases = [r["phase"] for r in rows if r.get("phase")]
    socs = [float(r["battery_soc_pct"]) for r in rows if r.get("battery_soc_pct")]
    powers = [float(r["power_w"]) for r in rows if r.get("power_w")]

    # Calculate flight distance from sequential coordinates
    dist = 0.0
    for i in range(1, len(rows)):
        try:
            dn = float(rows[i]["north"]) - float(rows[i-1]["north"])
            de = float(rows[i]["east"]) - float(rows[i-1]["east"])
            dz = float(rows[i]["altitude"]) - float(rows[i-1]["altitude"])
            dist += math.sqrt(dn**2 + de**2 + dz**2)
        except Exception:
            pass

    max_alt_err = max(abs(a - 25.0) for a in alts if a > 15.0) if any(a > 15.0 for a in alts) else 0.0

    return {
        "total_samples": len(rows),
        "distance_flown_m": round(dist, 1),
        "max_altitude_m": round(max(alts), 2) if alts else 0.0,
        "min_altitude_m": round(min(alts), 2) if alts else 0.0,
        "max_altitude_error_cruise_m": round(max_alt_err, 2),
        "initial_soc_pct": round(socs[0], 1) if socs else 100.0,
        "final_soc_pct": round(socs[-1], 1) if socs else 100.0,
        "max_power_w": round(max(powers), 1) if powers else 0.0,
        "avg_power_w": round(sum(powers) / len(powers), 1) if powers else 0.0,
        "final_phase": phases[-1] if phases else "UNKNOWN",
    }


def run_mission(smoke_test: bool = False):
    print("=" * 80)
    print("PHASE E: COMPLETE 3-DRONE RESCUESWARM MISSION VALIDATION" if not smoke_test else "PHASE E: SIMULATOR PROCESS SMOKE TEST")
    print("=" * 80)

    cleanup_procs()
    time.sleep(1)

    print("\n--- SPAWNING GAZEBO, AGENT & 3 PX4 SITL INSTANCES ---")
    print("STEP 3 starting Gazebo", flush=True)
    gz_proc = start_proc("gazebo", ["/usr/bin/gz", "sim", "-r", "-s", "--render-engine", "ogre", str(ROOT / "dual_rescue.sdf")])
    time.sleep(2)

    print("STEP 4 starting MicroXRCEAgent", flush=True)
    agent_proc = start_proc("agent", ["/home/kalpeshbauskar/Micro-XRCE-DDS-Agent/build/MicroXRCEAgent", "udp4", "-p", "8898"])
    time.sleep(2)

    print("STEP 5 starting PX4 instances", flush=True)
    px4_procs = {}
    for i in range(fleet_size):
        runtime_dir = ROOT / f"runtime_{i}"
        extra = {
            "PX4_SYS_AUTOSTART": "4026",
            "PX4_GZ_STANDALONE": "1",
            "PX4_GZ_WORLD": "dual_rescue",
            "PX4_GZ_MODEL_NAME": f"rescue_{i}",
            "PX4_SIM_MODEL": "gz_rescue_heavy",
            "PX4_UXRCE_DDS_PORT": "8898",
            "PX4_UXRCE_DDS_NS": f"drone{i+1}",
            "PX4_GZ_SIM_RENDER_ENGINE": "ogre",
            "PATH": "/usr/bin:/home/kalpeshbauskar/PX4-Autopilot/build/px4_sitl_default/bin:" + env.get("PATH", ""),
        }
        proc = start_proc(
            f"px4-{i+1}",
            ["/home/kalpeshbauskar/PX4-Autopilot/build/px4_sitl_default/bin/px4", "-i", str(i), "-s", "etc/init.d-posix/rcS", ".", "-d"],
            runtime_dir,
            extra,
        )
        px4_procs[i] = proc

    if smoke_test:
        print("\n--- SMOKE TEST: VERIFYING SIMULATOR PROCESSES REMAIN ALIVE FOR 20 SECONDS ---", flush=True)
        print(f"  Gazebo PID:          {gz_proc.pid}")
        print(f"  MicroXRCEAgent PID:  {agent_proc.pid}")
        for i, p in px4_procs.items():
            print(f"  PX4 Drone {i+1} PID:      {p.pid}")

        t_smoke_start = time.monotonic()
        while time.monotonic() - t_smoke_start < 20.0:
            elapsed = time.monotonic() - t_smoke_start
            time.sleep(2.0)
            all_alive = (gz_proc.poll() is None) and (agent_proc.poll() is None) and all(p.poll() is None for p in px4_procs.values())
            if not all_alive:
                print(f"\nSMOKE TEST FAILED at {elapsed:.1f}s: One or more simulator processes died!", flush=True)
                cleanup_procs()
                return False, {}
            print(f"  [Smoke {elapsed:4.1f}s/20s] Gazebo(PID {gz_proc.pid}: alive), Agent(PID {agent_proc.pid}: alive), PX4_1(PID {px4_procs[0].pid}: alive), PX4_2(PID {px4_procs[1].pid}: alive), PX4_3(PID {px4_procs[2].pid}: alive)", flush=True)

        print("\nSMOKE TEST SUCCESSFUL: All 5 simulator processes remained healthy and alive for 20.0 seconds!", flush=True)
        cleanup_procs()
        return True, {}

    time.sleep(12)

    # Preflight check
    all_alive = (gz_proc.poll() is None) and (agent_proc.poll() is None) and all(p.poll() is None for p in px4_procs.values())
    if not all_alive:
        print("FAILED: Pre-flight check failed! One or more simulator processes died.")
        cleanup_procs()
        return False, {}

    print("Pre-flight passed: 3 PX4 SITL instances alive, ports isolated, DDS ready.")

    print("STEP 6 starting mission controller", flush=True)
    mission_proc = start_proc("mission", [sys.executable, "-u", str(ROOT / "mission.py")])

    t0 = time.monotonic()
    cpu_samples = []
    mem_samples = []

    print("\n--- 3. MONITORING AUTONOMOUS MISSION EXECUTION ---")
    last_print = 0.0

    while True:
        now = time.monotonic()
        elapsed = now - t0

        if int(elapsed) % 2 == 0:
            cpu_samples.append(psutil.cpu_percent(interval=None))
            mem_samples.append(psutil.virtual_memory().percent)

        # Print periodic progress
        if now - last_print >= 10.0:
            last_print = now
            status_lines = []
            for d_idx in range(fleet_size):
                stat_file = OUTPUT_DIR / f"drone{d_idx+1}-status.json"
                if stat_file.exists():
                    try:
                        s = json.loads(stat_file.read_text())
                        phase = s.get("phase", "?")
                        drops = len(s.get("drops", []))
                        soc = s.get("hardware", {}).get("battery", {}).get("soc_pct", 0)
                        status_lines.append(f"D{d_idx+1}: {phase} ({drops} drops, {soc:.1f}%)")
                    except Exception:
                        pass
            if status_lines:
                print(f"  [Mission {elapsed:5.1f}s/1800s] {' | '.join(status_lines)}", flush=True)

        # Check mission process completion
        if mission_proc.poll() is not None:
            print(f"\n>>> Mission process completed with return code {mission_proc.returncode} at {elapsed:.1f}s!\n", flush=True)
            break

        # Check safety timeout (30 minutes max)
        if elapsed > MAX_MISSION_TIME_SEC:
            print(f"\nERROR: Mission exceeded maximum competition flight time ({MAX_MISSION_TIME_SEC}s)!\n", flush=True)
            break

        # Check process health
        for name, p, _ in children:
            if name != "mission" and p.poll() is not None:
                print(f"\nCRITICAL: Process {name} crashed during mission execution!\n", flush=True)
                break

        time.sleep(0.5)

    cleanup_procs()

    print("\n" + "=" * 80)
    print("PHASE E: POST-MISSION COMPREHENSIVE PERFORMANCE COMPILATION")
    print("=" * 80)

    # Read mission result
    res_file = OUTPUT_DIR / "mission-result.json"
    if not res_file.exists():
        print("FAILED: mission-result.json was not generated!")
        return False, {}

    res_data = json.loads(res_file.read_text())
    controllers = res_data.get("controllers", [])
    min_sep = res_data.get("minimum_separation_m", 0.0)

    # Parse per-drone metrics
    drone_summaries = {}
    total_drops = 0
    total_released_mass = 0.0
    total_energy_consumed = 0.0
    fleet_pass = True

    for i in range(fleet_size):
        d_num = i + 1
        stat = controllers[i] if i < len(controllers) else {}
        csv_data = parse_telemetry_csv(OUTPUT_DIR / f"drone{d_num}-telemetry.csv")
        px4_log = scan_log(OUTPUT_DIR / f"px4-{d_num}.log")

        init_pkgs = PAYLOAD_ALLOCATION[i]
        drops = stat.get("drops", [])
        delivered_cnt = len(drops)
        total_drops += delivered_cnt
        total_released_mass += delivered_cnt * PACKAGE_MASS_KG

        init_auw = get_drone_initial_auw_kg(i)
        final_auw = get_drone_dry_mass_kg(i) + (init_pkgs - delivered_cnt) * PACKAGE_MASS_KG

        hw = stat.get("hardware", {})
        bat = hw.get("battery", {})
        consumed_wh = bat.get("consumed_wh", 0.0)
        final_soc = bat.get("soc_pct", 0.0)
        reserve_ok = bat.get("is_reserve_intact", True)
        total_energy_consumed += consumed_wh

        done_ok = stat.get("done", False)
        error = stat.get("error", None)

        drone_pass = (delivered_cnt == init_pkgs) and done_ok and (error is None) and reserve_ok
        if not drone_pass:
            fleet_pass = False

        d_summary = {
            "drone_num": d_num,
            "initial_auw_kg": init_auw,
            "final_auw_kg": round(final_auw, 3),
            "packages_carried": init_pkgs,
            "packages_delivered": delivered_cnt,
            "payload_released_kg": round(delivered_cnt * PACKAGE_MASS_KG, 3),
            "distance_flown_m": csv_data.get("distance_flown_m", 0.0),
            "total_mission_time_s": round(stat.get("elapsed_s", 0.0), 1),
            "energy_consumed_wh": consumed_wh,
            "final_soc_percent": final_soc,
            "reserve_intact": reserve_ok,
            "reserve_margin_wh": round(bat.get("reserve_wh", 53.28), 2),
            "max_altitude_error_m": csv_data.get("max_altitude_error_cruise_m", 0.0),
            "coverage_grid_fraction": round(stat.get("coverage_grid_fraction", 0.0) * 100.0, 1),
            "zone_area_m2": stat.get("zone_area_m2", 0.0),
            "detections_count": len(stat.get("detections", [])),
            "drops": drops,
            "px4_errors": px4_log.get("error_count", 0),
            "px4_warnings": px4_log.get("warn_count", 0),
            "final_phase": stat.get("phase", "UNKNOWN"),
            "done_status": done_ok,
            "error_msg": error,
            "drone_pass": drone_pass,
        }
        drone_summaries[f"drone_{d_num}"] = d_summary

    avg_cpu = sum(cpu_samples) / max(len(cpu_samples), 1)
    peak_cpu = max(cpu_samples) if cpu_samples else 0.0
    avg_mem = sum(mem_samples) / max(len(mem_samples), 1)

    overall_pass = fleet_pass and (total_drops == 10) and (total_released_mass == 2.000)

    fleet_summary = {
        "fleet_size": fleet_size,
        "combined_initial_auw_kg": get_fleet_initial_auw_kg(),
        "total_packages_delivered": total_drops,
        "total_payload_released_kg": round(total_released_mass, 3),
        "total_fleet_energy_consumed_wh": round(total_energy_consumed, 2),
        "fleet_usable_energy_remaining_wh": round(fleet_size * BATTERY_SPECS.usable_energy_wh - total_energy_consumed, 2),
        "minimum_separation_m": round(min_sep, 2),
        "avg_cpu_percent": round(avg_cpu, 1),
        "peak_cpu_percent": round(peak_cpu, 1),
        "avg_mem_percent": round(avg_mem, 1),
        "overall_pass": overall_pass,
        "drones": drone_summaries,
    }

    (OUTPUT_DIR / "phase_e_results.json").write_text(json.dumps(fleet_summary, indent=2))
    print(f"\nPhase E JSON written to {OUTPUT_DIR / 'phase_e_results.json'}")

    return overall_pass, fleet_summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Phase E 3-Drone Mission Validation")
    parser.add_argument("--smoke-test", action="store_true", help="Run 20-second simulator smoke test only")
    cli_args, _ = parser.parse_known_args()

    try:
        ok, _ = run_mission(smoke_test=cli_args.smoke_test)
        sys.exit(0 if ok else 1)
    finally:
        cleanup_procs()
