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
# COMPONENT-LEVEL MASS MODEL (BOM) PER DRONE - FINAL ORDERED BOM
# ============================================================================

HARDWARE_BOM: Dict[str, ComponentSpec] = {
    "frame": ComponentSpec(
        name="Zenith Unmanned Systems Heavy-Lift CF Frame (22-Inch Props)",
        mass_kg=0.936,
        source=DataSource.DATASHEET,
        description="Heavy-lift quadcopter frame designed for 22in props with 25mm carbon fiber arms (Zenith Unmanned Systems)",
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
        description="Canopy, landing gear T-joints, camera/RTK mounts",
    ),
    "motors": ComponentSpec(
        name="4x Hobbywing X6-SE 280KV + integrated 6S FOC ESC",
        mass_kg=1.228,
        source=DataSource.DATASHEET,
        description="Hobbywing X6-SE 280KV motor with built-in 30A/60A FOC ESC (307g per motor+ESC without prop, Aerokart CW/CCW combo)",
    ),
    "propellers": ComponentSpec(
        name="4x Hobbywing 2270 (22x7.0in) Folding Propellers",
        mass_kg=0.264,
        source=DataSource.DATASHEET,
        description="2x CW and 2x CCW 22x7.0 folding carbon-polymer propellers (66g each, Aerokart X6-SE combo)",
    ),
    "pixhawk": ComponentSpec(
        name="Think Robotics Pixhawk 6C Pro Kit",
        mass_kg=0.077,
        source=DataSource.DATASHEET,
        description="Pixhawk 6C Pro flight controller kit with damping base, safety switch, buzzer, and cables (Think Robotics)",
    ),
    "power_module": ComponentSpec(
        name="PM02 Power Module (12S)",
        mass_kg=0.026,
        source=DataSource.DATASHEET,
        description="Analog voltage/current sense + 5.2V supply to the flight controller (Think Robotics Pixhawk kit)",
    ),
    "rtk_gnss_rover": ComponentSpec(
        name="GenX Ublox ZED-F9P RTK GNSS Receiver + Helix Antenna",
        mass_kg=0.041,
        source=DataSource.DATASHEET,
        description="Multi-band L1+L2+L5 RTK GNSS receiver (20g) + GENX LH-105A2-B high-gain helix antenna with MMCX-SMA cable (41g total, RoboKits India)",
    ),
    "can_hub": ComponentSpec(
        name="Holybro CAN Hub",
        mass_kg=0.018,
        source=DataSource.DATASHEET,
        description="Holybro CAN Hub for UAVCAN / Cyphal bus distribution and I2C/UART interconnects (Zbotic)",
    ),
    "telemetry_radio": ComponentSpec(
        name="Radio Telemetry V6 433 MHz 100 mW",
        mass_kg=0.025,
        source=DataSource.DATASHEET,
        description="SiK-class 433 MHz MAVLink telemetry air unit (Think Robotics Pixhawk kit)",
    ),
    "rc_receiver": ComponentSpec(
        name="RadioMaster RP3 V2 ELRS Receiver",
        mass_kg=0.003,
        source=DataSource.DATASHEET,
        description="2.4 GHz ExpressLRS safety-pilot override receiver",
    ),
    "pdb": ComponentSpec(
        name="Power Distribution Board 300A",
        mass_kg=0.120,
        source=DataSource.DATASHEET,
        description="Heavy-duty 300A power distribution board with filtered battery rails",
    ),
    "dcdc_converters": ComponentSpec(
        name="2x XL4016 8A Buck Converters",
        mass_kg=0.055,
        source=DataSource.ESTIMATE,
        description="Jetson 19V supply (0.040) and 6.0V servo rail (0.015)",
    ),
    "jetson_orin_nano": ComponentSpec(
        name="NVIDIA Jetson Orin Nano Super Developer Kit",
        mass_kg=0.230,
        source=DataSource.DATASHEET,
        description="Companion computer module, carrier board, heatsink and fan",
    ),
    "storage": ComponentSpec(
        name="HIKVISION E3000 Internal NVMe PCIe M.2 SSD 256GB",
        mass_kg=0.008,
        source=DataSource.DATASHEET,
        description="Hikvision E3000 256GB NVMe SSD for Jetson OS, models, and mission logs (Amazon)",
    ),
    "camera": ComponentSpec(
        name="Arducam IMX477 HQ IR-CUT Camera, 6mm CS Lens",
        mass_kg=0.083,
        source=DataSource.DATASHEET,
        description="12.3MP 1/2.3-inch search camera with 6mm CS lens and ribbon cable (Robu)",
    ),
    "vtx": ComponentSpec(
        name="SpeedyBee TX800 5.8GHz 800mW Video Transmitter",
        mass_kg=0.006,
        source=DataSource.DATASHEET,
        description="SpeedyBee TX800 5.8GHz FPV video transmitter (5.6g) + antenna for real-time video downlink (Robu)",
    ),
    "wifi_hardware": ComponentSpec(
        name="ALFA AWUS036ACM USB Wi-Fi Adapter",
        mass_kg=0.070,
        source=DataSource.DATASHEET,
        description="MT7612U 802.11s mesh node with dual 5dBi antennas",
    ),
    "payload_drop_rack_4slot": ComponentSpec(
        name="5-Slot Drop Rack with 5x MG90S Servos",
        mass_kg=0.296,
        source=DataSource.DATASHEET,
        description="PETG/CF rack (0.180), 5x Robu MG90S 9g metal gear servos (0.067), release horns/pins (0.040), PCA9685 (0.009)",
    ),
    "payload_drop_rack_5slot": ComponentSpec(
        name="5-Slot Drop Rack with 5x MG90S Servos",
        mass_kg=0.296,
        source=DataSource.DATASHEET,
        description="PETG/CF rack (0.180), 5x Robu MG90S 9g metal gear servos (0.067), release horns/pins (0.040), PCA9685 (0.009)",
    ),
    "payload_drop_rack_2slot": ComponentSpec(
        name="2-Slot Mechanical Release Rack",
        mass_kg=0.140,
        source=DataSource.ESTIMATE,
        description="Compact 2-bay package release rack with MG90S servos for auxiliary operations",
    ),
    "wiring": ComponentSpec(
        name="Power & Signal Wiring Harness + Jetson GH MAVLink Cable",
        mass_kg=0.180,
        source=DataSource.ESTIMATE,
        description="XT90 power leads, 12 AWG arm leads, Robu GH 6-pin female MAVLink cable (300mm), signal harness",
    ),
    "fasteners": ComponentSpec(
        name="Screws, Standoffs, Straps & Mounting Hardware",
        mass_kg=0.180,
        source=DataSource.ESTIMATE,
        description="M3 bolts/nuts/standoffs, damper balls set, 30cm battery straps, velcro, zip ties",
    ),
    "battery": ComponentSpec(
        name="Revogreen 22.8V 22000mAh Solid State 6S Lithium Ion Battery XT90",
        mass_kg=1.430,
        source=DataSource.DATASHEET,
        description="Semi-solid-state pouch cells, 22.8V nominal (6S), 501.6 Wh, 110A cont / 155A peak, 170x70x70mm, XT90 (Revogreen)",
    ),
}


