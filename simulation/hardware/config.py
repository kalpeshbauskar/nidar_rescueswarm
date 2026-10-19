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
        name="Rev-B Heavy-Lift Quadcopter CF Frame (850mm)",
        mass_kg=1.250,
        source=DataSource.ESTIMATE,
        description="850mm diagonal carbon fiber quadcopter frame (<900mm limit), central plates, 25mm arms, clamps",
    ),
    "landing_gear": ComponentSpec(
        name="Carbon Fiber Landing Gear (780mm track)",
        mass_kg=0.250,
        source=DataSource.ESTIMATE,
        description="High-clearance wide-track T-landing gear with silicone damper skids",
    ),
    "motors": ComponentSpec(
        name="4x T-Motor MN4014 KV330",
        mass_kg=0.600,
        source=DataSource.DATASHEET,
        description="4x 150g brushless outrunner motors including factory lead wires and prop adapters",
    ),
    "escs": ComponentSpec(
        name="4x 40A 6S BLHeli_32 ESCs",
        mass_kg=0.160,
        source=DataSource.DATASHEET,
        description="4x 40g ESCs with aluminium heat sinks rated 40A continuous / 50A burst",
    ),
    "propellers": ComponentSpec(
        name="4x 17x5.8 Carbon Fiber Propellers",
        mass_kg=0.120,
        source=DataSource.DATASHEET,
        description="2x CW and 2x CCW balanced 17x5.8 ultralight carbon fiber propellers (30g each)",
    ),
    "pixhawk": ComponentSpec(
        name="Holybro Pixhawk 6X Autopilot",
        mass_kg=0.110,
        source=DataSource.DATASHEET,
        description="Pixhawk 6X flight controller and standard baseboard with shock damping",
    ),
    "gps": ComponentSpec(
        name="Holybro H-RTK NEO-M9N GNSS",
        mass_kg=0.085,
        source=DataSource.DATASHEET,
        description="High-precision GNSS/compass module with carbon mast",
    ),
    "power_module_pdb": ComponentSpec(
        name="Holybro PM02D / High-Amp PDB",
        mass_kg=0.120,
        source=DataSource.DATASHEET,
        description="Hall-effect current sensor, dual 5.2V BEC, 120A continuous distribution board",
    ),
    "jetson_orin_nano": ComponentSpec(
        name="NVIDIA Jetson Orin Nano Developer Board",
        mass_kg=0.200,
        source=DataSource.DATASHEET,
        description="Companion computer module, carrier board, heatsink and PWM cooling fan",
    ),
    "oak_d_lite": ComponentSpec(
        name="Luxonis OAK-D Lite Spatial AI Camera",
        mass_kg=0.061,
        source=DataSource.DATASHEET,
        description="Stereo depth and 4K RGB vision camera with USB-C interface",
    ),
    "rfd868x_in": ComponentSpec(
        name="RFD868x-IN Telemetry Modem",
        mass_kg=0.045,
        source=DataSource.DATASHEET,
        description="868 MHz long-range telemetry modem + dipole antenna",
    ),
    "wifi_hardware": ComponentSpec(
        name="Dual-band 5 GHz Wi-Fi NIC",
        mass_kg=0.035,
        source=DataSource.DATASHEET,
        description="M.2 802.11ac/ax high-throughput Wi-Fi adapter for local swarm mesh",
    ),
    "antennas": ComponentSpec(
        name="5 GHz RP-SMA Antennas & Pigtails",
        mass_kg=0.030,
        source=DataSource.ESTIMATE,
        description="Dual 5 GHz 3dBi dipole antennas and RG178 coaxial pigtails",
    ),
    "dcdc_bec_converters": ComponentSpec(
        name="Dual DC-DC Step-Down Regulators",
        mass_kg=0.065,
        source=DataSource.ESTIMATE,
        description="5V 5A and 12V 3A high-efficiency switching regulators for companion electronics",
    ),
    "payload_drop_rack_4slot": ComponentSpec(
        name="5-Slot Mechanical Quick-Release Drop Rack",
        mass_kg=0.250,
        source=DataSource.NEEDS_PHYSICAL_MEASUREMENT,
        description="Carbon fibre mounting plate, 5-bay package guides, micro servos and release pins",
    ),
    "payload_drop_rack_5slot": ComponentSpec(
        name="5-Slot Mechanical Quick-Release Drop Rack",
        mass_kg=0.250,
        source=DataSource.NEEDS_PHYSICAL_MEASUREMENT,
        description="Carbon fibre mounting plate, 5-bay package guides, micro servos and release pins",
    ),
    "payload_drop_rack_2slot": ComponentSpec(
        name="2-Slot Mechanical Release Rack",
        mass_kg=0.180,
        source=DataSource.NEEDS_PHYSICAL_MEASUREMENT,
        description="Compact 2-bay package release rack for Drone 3",
    ),
    "wiring": ComponentSpec(
        name="Power & Signal Wiring Harness",
        mass_kg=0.120,
        source=DataSource.NEEDS_PHYSICAL_MEASUREMENT,
        description="10 AWG silicone power leads, 16 AWG motor extensions, CAN/UART/I2C harness",
    ),
    "connectors": ComponentSpec(
        name="Power & Data Connectors",
        mass_kg=0.045,
        source=DataSource.ESTIMATE,
        description="XT90-S anti-spark main connector, XT60 auxiliary, JST-GH locking connectors",
    ),
    "heat_shrink": ComponentSpec(
        name="Heat Shrink Tubing & Insulation",
        mass_kg=0.020,
        source=DataSource.ESTIMATE,
        description="Polyolefin heat shrink on power splices, ESC joints and wiring wraps",
    ),
    "fasteners": ComponentSpec(
        name="Screws, Standoffs & Nuts",
        mass_kg=0.055,
        source=DataSource.ESTIMATE,
        description="M3/M4 stainless steel screws, nylon standoffs, brass inserts, locking nuts",
    ),
    "vibration_mounts": ComponentSpec(
        name="Avionics Silicone Isolators",
        mass_kg=0.025,
        source=DataSource.ESTIMATE,
        description="Silicone damping balls for flight controller and sensor sub-assemblies",
    ),
    "storage": ComponentSpec(
        name="NVMe SSD & High-Endurance MicroSD",
        mass_kg=0.015,
        source=DataSource.DATASHEET,
        description="256 GB M.2 NVMe SSD for Jetson OS/models + 64 GB MicroSD for Pixhawk logging",
    ),
    "buzzer_status_leds": ComponentSpec(
        name="Arming LED & Piezo Buzzer",
        mass_kg=0.025,
        source=DataSource.DATASHEET,
        description="External daylight-visible RGB status LED and 90 dB emergency locator buzzer",
    ),

    "landing_gear_ext": ComponentSpec(
        name="Extended CF Landing Skids",
        mass_kg=0.100,
        source=DataSource.ESTIMATE,
        description="Extended wide-track carbon fiber landing gear to prevent rollover in 5m/s wind",
    ),

    "camera_bracket": ComponentSpec(
        name="Extended Camera Mounting Bracket",
        mass_kg=0.015,
        source=DataSource.ESTIMATE,
        description="Carbon fiber bracket for forward-and-lower camera mounting",
    ),
    "gimbal": ComponentSpec(
        name="2-Axis Camera Gimbal",
        mass_kg=0.065,
        source=DataSource.ESTIMATE,
        description="Lightweight 2-axis stabilized mount for OAK-D Lite. ESTIMATE.",
    ),
    "battery": ComponentSpec(
        name="6S 16.0V 16,000 mAh LiPo Battery",
        mass_kg=1.930,
        source=DataSource.DATASHEET,
        description="6S1P 25C high-energy LiPo battery pack with 10 AWG silicon wire and XT90 connector",
    ),
    "misc_engineering_allowance": ComponentSpec(
        name="Engineering Allowance & Hardware Margin",
        mass_kg=-0.516,
        source=DataSource.ESTIMATE,
        description="5% reserve for conformal coating, cable ties, tape, labels, and manufacturing variance",
    ),
}


