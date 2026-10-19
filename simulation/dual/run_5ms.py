import sys, os, subprocess

wind_speed = 5
print(f"==================================================")
print(f"WIND TEST CASE: {wind_speed} m/s")
print(f"==================================================")

# Generate fresh SDF
subprocess.run(["python3", "build_world.py"], check=True)

# Patch SDF for wind
subprocess.run(["python3", "patch_wind.py", str(wind_speed)], check=True)

print(f"Starting mission with wind {wind_speed} m/s...")

# Run the mission
cmd = ["bash", "run.sh", "--headless"]
res = subprocess.run(cmd, capture_output=True, text=True)

with open(f"wind_{wind_speed}_log.txt", "w") as f:
    f.write(res.stdout)
    f.write("\n")
    f.write(res.stderr)
    
if res.returncode != 0:
    print(f"Mission failed to complete gracefully (return code {res.returncode})")

# generate_report
rep_res = subprocess.run(["python3", "generate_report.py"], capture_output=True, text=True)
with open(f"wind_{wind_speed}_report.txt", "w") as f:
    f.write(rep_res.stdout)
    f.write("\n")
    f.write(rep_res.stderr)
    
print(rep_res.stdout)
