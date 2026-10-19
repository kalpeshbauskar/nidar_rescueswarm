#!/usr/bin/env python3
import sys, os, time, subprocess, json, psutil

def run_cycle(cycle, wind):
    print(f"\n--- CYCLE {cycle} (Wind: {wind} m/s) ---")
    start_time = time.time()
    dual_dir = "/home/kalpeshbauskar/nidar_rescueswarm/simulation/dual"
    
    subprocess.run(["pkill", "-9", "-f", "gz sim"], stderr=subprocess.DEVNULL)
    subprocess.run(["pkill", "-9", "-f", "px4"], stderr=subprocess.DEVNULL)
    subprocess.run(["pkill", "-9", "-f", "MicroXRCEAgent"], stderr=subprocess.DEVNULL)
    time.sleep(1)
    
    env_cmd = "source /opt/ros/jazzy/setup.bash && source /home/kalpeshbauskar/px4_ros2_ws/install/setup.bash && source /home/kalpeshbauskar/nidar_rescueswarm/ros2_ws/install/setup.bash && source /home/kalpeshbauskar/nidar_rescueswarm/venv/bin/activate"
    
    subprocess.run([f"bash", "-c", f"{env_cmd} && python3 build_world.py"], cwd=dual_dir, check=True)
    subprocess.run([f"bash", "-c", f"{env_cmd} && python3 patch_wind.py {wind} dual_rescue.sdf"], cwd=dual_dir, check=True)
    
    proc = subprocess.Popen(["bash", "-c", f"{env_cmd} && python3 run.py --headless"], cwd=dual_dir, stdout=open(f"cycle_{cycle}_run.log", "w"), stderr=subprocess.STDOUT, text=True)
    
    max_cpu = 0
    mem_start = None
    mem_end = None
    res_dir = None
    
    while True:
        ret = proc.poll()
        if ret is not None: break
            
        try:
            p = psutil.Process(proc.pid)
            children = p.children(recursive=True)
            total_rss = 0
            cpu = 0
            for child in children:
                try:
                    total_rss += child.memory_info().rss
                    cpu += child.cpu_percent(interval=0.0)
                except: pass
            if mem_start is None and total_rss > 0: mem_start = total_rss
            mem_end = total_rss
            max_cpu = max(max_cpu, cpu)
        except: pass
            
        if not res_dir:
            try: res_dir = open(os.path.join(dual_dir, 'latest-run.txt')).read().strip()
            except: pass
        time.sleep(2)
        
    duration = time.time() - start_time
    events = []
    if res_dir and os.path.exists(os.path.join(res_dir, 'mission.log')):
        with open(os.path.join(res_dir, 'mission.log')) as f:
            for line in f:
                try: events.append(json.loads(line))
                except: pass
                    
    detections = len([e for e in events if e.get('event') == 'package_released'])
    phases = [e.get('phase') for e in events if e.get('event') == 'phase']
    arms = phases.count('ARM')
    rtls = phases.count('RTL')
    lands = phases.count('LAND')
    disarms = phases.count('DISARM')
    
    return {
        'cycle': cycle, 'wind': wind, 'success': (arms == 2 and rtls == 2 and lands == 2 and disarms == 2 and detections == 10),
        'duration': duration, 'mem_start': mem_start, 'mem_end': mem_end, 'max_cpu': max_cpu,
        'arms': arms, 'rtls': rtls, 'lands': lands, 'disarms': disarms, 'drops': detections, 'res_dir': res_dir
    }

if __name__ == "__main__":
    results = []
    for c, w in [(1, 0), (2, 5.0), (3, 0)]:
        results.append(run_cycle(c, w))
        
    with open('soak_results.json', 'w') as f:
        json.dump(results, f, indent=2)
    print("ALL DONE")