# ============================================================================
# PROPULSION BENCHMARK TEST DATA (T-Motor MN4014 KV330 + 17x5.8 Props on 6S 22.2V)
# ============================================================================
# Source: T-Motor Official Dynamometer Test Bench Data (6S 22.2V nominal)
# Columns: Throttle fraction [0..1], Thrust per motor (kgf), Current per motor (A), Power (W)
MOTOR_TEST_DATA: List[Tuple[float, float, float, float]] = [
    # (throttle, thrust_kgf, current_a, power_w)
    (0.35, 0.520, 1.8, 40.0),
    (0.40, 0.680, 2.5, 55.5),
    (0.50, 1.020, 4.4, 97.7),
    (0.60, 1.420, 7.2, 159.8),
    (0.65, 1.620, 8.8, 195.4),
    (0.70, 1.830, 10.6, 235.3),
    (0.75, 2.040, 12.4, 275.3),
    (0.80, 2.240, 14.1, 313.0),
    (0.85, 2.400, 15.3, 339.7),
    (0.90, 2.510, 16.2, 359.6),
    (1.00, 2.600, 17.0, 377.4),
]

# Physical propulsion limits per drone (4 motors)
MOTORS_PER_DRONE: int = 4
MAX_THRUST_PER_MOTOR_KGF: float = 2.600  # DATASHEET
MAX_CURRENT_PER_MOTOR_A: float = 17.0    # DATASHEET
MAX_TOTAL_THRUST_KGF: float = MOTORS_PER_DRONE * MAX_THRUST_PER_MOTOR_KGF  # 10.4 kgf (~102.0 N)
MAX_PROPULSION_CURRENT_A: float = MOTORS_PER_DRONE * MAX_CURRENT_PER_MOTOR_A  # 68.0 A
MIN_TW_RATIO_REQUIRED: float = 1.50      # Validation threshold


