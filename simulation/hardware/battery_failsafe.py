from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional
from .config import BATTERY_SPECS, get_drone_initial_auw_kg
from .propulsion import calculate_propulsion_state, BatterySOCIntegrator

class FailsafeResponse(Enum):
    NORMAL = "NORMAL"
    SHORTEN_MISSION = "SHORTEN_MISSION"
    MISSION_INHIBITED = "MISSION_INHIBITED"
    RTL = "RTL"
    ABORT_DELIVERY_RTL = "ABORT_DELIVERY_RTL"
    SAFE_LANDING = "SAFE_LANDING"
    IGNORE_ANOMALY = "IGNORE_ANOMALY"

@dataclass
class BatteryState:
    soc: float
    remaining_wh: float
    consumed_wh: float
    distance_home_m: float
    flight_mode: str
    package_release_inhibited: bool = False

class BatteryFailsafeSimulator:
    def __init__(self, drone_id: int):
        self.drone_id = drone_id
        self.integrator = BatterySOCIntegrator(drone_id)
        # Use existing configured values but allow override for tests
        self.capacity_derating = 1.0 
        self.wind_penalty = 1.0

    def set_soc(self, target_soc: float):
        self.integrator.energy_consumed_wh = self.integrator.nominal_energy_wh * (1.0 - target_soc)

    def estimate_rtl_wh(self, distance_home_m: float, auw_kg: float) -> float:
        # Assuming RTL speed of 10 m/s
        rtl_speed = 10.0
        time_to_home = distance_home_m / rtl_speed
        
        # Calculate propulsion power at current mass
        prop = calculate_propulsion_state(auw_kg)
        factor = BatterySOCIntegrator.PHASE_POWER_FACTORS["RETURN"] * self.wind_penalty
        power_w = prop.hover_propulsion_power_w * factor
        
        rtl_wh = (power_w * time_to_home) / 3600.0
        # Add 10 Wh allowance for descent/landing
        return rtl_wh + 10.0

    def evaluate_preflight(self, estimated_mission_wh: float) -> FailsafeResponse:
        nominal_usable = self.integrator.nominal_energy_wh * self.capacity_derating
        remaining_energy = nominal_usable - self.integrator.energy_consumed_wh
        reserve = self.integrator.reserve_energy_wh
        available_above_reserve = remaining_energy - reserve
        
        if available_above_reserve < 0:
            return FailsafeResponse.MISSION_INHIBITED
        if available_above_reserve >= estimated_mission_wh:
            return FailsafeResponse.NORMAL
        if available_above_reserve >= estimated_mission_wh * 0.5:
            return FailsafeResponse.SHORTEN_MISSION
        return FailsafeResponse.MISSION_INHIBITED

    def evaluate_inflight(self, distance_home_m: float, current_mode: str, auw_kg: float, sensor_anomaly: bool = False) -> FailsafeResponse:
        if sensor_anomaly:
            return FailsafeResponse.IGNORE_ANOMALY

        nominal_usable = self.integrator.nominal_energy_wh * self.capacity_derating
        remaining_energy = nominal_usable - self.integrator.energy_consumed_wh
        reserve = self.integrator.reserve_energy_wh
        rtl_wh = self.estimate_rtl_wh(distance_home_m, auw_kg)
        
        energy_margin = remaining_energy - reserve - rtl_wh
        
        if energy_margin < 0:
            if current_mode == "DELIVERY_APPROACH":
                return FailsafeResponse.ABORT_DELIVERY_RTL
            if current_mode == "RTL":
                # If margin is severely negative and we cannot make it home safely
                if remaining_energy < rtl_wh:
                    return FailsafeResponse.SAFE_LANDING
                return FailsafeResponse.RTL
            return FailsafeResponse.RTL
        
        return FailsafeResponse.NORMAL
