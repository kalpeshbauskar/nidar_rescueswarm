import subprocess

print("Running test_hover_drone.py...")
cmd = ["bash", "-c", "source /home/kalpeshbauskar/nidar_rescueswarm/simulation/env.sh && cd dual && python3 test_hover_drone.py --drone 1 --hover-time 15"]
subprocess.run(cmd)

