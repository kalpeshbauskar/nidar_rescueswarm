#!/bin/bash
cd /home/kalpeshbauskar/nidar_rescueswarm
source simulation/env.sh
echo "=== ENV VARS ==="
echo "GZ_CONFIG_PATH=$GZ_CONFIG_PATH"
echo "GZ_IP=$GZ_IP"
echo "GZ_PARTITION=$GZ_PARTITION"
echo "ROS_AUTOMATIC_DISCOVERY_RANGE=$ROS_AUTOMATIC_DISCOVERY_RANGE"
echo "=== GZ COMMANDS ==="
gz --commands | grep sim
echo "=== GZ SIM VERSION ==="
gz sim --versions
