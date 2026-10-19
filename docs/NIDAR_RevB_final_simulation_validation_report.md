# NIDAR Rev-B Final Simulation Validation Report

## 1. Executive Summary
The NIDAR Rev-B architecture has successfully completed Software-In-The-Loop (SITL) validation for dual-drone swarm operations, hardware integration, mission behavior, and robust failsafe capabilities. The simulation validates an 850 mm wheelbase drone (<900 mm limit) with a 6.280 kg loaded All-Up Weight (AUW), executing automated delivery missions with 5 m/s search and up to 10 m/s transit speeds.

**IMPORTANT DISTINCTION**:
- **PX4/Gazebo SITL VALIDATED**: Logic, state machines, communication failsafes, battery math, and payload detachments.
- **REAL HARDWARE NOT YET VALIDATED**: Physical thermals, RF propagation, real structural flex, and environmental degradation (see Limitations).

## 2. Final Aircraft Dimensions
- **FRAME CORE BODY**: 420 x 420 mm central electronics and payload section
- **NON-PROP STRUCTURAL ENVELOPE**: 800 x 800 x 420 mm (< 900 mm)
- **MOTOR DIAGONAL WHEELBASE**: 850 mm (strictly < 900 mm)
- **PROP-TIP ENVELOPE**: approximately 1058 x 1058 mm
- **PROP-TIP CLEARANCE**: 142.8 mm (31.2% diameter clean airflow margin)
- **LANDING-GEAR TRACK**: 780 mm

## 3. Complete Hardware/BOM Summary
- **EMPTY FLIGHT MASS**: 5.280 kg / drone
- **LOADED AUW**: 6.280 kg / drone
- **FLEET LOADED AUW**: 12.560 kg (2 drones)
- **T/W RATIO**: 2.23 (Loaded)

## 4. Propulsion Specification
- **MOTOR**: T-Motor MN501-S KV360
- **ESC**: 60A 6S
- **PROP**: T-Motor P18x6.1 (457.2 mm / 18 inch)

## 5. Battery / Energy Model
- **BATTERY**: 6S 16Ah LiPo
- **NOMINAL VOLTAGE**: 22.2 V
- **NOMINAL ENERGY**: 355.2 Wh
- **PROTECTED RESERVE**: 20% (71.04 Wh)

## 6. Package Rack + Claw
- **RACK MASS**: 0.250 kg
- **CLAW MASS**: 0.061 kg
- **PACKAGES**: 5 per drone (10 total for fleet)
- **PACKAGE MASS**: 0.200 kg each
- **PACKAGE DIMENSIONS**: 200 x 100 x 50 mm

*Package Mass Decrement (kg)*:
6.280 -> 6.080 -> 5.880 -> 5.680 -> 5.480 -> 5.280 kg

## 7. Camera / Gimbal
- **GIMBAL MASS**: 0.065 kg
- **CAMERA**: OAK-D simulated RGB/Depth payload.

## 8. Communications Architecture
- **RFD868x-IN**: Long-range telemetry link.
- **5 GHz Wi-Fi**: High-bandwidth local mesh.
- **ISOLATION**: True multi-drone logical isolation verified via namespace separation.
- **OFFLINE**: Fully local dependencies; no cloud integration required.

## 9. Speed Validation
- **SEARCH SPEED**: 5 m/s
- **TRANSIT SPEED**: up to 10 m/s
- **RTL SPEED**: up to 10 m/s
- **MAX VALIDATED SIMULATION FORWARD SPEED**: 10 m/s

## 10. Wind Validation
- **5 m/s CROSSWIND**: PASS

## 11. Normal Integrated Mission
- **Detections**: 10/10
- **Deliveries**: 10/10
- **Physical detachments**: 10/10
- **RTL**: 2/2
- **Landing**: 2/2
- **Disarm**: 2/2
- **Mission duration**: approximately 650 s
- **Mission energy**: 70.4 Wh / drone
- **Final analytical energy-derived SOC**: 80.2%
- **QGroundControl**: PASS
- **Gazebo**: PASS
- **Demo launcher**: PASS

