#!/usr/bin/env bash
source /opt/ros/jazzy/setup.bash
source /home/kalpeshbauskar/px4_ros2_ws/install/setup.bash
source /home/kalpeshbauskar/nidar_rescueswarm/ros2_ws/install/setup.bash
source /home/kalpeshbauskar/nidar_rescueswarm/venv/bin/activate
cd simulation/dual
python3 run.py --headless
