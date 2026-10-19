from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

class FlightMode(Enum):
    TAKEOFF = "TAKEOFF"
    SEARCH = "SEARCH"
    DELIVERY_APPROACH = "DELIVERY_APPROACH"
    POST_DROP = "POST_DROP"
    RTL = "RTL"
    HOLD = "HOLD"
    LAND = "LAND"

class GNSSState(Enum):
    VALID = "VALID"
    DEGRADED = "DEGRADED"
    INVALID = "INVALID"
    JUMP_OUTLIER = "JUMP_OUTLIER"

class EstimatorStatus(Enum):
    HEALTHY = "HEALTHY"
    RELY_ON_LOCAL = "RELY_ON_LOCAL"
    UNSAFE = "UNSAFE"
    REACQUIRING = "REACQUIRING"

@dataclass
class NavigationState:
    drone_id: int
    gnss: GNSSState = GNSSState.VALID
    global_pos_valid: bool = True
    local_pos_valid: bool = True
    estimator: EstimatorStatus = EstimatorStatus.HEALTHY
    current_mode: FlightMode = FlightMode.TAKEOFF
    package_release_inhibited: bool = False
    event_log: List[Dict] = field(default_factory=list)

class NavigationSimulator:
    def __init__(self, drone_id: int):
        self.drone_id = drone_id
        self.state = NavigationState(drone_id=drone_id)
        self.state.current_mode = FlightMode.SEARCH

    def inject_gnss_failure(self, failure_type: str, local_nav_valid: bool = True):
        if failure_type == "TEMPORARY_LOSS" or failure_type == "PROLONGED_LOSS":
            self.state.gnss = GNSSState.INVALID
            self.state.global_pos_valid = False
            self.state.local_pos_valid = local_nav_valid
            if local_nav_valid:
                self.state.estimator = EstimatorStatus.RELY_ON_LOCAL
            else:
                self.state.estimator = EstimatorStatus.UNSAFE
        elif failure_type == "JUMP_OUTLIER":
            self.state.gnss = GNSSState.JUMP_OUTLIER
            self.state.global_pos_valid = False # Rejected by estimator
            self.state.local_pos_valid = local_nav_valid
            self.state.estimator = EstimatorStatus.RELY_ON_LOCAL

    def restore_gnss(self):
        self.state.gnss = GNSSState.VALID
        self.state.estimator = EstimatorStatus.REACQUIRING
        # After some time, it becomes healthy
        self.state.global_pos_valid = True
        self.state.estimator = EstimatorStatus.HEALTHY
        self.state.package_release_inhibited = False

    def update_failsafe(self, links_up: bool = True) -> FlightMode:
        """Determines next flight mode based on navigation and links"""
        # Delivery Safety Rule
        if self.state.estimator != EstimatorStatus.HEALTHY or not self.state.global_pos_valid:
            self.state.package_release_inhibited = True
        else:
            self.state.package_release_inhibited = False

        if not links_up and not self.state.local_pos_valid and not self.state.global_pos_valid:
            self.state.current_mode = FlightMode.LAND
            return self.state.current_mode

        if not links_up:
            if self.state.global_pos_valid:
                self.state.current_mode = FlightMode.RTL
            else:
                self.state.current_mode = FlightMode.LAND
            return self.state.current_mode

        if self.state.gnss != GNSSState.VALID or not self.state.global_pos_valid:
            if self.state.local_pos_valid:
                # Can hold safely
                if self.state.current_mode in [FlightMode.SEARCH, FlightMode.DELIVERY_APPROACH, FlightMode.RTL, FlightMode.POST_DROP]:
                    self.state.current_mode = FlightMode.HOLD
            else:
                self.state.current_mode = FlightMode.LAND
        
        return self.state.current_mode

