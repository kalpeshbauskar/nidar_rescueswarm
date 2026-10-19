import json
import subprocess

with open("config.json", "r") as f:
    cfg = json.load(f)

cfg["profiles"]["competition_2drone"]["packages_total"] = 2
cfg["profiles"]["competition_2drone"]["package_allocation"] = [1, 1]
cfg["profiles"]["competition_2drone"]["drones"][0]["packages"] = 1
cfg["profiles"]["competition_2drone"]["drones"][1]["packages"] = 1

with open("config.json", "w") as f:
    json.dump(cfg, f, indent=2)

subprocess.run(["python3", "build_world.py"], check=True)
subprocess.run(["python3", "patch_wind.py", "5.0", "dual_rescue.sdf"], check=True)

print("Running 5 m/s micro-test...")
cmd = "source /home/kalpeshbauskar/nidar_rescueswarm/simulation/env.sh && cd /home/kalpeshbauskar/nidar_rescueswarm/simulation/dual && python3 run.py --headless"
subprocess.run(["bash", "-c", cmd])

cfg["profiles"]["competition_2drone"]["packages_total"] = 10
cfg["profiles"]["competition_2drone"]["package_allocation"] = [5, 5]
cfg["profiles"]["competition_2drone"]["drones"][0]["packages"] = 5
cfg["profiles"]["competition_2drone"]["drones"][1]["packages"] = 5

with open("config.json", "w") as f:
    json.dump(cfg, f, indent=2)
subprocess.run(["python3", "build_world.py"], check=True)
