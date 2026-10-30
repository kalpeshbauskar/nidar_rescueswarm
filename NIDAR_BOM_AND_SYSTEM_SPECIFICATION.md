# NIDAR RescueSwarm — Master Bill of Materials (BOM) & System Specification

**Official Competition & Final Ordered Procurement Document**

- **Project:** NIDAR Autonomous Multi-UAV Search & Rescue Swarm
- **Airframe Architecture:** Zenith Unmanned Systems Heavy-Lift Carbon Fiber Quadcopter (980 mm Wheelbase, 22-Inch Props)
- **Airframe Rule Compliance:** 100% Custom Heavy-Lift Airframe Architecture (25 mm carbon fiber tube arms)
- **Fleet Configuration:** 2-Drone Autonomous Coordinated Search & Precision Humanitarian Delivery Swarm
- **Payload Delivery Architecture:** 5-Slot Underslung Quick-Release Drop Rack with 5x MG90S Metal Gear Servos
- **Payload Provision:** 10x 200g cylindrical humanitarian aid kits (5 per drone, organizer-supplied on-site at ₹0 procurement cost)
- **Navigation Architecture:** GenX Ublox ZED-F9P Multi-Band L1+L2+L5 RTK GNSS Receiver + GENX Active Helix Antenna (1 cm + 1 ppm RTK Fix precision) + Ground CORS Survey Base Station
- **Sensor Configuration:** LiDAR Sensor Removed; High-Accuracy Centimeter RTK Differential Positioning Active
- **Propulsion System:** 4x Hobbywing X6-SE 280KV Motor & 2270 Folding Propeller Combo with Integrated 30A/60A FOC ESC (24.0 kgf peak thrust per drone)
- **Energy Storage:** Revogreen 22.8V 22,000 mAh Solid-State 6S Lithium-Ion Battery (501.6 Wh, 1,430 g, 110A cont / 155A peak)
- **AI Compute & Vision:** NVIDIA Jetson Orin Nano Super Dev Kit (67 TOPS) + Hikvision E3000 256GB NVMe SSD + Arducam IMX477 HQ 12.3MP (6mm CS Lens)
- **Live Video Downlink:** SpeedyBee TX800 5.8GHz 800mW Video Transmitter
- **Swarm Communications:** 100% Standalone Off-Grid Private Tactical Mesh Network (802.11s 5 GHz Wi-Fi mesh + SiK 433 MHz telemetry + ELRS 2.4 GHz safety override)
- **Aircraft Mass:** Single Drone Dry Mass: **5,582.0 g (5.582 kg)** | Single Drone Loaded AUW (incl. 5 kits): **6,582.0 g (6.582 kg)**
- **Fleet AUW:** 2-Drone Fleet Total AUW: **13,164.0 g (13.164 kg)** — strictly within the 25.0 kg competition limit (47.3% margin)
- **Thrust-to-Weight Ratio:** **3.65:1 (Loaded AUW)** / **4.30:1 (Dry Mass)**
- **Mission Endurance:** **35.7 minutes** continuous hover on 80% usable capacity (401.3 Wh usable, 100.3 Wh 20% hard reserve intact)

---

## Final Ordered Bill of Materials Schedule

