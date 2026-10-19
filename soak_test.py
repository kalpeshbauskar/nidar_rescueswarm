import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from px4_msgs.msg import VehicleLocalPosition
import subprocess, time, sys, os, signal, shutil, json

class SoakTester(Node):
    def __init__(self):
        super().__init__('soak_tester')
        self.t1 = 0.0
        self.t2 = 0.0
        self.sub1 = self.create_subscription(VehicleLocalPosition, '/drone1/fmu/out/vehicle_local_position_v1', self.cb1, qos_profile_sensor_data)
        self.sub2 = self.create_subscription(VehicleLocalPosition, '/drone2/fmu/out/vehicle_local_position_v1', self.cb2, qos_profile_sensor_data)

    def cb1(self, msg):
        self.t1 = time.monotonic()
    def cb2(self, msg):
        self.t2 = time.monotonic()

def main():
    root_dir = '/home/kalpeshbauskar/nidar_rescueswarm'
    logs_dir = os.path.join(root_dir, 'soak_test_logs')
    os.makedirs(logs_dir, exist_ok=True)
    
    subprocess.run("pkill -f px4 2>/dev/null || true", shell=True)
    subprocess.run("pkill -f gz 2>/dev/null || true", shell=True)
    subprocess.run("pkill -f MicroXRCEAgent 2>/dev/null || true", shell=True)
    
    env = os.environ.copy()
    env['PATH'] = '/usr/bin:/home/kalpeshbauskar/PX4-Autopilot/build/px4_sitl_default/bin:' + env.get('PATH', '')

    dual_dir = os.path.join(root_dir, 'simulation', 'dual')
    
    print("Launching Gazebo...")
    gz_proc = subprocess.Popen(['/usr/bin/gz', 'sim', '-r', '-s', 'dual_rescue.sdf', '--render-engine', 'ogre'], cwd=dual_dir, env=env, stdout=open(os.path.join(logs_dir, 'gz.log'), 'w'), stderr=subprocess.STDOUT)
    
    print("Launching Agent...")
    agent_proc = subprocess.Popen(['/home/kalpeshbauskar/Micro-XRCE-DDS-Agent/build/MicroXRCEAgent', 'udp4', '-p', '8898'], cwd=dual_dir, env=env, stdout=open(os.path.join(logs_dir, 'agent.log'), 'w'), stderr=subprocess.STDOUT)
    
    time.sleep(3)
    
    print("Launching PX4 instances...")
    env0 = env.copy()
    env0.update({
        'PX4_SYS_AUTOSTART': '4026', 'PX4_GZ_STANDALONE': '1', 'PX4_GZ_WORLD': 'dual_rescue',
        'PX4_GZ_MODEL_NAME': 'rescue_0', 'PX4_SIM_MODEL': 'gz_rescue_heavy', 'PX4_UXRCE_DDS_PORT': '8898',
        'PX4_UXRCE_DDS_NS': 'drone1', 'PX4_GZ_SIM_RENDER_ENGINE': 'ogre'
    })
    px4_0 = subprocess.Popen(['px4', '-i', '0', '-s', 'etc/init.d-posix/rcS', '.', '-d'], cwd=os.path.join(dual_dir, 'runtime_0'), env=env0, stdout=open(os.path.join(logs_dir, 'px4_0.log'), 'w'), stderr=subprocess.STDOUT)
    
    env1 = env0.copy()
    env1.update({'PX4_GZ_MODEL_NAME': 'rescue_1', 'PX4_UXRCE_DDS_NS': 'drone2'})
    px4_1 = subprocess.Popen(['px4', '-i', '1', '-s', 'etc/init.d-posix/rcS', '.', '-d'], cwd=os.path.join(dual_dir, 'runtime_1'), env=env1, stdout=open(os.path.join(logs_dir, 'px4_1.log'), 'w'), stderr=subprocess.STDOUT)

    rclpy.init()
    node = SoakTester()
    
    print("Waiting 20 seconds for boot...")
    for _ in range(200):
        rclpy.spin_once(node, timeout_sec=0.1)
    
    now = time.monotonic()
    node.t1 = now
    node.t2 = now
    test_start = now
    
    milestones = {60: False, 300: False, 435: False, 450: False, 600: False}
    health_records = {}
    
    max_age_1 = 0
    max_age_2 = 0
    fail_reason = None
    elapsed = 0.0
    
    try:
        while True:
            now = time.monotonic()
            elapsed = now - test_start
            
            rclpy.spin_once(node, timeout_sec=0.1)
            
            age1 = now - node.t1
            age2 = now - node.t2
            
            max_age_1 = max(max_age_1, age1)
            max_age_2 = max(max_age_2, age2)
            
            if int(elapsed) % 20 == 0:
                print(f"[{elapsed:.1f}s] Drone1 Age: {age1:.2f}s, Drone2 Age: {age2:.2f}s", flush=True)
                time.sleep(0.5)
            
            for m in milestones:
                if elapsed >= m and not milestones[m]:
                    health_records[m] = {'drone1_age': age1, 'drone2_age': age2, 'healthy': (age1 < 2.0 and age2 < 2.0)}
                    milestones[m] = True
                    print(f"Milestone {m}s recorded.", flush=True)
            
            if age1 > 2.0: fail_reason = f"Drone1 telemetry stale > 2s at {elapsed:.1f}s"; break
            if age2 > 2.0: fail_reason = f"Drone2 telemetry stale > 2s at {elapsed:.1f}s"; break
                
            if gz_proc.poll() is not None: fail_reason = "Gazebo exited unexpectedly"; break
            if agent_proc.poll() is not None: fail_reason = "MicroXRCEAgent exited unexpectedly"; break
            if px4_0.poll() is not None: fail_reason = "PX4_0 exited unexpectedly"; break
            if px4_1.poll() is not None: fail_reason = "PX4_1 exited unexpectedly"; break
            
            if elapsed >= 605:
                print("Test completed successfully.", flush=True)
                break
                
    finally:
        print("Shutting down processes...", flush=True)
        for p in [gz_proc, agent_proc, px4_0, px4_1]:
            try: p.terminate()
            except: pass
        time.sleep(2)
        for p in [gz_proc, agent_proc, px4_0, px4_1]:
            try: p.kill()
            except: pass
        
        subprocess.run("pkill -f px4 2>/dev/null || true", shell=True)
        subprocess.run("pkill -f gz 2>/dev/null || true", shell=True)
        subprocess.run("pkill -f MicroXRCEAgent 2>/dev/null || true", shell=True)
        
        logs = {
            'gz': open(os.path.join(logs_dir, 'gz.log')).read(),
            'agent': open(os.path.join(logs_dir, 'agent.log')).read(),
            'px4_0': open(os.path.join(logs_dir, 'px4_0.log')).read(),
            'px4_1': open(os.path.join(logs_dir, 'px4_1.log')).read()
        }
        
        report = {
            'duration': elapsed,
            'fail_reason': fail_reason,
            'max_age_1': max_age_1,
            'max_age_2': max_age_2,
            'milestones': health_records,
            'errors': {
                'unreachable': logs['px4_0'].lower().count('unreachable') + logs['px4_1'].lower().count('unreachable') + logs['gz'].lower().count('unreachable'),
                'multicast': logs['px4_0'].lower().count('multicast') + logs['px4_1'].lower().count('multicast'),
                'disconnect': logs['agent'].lower().count('disconnect'),
                'timeout': logs['px4_0'].lower().count('timeout') + logs['px4_1'].lower().count('timeout')
            }
        }
        
        with open(os.path.join(logs_dir, 'report.json'), 'w') as f:
            json.dump(report, f, indent=2)
            
        print(f"Report written to {logs_dir}/report.json", flush=True)
        if fail_reason:
            print("FAIL:", fail_reason)
        else:
            print("PASS: Soak test completed successfully.")
        sys.exit(0 if fail_reason is None else 1)

if __name__ == '__main__':
    main()
