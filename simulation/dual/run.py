#!/usr/bin/env python3
import argparse, fcntl, json, os, signal, subprocess, time, sys
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parent
p = argparse.ArgumentParser()
p.add_argument('--headless', action='store_true')
p.add_argument('--setup-only', action='store_true')
p.add_argument('--fleet-size', type=int, default=None, help='Override fleet size')
args = p.parse_args()

lock = open(ROOT / 'run.lock', 'w')
try:
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
except BlockingIOError:
    raise SystemExit('A dual mission is already running.')

output = Path('/home/kalpeshbauskar/nidar_rescueswarm/simulation/dual') / ('results_' + datetime.now().strftime('%Y%m%d_%H%M%S'))
output.mkdir(parents=True, exist_ok=True)
(ROOT / 'latest-run.txt').write_text(str(output))

env = os.environ.copy()
env.update(
    ROS_DOMAIN_ID='88',
    GZ_PARTITION='nidar_rescueswarm',
    ROS_LOG_DIR=str(output / 'ros'),
    DUAL_RUN_DIR=str(output),
    GZ_CONFIG_PATH='/usr/share/gz' + ((':' + os.environ.get('GZ_CONFIG_PATH')) if os.environ.get('GZ_CONFIG_PATH') else ''),
    GZ_SIM_RESOURCE_PATH=os.environ.get(
        'GZ_SIM_RESOURCE_PATH',
        '/home/kalpeshbauskar/nidar_rescueswarm/simulation/imported/PX4-Autopilot/Tools/simulation/gz/models:/home/kalpeshbauskar/PX4-Autopilot/Tools/simulation/gz/models'
    ),
    GZ_SIM_SYSTEM_PLUGIN_PATH=os.environ.get(
        'GZ_SIM_SYSTEM_PLUGIN_PATH',
        '/home/kalpeshbauskar/PX4-Autopilot/build/px4_sitl_default/src/modules/simulation/gz_plugins'
    ),
    LIBGL_ALWAYS_SOFTWARE='1',
    QT_QPA_PLATFORM='xcb',
    LIBGL_DRI3_DISABLE='1',
    __GLX_VENDOR_LIBRARY_NAME='mesa',
)
children = []

def start(name, cmd, cwd=ROOT, extra=None):
    log = open(output / (name + '.log'), 'w')
    e = env.copy()
    e.update(extra or {})
    proc = subprocess.Popen(
        cmd, cwd=cwd, env=e, stdout=log, stderr=subprocess.STDOUT, start_new_session=True
    )
    children.append((name, proc, log))
    print(name, 'started', flush=True)
    return proc

try:
    # Determine active fleet size from config
    cfg = json.loads((ROOT / 'config.json').read_text())
    active_profile = cfg.get('active_profile', 'competition_3drone')
    drone_configs = cfg.get('profiles', {}).get(active_profile, {}).get('drones', None)
    if args.fleet_size is not None:
        fleet_size = args.fleet_size
    elif drone_configs is not None:
        fleet_size = len(drone_configs)
    else:
        fleet_size = 2

    start('gazebo', ['gz', 'sim', '-r', '--render-engine', 'ogre', str(ROOT / 'dual_rescue.sdf')] + (['-s'] if args.headless else []))
    start('agent', ['/home/kalpeshbauskar/Micro-XRCE-DDS-Agent/build/MicroXRCEAgent', 'udp4', '-p', '8898'])

    for i in range(fleet_size):
        runtime_dir = ROOT / f'runtime_{i}'
        runtime_dir.mkdir(parents=True, exist_ok=True)
        extra = {
            'PX4_SYS_AUTOSTART': '4026',
            'PX4_GZ_STANDALONE': '1',
            'PX4_GZ_WORLD': 'dual_rescue',
            'PX4_GZ_MODEL_NAME': f'rescue_{i}',
            'PX4_SIM_MODEL': 'gz_rescue_heavy',
            'PX4_UXRCE_DDS_PORT': '8898',
            'PX4_UXRCE_DDS_NS': f'drone{i+1}',
            'PX4_GZ_SIM_RENDER_ENGINE': 'ogre',
            'PATH': '/usr/bin:/home/kalpeshbauskar/PX4-Autopilot/build/px4_sitl_default/bin:' + env.get('PATH', ''),
        }
        start(
            f'px4-{i+1}',
            ['/home/kalpeshbauskar/PX4-Autopilot/build/px4_sitl_default/bin/px4', '-i', str(i), '-s', 'etc/init.d-posix/rcS', '.', '-d'],
            runtime_dir,
            extra,
        )

    mission = None
    begin = time.monotonic()
    print('Results:', output, f'Fleet size: {fleet_size}', flush=True)

    while time.monotonic() - begin < 2700:
        if mission is None and not args.setup_only and time.monotonic() - begin > 15:
            mission = start('mission', [sys.executable, '-u', str(ROOT / 'mission.py')])
        for name, proc, log in children:
            if proc.poll() is not None:
                if name == 'mission' and proc.returncode == 0:
                    print('Mission finished. Stopping simulator.', flush=True)
                    sys.exit(0)
                raise RuntimeError(f'{name} exited {proc.returncode}; see {output/(name+".log")}')
        time.sleep(1)
    raise RuntimeError('Supervisor exceeded 45 minutes')

except KeyboardInterrupt:
    print('Stopping dual simulation.', flush=True)
finally:
    for name, proc, log in reversed(children):
        if proc.poll() is None:
            os.killpg(proc.pid, signal.SIGINT)
    for name, proc, log in reversed(children):
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid, signal.SIGKILL)
            proc.wait()
        log.close()
