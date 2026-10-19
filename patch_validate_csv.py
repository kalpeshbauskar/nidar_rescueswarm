import re

with open("simulation/dual/validate.py", "r") as f:
    data = f.read()

# Replace the simple error check with one that opens the CSV
replacement = """import os
import csv

def is_safe_timeout(c, run_dir):
    if c.get("error") != "landing timeout":
        return False
    # Check telemetry CSV for actual landed evidence
    csv_file = os.path.join(run_dir, f"drone{c['drone']}-telemetry.csv")
    if not os.path.exists(csv_file):
        return False
    try:
        with open(csv_file, "r") as f_csv:
            lines = f_csv.readlines()
            if len(lines) < 2:
                return False
            last_line = lines[-1].strip().split(',')
            # Header: elapsed,phase,north,east,altitude,route_index,armed,nav_state,frames,auw_kg,tw_ratio,battery_soc_pct,power_w,target_n,target_e,target_alt,pos_err_h,alt_err,roll,pitch,yaw,vx,vy,vz
            altitude = float(last_line[4])
            roll = float(last_line[18])
            pitch = float(last_line[19])
            # Ground reached (alt < 0.5m), stable (roll/pitch < 30 deg ~ 0.5 rad)
            if altitude < 0.5 and abs(roll) < 0.5 and abs(pitch) < 0.5:
                return True
    except Exception:
        pass
    return False

# In the main loop:
"""
data = replacement + data

# Replace the mission_success assignment
data = re.sub(
    r'all\(c\.get\("done"\) and c\.get\("error"\) in \(None, "landing timeout"\) for c in result\["controllers"\]\)',
    'all(c.get("done") and (c.get("error") is None or is_safe_timeout(c, LATEST_RUN_DIR)) for c in result["controllers"])',
    data
)

# wait, LATEST_RUN_DIR is just `latest_dir` in validate.py
data = data.replace('LATEST_RUN_DIR', 'latest_dir')

with open("simulation/dual/validate.py", "w") as f:
    f.write(data)
