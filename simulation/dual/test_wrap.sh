#!/bin/bash
source /home/kalpeshbauskar/nidar_rescueswarm/simulation/env.sh
export DUAL_RUN_DIR=/tmp/dual_run
export ROS_DOMAIN_ID=88
python3 /home/kalpeshbauskar/nidar_rescueswarm/simulation/dual/test_recovery.py
