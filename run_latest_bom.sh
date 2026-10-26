#!/usr/bin/env bash
set -e

PROJECT_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
cd "$PROJECT_ROOT"

echo "=========================================================="
echo "  Configuring: LATEST BOM SIMULATION (22 Ah / A6-M 1,050mm)"
echo "  - Battery: Tattu 22,000 mAh 6S (488.4 Wh)"
echo "  - Motors: 4x T-Motor A6-M KV280 (6.0 kgf peak / 24 kgf total)"
echo "  - Props: 23-inch MF2311P-M Folding (1,050 mm Wheelbase)"
echo "  - Camera: Arducam IMX477 HQ (63° HFOV)"
echo "  - AUW: 8.143 kg loaded (5 pkgs) / 7.143 kg dry"
echo "=========================================================="

git checkout main
source /opt/ros/jazzy/setup.bash
cd ros2_ws
colcon build --packages-select nidar_vision > /dev/null 2>&1
cd "$PROJECT_ROOT"

echo "Launching Latest BOM Simulation..."
exec ./run_nidar_demo.sh "$@"
