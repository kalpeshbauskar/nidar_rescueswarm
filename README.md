# NIDAR RescueSwarm 🚁👥

**Autonomous Multi-UAV Search and Rescue Swarm System**  
*High-reliability coordinated aerial search, real-time onboard computer vision human detection, and safety-gated emergency payload delivery.*

---

## 🌟 Executive Summary

**NIDAR RescueSwarm** is an autonomous multi-drone disaster response framework designed to operate in adverse conditions (flood zones, collapsed structures, remote wilderness). Built on **ROS 2 (Jazzy)**, **PX4 Autopilot**, and **Gazebo Harmonic**, the system coordinates a fleet of specialized heavy-lift quadcopters executing automated grid search, deep-learning based human survivor detection, geotagged target verification, and a multi-frame safety gate for emergency medical payload delivery.

---

## 📐 System Architecture

```
                                  +-----------------------------+
                                  |     NIDAR Control Centre    |
                                  | (PyQt / Mission Dispatcher) |
                                  +--------------+--------------+
                                                 |
                         +-----------------------+-----------------------+
                         |                                               |
             +-----------v-----------+                       +-----------v-----------+
             |    Drone 0 (Scout)    |                       |    Drone 1 (Relief)   |
             | Rev-B 850mm Quadcopter|                       | Rev-B 850mm Quadcopter|
             +-----------+-----------+                       +-----------+-----------+
                         |                                               |
     +-------------------+-------------------+       +-------------------+-------------------+
     |                   |                   |       |                   |                   |
+----v-----+       +-----v----+       +------v---+ +----v-----+       +-----v----+       +------v---+
| PX4 Auto |       | OAK-D /  |       | ROS 2    | | PX4 Auto |       | OAK-D /  |       | ROS 2    |
| -pilot   |       | Gazebo   |       | YOLO     | | -pilot   |       | Gazebo   |       | YOLO     |
| (uORB)   |       | Camera   |       | Person   | | (uORB)   |       | Camera   |       | Person   |
+----+-----+       +-----+----+       +----+-----+ +----+-----+       +-----+----+       +----+-----+
     |                   |                 |            |                   |                 |
     |                   +--------+--------+            |                   +--------+--------+
     |                            |                     |                            |
     v                            v                     v                            v
[Fast-DDS]            [Target Geotag & BBox]       [Fast-DDS]            [Target Geotag & BBox]
     |                            |                     |                            |
     +----------------------------+                     +----------------------------+
                                  \                     /
                               +---v-------------------v---+
                               |  Safety Release Gate &    |
                               |  Payload Drop Controller  |
                               +---------------------------+
```

---

## 🚀 Key Features & Capabilities

1. **Dual-Drone Coordinated Search**:
   - Synchronized mission waypoint generation with spatial sector partitioning to prevent mid-air conflict.
   - Dynamic real-time telemetry streaming (GPS, Battery %, Flight Mode, uORB vehicle status).

2. **Onboard Computer Vision & Survivor Detection**:
   - **Custom-Trained YOLO Person Detector** (`models/person_best.onnx`, `models/person_best.pt`): Low-latency inference (<25ms) optimized for aerial viewpoints.
   - Dual-pipeline support: High-speed YOLOv11/v8 or MobileNet-SSD detector options.
   - **RViz Visualization**: Real-time camera feeds with color-coded bounding boxes, confidence overlays, and survivor coordinate markers.

3. **Multi-Frame Verification & Hardware Release Gate**:
   - Strict safety logic requiring continuous multi-frame human detections and altitude/velocity bounds before unlocking payload servo release.
   - Prevents false-positive drops over debris or moving vehicles.

4. **Complete CAD & Hardware Specs**:
   - Custom 850mm wheelbase carbon-fiber quadcopter CAD models (`cad/nidar_revb_850_full_assembly.stl`).
   - Detailed Bill of Materials (`BOM.csv`, `NIDAR_BOM_and_Mission_Report.xlsx`).

