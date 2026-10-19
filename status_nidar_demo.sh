#!/usr/bin/env bash

check_process() {
    if pgrep -f "$1" > /dev/null; then
        echo "$2: RUNNING"
    else
        echo "$2: NOT RUNNING"
    fi
}

echo "--- NIDAR DEMO STATUS ---"
check_process "gz sim" "Gazebo"
check_process "MicroXRCEAgent" "MicroXRCEAgent"
check_process "px4 -i 0" "PX4 rescue_0"
check_process "px4 -i 1" "PX4 rescue_1"
check_process "QGroundControl" "QGroundControl"
check_process "mission.py" "mission controller"
