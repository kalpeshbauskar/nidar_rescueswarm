#!/usr/bin/env bash
source /opt/ros/jazzy/setup.bash
export GZ_CONFIG_PATH=/usr/share/gz:$GZ_CONFIG_PATH
cd simulation/dual
python3 build_world.py
grep -i "real_time_factor" dual_rescue.sdf
