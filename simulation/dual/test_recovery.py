import os, sys, time, json
import numpy as np
import rclpy
from px4_msgs.msg import VehicleLocalPosition, VehicleStatus, VehicleAttitude, VehicleLandDetected

sys.path.append('/home/kalpeshbauskar/nidar_rescueswarm/simulation/dual')
import mission

def run_test():
    rclpy.init()
    d = mission.Drone(0)
    
    current_time = 0.0
    def fake_time(): return current_time
    time.monotonic = fake_time
    d.start = fake_time()
    d.last_cmd = fake_time()
    d.last_status = fake_time()
    d.since = fake_time()
    
    def set_pos(n, e, d_alt):
        d.global_p = np.array([n, e, d_alt])
        msg = VehicleLocalPosition()
        msg.xy_valid = True
        msg.z_valid = True
        msg.vx = 0.0
        msg.vy = 0.0
        msg.vz = 0.0
        d.position(msg)
        d.p_at = current_time
        d.camera_at = current_time
        
    def fresh_tick():
        d.p_at = current_time
        d.camera_at = current_time
        d.tick()

    def set_status(nav, arm):
        msg = VehicleStatus()
        msg.nav_state = nav
        msg.arming_state = arm
        d.s = msg

    d.att = VehicleAttitude()
    d.offset = np.array([0.0, 0.0, 0.0])
    
    set_pos(0, -50, -25)
    set_status(14, 2)
    d.phase = 'SEARCH'
    d.route = [ (100, -50), (200, -50) ]
    d.index = 0
    d.packages_used = 0
    d.cargo = {i: 'attached' for i in range(10)}
    d.set_target(100, -50, 25)
    
    print("=== BEGIN TARGETED TEST ===")
    print(f"Phase: {d.phase}")
    
    print("\n[Injecting candidate detection (hits=3)]")
    d.detections.append({'n': 50, 'e': -50, 'hits': 3, 'delivered': False, 'rejected': False, 'last': current_time})
    print("Candidate state before rejection:", d.detections[0])
    print(f"Package count before rejection: {d.packages_used}")
    
    fresh_tick()
    print(f"Phase after tick: {d.phase}")
    
    set_pos(50, -49.35, -25)
    fresh_tick()
    current_time += 2.0
    fresh_tick()
    print(f"Phase after APPROACH arrival: {d.phase}")
    
    set_pos(50, -49.35, -5)
    fresh_tick()
    current_time += 5.0  # Make it 7.0 seconds total age
    
    print(f"\n[Failing low-altitude confirmation... (age={current_time - d.detections[0]['last']}s)]")
    fresh_tick()
    
    print(f"\nPhase after failed confirmation: {d.phase}")
    print("Candidate state after rejection:", d.detections[0])
    print(f"Package count after rejection: {d.packages_used}")
    print(f"Drops recorded (physical packages detached): {len(d.drops)}")
    
    set_pos(50, -49.35, -25)
    fresh_tick()
    current_time += 2.0
    fresh_tick()
    print(f"Phase after ASCEND arrival: {d.phase}")
    
    set_pos(0, -50, -25)
    fresh_tick()
    current_time += 2.0
    fresh_tick()
    print(f"Phase after RESUME arrival: {d.phase}")
    print(f"SEARCH resumption target: {d.target}")
    
    print("\n[Injecting subsequent observation within 6m]")
    with d.lock:
        n_obs, e_obs = 51.0, -49.0
        distances = [np.hypot(det['n'] - n_obs, det['e'] - e_obs) for det in d.detections]
        k = int(np.argmin(distances)) if distances else -1
        if k >= 0 and distances[k] <= 6:
            det = d.detections[k]
            det['hits'] += 1
            det['last'] = current_time
    
    print("Candidate state after merge:", d.detections[0])
    fresh_tick()
    print(f"Phase after subsequent observation tick: {d.phase}")
    
    if d.phase == 'SEARCH' and d.detections[0]['rejected'] and d.packages_used == 0:
        print("\nPASS")
    else:
        print("\nFAIL")
        
    rclpy.shutdown()

if __name__ == '__main__':
    run_test()
