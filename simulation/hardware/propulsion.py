"""Propulsion, Aerodynamics, Mass Dynamics, Electrical Validation, and Battery/SOC Models.

All propulsion metrics are computed via interpolation of measured Hobbywing X6-SE 280KV + 2270
folding propeller test bench data rather than hardcoded approximations.
"""

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from .config import (
    BATTERY_SPECS,
    ELECTRICAL_LIMITS,
    MAX_CURRENT_PER_MOTOR_A,
    MAX_PROPULSION_CURRENT_A,
    MAX_THRUST_PER_MOTOR_KGF,
    MAX_TOTAL_THRUST_KGF,
    MIN_TW_RATIO_REQUIRED,
    MOTOR_TEST_DATA,
    MOTORS_PER_DRONE,
    PACKAGE_MASS_KG,
    PAYLOAD_ALLOCATION,
    get_drone_dry_mass_kg,
    get_drone_initial_auw_kg,
)


def _interpolate_1d(x: float, xp: List[float], fp: List[float]) -> float:
    """Piecewise linear 1D interpolation with flat boundary clamping."""
    if x <= xp[0]:
        return fp[0]
    if x >= xp[-1]:
        return fp[-1]
    for i in range(len(xp) - 1):
        if xp[i] <= x <= xp[i + 1]:
            dx = xp[i + 1] - xp[i]
            if dx == 0:
                return fp[i]
            t = (x - xp[i]) / dx
            return fp[i] + t * (fp[i + 1] - fp[i])
    return fp[-1]


# Extract sorted curve lists for fast lookup
_THRUST_POINTS = [pt[1] for pt in MOTOR_TEST_DATA]
_THROTTLE_POINTS = [pt[0] for pt in MOTOR_TEST_DATA]
_CURRENT_POINTS = [pt[2] for pt in MOTOR_TEST_DATA]
_POWER_POINTS = [pt[3] for pt in MOTOR_TEST_DATA]


@dataclass(frozen=True)
class PropulsionState:
    auw_kg: float
    required_hover_thrust_kgf: float
    thrust_per_motor_kgf: float
    estimated_hover_throttle: float
    motor_current_a: float
    total_propulsion_current_a: float
    hover_propulsion_power_w: float
    total_hover_power_w: float
    maximum_thrust_kgf: float
    tw_ratio: float
    thrust_reserve_pct: float
    is_tw_valid: bool


def calculate_propulsion_state(auw_kg: float) -> PropulsionState:
    """Calculate exact hover propulsion parameters by interpolating the motor test bench curve."""
    if auw_kg <= 0:
        raise ValueError(f"AUW must be positive, got {auw_kg}")

    required_thrust = auw_kg
    thrust_per_motor = required_thrust / MOTORS_PER_DRONE

    # Clamp thrust for interpolation lookup
    clamped_thrust = min(thrust_per_motor, MAX_THRUST_PER_MOTOR_KGF)

    throttle = _interpolate_1d(clamped_thrust, _THRUST_POINTS, _THROTTLE_POINTS)
    motor_current = _interpolate_1d(clamped_thrust, _THRUST_POINTS, _CURRENT_POINTS)
    motor_power = _interpolate_1d(clamped_thrust, _THRUST_POINTS, _POWER_POINTS)

    total_prop_current = MOTORS_PER_DRONE * motor_current
    hover_prop_power = MOTORS_PER_DRONE * motor_power
    total_hover_power = hover_prop_power + ELECTRICAL_LIMITS.avionics_power_nominal_w

    max_thrust = MAX_TOTAL_THRUST_KGF
    tw_ratio = max_thrust / auw_kg
    thrust_reserve = ((max_thrust - auw_kg) / max_thrust) * 100.0
    tw_valid = tw_ratio >= MIN_TW_RATIO_REQUIRED

    return PropulsionState(
        auw_kg=round(auw_kg, 4),
        required_hover_thrust_kgf=round(required_thrust, 4),
        thrust_per_motor_kgf=round(thrust_per_motor, 4),
        estimated_hover_throttle=round(throttle, 4),
        motor_current_a=round(motor_current, 2),
        total_propulsion_current_a=round(total_prop_current, 2),
        hover_propulsion_power_w=round(hover_prop_power, 2),
        total_hover_power_w=round(total_hover_power, 2),
        maximum_thrust_kgf=round(max_thrust, 2),
        tw_ratio=round(tw_ratio, 3),
        thrust_reserve_pct=round(thrust_reserve, 2),
        is_tw_valid=tw_valid,
    )


@dataclass(frozen=True)
class ElectricalCheckResult:
    motor_current_ok: bool
    esc_limit_ok: bool
    battery_discharge_ok: bool
    pdb_capacity_ok: bool
    connector_capacity_ok: bool
    wiring_capacity_ok: bool
    all_ok: bool
    details: Dict[str, str]


