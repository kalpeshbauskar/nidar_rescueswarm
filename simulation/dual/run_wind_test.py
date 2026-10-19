import sys, os, subprocess

def run_test(wind_speed):
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
        return False
        
    # generate_report
    rep_res = subprocess.run(["python3", "generate_report.py"], capture_output=True, text=True)
    with open(f"wind_{wind_speed}_report.txt", "w") as f:
        f.write(rep_res.stdout)
        f.write("\n")
        f.write(rep_res.stderr)
        
    print(rep_res.stdout)
    
    if "PASS" in rep_res.stdout.split("\n")[-2:]:
        print(f"CASE {wind_speed} m/s PASSED")
        return True
    else:
        print(f"CASE {wind_speed} m/s FAILED")
        return False

# cases = [0, 3, 5, 8]
cases = [0, 3, 5, 8]
highest_pass = None

for c in cases:
    if not run_test(c):
        print(f"STOPPING AT {c} m/s DUE TO FAILURE.")
        sys.exit(1)
    highest_pass = c

print("8 m/s passed comfortably, attempting 10 m/s...")
if run_test(10):
    highest_pass = 10

print("==================================================")
print(f"HIGHEST TESTED PASSING WIND:\n{highest_pass} m/s")
print("WIND ROBUSTNESS PHASE:\nPASS")
print("==================================================")
