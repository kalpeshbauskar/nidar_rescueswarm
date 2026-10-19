#!/usr/bin/env bash
./clean_stale.sh

source /opt/ros/jazzy/setup.bash
source /home/kalpeshbauskar/px4_ros2_ws/install/setup.bash
source /home/kalpeshbauskar/nidar_rescueswarm/ros2_ws/install/setup.bash
source /home/kalpeshbauskar/nidar_rescueswarm/venv/bin/activate
cd simulation/dual

# Re-configure run.py to launch test_simul_2drone.py temporarily for preflight
sed -i "s/str(ROOT \/ 'mission.py')/str(ROOT \/ 'test_simul_2drone.py'), '--hover-time', '15.0'/g" run.py

echo "Starting PREFLIGHT..."
python3 run.py --headless > preflight_run.log 2>&1

# Restore mission.py in run.py
sed -i "s/str(ROOT \/ 'test_simul_2drone.py'), '--hover-time', '15.0'/str(ROOT \/ 'mission.py')/g" run.py

echo "PREFLIGHT COMPLETE. Checking log..."
tail -n 30 preflight_run.log
