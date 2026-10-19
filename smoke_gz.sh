#!/usr/bin/env bash
source /opt/ros/jazzy/setup.bash
export GZ_CONFIG_PATH=/usr/share/gz:$GZ_CONFIG_PATH
export GZ_SIM_RESOURCE_PATH=/home/kalpeshbauskar/nidar_rescueswarm/simulation/imported/PX4-Autopilot/Tools/simulation/gz/models:/home/kalpeshbauskar/PX4-Autopilot/Tools/simulation/gz/models
export GZ_SIM_SYSTEM_PLUGIN_PATH=/home/kalpeshbauskar/PX4-Autopilot/build/px4_sitl_default/src/modules/simulation/gz_plugins
cd simulation/dual
python3 build_world.py
gz sim -s -r dual_rescue.sdf &
GZ_PID=$!
sleep 10
echo "=== CLOCK ==="
gz topic -e -t /clock -n 2
echo "=== TOPICS ==="
gz topic -l
sleep 10
echo "=== FINAL CLOCK ==="
gz topic -e -t /clock -n 1
kill $GZ_PID