def validate_electrical_limits(
    propulsion_current_a: float,
    avionics_current_a: Optional[float] = None,
) -> ElectricalCheckResult:
    """Validate electrical load against ESC, battery, PDB, connector, and wiring ratings."""
    if avionics_current_a is None:
        avionics_current_a = (
            ELECTRICAL_LIMITS.avionics_power_nominal_w / ELECTRICAL_LIMITS.nominal_voltage_v
        )

    motor_current = propulsion_current_a / MOTORS_PER_DRONE
    total_drone_current = propulsion_current_a + avionics_current_a

    motor_ok = motor_current <= MAX_CURRENT_PER_MOTOR_A
    esc_ok = motor_current <= ELECTRICAL_LIMITS.esc_continuous_current_a

    max_battery_continuous_a = (
        BATTERY_SPECS.capacity_ah * BATTERY_SPECS.max_continuous_discharge_c
    )
    battery_ok = total_drone_current <= max_battery_continuous_a

    pdb_ok = total_drone_current <= ELECTRICAL_LIMITS.pdb_continuous_current_a
    conn_ok = total_drone_current <= ELECTRICAL_LIMITS.connector_continuous_a
    main_wire_ok = total_drone_current <= ELECTRICAL_LIMITS.main_wire_10awg_rating_a
    motor_wire_ok = motor_current <= ELECTRICAL_LIMITS.motor_wire_16awg_rating_a
    wiring_ok = main_wire_ok and motor_wire_ok

    all_ok = (
        motor_ok
        and esc_ok
        and battery_ok
        and pdb_ok
        and conn_ok
        and wiring_ok
    )

    details = {
        "motor_current": f"{motor_current:.1f}A <= max tested {MAX_CURRENT_PER_MOTOR_A}A",
        "esc_rating": f"{motor_current:.1f}A <= ESC rated {ELECTRICAL_LIMITS.esc_continuous_current_a}A",
        "battery_discharge": f"{total_drone_current:.1f}A <= {BATTERY_SPECS.max_continuous_discharge_c}C continuous {max_battery_continuous_a}A",
        "pdb_capacity": f"{total_drone_current:.1f}A <= PDB rated {ELECTRICAL_LIMITS.pdb_continuous_current_a}A",
        "connector_capacity": f"{total_drone_current:.1f}A <= XT90-S rated {ELECTRICAL_LIMITS.connector_continuous_a}A",
        "main_wire_10awg": f"{total_drone_current:.1f}A <= 10 AWG rated {ELECTRICAL_LIMITS.main_wire_10awg_rating_a}A",
        "motor_wire_16awg": f"{motor_current:.1f}A <= 16 AWG rated {ELECTRICAL_LIMITS.motor_wire_16awg_rating_a}A",
    }

    return ElectricalCheckResult(
        motor_current_ok=motor_ok,
        esc_limit_ok=esc_ok,
        battery_discharge_ok=battery_ok,
        pdb_capacity_ok=pdb_ok,
        connector_capacity_ok=conn_ok,
        wiring_capacity_ok=wiring_ok,
        all_ok=all_ok,
        details=details,
    )


class PayloadTracker:
    """Tracks dynamic payload release, mass reduction, and CG offset."""

    def __init__(self, drone_id: int):
        self.drone_id = drone_id
        self.dry_mass_kg = get_drone_dry_mass_kg(drone_id)
        self.initial_packages = PAYLOAD_ALLOCATION[drone_id]
        self.packages_remaining = self.initial_packages
        self.history: List[Dict[str, float]] = []
        self._record_state(reason="initial_onboard")

    @property
    def current_payload_mass_kg(self) -> float:
        return self.packages_remaining * PACKAGE_MASS_KG

    @property
    def current_auw_kg(self) -> float:
        return round(self.dry_mass_kg + self.current_payload_mass_kg, 4)

    def release_package(self, package_id: Optional[str] = None) -> PropulsionState:
        """Release one package and update mass, T/W, and propulsion state."""
        if self.packages_remaining <= 0:
            raise RuntimeError(f"Drone {self.drone_id + 1} has no packages remaining to release.")
        self.packages_remaining -= 1
        return self._record_state(reason=f"released_{package_id or self.packages_remaining}")

    def _record_state(self, reason: str) -> PropulsionState:
        auw = self.current_auw_kg
        prop = calculate_propulsion_state(auw)
        # 4-bay rack geometry: +/- 0.12m X, +/- 0.07m Y
        # Compute simplified CG shift
        cg_x = 0.0
        cg_y = 0.0
        if self.packages_remaining > 0:
            # Package slots symmetrical around origin
            cg_x = 0.005 * (self.packages_remaining % 2)
        record = {
            "reason": reason,
            "packages_remaining": self.packages_remaining,
            "payload_mass_kg": self.current_payload_mass_kg,
            "auw_kg": auw,
            "tw_ratio": prop.tw_ratio,
            "hover_throttle": prop.estimated_hover_throttle,
            "hover_power_w": prop.total_hover_power_w,
            "total_current_a": prop.total_propulsion_current_a,
            "cg_x_m": cg_x,
            "cg_y_m": cg_y,
        }
        self.history.append(record)
        return prop