---

## 📁 Repository Structure

```
.
├── cad/                          # 3D CAD models & STL mechanical assemblies
│   ├── nidar_revb_850_full_assembly.stl
│   └── stl/                      # Subassembly parts (arms, landing gear, mounts)
├── datasets/                     # Curated evaluation datasets
│   └── nidar_person_v2/          # YOLO formatted person detection dataset & YAML
├── docs/                         # Engineering & validation documentation
│   ├── NIDAR_RescueSwarm_Master_Mission_Report.pdf
│   ├── NIDAR_RevB_Final_Engineering_Report.pdf
│   ├── NIDAR_RevB_final_simulation_validation_report.md
│   ├── NIDAR_two_drone_final_validation_report.md
│   ├── judge_demo_checklist.md
│   └── two_drone_master_bom.md
├── models/                       # Trained perception & neural network models
│   ├── person_best.onnx          # Edge-optimized ONNX model
│   ├── person_best.pt            # PyTorch model weights
│   ├── nidar_person_v2/          # Checkpoints & evaluation metrics
│   └── ssd/                      # MobileNet-SSD detector weights & configs
├── ros2_ws/                      # ROS 2 Workspace
│   └── src/nidar_vision/         # Vision & sensor fusion package
│       ├── config/               # RViz and node configurations
│       ├── launch/               # ROS 2 launch files (fleet, gazebo, oak)
│       └── nidar_vision/         # Detection, metrics & camera nodes
├── simulation/                   # Gazebo Harmonic & PX4 simulation environment
│   ├── dual/                     # Dual-drone rescue world (dual_rescue.sdf)
│   ├── imported/humans/          # 3D photorealistic human survivor meshes & textures
│   └── hardware/                 # Actuator & sensor configuration
├── scripts/                      # Utility and verification scripts
├── tests/                        # Automated unit & integration tests
├── training/                     # Model training & fine-tuning pipelines
├── BOM.csv                       # Master Hardware Bill of Materials
├── control_centre.py             # Operator ground control station GUI
├── run_control_centre.sh         # Launch script for Ground Control GUI
├── run_nidar_demo.sh             # End-to-end full mission execution script
└── requirements.txt              # Python package dependencies
```

---

## 🛠️ Quick Start Guide

### Prerequisites
- Ubuntu 24.04 LTS (Noble) / Ubuntu 22.04 LTS
- ROS 2 Jazzy or Humble
- Gazebo Harmonic (Gz Sim)
- Python 3.10+ with `venv`

### Setup Environment
```bash
# Clone the repository
git clone https://github.com/kalpeshbauskar/nidar_rescueswarm.git
cd nidar_rescueswarm

# Install Python requirements
python3 -m pip install -r requirements.txt

# Build ROS 2 workspace
cd ros2_ws
colcon build --symlink-install
source install/setup.bash
cd ..
```

### Launch the Mission & Control Centre
```bash
# Launch Ground Station GUI
./run_control_centre.sh

# Run end-to-end dual-drone simulated rescue mission
./run_nidar_demo.sh
```

---

## 📊 Reports & Validation Deliverables

- **Master Mission Report**: [`docs/NIDAR_RescueSwarm_Master_Mission_Report.pdf`](docs/NIDAR_RescueSwarm_Master_Mission_Report.pdf)
- **Engineering Report**: [`docs/NIDAR_RevB_Final_Engineering_Report.pdf`](docs/NIDAR_RevB_Final_Engineering_Report.pdf)
- **Bill of Materials**: [`BOM.csv`](BOM.csv) & [`docs/two_drone_master_bom.md`](docs/two_drone_master_bom.md)
- **Mission Execution Log**: [`detailed_report_of_mission.csv`](detailed_report_of_mission.csv)

---

## 👥 Authors & Team
- **Kalpesh Bauskar** ([GitHub](https://github.com/kalpeshbauskar))
- NIDAR RescueSwarm Robotics Team