# ============================================================================
# ELECTRICAL & POWER SYSTEM SPECIFICATIONS
# ============================================================================

@dataclass(frozen=True)
class ElectricalLimits:
    esc_continuous_current_a: float = 40.0   # DATASHEET: 40A per ESC
    esc_burst_current_a: float = 50.0        # DATASHEET: 50A for 10s
    pdb_continuous_current_a: float = 120.0  # DATASHEET: 120A continuous
    connector_continuous_a: float = 90.0     # DATASHEET: XT90-S 90A cont / 120A peak
    main_wire_10awg_rating_a: float = 140.0  # DATASHEET: 10 AWG silicone <30cm
    motor_wire_16awg_rating_a: float = 35.0  # DATASHEET: 16 AWG silicone chassis
    avionics_power_nominal_w: float = 32.0   # Jetson (15W) + Gimbal (2W) (15W) + Pixhawk (5W) + OAK-D (3W) + RFD (2W) + BEC (5W)
    nominal_voltage_v: float = 22.2          # 6S LiPo nominal voltage


ELECTRICAL_LIMITS = ElectricalLimits()


# ============================================================================
# BATTERY SPECIFICATIONS (6S LiPo 12,000 mAh)
# ============================================================================

@dataclass(frozen=True)
class BatterySpecs:
    nominal_voltage_v: float = 22.2          # DATASHEET
    capacity_mah: float = 16000.0            # DATASHEET
    capacity_ah: float = 16.0
    nominal_energy_wh: float = 355.2         # 22.2V * 12.0Ah = 266.4 Wh
    usable_fraction: float = 0.80            # 80% usable energy
    reserve_fraction: float = 0.20           # 20% hard reserve
    usable_energy_wh: float = 284.16         # 0.80 * 266.4 = 213.12 Wh (767,232 J)
    reserve_energy_wh: float = 71.04         # 0.20 * 266.4 = 53.28 Wh (191,808 J)
    max_continuous_discharge_c: float = 25.0 # DATASHEET: 25C continuous (300 A)
    battery_mass_kg: float = 1.670           # DATASHEET: 1.670 kg


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