# ============================================================================
# PROPULSION MODEL (Hobbywing X6-SE 280KV + 2270 Propeller Combo on 6S 22.8V)
# ============================================================================
# Hobbywing X6-SE 280KV with integrated 30A/60A FOC ESC and 22x7.0 (2270) folding props.
# Max thrust: 6.00 kgf per axis (24.0 kgf total for 4 motors), recommended load 2.0-2.5 kg/axis.
# Tested efficiency: ~10.2 g/W at 1.5 - 2.5 kgf hover range at 22.8V nominal.
# Columns: Throttle fraction [0..1], Thrust per motor (kgf), Current per motor (A), Power (W)
MOTOR_TEST_DATA: List[Tuple[float, float, float, float]] = [
    # (throttle, thrust_kgf, current_a, power_w)
    (0.35, 0.735, 1.8, 41.0),
    (0.40, 0.960, 2.7, 61.5),
    (0.50, 1.500, 5.2, 118.5),
    (0.55, 1.815, 6.9, 157.3),
    (0.60, 2.160, 9.0, 205.2),
    (0.65, 2.535, 11.4, 259.9),
    (0.70, 2.940, 14.2, 323.7),
    (0.75, 3.375, 17.5, 399.0),
    (0.80, 3.840, 21.3, 485.6),
    (0.85, 4.335, 25.5, 581.4),
    (0.90, 4.860, 30.2, 688.5),
    (1.00, 6.000, 41.5, 946.2),
]

