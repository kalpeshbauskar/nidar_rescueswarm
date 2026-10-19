"""Private Offline Network and Deterministic Failsafe State Machine.

Simulates dual-tier communications:
1. RFD868x-IN Multipoint (868 MHz) - Critical Telemetry
2. Private 5 GHz Wi-Fi LAN - High Bandwidth (Video / Dense Telemetry)

Strictly zero reliance on external Internet, LTE, 5G, GSM, or public cloud.
Implements navigation-aware link loss failsafe behavior.
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from .config import NETWORK_SPECS


class LinkStatus(Enum):
    CONNECTED = "CONNECTED"
    DEGRADED = "DEGRADED"
    DISCONNECTED = "DISCONNECTED"


class NetworkCase(Enum):
    CASE_1_NORMAL = "NORMAL_DUAL_LINK"
    CASE_2_WIFI_LOST_RFD_OK = "WIFI_LOST_RFD_OK"
    CASE_3_RFD_LOST_WIFI_OK = "RFD_LOST_WIFI_OK"
    CASE_4_TOTAL_LINK_LOSS = "TOTAL_LINK_LOSS"
    CASE_5_CONNECTION_RESTORED = "CONNECTION_RESTORED"


class FailsafeAction(Enum):
    NO_ACTION_CONTINUE = "NO_ACTION_CONTINUE"
    DEGRADE_VIDEO_CONTINUE_RFD = "DEGRADE_VIDEO_CONTINUE_RFD"
    SWITCH_TO_WIFI_BACKUP_TELEMETRY = "SWITCH_TO_WIFI_BACKUP_TELEMETRY"
    AUTONOMOUS_RTL = "AUTONOMOUS_RTL"
    SAFE_HOLD_AND_LAND = "SAFE_HOLD_AND_LAND"
    RESTORE_NORMAL_OPERATION = "RESTORE_NORMAL_OPERATION"


@dataclass
class NetworkState:
    drone_id: int
    static_ip: str
    gcs_ip: str
    wifi_status: LinkStatus = LinkStatus.CONNECTED
    rfd_status: LinkStatus = LinkStatus.CONNECTED
    video_streaming_enabled: bool = True
    telemetry_streaming_enabled: bool = True
    telemetry_carrier: str = "RFD868x-IN"
    current_case: NetworkCase = NetworkCase.CASE_1_NORMAL
    active_failsafe: FailsafeAction = FailsafeAction.NO_ACTION_CONTINUE
    buffered_messages_count: int = 0
    event_log: List[Dict[str, str]] = field(default_factory=list)


class SwarmNetworkSimulator:
    """Simulates private local network states, link failures, and deterministic safe actions."""

    def __init__(self, drone_id: int):
        self.drone_id = drone_id
        drone_num = drone_id + 1
        self.state = NetworkState(
            drone_id=drone_num,
            static_ip=NETWORK_SPECS.drone_ips.get(drone_num, f"10.42.0.{10+drone_num}"),
            gcs_ip=NETWORK_SPECS.gcs_ip,
        )

    def log_event(self, event_type: str, message: str) -> None:
        self.state.event_log.append({
            "event": event_type,
            "message": message,
            "case": self.state.current_case.value,
            "failsafe": self.state.active_failsafe.value,
        })

    def set_link_state(
        self,
        wifi_connected: bool,
        rfd_connected: bool,
        nav_solution_valid: bool = True,
    ) -> Tuple[NetworkCase, FailsafeAction]:
        """Evaluate network health and determine safe autonomous action."""
        prev_case = self.state.current_case

        # Update link statuses
        self.state.wifi_status = (
            LinkStatus.CONNECTED if wifi_connected else LinkStatus.DISCONNECTED
        )
        self.state.rfd_status = (
            LinkStatus.CONNECTED if rfd_connected else LinkStatus.DISCONNECTED
        )

        # Case 1: Normal (Both links operational)
        if wifi_connected and rfd_connected:
            if prev_case in (
                NetworkCase.CASE_2_WIFI_LOST_RFD_OK,
                NetworkCase.CASE_3_RFD_LOST_WIFI_OK,
                NetworkCase.CASE_4_TOTAL_LINK_LOSS,
            ):
                self.state.current_case = NetworkCase.CASE_5_CONNECTION_RESTORED
                self.state.active_failsafe = FailsafeAction.RESTORE_NORMAL_OPERATION
                self.state.video_streaming_enabled = True
                self.state.telemetry_streaming_enabled = True
                self.state.telemetry_carrier = "RFD868x-IN"
                self.log_event("LINK_RECOVERY", "Connection restored to GCS. Flushing buffered telemetry.")
                self.state.buffered_messages_count = 0
                return self.state.current_case, self.state.active_failsafe

            self.state.current_case = NetworkCase.CASE_1_NORMAL
            self.state.active_failsafe = FailsafeAction.NO_ACTION_CONTINUE
            self.state.video_streaming_enabled = True
            self.state.telemetry_streaming_enabled = True
            self.state.telemetry_carrier = "RFD868x-IN"
            return self.state.current_case, self.state.active_failsafe

        # Case 2: Wi-Fi lost + RFD working
        if (not wifi_connected) and rfd_connected:
            self.state.current_case = NetworkCase.CASE_2_WIFI_LOST_RFD_OK
            self.state.active_failsafe = FailsafeAction.DEGRADE_VIDEO_CONTINUE_RFD
            self.state.video_streaming_enabled = False  # Disable high-bandwidth video
            self.state.telemetry_streaming_enabled = True
            self.state.telemetry_carrier = "RFD868x-IN"
            self.log_event("WIFI_LOST", "5 GHz Wi-Fi link lost. High-bandwidth video disabled. Telemetry on RFD868x-IN.")
            return self.state.current_case, self.state.active_failsafe

        # Case 3: RFD lost + Wi-Fi working
        if wifi_connected and (not rfd_connected):
            self.state.current_case = NetworkCase.CASE_3_RFD_LOST_WIFI_OK
            self.state.active_failsafe = FailsafeAction.SWITCH_TO_WIFI_BACKUP_TELEMETRY
            self.state.video_streaming_enabled = True
            self.state.telemetry_streaming_enabled = True
            self.state.telemetry_carrier = "5GHz_Wi-Fi_UDP_Backup"
            self.log_event("RFD_LOST", "RFD868x-IN link down. Critical telemetry switched to Wi-Fi UDP backup.")
            return self.state.current_case, self.state.active_failsafe

        # Case 4: Both links lost (Total Link Loss)
        self.state.current_case = NetworkCase.CASE_4_TOTAL_LINK_LOSS
        self.state.video_streaming_enabled = False
        self.state.telemetry_streaming_enabled = False
        self.state.telemetry_carrier = "NONE_BUFFERING"
        self.state.buffered_messages_count += 1

        # Navigation-aware safe behavior
        if nav_solution_valid:
            # Position solution is healthy -> Safe RTL may be commanded
            self.state.active_failsafe = FailsafeAction.AUTONOMOUS_RTL
            self.log_event("TOTAL_LINK_LOSS", "Both links lost with VALID navigation. Executing deterministic RTL.")
        else:
            # Navigation unavailable / degraded -> DO NOT blindly RTL! Use defined safe hold and land
            self.state.active_failsafe = FailsafeAction.SAFE_HOLD_AND_LAND
            self.log_event("TOTAL_LINK_LOSS", "Both links lost with INVALID navigation. Executing safe hold/land.")

        return self.state.current_case, self.state.active_failsafe
