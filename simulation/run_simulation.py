#!/usr/bin/env python3
"""Start the local RescueSwarm simulator; Ctrl+C stops its child processes."""
import argparse, os, signal, subprocess, time
from datetime import datetime
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--flight-check',action='store_true');p.add_argument('--search',action='store_true');p.add_argument('--headless',action='store_true');a=p.parse_args()
if a.search and a.flight_check:p.error('Choose --search or --flight-check, not both')
root=Path(__file__).resolve().parent
logdir=root/'logs'/datetime.now().strftime('%Y%m%d-%H%M%S');logdir.mkdir(parents=True)
children=[]
def start(name,args):
    log=open(logdir/(name+'.log'),'w')
    proc=subprocess.Popen(args,cwd=root,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
    children.append((name,proc,log));print(f'{name}: started; log {logdir/(name+".log")}',flush=True)
    return proc
try:
    start('agent',['/home/kalpeshbauskar/Micro-XRCE-DDS-Agent/build/MicroXRCEAgent','udp4','-p','8899'])
    start('world',['bash',str(root/'launch_world.sh')]+(['-s'] if a.headless else []))
    start('px4',['bash',str(root/'launch_px4.sh'),'-d'])
    start('camera_bridge',['ros2','run','ros_gz_bridge','parameter_bridge','/x500_claw/camera@sensor_msgs/msg/Image[gz.msgs.Image'])
    start('geotag',['python','-u',str(root/'geotag_detector.py')]) if a.search else start('detector',['ros2','run','rescueswarm_detect','detector_node'])
    flight=None;started=time.monotonic()
    print('Simulation starting. Flight runs with --flight-check or --search. Ctrl+C stops the stack.',flush=True)
    while True:
        if (a.flight_check or a.search) and flight is None and time.monotonic()-started>15:
            flight=start('flight_check',['python','-u',str(root/('search_mission.py' if a.search else 'flight_check.py'))])
        for name,proc,log in children:
            if proc.poll() is not None:
                if name=='flight_check' and proc.returncode==0:
                    continue
                raise RuntimeError(f'{name} exited with code {proc.returncode}; see {logdir/(name+".log")}')
        time.sleep(1)
except KeyboardInterrupt:
    print('Stopping simulation.',flush=True)
finally:
    for name,proc,log in reversed(children):
        if proc.poll() is None:os.killpg(proc.pid,signal.SIGINT)
    for name,proc,log in reversed(children):
        try:proc.wait(timeout=5)
        except subprocess.TimeoutExpired:os.killpg(proc.pid,signal.SIGKILL);proc.wait()
        log.close()
