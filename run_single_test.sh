#!/bin/bash
cd /home/kalpeshbauskar/nidar_rescueswarm
source simulation/env.sh
cd dual

PKGS=$1
echo "Running test with $PKGS packages..."
# Set config
cat <<JSON > config.json
{
  "area_m2": 100000,
  "zones": [{"id":0,"east_min":-160,"east_max":0,"north_min":-156.25,"north_max":156.25,"area_m2":50000},
            {"id":1,"east_min":0,"east_max":160,"north_min":-156.25,"north_max":156.25,"area_m2":50000}],
  "altitude_m": 25,
  "lane_spacing_m": 20,
  "packages_per_drone": $PKGS,
  "package_mass_kg": 0.2,
  "world_origin": [47.397971057728974, 8.546163739800146, 0]
}
JSON
python3 build_world.py > /dev/null

export GZ_PARTITION='nidar_dual'
export ROS_DOMAIN_ID='88'

# Start gazbeo headless
/usr/bin/gz sim -r -s dual_rescue.sdf --render-engine ogre > gz.log 2>&1 &
GZ_PID=$!

# Start agent
/home/kalpeshbauskar/Micro-XRCE-DDS-Agent/build/MicroXRCEAgent udp4 -p 8898 > agent.log 2>&1 &
AGENT_PID=$!

sleep 5

# Start PX4
export PX4_SYS_AUTOSTART=4026
export PX4_GZ_STANDALONE=1
export PX4_GZ_WORLD=dual_rescue
export PX4_GZ_MODEL_NAME=rescue_0
export PX4_SIM_MODEL=gz_rescue_heavy
export PX4_UXRCE_DDS_PORT=8898
export PX4_UXRCE_DDS_NS=drone1
export PX4_GZ_SIM_RENDER_ENGINE=ogre
export PATH=/usr/bin:/home/kalpeshbauskar/PX4-Autopilot/build/px4_sitl_default/bin:$PATH

cd runtime_0
px4 -i 0 -s etc/init.d-posix/rcS . -d > px4.log 2>&1 &
PX4_PID=$!
cd ..

sleep 10
echo "Starting hover test..."
python3 /home/kalpeshbauskar/nidar_rescueswarm/hover_test.py
RES=$?

kill -9 $PX4_PID $AGENT_PID $GZ_PID 2>/dev/null
wait $GZ_PID 2>/dev/null
exit $RES
