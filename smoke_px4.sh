#!/usr/bin/env bash
source /opt/ros/jazzy/setup.bash
source /home/kalpeshbauskar/nidar_rescueswarm/venv/bin/activate
cd simulation/dual
python3 run.py --setup-only --headless &
RUN_PID=$!
sleep 20

echo "=== CHECKING PIDS ==="
ps -ef | grep gz | grep -v grep
ps -ef | grep MicroXRCEAgent | grep -v grep
ps -ef | grep px4 | grep -v grep

echo "=== PX4 LOGS ==="
# Find newest results folder
RES_DIR=$(ls -td results_* | head -1)
tail -n 10 $RES_DIR/px4-1.log
tail -n 10 $RES_DIR/px4-2.log

kill $RUN_PID
