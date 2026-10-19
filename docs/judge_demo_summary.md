# NIDAR RescueSwarm - Judge Demo Summary

**PROJECT:** NIDAR RescueSwarm
**ARCHITECTURE:** 2 drones, 5+5 packages
**MISSION:** search -> detect -> deliver -> RTL -> land
**WIND TOLERANCE:** 5 m/s continuous crosswind

**KEY NUMBERS:**
- 850 mm wheelbase (motor-to-motor diagonal, < 900 mm limit)
- 420 x 420 mm frame core body
- 800 x 800 x 420 mm envelope (excluding propellers, < 900 mm)
- 1058 x 1058 mm envelope (including propeller tips)
- 780 mm landing gear track width
- 142.8 mm propeller blade tip clearance (31.2% diameter margin)
- 6.280 kg / drone
- 12.560 kg fleet
- 2.000 kg payload (10 x 0.200 kg)
- 10/10 detections
- 10/10 deliveries
- 10 physical detachments
- ~650 s mission
- 80.2% final SOC (70.4 Wh energy used)
- 0 missing deliveries
- 0 duplicate deliveries
- 0 collisions/cross-control
- mission PASS

**CLAW MECHANISM EXPLANATION:**
The drones are equipped with a physical, visible claw mechanism mated to a gravity-fed 5-slot storage rack. The claw actively controls the release of a single package at a time. Upon command, a physical detachment in the physics engine instantly removes exactly 0.200 kg from the drone's mass, allowing the package to drop under the force of gravity, while the claw and rack remain completely onboard the drone.
