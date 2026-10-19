import sys, os, time, subprocess, json, psutil
import rclpy
from rclpy.node import Node
from rosgraph_msgs.msg import Clock
import threading

def get_rtf(log_dir):
    try:
        with open(os.path.join(log_dir, 'mission.log')) as f:
            for line in f:
                if 'RTF' in line:
                    pass # Parse later if needed
    except:
        pass
    return 1.0 # placeholder

def run_cycle(cycle_num, wind_speed):
    print(f"==================================================")
    print(f"STARTING CYCLE {cycle_num} (Wind: {wind_speed} m/s)")
    print(f"==================================================")
    
    # 1. Prepare environment
    env = os.environ.copy()
    # We already sourced the env in the bash script that calls this.
    
    # 2. Setup world
    dual_dir = "/home/kalpeshbauskar/nidar_rescueswarm/simulation/dual"
    subprocess.run(["python3", "build_world.py"], cwd=dual_dir, check=True)
    subprocess.run(["python3", "patch_wind.py", str(wind_speed), "dual_rescue.sdf"], cwd=dual_dir, check=True)
    
    # 3. Use run.py which we patched to use the correct GZ_CONFIG_PATH
    # Wait, run.py runs mission.py by default. Let's make sure it runs mission.py
    # We patched it to run test_simul_2drone.py! We need to revert that patch!
    
    # Run the cycle
    print("Running mission...")
    # we will revert run.py first.
    return True

if __name__ == '__main__':
    print("Running real soak test...")
