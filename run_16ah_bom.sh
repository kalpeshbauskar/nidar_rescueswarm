#!/usr/bin/env bash
set -e

PROJECT_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
cd "$PROJECT_ROOT"

echo "=========================================================="
echo "  Configuring: ORIGINAL SIMULATION (16 Ah / Rev-B 850mm)"
echo "  - Battery: 16,000 mAh 6S (355.2 Wh)"
echo "  - Motors: 4x T-Motor MN4014 KV330 (2.6 kgf peak / 10.4 kgf total)"
echo "  - Props: 17x5.8 Carbon Fiber (850 mm Wheelbase)"
echo "  - Camera: Luxonis OAK-D Lite (90° HFOV)"
echo "  - AUW: ~6.4 kg loaded / 5.4 kg dry"
echo "=========================================================="

git checkout original-simulation
source /opt/ros/jazzy/setup.bash
cd ros2_ws
colcon build --packages-select nidar_vision > /dev/null 2>&1
cd "$PROJECT_ROOT"

echo "Launching Original 16 Ah Simulation..."
exec ./run_nidar_demo.sh "$@"
