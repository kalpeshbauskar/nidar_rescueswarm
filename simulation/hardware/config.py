"""Authoritative Hardware Configuration and Single Source of Truth for NIDAR RescueSwarm.

All component masses, motor thrust curves, ESC ratings, battery parameters,
electrical limits, network topology, and payload distributions are defined here.
No constants should be duplicated in other simulation modules.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Tuple


class DataSource(Enum):
    DATASHEET = "DATASHEET"
    SIMULATION_DERIVED = "SIMULATION_DERIVED"
    ESTIMATE = "ESTIMATE"
    NEEDS_PHYSICAL_MEASUREMENT = "NEEDS_PHYSICAL_MEASUREMENT"


@dataclass(frozen=True)
class ComponentSpec:
    name: str
    mass_kg: float
    source: DataSource
    description: str


# ============================================================================
# COMPONENT-LEVEL MASS MODEL (BOM) PER DRONE
# ============================================================================

HARDWARE_BOM: Dict[str, ComponentSpec] = {
    "frame": ComponentSpec(
        name="Rev-B XL Heavy-Lift Quadcopter CF Frame (1,050mm)",
        mass_kg=0.936,
        source=DataSource.ESTIMATE,
        description="1,050mm diagonal frame for 23in props: 500x500x3 CF plates (0.360), 4x 25x21mm arms cut to 430mm (0.396), 4x Z25 folding joints (0.180)",
    ),
    "landing_gear": ComponentSpec(
        name="Carbon Fiber Landing Gear (780mm track)",
        mass_kg=0.146,
        source=DataSource.ESTIMATE,
        description="2x 16x14x1000mm CF tubes cut into legs and skids",
    ),
    "printed_parts": ComponentSpec(
        name="PETG Printed Parts",
        mass_kg=0.160,
        source=DataSource.ESTIMATE,
        description="Canopy, landing gear T-joints, camera/GPS mounts",
    ),
    "motors": ComponentSpec(
        name="4x T-Motor A6-M KV280 + integrated 6S FOC ESC",
        mass_kg=1.320,
        source=DataSource.ESTIMATE,
        description="A6-M-6S modular kit is 390g per arm incl. prop (datasheet); 330g motor+ESC+clamp, 60g prop. Mounts directly on 25mm tube (no Tarot mount)",
    ),
    "propellers": ComponentSpec(
        name="4x T-Motor MF2311P-M 23in Folding Propellers",
        mass_kg=0.240,
        source=DataSource.ESTIMATE,
        description="2x CW and 2x CCW 23x11 folding polymer props (585mm), ~60g each incl. holder",
    ),
    "pixhawk": ComponentSpec(
        name="Pixhawk 6C Pro (FMUv6C) Kit",
        mass_kg=0.077,
        source=DataSource.ESTIMATE,
        description="Full-size FMUv6C flight controller with OLED, RGB LED, I2C splitter and PWM modules (ThinkRobotics kit)",
    ),
    "power_module": ComponentSpec(
        name="PM02 Power Module (12S)",
        mass_kg=0.026,
        source=DataSource.ESTIMATE,
        description="Analog voltage/current sense + 5.2V supply to the flight controller (in Pixhawk kit)",
    ),
    "gps": ComponentSpec(
        name="M9N GNSS + Compass with Folding Stand",
        mass_kg=0.057,
        source=DataSource.ESTIMATE,
        description="u-blox M9N GPS (0.032) + folding mast (0.025), in Pixhawk kit",
    ),
    "telemetry_radio": ComponentSpec(
        name="Radio Telemetry V6 433 MHz 100 mW",
        mass_kg=0.025,
        source=DataSource.ESTIMATE,
        description="SiK-class MAVLink telemetry air unit (in Pixhawk kit)",
    ),
    "rc_receiver": ComponentSpec(
        name="RadioMaster RP3 V2 ELRS Receiver",
        mass_kg=0.003,
        source=DataSource.DATASHEET,
        description="2.4 GHz safety-pilot override receiver",
    ),
    "lidar": ComponentSpec(
        name="Benewake TFmini Plus LiDAR",
        mass_kg=0.012,
        source=DataSource.DATASHEET,
        description="0.1-12m height-above-ground sensor for the 5m drop and landing",
    ),
    "pdb": ComponentSpec(
        name="Holybro PDB 300A",
        mass_kg=0.229,
        source=DataSource.DATASHEET,
        description="300A power distribution board sized for the A6-M 4x40A peak current",
    ),
    "dcdc_converters": ComponentSpec(
        name="2x XL4016 8A Buck Converters",
        mass_kg=0.055,
        source=DataSource.ESTIMATE,
        description="Jetson supply (0.040) and 6.8V DS3225 servo rail (0.015)",
    ),
    "jetson_orin_nano": ComponentSpec(
        name="NVIDIA Jetson Orin Nano Super Developer Kit",
        mass_kg=0.230,
        source=DataSource.ESTIMATE,
        description="Companion computer module, carrier board, heatsink and fan",
    ),
    "storage": ComponentSpec(
        name="NVMe SSD 256 GB",
        mass_kg=0.008,
        source=DataSource.ESTIMATE,
        description="Jetson OS, TensorRT engines and flight logs",
    ),
    "camera": ComponentSpec(
        name="Arducam IMX477 HQ IR-CUT Camera, 6mm CS Lens",
        mass_kg=0.083,
        source=DataSource.ESTIMATE,
        description="12.3MP search camera with CS lens and CSI cable",
    ),
    "wifi_hardware": ComponentSpec(
        name="ALFA AWUS036ACM USB Wi-Fi Adapter",
        mass_kg=0.070,
        source=DataSource.ESTIMATE,
        description="MT7612U 802.11s mesh node with 2x 5dBi antennas",
    ),
    "payload_drop_rack_4slot": ComponentSpec(
        name="5-Slot Drop Rack with DS3225 Servos",
        mass_kg=0.529,
        source=DataSource.NEEDS_PHYSICAL_MEASUREMENT,
        description="PETG/CF rack (0.180), 5x DS3225 servos (0.300), 5x metal horns (0.025), CF release pins (0.015), PCA9685 (0.009)",
    ),
    "payload_drop_rack_5slot": ComponentSpec(
        name="5-Slot Drop Rack with DS3225 Servos",
        mass_kg=0.529,
        source=DataSource.NEEDS_PHYSICAL_MEASUREMENT,
        description="PETG/CF rack (0.180), 5x DS3225 servos (0.300), 5x metal horns (0.025), CF release pins (0.015), PCA9685 (0.009)",
    ),
    "payload_drop_rack_2slot": ComponentSpec(
        name="2-Slot Mechanical Release Rack",
        mass_kg=0.180,
        source=DataSource.NEEDS_PHYSICAL_MEASUREMENT,
        description="Compact 2-bay package release rack for Drone 3",
    ),
    "wiring": ComponentSpec(
        name="Power & Signal Wiring Harness",
        mass_kg=0.222,
        source=DataSource.NEEDS_PHYSICAL_MEASUREMENT,
        description="XT90-S, 10 AWG battery leads, 12 AWG leads to the arm-tip ESCs, heat shrink, Dupont/JST signal leads, Jetson DC lead",
    ),
    "fasteners": ComponentSpec(
        name="Screws, Standoffs, Straps & Mounting Hardware",
        mass_kg=0.225,
        source=DataSource.ESTIMATE,
        description="M3 bolts/nuts/standoffs, damper set, battery straps, ties, velcro, tape, solder",
    ),
    "battery": ComponentSpec(
        name="Tattu 22,000 mAh 6S 25C LiPo",
        mass_kg=2.490,
        source=DataSource.DATASHEET,
        description="22.2V 488Wh 6S1P pack with XT90-S, 200x91x64mm",
    ),
}


# ============================================================================
# PROPULSION MODEL (T-Motor A6-M-6S KV280 + MF2311P-M 23in prop on 6S 22.2V)
# ============================================================================
# T-Motor publishes only three points: max thrust 6.0 kgf, rated thrust 2-2.5 kgf,
# and 10 g/W at 2.3 kgf. The curve below is SIMULATION_DERIVED from those points:
# thrust = 6.0 * throttle^2 and power = 65.94 * thrust^1.5 (momentum-theory scaling
# anchored at 230 W for 2.3 kgf). Replace with bench data once a kit is measured.
# Columns: Throttle fraction [0..1], Thrust per motor (kgf), Current per motor (A), Power (W)
MOTOR_TEST_DATA: List[Tuple[float, float, float, float]] = [
    # (throttle, thrust_kgf, current_a, power_w)
    (0.35, 0.735, 1.9, 41.5),
    (0.40, 0.960, 2.8, 62.0),
    (0.50, 1.500, 5.5, 121.1),
    (0.60, 2.160, 9.4, 209.3),
    (0.65, 2.535, 12.0, 266.1),
    (0.70, 2.940, 15.0, 332.4),
    (0.75, 3.375, 18.4, 408.8),
    (0.80, 3.840, 22.4, 496.2),
    (0.85, 4.335, 26.8, 595.1),
    (0.90, 4.860, 31.8, 706.5),
    (1.00, 6.000, 43.7, 969.1),
]

# Physical propulsion limits per drone (4 motors)
MOTORS_PER_DRONE: int = 4
MAX_THRUST_PER_MOTOR_KGF: float = 6.000  # DATASHEET
MAX_CURRENT_PER_MOTOR_A: float = 43.7    # SIMULATION_DERIVED (100% throttle on the curve above)
MAX_TOTAL_THRUST_KGF: float = MOTORS_PER_DRONE * MAX_THRUST_PER_MOTOR_KGF  # 24.0 kgf (~235.4 N)
MAX_PROPULSION_CURRENT_A: float = MOTORS_PER_DRONE * MAX_CURRENT_PER_MOTOR_A  # 174.8 A
MIN_TW_RATIO_REQUIRED: float = 1.50      # Validation threshold


# ============================================================================
# ELECTRICAL & POWER SYSTEM SPECIFICATIONS
# ============================================================================

@dataclass(frozen=True)
class ElectricalLimits:
    esc_continuous_current_a: float = 40.0   # DATASHEET: A6-M FOC ESC 40A short-time peak (hover is ~9A)
    esc_burst_current_a: float = 50.0        # DATASHEET: A6-M 6S FOC 50A ESC
    pdb_continuous_current_a: float = 300.0  # DATASHEET: Holybro PDB 300A
    connector_continuous_a: float = 90.0     # DATASHEET: XT90-S 90A cont / 120A peak
    main_wire_10awg_rating_a: float = 140.0  # DATASHEET: 10 AWG silicone <30cm
    motor_wire_16awg_rating_a: float = 35.0  # DATASHEET: 16 AWG silicone chassis
    avionics_power_nominal_w: float = 30.5   # Jetson+SSD+Wi-Fi+camera (25.6W via buck) + Pixhawk+GPS+radios+LiDAR (4.3W via PM02) + servos (0.6W)
    nominal_voltage_v: float = 22.2          # 6S LiPo nominal voltage


ELECTRICAL_LIMITS = ElectricalLimits()


# ============================================================================
# BATTERY SPECIFICATIONS (Tattu 6S LiPo 22,000 mAh)
# ============================================================================

@dataclass(frozen=True)
class BatterySpecs:
    nominal_voltage_v: float = 22.2          # DATASHEET
    capacity_mah: float = 22000.0            # DATASHEET
    capacity_ah: float = 22.0
    nominal_energy_wh: float = 488.4         # 22.2V * 22.0Ah
    usable_fraction: float = 0.80            # 80% usable energy
    reserve_fraction: float = 0.20           # 20% hard reserve
    usable_energy_wh: float = 390.72         # 0.80 * 488.4 Wh
    reserve_energy_wh: float = 97.68         # 0.20 * 488.4 Wh
    max_continuous_discharge_c: float = 25.0 # DATASHEET: 25C continuous (550 A)
    battery_mass_kg: float = 2.490           # DATASHEET: ~2.49 kg


BATTERY_SPECS = BatterySpecs()


# ============================================================================
# FLEET, PAYLOAD & MISSION CONSTRAINTS
# ============================================================================

FLEET_SIZE: int = 2
TOTAL_PACKAGES: int = 10
PACKAGE_MASS_KG: float = 0.200               # 200 grams each
PAYLOAD_ALLOCATION: Tuple[int, ...] = (5, 5)     # Drone 1 = 5, Drone 2 = 5
TOTAL_PAYLOAD_MASS_KG: float = TOTAL_PACKAGES * PACKAGE_MASS_KG  # 2.000 kg

MAX_FLEET_AUW_KG: float = 25.0               # Maximum combined fleet AUW
MAX_MISSION_TIME_SEC: float = 30 * 60.0      # 30 minutes MAXIMUM mission duration (1800 s)


# ============================================================================
# PRIVATE LOCAL NETWORK SPECIFICATIONS (Offline, Zero Internet)
# ============================================================================

@dataclass(frozen=True)
class NetworkTopology:
    subnet: str = "10.42.0.0/24"
    gcs_ip: str = "10.42.0.1"
    drone_ips: Dict[int, str] = field(
        default_factory=lambda: {
            1: "10.42.0.11",
            2: "10.42.0.12",
            3: "10.42.0.13",
        }
    )
    rfd_frequency_mhz: float = 868.0
    rfd_mode: str = "Point-to-Multipoint TDMA"
    wifi_band: str = "5 GHz 802.11ac/ax Private Local WPA3 LAN"
    internet_required: bool = False
    lte_gsm_5g_required: bool = False
    cloud_required: bool = False


NETWORK_SPECS = NetworkTopology()


# ============================================================================
# HELPER FUNCTIONS TO ACCESS BOM MASSES
# ============================================================================

def get_drone_dry_mass_kg(drone_id: int) -> float:
    """Compute dry mass (including battery, zero payload) for a specific drone."""
    total = 0.0
    for key, item in HARDWARE_BOM.items():
        if key == "payload_drop_rack_5slot":
            continue  # Alias for payload_drop_rack_4slot to avoid double counting
        elif key == "payload_drop_rack_4slot":
            if drone_id in (0, 1):  # Drone 1 and Drone 2 carry 5-slot racks
                total += item.mass_kg
        elif key == "payload_drop_rack_2slot":
            if drone_id == 2:       # Drone 3 carries 2-slot rack
                total += item.mass_kg
        else:
            total += item.mass_kg
    return round(total, 4)


def get_drone_initial_auw_kg(drone_id: int) -> float:
    """Compute initial AUW with all designated packages onboard."""
    dry_mass = get_drone_dry_mass_kg(drone_id)
    packages_count = PAYLOAD_ALLOCATION[drone_id]
    payload_mass = packages_count * PACKAGE_MASS_KG
    return round(dry_mass + payload_mass, 4)


def get_fleet_initial_auw_kg() -> float:
    """Compute total combined fleet AUW across all drones."""
    return sum(get_drone_initial_auw_kg(i) for i in range(FLEET_SIZE))