# Physical propulsion limits per drone (4 motors)
MOTORS_PER_DRONE: int = 4
MAX_THRUST_PER_MOTOR_KGF: float = 6.000  # DATASHEET: 6.0-6.2 kgf per motor
MAX_CURRENT_PER_MOTOR_A: float = 41.5    # SIMULATION_DERIVED (100% full throttle)
MAX_TOTAL_THRUST_KGF: float = MOTORS_PER_DRONE * MAX_THRUST_PER_MOTOR_KGF  # 24.0 kgf (~235.4 N)
MAX_PROPULSION_CURRENT_A: float = MOTORS_PER_DRONE * MAX_CURRENT_PER_MOTOR_A  # 166.0 A
MIN_TW_RATIO_REQUIRED: float = 1.50      # Validation threshold


# ============================================================================
# ELECTRICAL & POWER SYSTEM SPECIFICATIONS
# ============================================================================

@dataclass(frozen=True)
class ElectricalLimits:
    esc_continuous_current_a: float = 30.0   # DATASHEET: Hobbywing X6-SE integrated FOC ESC 30A cont (hover is ~7-8A)
    esc_burst_current_a: float = 60.0        # DATASHEET: Hobbywing X6-SE 60A peak burst (10s)
    pdb_continuous_current_a: float = 300.0  # DATASHEET: Heavy-duty 300A PDB
    connector_continuous_a: float = 90.0     # DATASHEET: Amass XT90 90A cont / 120A peak
    main_wire_10awg_rating_a: float = 140.0  # DATASHEET: 10 AWG silicone <30cm
    motor_wire_16awg_rating_a: float = 35.0  # DATASHEET: 16 AWG silicone chassis
    avionics_power_nominal_w: float = 30.0   # Jetson+SSD+Wi-Fi+camera (24.5W via buck) + Pixhawk+RTK+radios+VTX (5.0W via PM02) + servos (0.5W)
    nominal_voltage_v: float = 22.8          # 6S Solid-State Lithium Ion nominal voltage (6 x 3.8V)


ELECTRICAL_LIMITS = ElectricalLimits()


# ============================================================================
# BATTERY SPECIFICATIONS (Revogreen 22.8V 22,000 mAh Solid-State 6S Li-Ion)
# ============================================================================

@dataclass(frozen=True)
class BatterySpecs:
    nominal_voltage_v: float = 22.8          # DATASHEET: 22.8V (6 x 3.8V)
    max_voltage_v: float = 25.2              # DATASHEET: 25.2V (4.2V/cell)
    cutoff_voltage_v: float = 18.0           # DATASHEET: 18.0V (3.0V/cell)
    capacity_mah: float = 22000.0            # DATASHEET: 22,000 mAh
    capacity_ah: float = 22.0                # DATASHEET: 22.0 Ah
    nominal_energy_wh: float = 501.6         # 22.8V * 22.0Ah = 501.6 Wh (rated 502 Wh)
    usable_fraction: float = 0.80            # 80% usable energy
    reserve_fraction: float = 0.20           # 20% hard emergency reserve
    usable_energy_wh: float = 401.28         # 0.80 * 501.6 Wh
    reserve_energy_wh: float = 100.32        # 0.20 * 501.6 Wh
    max_continuous_discharge_c: float = 5.0  # DATASHEET: 5C continuous (110 A)
    max_peak_discharge_c: float = 7.0        # DATASHEET: 7C peak 10s (155 A)
    battery_mass_kg: float = 1.430           # DATASHEET: 1,430 g (1.430 kg)


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
