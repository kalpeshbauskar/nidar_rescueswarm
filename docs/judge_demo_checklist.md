# NIDAR RescueSwarm - Judge Demo Checklist

**PRE-FLIGHT VALIDATIONS**
- [x] Verify exact package allocation: 2 drones, 5+5 distribution.
- [x] Verify AUW: 6.280 kg / drone, 12.560 kg fleet total.
- [x] Verify drone dimensions: 850 mm wheelbase (<900mm limit), 800x800x420 mm body, 780 mm landing track.
- [x] Verify physics engine parameters (masses, inertias).
- [x] Verify QGroundControl connectivity for 2 drones simultaneously.
- [x] Verify Wind Simulation set to 5 m/s crosswind.

**MISSION VALIDATIONS**
- [x] Drones take off sequentially without collisions.
- [x] Both drones perform dynamic Search -> Transit -> Approach -> Hover.
- [x] 10 independent physical package releases occur visually.
- [x] 10 independent 0.200 kg mass decrements occur in physics engine.
- [x] Drones execute RTL simultaneously without collisions.
- [x] Drones land and automatically disarm.
- [x] Final battery state correctly reported (~80.2% SOC remaining, 70.4 Wh consumed).
- [x] Post-mission logs successfully extracted and evaluated by validate.py.
