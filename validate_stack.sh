#!/bin/bash
cd /home/kalpeshbauskar/nidar_rescueswarm
source simulation/env.sh
cd /home/kalpeshbauskar/nidar_rescueswarm/simulation/dual

echo "Starting Gazebo..."
/usr/bin/gz sim -r -s dual_rescue.sdf --render-engine ogre > gz.log 2>&1 &
GZ_PID=$!

echo "Starting MicroXRCEAgent..."
/home/kalpeshbauskar/Micro-XRCE-DDS-Agent/build/MicroXRCEAgent udp4 -p 8898 > agent.log 2>&1 &
AGENT_PID=$!

sleep 3

echo "Starting PX4..."
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

echo "Waiting 25 seconds for PX4 to boot and connect..."
sleep 25

echo "Checking ROS topics..."
ros2 topic list > ros_topics.log

echo "Checking telemetry..."
timeout 10 ros2 topic echo /drone1/fmu/out/vehicle_local_position_v1 --once > telemetry.log || true

echo "Shutting down..."
kill -9 $PX4_PID $AGENT_PID $GZ_PID 2>/dev/null
wait $GZ_PID 2>/dev/null
pkill -f "ros2 topic echo" 2>/dev/null || true
pkill -f px4 2>/dev/null || true
pkill -f gz 2>/dev/null || true

echo "=== GZ LOG ==="
cat gz.log | grep -iE 'error|network is unreachable' | tail -n 5 || true
echo "=== AGENT LOG ==="
cat agent.log | grep -iE 'error|connect|unreachable' | tail -n 5 || true
echo "=== PX4 LOG ==="
cat runtime_0/px4.log | grep -iE 'error|network is unreachable|ready for takeoff' | tail -n 5 || true
echo "=== ROS TOPICS ==="
cat ros_topics.log | grep '/drone1/fmu/out/vehicle_local_position_v1' || echo "NO TOPIC"
echo "=== TELEMETRY ==="
head -n 20 telemetry.log | grep -E 'x:|y:|z:' || echo "NO TELEMETRY"
