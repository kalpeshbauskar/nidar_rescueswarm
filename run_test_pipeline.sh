#!/bin/bash
./run_nidar_demo.sh > demo_output.log 2>&1 &
DEMO_PID=$!
sleep 20
source venv/bin/activate
source /opt/ros/jazzy/setup.bash
source ros2_ws/install/setup.bash
ros2 launch nidar_vision vision_gazebo.launch.py > yolo_output.log 2>&1 &
YOLO_PID=$!
sleep 15
ros2 topic list > topic_list.log 2>&1
ros2 topic hz /nidar/camera/image_raw --window 2 > topic_hz.log 2>&1 &
HZ_PID=$!
sleep 5
kill $HZ_PID
kill $YOLO_PID
kill $DEMO_PID
./stop_nidar_demo.sh