## 12. Communications Failsafes
- **Normal network**: PASS
- **Wi-Fi loss**: PASS
- **RFD loss**: PASS
- **Both links lost + valid navigation**: PASS — autonomous RTL
- **Both links lost + degraded navigation**: PASS — safe hold/land
- **Link restoration**: PASS
- **Multi-drone isolation**: PASS
- **Offline/no-cloud dependency**: PASS

## 13. GPS / Navigation Failsafes
- **Normal navigation**: PASS
- **Temporary GNSS loss**: PASS
- **Prolonged GNSS loss**: PASS
- **Search navigation failure**: PASS
- **Delivery navigation failure**: PASS
- **Post-drop navigation failure**: PASS
- **RTL navigation failure**: PASS
- **Navigation failure + healthy links**: PASS
- **Navigation failure + total link loss**: PASS
- **GNSS restoration**: PASS
- **GNSS outlier / position jump**: PASS
- **Multi-drone isolation**: PASS

## 14. Battery / Energy Failsafes
- **Normal battery**: PASS
- **60% SOC start**: PASS
- **40% SOC start**: PASS
- **Near-reserve start**: PASS
- **Search energy abort**: PASS
- **Delivery energy abort**: PASS
- **Post-drop low energy**: PASS
- **Low energy during RTL**: PASS
- **Return-energy estimation**: PASS
- **Headwind energy penalty**: PASS
- **Capacity derating**: PASS
- **Multi-drone battery isolation**: PASS
- **Battery sensor anomaly**: PASS

## 15. Real-Runtime Soak / Stress Validation
- **DATA SOURCE**: REAL RUNTIME
- **PHYSICS**: normal real-time / controlled RTF
- **ACCELERATED RTF=0**: NOT USED
- **Cycle 1**: PASS
- **Cycle 2 — real 5 m/s wind**: PASS
- **Cycle 3**: PASS

*Test was conducted as three consecutive real-runtime mission cycles with clean simulator-stack reset/relaunch between cycles.*

- **Total real wall time**: 1433 s (approximately 24 minutes)
- **Total detections**: 30/30
- **Total deliveries**: 30/30
- **Physical detachments**: 30/30
- **RTL**: 6/6
- **Landing**: 6/6
- **Disarm**: 6/6
- **Unexpected PX4 restarts**: 0
- **Gazebo crashes**: 0
- **MicroXRCE crashes**: 0
- **Port conflicts**: 0
- **CPU average**: 45%
- **CPU peak**: 90%
- **RTF average**: 0.98
- **Lowest RTF**: 0.85
- **Maximum telemetry gap**: N/A — not instrumented in this run
- **Namespace collisions**: 0
- **Cross-controlled commands**: 0
- **NaN/Inf**: 0
- **Estimator resets**: 0
- **Package-state corruption**: 0

*Memory:* No progressively worsening memory-growth pattern was observed across the three cycles. Memory growth tapered from +167 MB to +95 MB to +10 MB (Start: 405 MB; After Cycle 1: 572 MB; After Cycle 2: 667 MB; After Cycle 3: 677 MB).

## 16. Demo Instructions
Start the full 2-drone mission demonstration:
```bash
./run_nidar_demo.sh
```
Check status:
```bash
./status_nidar_demo.sh
```
Stop/Cleanup:
```bash
./stop_nidar_demo.sh
```

## 17. Limitations / Physical Tests Still Required
This simulation **DOES NOT** prove:
- Actual MN501-S motor thermal behavior.
- Actual ESC thermal behavior.
- Real LiPo voltage sag / internal resistance.
- Real battery aging over charge cycles.
- Structural arm deflection under load.
- Real propeller flex.
- RF range/interference in physical field conditions.
- Real RFD868x-IN RF performance.
- Real Wi-Fi RF performance.
- Real OAK-D performance in smoke / rain / glare / low-light.
- Real servo/claw mechanical friction.
- Package mechanical jamming probability during release.
- Real landing-surface variation (slopes, vegetation).
- Real wind turbulence (only uniform crosswinds were simulated).
- Real-world aerodynamic coefficients.

These characteristics require rigorous bench, ground, and physical flight testing. Do not present these simulation results as physical certification.
