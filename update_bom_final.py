import pathlib

bom = """# NIDAR RescueSwarm - Two-Drone Master BOM
**Date:** 2026-09-25
**Branch:** hardware-integration-v2
**Status:** FINAL REV-B CHECKPOINT

## 1. Master BOM (Per Drone)
| Category | Component | Qty | Mass/Unit (kg) | Total Mass (kg) |
|----------|-----------|-----|---------------|----------------|
| Structure | Rev-B Heavy-Lift Quadcopter CF Frame (850mm) | 1 | 1.250 | 1.250 |
| Structure | Landing Gear (780mm track) | 1 | 0.100 | 0.100 |
| Propulsion | T-Motor MN501-S KV360 | 4 | 0.175 | 0.700 |
| Propulsion | P18x6.1 Propeller | 4 | 0.0315| 0.126 |
| Power Electronics | 60A 6S ESC | 4 | 0.045 | 0.180 |
| Power Electronics | PDB | 1 | 0.080 | 0.080 |
| Avionics | Pixhawk 6C | 1 | 0.050 | 0.050 |
| Avionics | M10 GPS | 1 | 0.035 | 0.035 |
| Avionics | Jetson Orin Nano | 1 | 0.250 | 0.250 |
| Sensors | OAK-D Lite | 1 | 0.061 | 0.061 |
| Mounts | Gimbal | 1 | 0.065 | 0.065 |
| Telecom | RFD868x-IN | 1 | 0.015 | 0.015 |
| Telecom | Wi-Fi 5GHz | 1 | 0.015 | 0.015 |
| Payload System| Gravity-fed rack | 1 | 0.250 | 0.250 |
| Payload System| Claw | 1 | 0.061 | 0.061 |
| Battery | 6S 16Ah LiPo | 1 | 1.670 | 1.670 |
| Wiring | Miscellaneous | 1 | 0.372 | 0.372 |
| **TOTAL DRY** | **Empty Mass** | | | **5.280** |
| Payload | Packages (0.200 kg x 5) | 5 | 0.200 | 1.000 |
| **TOTAL WET** | **Loaded AUW** | | | **6.280** |

## 2. Fleet Totals (2 Drones)
- **Fleet Empty Mass**: 10.560 kg
- **Fleet Loaded AUW**: 12.560 kg
- **Total Packages**: 10

## 3. Power System
- Battery: 6S 16Ah
- Nominal Wh: 355.2 Wh
- Reserve Wh (20%): 71.0 Wh
- Final SOC (Analyzed): 80.2%
- Mission Energy used: 70.4 Wh / drone

## 4. Physical Dimensions
- Frame Body Size: 420 x 420 mm central plate / avionics core
- Envelope (no props): 800 x 800 x 420 mm (< 900 mm constraint)
- Wheelbase: 850 mm (motor-to-motor diagonal, < 900 mm limit)
- Motor Spacing (adjacent): 600.0 mm
- Propeller Blade Tip Clearance: 142.8 mm (31.2% diameter margin for optimal aerodynamic isolation)
- Envelope (with props): 1058 x 1058 mm
- Landing Gear Track Width: 780 mm
"""
pathlib.Path("docs/two_drone_master_bom.md").write_text(bom)
print("Updated docs/two_drone_master_bom.md with 850mm wheelbase specifications.")
