#!/usr/bin/env bash
# ==============================================================================
# NIDAR RESCUESWARM // TACTICAL MISSION CONTROL CENTRE LAUNCHER
# ==============================================================================

set -e

PROJECT_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)

# 1. Environment configuration
source /opt/ros/jazzy/setup.bash 2>/dev/null || true
source /home/kalpeshbauskar/px4_ros2_ws/install/setup.bash 2>/dev/null || true
source "$PROJECT_ROOT/ros2_ws/install/setup.bash" 2>/dev/null || true
source "$PROJECT_ROOT/venv/bin/activate" 2>/dev/null || true

export ROS_DOMAIN_ID=88
export GZ_PARTITION=nidar_rescueswarm
export ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST
export GZ_IP=127.0.0.1
export NIDAR_GCS_BOOTSTRAPPED=1

# Qt & OpenGL settings matching demo stack
export QT_QPA_PLATFORM=xcb
export QT_QPA_PLATFORM_PLUGIN_PATH=/usr/lib/x86_64-linux-gnu/qt5/plugins
export LIBGL_ALWAYS_SOFTWARE=1
export LIBGL_DRI3_DISABLE=1
export __GLX_VENDOR_LIBRARY_NAME=mesa

# 2. Launch Control Centre
echo "=========================================================="
echo "    LAUNCHING NIDAR TACTICAL MISSION CONTROL CENTRE       "
echo "    ROS_DOMAIN_ID: 88 | GZ_PARTITION: nidar_rescueswarm   "
echo "=========================================================="

exec python3 "$PROJECT_ROOT/control_centre.py" "$@"
