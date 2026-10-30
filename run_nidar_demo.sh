#!/usr/bin/env bash
set -e

PROJECT_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
cd "$PROJECT_ROOT/simulation/dual"

echo "Cleaning stale processes..."
"$PROJECT_ROOT/stop_nidar_demo.sh" || true
sleep 2

source /opt/ros/jazzy/setup.bash
source /home/kalpeshbauskar/px4_ros2_ws/install/setup.bash
source /home/kalpeshbauskar/nidar_rescueswarm/ros2_ws/install/setup.bash
source /home/kalpeshbauskar/nidar_rescueswarm/venv/bin/activate
export YOLO_CONFIG_DIR=$PROJECT_ROOT/.yolo
export GZ_CONFIG_PATH=/usr/share/gz${GZ_CONFIG_PATH:+:$GZ_CONFIG_PATH}
export GZ_SIM_RESOURCE_PATH=$PROJECT_ROOT/simulation/imported/PX4-Autopilot/Tools/simulation/gz/models:/home/kalpeshbauskar/PX4-Autopilot/Tools/simulation/gz/models:$PROJECT_ROOT/simulation/imported/humans
export GZ_SIM_SYSTEM_PLUGIN_PATH=/home/kalpeshbauskar/PX4-Autopilot/build/px4_sitl_default/src/modules/simulation/gz_plugins
export LIBGL_ALWAYS_SOFTWARE=1
export QT_QPA_PLATFORM=xcb
export LIBGL_DRI3_DISABLE=1
export __GLX_VENDOR_LIBRARY_NAME=mesa
export ROS_DOMAIN_ID=88
export GZ_PARTITION=nidar_rescueswarm
export ROS_LOG_DIR=$PROJECT_ROOT/simulation/logs
export ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST
export GZ_IP=127.0.0.1

echo "Validating configuration..."
python3 build_world.py
WIND_SPEED="${WIND_SPEED:-0.0}"
if (( $(echo "$WIND_SPEED > 0.001" | bc -l) )); then
    python3 patch_wind.py "$WIND_SPEED" dual_rescue.sdf
    echo "Wind active: ${WIND_SPEED} m/s applied to environment."
else
    echo "Calm weather mode: 0.0 m/s wind (stable, level flight)."
fi
echo "Configuration Validated: Final Ordered BOM (Zenith 22-Inch / Hobbywing X6-SE / Revogreen Solid-State)."

echo "Launching Gazebo GUI..."
gz sim -r --render-engine ogre dual_rescue.sdf &
GZ_PID=$!

echo "Launching MicroXRCEAgent..."
MicroXRCEAgent udp4 -p 8898 > /dev/null 2>&1 &
AGENT_PID=$!

echo "Launching PX4 instances..."
mkdir -p runtime_0 runtime_1

export PATH="/usr/bin:/home/kalpeshbauskar/PX4-Autopilot/build/px4_sitl_default/bin:$PATH"

(
    cd runtime_0
    export PX4_SYS_AUTOSTART=4026
    export PX4_GZ_STANDALONE=1
    export PX4_GZ_WORLD=dual_rescue
    export PX4_GZ_MODEL_NAME=rescue_0
    export PX4_SIM_MODEL=gz_rescue_heavy
    export PX4_UXRCE_DDS_PORT=8898
    export PX4_UXRCE_DDS_NS=drone1
    export PX4_GZ_SIM_RENDER_ENGINE=ogre
    /home/kalpeshbauskar/PX4-Autopilot/build/px4_sitl_default/bin/px4 -i 0 -s etc/init.d-posix/rcS /home/kalpeshbauskar/PX4-Autopilot/build/px4_sitl_default -d > px4.log 2>&1
) &
PX4_0_PID=$!

(
    cd runtime_1
    export PX4_SYS_AUTOSTART=4026
    export PX4_GZ_STANDALONE=1
    export PX4_GZ_WORLD=dual_rescue
    export PX4_GZ_MODEL_NAME=rescue_1
    export PX4_SIM_MODEL=gz_rescue_heavy
    export PX4_UXRCE_DDS_PORT=8898
    export PX4_UXRCE_DDS_NS=drone2
    export PX4_GZ_SIM_RENDER_ENGINE=ogre
    /home/kalpeshbauskar/PX4-Autopilot/build/px4_sitl_default/bin/px4 -i 1 -s etc/init.d-posix/rcS /home/kalpeshbauskar/PX4-Autopilot/build/px4_sitl_default -d > px4.log 2>&1
) &
PX4_1_PID=$!

echo "Launching QGroundControl..."
/home/kalpeshbauskar/Downloads/QGroundControl-x86_64.AppImage > /dev/null 2>&1 &
QGC_PID=$!

echo "Waiting for PX4 to boot and connect..."
sleep 15

echo ""
echo "=========================================="
echo "          SYSTEM READY"
echo "  Gazebo, XRCE, 2x PX4, QGC are running"
echo "=========================================="
if [ -n "$AUTO_START" ]; then
    echo "AUTO_START set. Starting mission automatically..."
else
    echo "Press ENTER to start the final 5 m/s mission (or set AUTO_START=1)..."
    read -r -p "" || true
fi

DETECTOR="${DETECTOR:-ssd}"
if [ "$DETECTOR" = "ssd" ]; then
    export YOLO_CONFIG_FILE="$PROJECT_ROOT/ros2_ws/src/nidar_vision/config/ssd_sim.yaml"
else
    export YOLO_CONFIG_FILE="$PROJECT_ROOT/ros2_ws/src/nidar_vision/config/yolo_sim.yaml"
fi
echo "Starting vision processing (Detector: $DETECTOR)..."
mkdir -p "$PROJECT_ROOT/simulation/logs"
ros2 launch nidar_vision vision_fleet.launch.py detector:="$DETECTOR" > "$PROJECT_ROOT/simulation/logs/vision.log" 2>&1 &
VISION_PID=$!

echo "Starting RViz2 Tactical Swarm Ground Station (RTK GNSS, Cameras, Speeds, Geotags, Deliveries)..."
ros2 launch nidar_vision vision_rviz.launch.py > "$PROJECT_ROOT/simulation/logs/rviz.log" 2>&1 &
RVIZ_PID=$!
sleep 2

if [ "${RUN_CONTROL_CENTRE:-0}" = "1" ]; then
    echo "Starting legacy Mission Control Centre..."
    python3 "$PROJECT_ROOT/control_centre.py" > "$PROJECT_ROOT/simulation/logs/control_centre.log" 2>&1 &
    CC_PID=$!
fi

echo "Starting mission controller..."
python3 mission.py &
MISSION_PID=$!

wait $MISSION_PID || true
[ -n "$CC_PID" ] && kill $CC_PID 2>/dev/null || true
[ -n "$RVIZ_PID" ] && kill $RVIZ_PID 2>/dev/null || true
kill $VISION_PID 2>/dev/null || true
echo "Mission completed. You can safely close Gazebo and QGC using ./stop_nidar_demo.sh."
