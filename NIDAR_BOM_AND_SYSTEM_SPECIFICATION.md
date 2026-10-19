# NIDAR RescueSwarm — Master Bill of Materials (BOM) & System Specification

**Official Competition & Engineering Procurement Document**

- **Project:** NIDAR Autonomous Multi-UAV Search & Rescue Swarm
- **Airframe Architecture:** Rev-B Heavy-Lift In-House Custom Carbon Fiber Quadcopter (850 mm Wheelbase)
- **Airframe Rule Compliance:** 100% In-House Custom-Designed & Fabricated (Zero COTS commercial market frames)
- **Fleet Configuration:** 2-Drone Autonomous Coordinated Search & Precision Humanitarian Delivery Swarm
- **Payload Delivery Architecture:** Dual-Action Mechanism: 5-Slot Underslung Magazine Rack + Motorized Parallel Pick-up/Drop Claw
- **Payload Provision:** 10x 200g cylindrical humanitarian aid kits (5 per drone, organizer-supplied on-site at ₹0 procurement cost)
- **Swarm Communications:** 100% Standalone Off-Grid Private Tactical Mesh Network (802.11s Wi-Fi 6 mesh + SiK 433 MHz telemetry + ELRS 2.4 GHz safety override)
- **Aircraft Mass:** Single Drone Dry Mass: **5,412.0 g (5.412 kg)** | Single Drone Loaded AUW (incl. 5 kits): **6,412.0 g (6.412 kg)**
- **Fleet AUW:** 2-Drone Fleet Total AUW: **12,824.0 g (12.824 kg)** — strictly within the 25.0 kg competition limit (48.7% margin)
- **Financial Budget:** Grand Total (All Components, Spares, Tools & Ground Equipment): **₹6,43,503 INR** (Core Buy Now: **₹6,03,659 INR** | Buy Later Spares: **₹39,844 INR**)

---

## Complete 75-Item Master Bill of Materials Schedule

