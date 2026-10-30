#!/usr/bin/env bash
set -e

PROJECT_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
cd "$PROJECT_ROOT"

echo "=========================================================="
echo "  Configuring: FINAL ORDERED BOM SIMULATION"
echo "  - Battery: Revogreen 22,000 mAh 6S Solid-State (22.8V / 501.6 Wh, 1.43 kg)"
echo "  - Motors: 4x Hobbywing X6-SE 280KV + 2270 Propeller Combo"
echo "  - Frame: Zenith Unmanned Systems 22-Inch Heavy-Lift Frame (980 mm)"
echo "  - Navigation: GenX Ublox ZED-F9P RTK GNSS Receiver + Helix Antenna (1cm CEP)"
echo "  - Base Station: CORS Survey-Grade L1+L2+L5 Industrial Antenna"
echo "  - Camera & VTX: Arducam IMX477 HQ 12.3MP + SpeedyBee TX800 5.8GHz"
echo "  - Quick-Release: 5x MG90S Metal Gear Servos on 5-Slot Drop Rack"
echo "  - Sensors: LiDAR Sensor Removed, Centimeter-Level RTK Added"
echo "  - Loaded AUW: 6.582 kg (5 pkgs) / Dry Mass: 5.582 kg | T/W: 3.65:1"
echo "=========================================================="

source /opt/ros/jazzy/setup.bash
cd ros2_ws
colcon build --packages-select nidar_vision > /dev/null 2>&1
cd "$PROJECT_ROOT"

echo "Launching Latest BOM Simulation..."
exec ./run_nidar_demo.sh "$@"
