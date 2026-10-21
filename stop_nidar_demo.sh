#!/usr/bin/env bash
echo "Stopping NIDAR simulation processes..."
pkill -f "gz sim" || true
pkill -f "ruby.*gz" || true
pkill -f "MicroXRCEAgent" || true
pkill -f "px4" || true
pkill -f "QGroundControl" || true
pgrep -f "mission\.py" | grep -v "record" | xargs -r kill 2>/dev/null || true
pkill -f "control_centre.py" || true
pkill -f "yolo_person_node" || true
pkill -f "ssd_person_node" || true
pkill -f "rviz_telemetry_node" || true
pkill -f "vision_fleet.launch" || true
pkill -f "parameter_bridge" || true
pkill -f "rviz2" || true
sleep 1
pkill -9 -f "px4" 2>/dev/null || true
pkill -9 -f "gz sim" 2>/dev/null || true
pkill -9 -f "ruby.*gz" 2>/dev/null || true
pkill -9 -f "MicroXRCEAgent" 2>/dev/null || true
pkill -9 -f "control_centre.py" 2>/dev/null || true
pgrep -f "mission\.py" | grep -v "record" | xargs -r kill -9 2>/dev/null || true
rm -f /tmp/px4* /tmp/sem.fastrtps* /dev/shm/fastrtps* 2>/dev/null || true
echo "All processes stopped."