| # | Category | Priority | Item Description | Model / Specification | Purpose / Usage | Qty D1 | Qty D2 | Qty Ground | Total Qty | Unit Wt (g) | Wt on D1 (g) | Unit Price (₹) | Line Total (₹) | Supplier |
| :---: | :--- | :---: | :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| 1 | A. Airframe (in-house, no COTS frame) | Core | Carbon fibre plate 500x500x3 mm | 3K twill CF sheet, 3 mm (500 x 500 mm) | Cut into top + bottom centre plates, avionics deck and battery tray (one sheet per drone) | 1 | 1 | 0 | 2 | 360 | 360 | ₹15,000 | ₹30,000 | ThinkRobotics |
| 2 | A. Airframe (in-house, no COTS frame) | Core | Carbon fibre tube 25x21x500 mm | Pro-Range glossy 3K roll-wrapped CF tube | Four motor arms, cut to ~330 mm for 850 mm wheelbase | 4 | 4 | 0 | 8 | 76 | 304 | ₹1,517 | ₹12,136 | Robu |
| 3 | A. Airframe (in-house, no COTS frame) | Core | Z25 CNC folding arm joint | Aluminium tube joint for 25 mm tube | Clamps each arm to centre plates and folds arms for transport | 4 | 4 | 0 | 8 | 45 | 180 | ₹1,539 | ₹12,312 | Robu |
| 4 | A. Airframe (in-house, no COTS frame) | Core | Tarot 25 mm motor mount TL9603 | CNC motor mount for 25 mm tube | Holds MN5008 motor at arm tip | 4 | 4 | 0 | 8 | 30 | 120 | ₹1,119 | ₹8,952 | Robu |
| 5 | A. Airframe (in-house, no COTS frame) | Core | Carbon fibre tube 16x14x1000 mm | 3K roll-wrapped CF tube | Landing gear legs and skids (~200 mm ground clearance) | 2 | 2 | 0 | 4 | 73 | 146 | ₹1,259 | ₹5,036 | Robu |
| 6 | A. Airframe (in-house, no COTS frame) | Core | PETG filament 1 kg | Anycubic PETG 1.75 mm, black | Prints canopy, landing gear T-joints, camera/GPS/speaker mounts and the 5-slot drop rack | 1 | 1 | 0 | 2 | 160 | 160 | ₹949 | ₹1,898 | Robocraze |
| 7 | A. Airframe (in-house, no COTS frame) | Core | Anti-vibration damper balls set | Glass-fibre anti-vibration plate with damper balls | Isolates flight controller and companion computer from motor vibration | 1 | 1 | 0 | 2 | 10 | 10 | ₹153 | ₹306 | Robu |
| 8 | A. Airframe (in-house, no COTS frame) | Core | Fastener kit | EasyMech M3 x 15 mm bolt + nut + washer set, 20 pcs (buy 4 sets per drone; add M3x10/M3x25 as needed) | Assembles plates, arms, mounts and gear | 4 | 4 | 0 | 8 | 17.5 | 70 | ₹78 | ₹624 | Robu |
| 9 | A. Airframe (in-house, no COTS frame) | Core | Battery strap 30 cm | 30 cm reusable LiPo strap (2 per drone) | Locks the 2 kg battery to the tray | 2 | 2 | 0 | 4 | 15 | 30 | ₹61 | ₹244 | Robu |
| 10 | B. Propulsion | Core | T-Motor Antigravity MN5008 KV340 | 6S, 135 g, 4.2 kgf max with P18x6.1 | Lift motors (replaces MN4014 KV330 from old BOM: more thrust and cheaper at Robu) | 4 | 4 | 0 | 8 | 135 | 540 | ₹10,429 | ₹83,432 | Robu |
| 11 | B. Propulsion | Core | Hobbywing XRotor 40A ESC | 40 A, 2-6S, multirotor | Motor speed controller (one per motor) | 4 | 4 | 0 | 8 | 40 | 160 | ₹2,349 | ₹18,792 | Robu |
| 12 | B. Propulsion | Core | T-Motor P18x6.1 propellers — qty in PAIRS (1 pair = 2 props) | 18 inch CF, CW + CCW | Propellers the MN5008 thrust data was measured with | 2 | 2 | 0 | 4 | 60 | 120 | ₹8,269 | ₹33,076 | Robu |
| 13 | C. Flight control & navigation | Core | Holybro Pixhawk 6C Mini flight controller | STM32H7 FC with cable set, buzzer and safety switch | Autopilot running PX4 (project firmware) | 1 | 1 | 0 | 2 | 42 | 42 | ₹22,049 | ₹44,098 | Robocraze |
| 14 | C. Flight control & navigation | Core | Folding GPS stand | Universal folding GPS mast | Lifts GPS/compass away from power wiring | 1 | 1 | 0 | 2 | 25 | 25 | ₹289 | ₹578 | Robu |
| 15 | C. Flight control & navigation | Core | Benewake TFmini Plus LiDAR | 0.1-12 m, 100 Hz, IP65 | Measures height above ground for the 5 m kit drop and landing | 1 | 1 | 0 | 2 | 12 | 12 | ₹5,326 | ₹10,652 | Robu |
| 16 | C. Flight control & navigation | Core | Holybro SiK Telemetry Radio V3 100 mW 433 MHz | Air + ground radio set | MAVLink telemetry between each drone and the single GCS (NIDAR requires one control station) | 1 | 1 | 0 | 2 | 25 | 25 | ₹9,446 | ₹18,892 | Robocraze |
| 17 | C. Flight control & navigation | Core | RadioMaster RP3 V2 ELRS 2.4 GHz receiver | ExpressLRS nano receiver | Safety pilot manual override link (2.4 GHz is licence-free in India) | 1 | 1 | 0 | 2 | 3 | 3 | ₹3,109 | ₹6,218 | Robu |
| 18 | D. Power system | Core | Tattu Plus 16000 mAh 6S 25C LiPo | 22.2 V, 355 Wh, XT90-S | Flight battery (one per drone; spare listed in section K) | 1 | 1 | 0 | 2 | 2063 | 2063 | ₹20,549 | ₹41,098 | Robu |
| 19 | D. Power system | Core | Power distribution board 3S-6S with BEC | SwiftWing PDB-6S, 120 A total, 5 V 3 A + 12 V 3 A outputs | Splits battery power to the 4 ESCs after the power module | 1 | 1 | 0 | 2 | 30 | 30 | ₹1,900 | ₹3,800 | Robu |
| 20 | D. Power system | Core | UBEC 5 V 5 A | 5.5-35 V in (2S-8S), 5 A continuous | Clean 5 V rail for the drop servos | 1 | 1 | 0 | 2 | 15 | 15 | ₹409 | ₹818 | Robu |
| 21 | D. Power system | Core | Synchronous step-down module 48V to 19V | Adjustable buck, set to 19 V | Powers the Jetson Orin Nano Super from the 6S battery | 1 | 1 | 0 | 2 | 30 | 30 | ₹399 | ₹798 | Robu |
| 22 | D. Power system | Core | Amass XT90-S anti-spark connector | XT90S female/male | Battery connector on the drone side (battery already has the male plug) | 1 | 1 | 0 | 2 | 10 | 10 | ₹159 | ₹318 | Robu |
| 23 | D. Power system | Core | 10 AWG silicone wire (red / black) | High-flex silicone wire | Main battery leads to power module and PDB | 2 | 2 | 0 | 4 | 25 | 50 | ₹172 | ₹688 | Robu |
| 24 | D. Power system | Core | Wiring consumables | 12 AWG silicone wire 10 m, black (motor leads) + heat-shrink kit 530 pcs; JST-GH leads come with the Pixhawk | Motor, signal and sensor wiring | 1 | 1 | 0 | 2 | 80 | 80 | ₹149 | ₹298 | Robu |
| 25 | E. AI search & video (both drones) | Core | NVIDIA Jetson Orin Nano Super Developer Kit | 8 GB, 67 TOPS, Wi-Fi card included | Runs ROS 2 + the project's YOLO person detector (CUDA) and streams live video to the GCS | 1 | 1 | 0 | 2 | 230 | 230 | ₹54,999 | ₹109,998 | Variety Infotech |
| 26 | E. AI search & video (both drones) | Core | NVMe SSD 256 GB M.2 2280 | Hikvision E3000 256 GB NVMe M.2 2280 (PCIe Gen3 x4) | Jetson OS, TensorRT engines and flight logs | 1 | 1 | 0 | 2 | 8 | 8 | ₹4,829 | ₹9,658 | Amazon India |
| 27 | E. AI search & video (both drones) | Core | Waveshare IMX477-160 12.3 MP camera | CSI camera, 160° FOV | Survivor search camera feeding /nidar/camera/image_raw | 1 | 1 | 0 | 2 | 30 | 30 | ₹8,319 | ₹16,638 | Robu |
| 28 | E. AI search & video (both drones) | Core | CSI cable 22-pin to 15-pin, 20 cm | ThinkRobotics CSI FPC cable (B), 22-pin to 15-pin, 200 mm | Connects the 15-pin IMX477 camera to the Orin Nano's 22-pin camera port | 1 | 1 | 0 | 2 | 3 | 3 | ₹150 | ₹300 | ThinkRobotics |
| 29 | G. Payload release (kit drop) | Core | 5-slot underslung drop rack | 3D printed PETG + CF base (project CAD) | Holds five 200 g survival kits (5x10x20 cm) and releases one per survivor | 1 | 1 | 0 | 2 | 140 | 140 | ₹0 | ₹0 | In-house print |
| 30 | G. Payload release (kit drop) | Core | TowerPro MG90S metal-gear servo | 2.2 kg-cm | Pulls the release pin of each slot | 5 | 5 | 0 | 10 | 13.4 | 67 | ₹125 | ₹1,250 | Robu |
| 31 | G. Payload release (kit drop) | Core | Release pins (3 mm solid carbon rod) | Pultruded CF rod 3 mm x 1000 mm, pack of 4, cut to 45 mm | Latch for each slot | 1 | 1 | 0 | 2 | 15 | 15 | ₹369 | ₹738 | Robu |
| 32 | G. Payload release (kit drop) | Core | PCA9685 16-ch PWM servo driver | I2C | Lets the companion computer fire each slot (as in project code); Pixhawk AUX outputs are the backup | 1 | 1 | 0 | 2 | 9 | 9 | ₹249 | ₹498 | Robu |
| 33 | G. Payload release (kit drop) | Core | Pro-Range DS3225 25 kg-cm servo (pick-up claw) | Metal gear digital servo, 180 degrees | Opens / closes the 3D-printed pick-up and drop claw. Claw body is printed in PETG, so no claw bracket is bought | 1 | 1 | 0 | 2 | 60 | 60 | ₹1,409 | ₹2,818 | Robu |
| 34 | G. Payload release (kit drop) | Core | Survival kit 200 g (organizer supplied) | 5x10x20 cm | Counted in all-up weight only | 5 | 5 | 0 | 10 | 200 | 1000 | ₹0 | ₹0 | NIDAR organisers |
| 35 | H. Ground control station | Core | RadioMaster Pocket ELRS radio | 2.4 GHz ELRS, EdgeTX | One safety-pilot transmitter per drone | 0 | 0 | 2 | 2 | 0 | 0 | ₹10,399 | ₹20,798 | Robu |
| 36 | H. Ground control station | Core | GCS laptop | i5/Ryzen 5, 16 GB RAM, Ubuntu 22.04 | Runs QGroundControl, ROS 2 and the project's control centre for both drones | 0 | 0 | 1 | 1 | 0 | 0 | ₹0 | ₹0 | Team-owned |
| 37 | H. Ground control station | Core | 9 ft (2.7 m) heavy-duty light stand mast | Boosty heavy-duty 9 ft light stand | Raises the ground mesh antenna and the SiK ground radio above the crowd | 0 | 0 | 1 | 1 | 0 | 0 | ₹1,500 | ₹1,500 | Amazon India |
| 38 | H. Ground control station | Core | ALFA AWUS036ACM dual-band USB Wi-Fi adapter (drone mesh node) | MT7612U chipset, AC1200, USB 3.0, 2 x 5 dBi antennas included | One per drone: forms an 802.11s mesh (Linux mt76 driver supports mesh point) so Scout and Delivery share geotags and ROS 2 topics directly, with the GCS as the third node | 1 | 1 | 0 | 2 | 70 | 70 | ₹5,000 | ₹10,000 | Amazon India |
| 39 | H. Ground control station | Core | ALFA AWUS036ACM (ground mesh node) | Same adapter as the drones | Third mesh node at the GCS laptop; replaces the outdoor access point | 0 | 0 | 1 | 1 | 0 | 0 | ₹5,000 | ₹5,000 | Amazon India |
| 40 | H. Ground control station | Core | Storite 5 m active USB 3.0 extension | USB 3.0 repeater cable | Lifts the ground mesh adapter up the mast for line of sight to both drones | 0 | 0 | 1 | 1 | 0 | 0 | ₹800 | ₹800 | Amazon India |
| 41 | H. Ground control station | Buy later | Spare ALFA AWUS036ACM |  | Mesh spare (drop or failure on a drone) | 0 | 0 | 1 | 1 | 0 | 0 | ₹5,000 | ₹5,000 | Amazon India |
| 42 | I. Charging & battery safety | Core | ISDT P20 dual-channel charger | 500 W, 2 x 20 A, 1-6S | Charges two 16 Ah packs at once (~1.5-2 h) | 0 | 0 | 1 | 1 | 0 | 0 | ₹14,109 | ₹14,109 | Robu |
| 43 | I. Charging & battery safety | Core | ISDT SP2425 power supply | 24 V 25 A, 600 W | AC mains supply for the P20 charger | 0 | 0 | 1 | 1 | 0 | 0 | ₹15,259 | ₹15,259 | Robu |
| 44 | I. Charging & battery safety | Core | LiPo fire-resistant bag (large) | 26x18x13 cm | Safe charging and transport of each pack | 0 | 0 | 3 | 3 | 0 | 0 | ₹859 | ₹2,577 | Robu |
| 45 | I. Charging & battery safety | Core | BX100 LiPo voltage checker | 1-8S with alarm | Pre-flight cell check | 0 | 0 | 2 | 2 | 0 | 0 | ₹209 | ₹418 | Robu |
| 46 | I. Charging & battery safety | Core | Fire extinguisher 2 kg ABC (ISI) | Eco Fire ABC powder 2 kg, ISI marked | Field safety at the pit / charging area | 0 | 0 | 1 | 1 | 0 | 0 | ₹1,300 | ₹1,300 | Amazon India |
| 47 | K. Spares | Buy later | Spare Tattu Plus 16000 mAh 6S | Same as D1 | Lets one drone fly while the other pack charges | 0 | 0 | 1 | 1 | 0 | 0 | ₹20,549 | ₹20,549 | Robu |
| 48 | K. Spares | Core | Spare propeller pair P18x6.1 (2 props) |  | Prop strikes in testing | 0 | 0 | 1 | 1 | 0 | 0 | ₹8,269 | ₹8,269 | Robu |
| 49 | K. Spares | Buy later | Spare MN5008 KV340 motor |  | Crash spare | 0 | 0 | 1 | 1 | 0 | 0 | ₹10,429 | ₹10,429 | Robu |
| 50 | K. Spares | Buy later | Spare XRotor 40A ESC |  | Crash spare | 0 | 0 | 1 | 1 | 0 | 0 | ₹2,349 | ₹2,349 | Robu |
| 51 | K. Spares | Core | Spare ELRS receiver | RP3 V2 | Spare RC link | 0 | 0 | 1 | 1 | 0 | 0 | ₹3,109 | ₹3,109 | Robu |
| 52 | K. Spares | Core | Spare MG90S servos |  | Drop-rack spares | 0 | 0 | 3 | 3 | 0 | 0 | ₹125 | ₹375 | Robu |
| 53 | K. Spares | Buy later | Spare CF arm tube 25 mm |  | Arm replacement | 0 | 0 | 1 | 1 | 0 | 0 | ₹1,517 | ₹1,517 | Robu |
| 54 | L. Tools & services | Core | CNC / waterjet cutting of CF plates | Per drone set, from project DXF/STL | Cuts the centre plates, deck and tray | 0 | 0 | 2 | 2 | 0 | 0 | ₹2,500 | ₹5,000 | Local CNC shop |
| 55 | L. Tools & services | Core | Yihua 927-IV 60 W soldering station |  | XT90, motor and ESC soldering | 0 | 0 | 1 | 1 | 0 | 0 | ₹3,899 | ₹3,899 | Robu |
| 56 | L. Tools & services | Core | Digital multimeter | UNI-T UT33D+ pocket multimeter | Wiring and BEC voltage checks | 0 | 0 | 1 | 1 | 0 | 0 | ₹935 | ₹935 | Robu |
| 57 | L. Tools & services | Core | Hex driver set + JST/XT crimp tool | Taparia KM9V Allen key set 1.5-10 mm 239 rupees + 1800-pc crimp terminal kit with pliers 1,559 rupees | Assembly and harness making | 0 | 0 | 1 | 1 | 0 | 0 | ₹1,798 | ₹1,798 | Robu |
| 58 | L. Tools & services | Core | Heat gun | Stanley SXH1800-IN 1800 W 2-speed | Heat shrink on power joints | 0 | 0 | 1 | 1 | 0 | 0 | ₹1,999 | ₹1,999 | Robu |
| 59 | L. Tools & services | Core | Hanging scale 50 kg + prop balancer | Destinio hanging scale 50 kg 798 rupees + universal prop balancer 490 rupees | Verify all-up weight and balance props | 0 | 0 | 1 | 1 | 0 | 0 | ₹1,288 | ₹1,288 | Amazon |
| 60 | L. Tools & services | Core | Nylon hex spacer M3 x 20 mm, male-female, 10 pcs | M3 x 20 mm nylon standoffs | Spaces the carbon plates / avionics deck; isolates electronics | 1 | 1 | 0 | 2 | 7 | 7 | ₹79 | ₹158 | Robu |
| 61 | L. Tools & services | Core | M3 x 30 mm socket bolt + nut set, 12 pcs | EasyMech M3 x 30 mm | Longer bolts through plates and spacers | 1 | 1 | 0 | 2 | 30 | 30 | ₹179 | ₹358 | Robu |
| 62 | L. Tools & services | Core | M3 x 16 mm SS socket bolt, 25 pcs | EasyMech SS304 M3 x 16 mm | Mounts for Jetson, Pixhawk, PDB, BEC and camera | 1 | 1 | 0 | 2 | 25 | 25 | ₹70 | ₹140 | Robu |
| 63 | L. Tools & services | Core | M3 nylon-insert (nyloc) nut, 25 pcs | EasyMech M3 MS nyloc nut | Vibration-proof nuts for the M3 bolts | 1 | 1 | 0 | 2 | 10 | 10 | ₹78 | ₹156 | Robu |
| 64 | L. Tools & services | Core | Dupont jumper wires female-female 20 cm, 40 pcs | ACEBOTT 40-pin F-F | Jetson UART to Pixhawk TELEM2, I2C to PCA9685, servo signal links | 1 | 1 | 0 | 2 | 12 | 12 | ₹175 | ₹350 | Robu |
| 65 | L. Tools & services | Core | Nylon cable ties 200 mm, 100 pcs | White nylon zip ties | Wire management on both drones | 0 | 0 | 1 | 1 | 8 | 8 | ₹72 | ₹72 | Robu |
| 66 | L. Tools & services | Core | Reusable reverse-velcro ties 20 x 220 mm | Silicone reusable ties | Holds the camera cable and Jetson wiring, removable | 1 | 1 | 0 | 2 | 15 | 15 | ₹99 | ₹198 | Robu |
| 67 | L. Tools & services | Core | Double-sided heavy-duty tape 20 mm x 3 m | AmiciTools weatherproof tape | Sticks BEC, PDB and lidar to the plates | 0 | 0 | 1 | 1 | 10 | 10 | ₹499 | ₹499 | Robu |
| 68 | L. Tools & services | Core | Solder wire 0.8 mm, 50 g | Lead-based 0.8 mm | Solders XT90, ESC and motor wires, PDB | 0 | 0 | 1 | 1 | 10 | 10 | ₹289 | ₹289 | Robu |
| 69 | L. Tools & services | Core | USB Type-C cable 1 m | ACEBOTT-style white Type-C cable | Pixhawk 6C Mini setup and logs from the laptop | 0 | 0 | 1 | 1 | 0 | 0 | ₹51 | ₹51 | Robu |
| 70 | L. Tools & services | Core | Wireless keyboard + mouse combo | Logitech MK275 USB wireless | Jetson first-time setup (JetPack, camera enable) | 0 | 0 | 1 | 1 | 0 | 0 | ₹2,199 | ₹2,199 | Robu |
| 71 | L. Tools & services | Core | Measuring tape 5 m | Stanley STHT36127-812 | Marks the 12 ft x 12 ft launch / landing area | 0 | 0 | 1 | 1 | 0 | 0 | ₹179 | ₹179 | Robu |
| 72 | L. Tools & services | Core | Jetson 19 V DC barrel plug lead | Cut the plug off the AC adapter that comes in the Jetson kit | Connects the 48V-to-19V buck module to the Jetson DC jack | 1 | 1 | 0 | 2 | 10 | 10 | ₹0 | ₹0 | From Jetson kit |
| 73 | L. Tools & services | Core | Wire stripper + cutter 130 mm | Stanley 130 mm wire stripper / cutter | Strips and cuts silicone wire for the harness and power leads | 0 | 0 | 1 | 1 | 0 | 0 | ₹369 | ₹369 | Robu |
| 74 | L. Tools & services | Core | Needle-nose pliers, long mini | Taparia 1408 long needle-nose mini plier | Holds small parts and wire when assembling and soldering | 0 | 0 | 1 | 1 | 0 | 0 | ₹190 | ₹190 | Robu |
| 75 | L. Tools & services | Core | Soldering flux paste 10 g | Noel flux paste | Cleaner solder joints on XT90, ESC and motor wires | 0 | 0 | 1 | 1 | 0 | 0 | ₹20 | ₹20 | Robu |

---

## Budget Summary

| Category / Subsystem | Total Fleet Cost (INR ₹) | Status |
| :--- | :---: | :---: |
| **Core Fleet & Mission Equipment (Buy Now)** | **₹6,03,659** | Essential |
| **Extra Mission Spares & Standby Units (Buy Later)** | **₹39,844** | Contingency |
| **GRAND TOTAL — ALL 75 COMPONENTS** | **₹6,43,503** | **Official Baseline** |