class BatterySOCIntegrator:
    """Integrates dynamic power consumption and tracks battery state of charge (SOC).

    Maintains hard separation between:
    - 80% usable energy (401.28 Wh)
    - 20% emergency reserve (100.32 Wh)
    """

    # Multipliers for flight phase power relative to steady hover
    PHASE_POWER_FACTORS = {
        "TAKEOFF": 1.25,
        "SEARCH": 1.05,       # 8 m/s cruise
        "APPROACH": 1.02,
        "DESCEND": 0.85,      # partial gravity descent
        "RELEASE": 1.00,      # stationary hover
        "ASCEND": 1.20,       # vertical climb
        "RESUME": 1.05,
        "RETURN": 1.05,
        "LAND": 0.90,
        "HOLD": 1.00,
        "WAIT": 0.05,         # disarmed/idle avionics only
        "WARMUP": 0.05,
        "OFFBOARD": 0.05,
        "ARM": 0.08,
        "DONE": 0.02,
    }

    def __init__(self, drone_id: int):
        self.drone_id = drone_id
        self.nominal_energy_wh = BATTERY_SPECS.nominal_energy_wh
        self.usable_energy_wh = BATTERY_SPECS.usable_energy_wh
        self.reserve_energy_wh = BATTERY_SPECS.reserve_energy_wh

        self.energy_consumed_wh = 0.0
        self.energy_by_phase_wh: Dict[str, float] = {}
        self.time_by_phase_sec: Dict[str, float] = {}
        self.last_update_monotonic: Optional[float] = None

    def update(self, phase: str, auw_kg: float, dt_sec: float) -> float:
        """Integrate energy consumed over interval dt_sec for current phase and AUW."""
        prop = calculate_propulsion_state(auw_kg)
        factor = self.PHASE_POWER_FACTORS.get(phase.upper(), 1.00)
        power_w = prop.hover_propulsion_power_w * factor + ELECTRICAL_LIMITS.avionics_power_nominal_w

        energy_delta_wh = (power_w * dt_sec) / 3600.0
        self.energy_consumed_wh += energy_delta_wh

        p_key = phase.upper()
        self.energy_by_phase_wh[p_key] = self.energy_by_phase_wh.get(p_key, 0.0) + energy_delta_wh
        self.time_by_phase_sec[p_key] = self.time_by_phase_sec.get(p_key, 0.0) + dt_sec

        return self.soc

    @property
    def usable_energy_remaining_wh(self) -> float:
        """Usable energy remaining in Wh."""
        return max(0.0, self.usable_energy_wh - self.energy_consumed_wh)

    @property
    def soc(self) -> float:
        """Total battery state of charge fraction [0..1]."""
        remaining_wh = max(0.0, self.nominal_energy_wh - self.energy_consumed_wh)
        return remaining_wh / self.nominal_energy_wh

    @property
    def usable_soc_remaining(self) -> float:
        """Fraction of usable energy remaining before touching reserve [0..1]."""
        remaining_usable_wh = max(0.0, self.usable_energy_wh - self.energy_consumed_wh)
        return remaining_usable_wh / self.usable_energy_wh

    @property
    def is_reserve_intact(self) -> bool:
        """True if energy consumed has not breached the 20% hard reserve threshold."""
        return self.energy_consumed_wh <= self.usable_energy_wh

    @property
    def supported_endurance_sec(self) -> float:
        """Hover endurance supported by the 80% usable battery capacity."""
        initial_prop = calculate_propulsion_state(get_drone_initial_auw_kg(self.drone_id))
        return (self.usable_energy_wh / initial_prop.total_hover_power_w) * 3600.0

    def validate_mission_energy(self, total_mission_time_sec: float) -> Tuple[bool, str]:
        """Check the competition battery logic:

        actual mission duration <= battery supported duration
        AND actual mission duration <= 30 minutes.
        (Does NOT require battery endurance >= 30 minutes).
        """
        max_allowed_sec = 30 * 60.0
        time_rule_ok = total_mission_time_sec <= max_allowed_sec
        reserve_ok = self.is_reserve_intact

        if not time_rule_ok:
            return False, f"Mission duration {total_mission_time_sec:.1f}s exceeded 30 minute maximum."
        if not reserve_ok:
            return (
                False,
                f"Battery reserve breached: consumed {self.energy_consumed_wh:.2f}Wh > "
                f"usable capacity {self.usable_energy_wh:.2f}Wh (Reserve: {self.reserve_energy_wh:.2f}Wh).",
            )
        return True, "Mission completed within usable battery energy and <= 30 minute rule."