| # | Category | Item Description | Model / Specification | Qty D1 | Qty D2 | Qty Ground | Total Qty | Unit Wt (g) | Wt on D1 (g) | Unit Price (₹) | Line Total (₹) | Supplier | Purchase Link | Status |
| :---: | :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- | :--- | :---: |
| 1 | Airframe | Zenith 22-Inch Heavy-Lift Frame | Carbon fiber quadcopter frame for 22 in props, 25mm arms | 1 | 1 | 0 | 2 | 936 | 936 | ₹24,500 | ₹49,000 | Zenith Unmanned Systems | — | Verified |
| 2 | Airframe | Carbon Fiber Landing Gear | 16x14 mm CF tubes (780 mm track width) | 2 | 2 | 0 | 4 | 73 | 146 | ₹1,259 | ₹5,036 | Robu | [Link](https://robu.in/product/3k-roll-wrapped-carbon-fibre-tube-hollow-16mmod-14mmid-1000mml/) | Verified |
| 3 | Airframe | PETG 3D-Printed Parts | Anycubic PETG 1.75 mm black (Canopy, RTK mast, mounts) | 1 | 1 | 0 | 2 | 160 | 160 | ₹949 | ₹1,898 | Robocraze | [Link](https://robocraze.com/products/anycubic-petg-black-1kg-1-75mm-petg-3d-printer-filament) | Verified |
| 4 | Airframe | Anti-vibration Damper Set | Glass-fibre damper plate with silicone damping balls | 1 | 1 | 0 | 2 | 10 | 10 | ₹153 | ₹306 | Robu | [Link](https://robu.in/product/glass-fiber-flight-controller-anti-vibration-set-shock-absorber-apmkkmwc/) | Verified |
| 5 | Airframe | Fastener & Hardware Kit | EasyMech M3 stainless steel bolt, nut, washer & standoff set | 4 | 4 | 0 | 8 | 22.5 | 90 | ₹100 | ₹800 | Robu | [Link](https://robu.in/product/easymech-m3-x-15mm-chhd-bolt-nut-and-washer-set-20-pcs/) | Verified |
| 6 | Airframe | Battery Straps 30 cm | 30 cm reusable high-grip straps (2 per drone) | 2 | 2 | 0 | 4 | 15 | 30 | ₹61 | ₹244 | Robu | [Link](https://robu.in/product/30cm-lipo-battery-strap-belt-reusable-cable-tie-wrap/) | Verified |
| 7 | Propulsion | Hobbywing X6-SE Motor & Prop Combo-CW | 280KV Motor + 30A/60A FOC ESC + 2270 CW Prop | 2 | 2 | 1 | 5 | 373 | 746 | ₹11,999 | ₹59,995 | Aerokart | [Link](https://aerokartindia.in/product/hobbywing-x6-se-280kv-motor-and-2270-propeller-combo-kits-cw/) | Ordered |
| 8 | Propulsion | Hobbywing X6-SE Motor & Prop Combo-CCW | 280KV Motor + 30A/60A FOC ESC + 2270 CCW Prop | 2 | 2 | 1 | 5 | 373 | 746 | ₹11,999 | ₹59,995 | Aerokart | [Link](https://aerokartindia.in/product/hobbywing-x6-se-280kv-motor-and-2270-propeller-combo-kits-ccw/) | Ordered |
| 9 | Avionics | Think Robotics Pixhawk Pro 6C Kit | STM32H7 FMUv6C autopilot + PM02 + 433MHz Telemetry | 1 | 1 | 0 | 2 | 77 | 77 | ₹37,699 | ₹75,398 | Think Robotics | [Link](https://thinkrobotics.com/products/pixhawk-kit-online) | Ordered |
| 10 | Avionics | Holybro CAN Hub | CAN bus splitter for UAVCAN / Cyphal bus devices | 1 | 1 | 0 | 2 | 18 | 18 | ₹1,850 | ₹3,700 | Zbotic | [Link](https://zbotic.in/product/holybro-can-hub/) | Ordered |
| 11 | Avionics | Jetson-FC MAVLink Cable | 1.25 mm 6-pin female GH connector with 300 mm wire (30 AWG) | 1 | 1 | 0 | 2 | 5 | 5 | ₹159 | ₹318 | Robu | [Link](https://robu.in/product/a1254-06y-1-25mm-6-pin-female-gh-housing-connector-with-300mm-wire30-awg/) | Ordered |
| 12 | RTK GNSS | GenX Ublox ZED-F9P RTK GNSS Receiver | Multi-band L1+L2+L5 RTK module + QMC5883P compass | 1 | 1 | 0 | 2 | 24 | 24 | ₹15,688 | ₹31,376 | RoboKits India | [Link](https://robokits.co.in/multirotor-spare-parts/genx-uav-product/genx-ublox-zed-f9p-rtk-gnss-receiver-rover-base-module) | Ordered |
| 13 | RTK GNSS | GENX RTK GPS Rover Helix Antenna | LH-105A2-B Multi-Band L1+L2+L5 active helix antenna (36 dB) | 1 | 1 | 0 | 2 | 17 | 17 | ₹2,139 | ₹4,278 | RoboKits India | [Link](https://robokits.co.in/multirotor-spare-parts/gps-sensors/rtk-gps-rover-gnss-multi-band-l1-l2-l5-helix-antenna) | Ordered |
| 14 | RTK GNSS | RTK GPS Base Station CORS Antenna | LS-125-A High Precision L1+L2+L5 Survey Choke-Ring Antenna | 0 | 0 | 1 | 1 | 450 | 0 | ₹7,194 | ₹7,194 | RoboKits India | [Link](https://robokits.co.in/multirotor-spare-parts/gps-sensors/rtk-gps-base-station-survey-grade-cors-high-precision-industrial-l1-l2-l5-antenna) | Ordered |
| 15 | Avionics | Radio Telemetry V6 433 MHz 100 mW | SiK-class 433 MHz MAVLink telemetry air unit (in FC kit) | 1 | 1 | 0 | 2 | 25 | 25 | ₹0 | ₹0 | Think Robotics | [Link](https://thinkrobotics.com/products/pixhawk-kit-online) | Ordered |
| 16 | Avionics | RadioMaster RP3 V2 ELRS Receiver | 2.4 GHz ExpressLRS nano receiver with dual T-antennas | 1 | 1 | 0 | 2 | 3 | 3 | ₹3,109 | ₹6,218 | Robu | [Link](https://robu.in/product/radiomaster-rp3-v2-expresslrs-2-4ghz-nano-receiver/) | Verified |
| 17 | Power | Revogreen 22.8V 22000mAh Solid State Battery | Semi-solid-state pouch cells, 501.6 Wh, 110A cont, XT90 | 1 | 1 | 0 | 2 | 1430 | 1430 | ₹20,500 | ₹41,000 | Revogreen | [Link](https://revogreenbatteries.com/products/22-8v-22000mah-solid-state-6s-lithium-ion-battery-xt90) | Ordered |
| 18 | Power | Heavy-Duty Power Distribution Board 300A | High-current PDB with filtered logic rails | 1 | 1 | 0 | 2 | 120 | 120 | ₹3,500 | ₹7,000 | Robu | [Link](https://robu.in/product/swiftwing-pdb-6s-power-distribution-board/) | Verified |
| 19 | Power | Dual XL4016 8A DC-DC Buck Converters | Synchronous step-down regulators (19V Jetson, 6V Servos) | 2 | 2 | 0 | 4 | 27.5 | 55 | ₹399 | ₹1,596 | Robu | [Link](https://robu.in/product/48v36v24v-to-19v12v9v5v3v-adjustable-synchronous-stepdown-module-car-charging-power-supply/) | Verified |
| 20 | Power | Amass XT90-S Anti-Spark Connector Pair | XT90S female/male with internal spark resistor | 1 | 1 | 0 | 2 | 10 | 10 | ₹159 | ₹318 | Robu | [Link](https://robu.in/product/xt90-s-anti-spark-connector-with-housing-female/) | Verified |
| 21 | Power | Silicone Power & Motor Wiring Harness | 10 AWG battery leads + 12 AWG arm motor leads | 1 | 1 | 0 | 2 | 175 | 175 | ₹600 | ₹1,200 | Robu | [Link](https://robu.in/product/10awg-high-voltage-silicone-wire-3000v-red/) | Verified |
| 22 | AI Compute | NVIDIA Jetson Orin Nano Super Dev Kit | 8 GB LPDDR5, 67 TOPS AI inference, Wi-Fi module | 1 | 1 | 0 | 2 | 230 | 230 | ₹54,999 | ₹109,998 | Variety Infotech | [Link](https://varietyinfotech.com/product/nvidia-jetson-orin-nano-super-developer-kit/) | Verified |
| 23 | Storage | HIKVISION E3000 M.2 NVMe SSD 256GB | 256GB PCIe Gen3 x4 M.2 NVMe SSD (up to 3500 MB/s) | 1 | 1 | 0 | 2 | 8 | 8 | ₹2,499 | ₹4,998 | Amazon | [Link](https://www.amazon.in/VISION-E3000-Internal-Memory-3500MB/dp/B09ML2YBRF/ref=sr_1_7) | Ordered |
| 24 | Vision | Arducam IMX477 HQ IR-Cut Camera 12.3MP | 12.3 MP 1/2.3-inch Sony IMX477 with 6mm CS lens | 1 | 1 | 0 | 2 | 83 | 83 | ₹6,499 | ₹12,998 | Robu | [Link](https://robu.in/product/arducam-high-quality-ir-cut-camera-for-jetson-nano-xavier-nx-12-3mp-1-2-3-inch-imx477-hq-camera-module-with-6mm-cs-lens/) | Ordered |
| 25 | Video Downlink | SpeedyBee TX800 5.8GHz 800mW VTX | SpeedyBee TX800 48CH 800mW VTX + MMCX antenna | 1 | 1 | 0 | 2 | 6 | 6 | ₹1,899 | ₹3,798 | Robu | [Link](https://robu.in/product/speedybee-tx800/) | Ordered |
| 26 | Network | ALFA AWUS036ACM Dual-Band Wi-Fi Adapter | MT7612U AC1200 802.11s tactical mesh adapter | 1 | 1 | 0 | 2 | 70 | 70 | ₹5,000 | ₹10,000 | Amazon | [Link](https://www.amazon.in/dp/B073X6RL9D) | Verified |
| 27 | Payload Drop | 5-Slot Relief Package Drop Rack | Carbon fiber spine with PETG retention bays | 1 | 1 | 0 | 2 | 180 | 180 | ₹0 | ₹0 | In-house print | — | Verified |
| 28 | Payload Drop | Robu MG90S 9g Metal Gear Servo Motors | MG90S metal-gear micro servos (2.2 kg-cm torque) | 5 | 5 | 0 | 10 | 13.4 | 67 | ₹189 | ₹1,890 | Robu | [Link](https://robu.in/product/mg90s-9g-servo-metal-gear/) | Ordered |
| 29 | Payload Drop | PCA9685 16-Channel PWM Servo Controller | I2C 12-bit PWM servo expansion driver | 1 | 1 | 0 | 2 | 9 | 9 | ₹249 | ₹498 | Robu | [Link](https://robu.in/product/pca9685-16-channel-12-bit-pwm-servo-driver-i2c-interface/) | Verified |
| 30 | Payload Drop | Carbon Fiber Release Latches & Horns | 3mm solid carbon pins with metal horns | 1 | 1 | 0 | 2 | 40 | 40 | ₹369 | ₹738 | Robu | [Link](https://robu.in/product/carbon-fiber-rod-3mm/) | Verified |
| 31 | Payload | Humanitarian Relief Canisters | 5x 200g cylindrical emergency medical/survival kits | 5 | 5 | 0 | 10 | 200 | 1000 | ₹0 | ₹0 | Organizers | — | Supplied |
| 32 | GCS | Ground Control Station Laptop | Ubuntu 24.04 LTS, QGroundControl, ROS 2 Jazzy | 0 | 0 | 1 | 1 | 0 | 0 | ₹0 | ₹0 | Team-owned | — | Verified |
| 33 | GCS | Ground ALFA AWUS036ACM Mesh Node | MT7612U Wi-Fi adapter with directional antenna | 0 | 0 | 1 | 1 | 0 | 0 | ₹5,000 | ₹5,000 | Amazon | [Link](https://www.amazon.in/dp/B073X6RL9D) | Verified |
| 34 | GCS | RadioMaster Pocket ELRS 2.4GHz Transmitter | Safety pilot manual override transmitter with EdgeTX | 0 | 0 | 2 | 2 | 0 | 0 | ₹8,999 | ₹17,998 | Robu | [Link](https://robu.in/product/radiomaster-pocket-radio-controller-m2-elrs/) | Verified |
| 35 | Spares | Field Spares (MG90S Servo & Propellers) | 1x MG90S servo + 1x CW prop + 1x CCW prop | 0 | 0 | 1 | 1 | 0 | 0 | ₹3,500 | ₹3,500 | Robu | [Link](https://robu.in/product/mg90s-9g-servo-metal-gear/) | Verified |
