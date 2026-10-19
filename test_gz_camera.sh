#!/bin/bash
PROJECT_ROOT=$(pwd)
source venv/bin/activate
export GZ_CONFIG_PATH=/usr/share/gz${GZ_CONFIG_PATH:+:$GZ_CONFIG_PATH}
export GZ_SIM_RESOURCE_PATH=$PROJECT_ROOT/simulation/imported/PX4-Autopilot/Tools/simulation/gz/models:/home/kalpeshbauskar/PX4-Autopilot/Tools/simulation/gz/models
export GZ_SIM_SYSTEM_PLUGIN_PATH=/home/kalpeshbauskar/PX4-Autopilot/build/px4_sitl_default/src/modules/simulation/gz_plugins
export LIBGL_ALWAYS_SOFTWARE=1
export QT_QPA_PLATFORM=xcb
export LIBGL_DRI3_DISABLE=1
export __GLX_VENDOR_LIBRARY_NAME=mesa
export GZ_PARTITION=nidar_rescueswarm
export GZ_IP=127.0.0.1

cd simulation/dual
python3 build_world.py
gz sim -s -r dual_rescue.sdf &
GZ_PID=$!
sleep 15
gz topic -e -t /rescue_0/camera -n 1 > ../../gz_camera.log 2>&1
kill $GZ_PID
