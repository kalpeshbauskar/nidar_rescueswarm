"""Automated tests for NIDAR RescueSwarm hardware integration.

Validates:
1. initial mass calculation per drone
2. package distribution ([4, 4, 2] = 10 packages = 2.0 kg)
3. package release mass reduction (4 -> 3 -> 2 -> 1 -> 0)
4. final empty-payload mass
5. fleet AUW (<= 25 kg)
6. thrust-to-weight ratio (T/W >= 1.5 at all stages)
7. motor and ESC current limits (interpolated vs 40A ESC and 17A motor max)
8. battery energy & hard reserve separation (501.6 Wh nominal, 401.28 Wh usable, 100.32 Wh reserve)
9. dynamic SOC tracking across flight phases
10. 30-minute maximum duration rule logic (duration <= 30 min AND duration <= battery capacity)
11. Wi-Fi failure case (video degraded, telemetry on RFD868x-IN)
12. RFD failure case (primary link failure logged, backup on Wi-Fi)
13. total link loss navigation-aware failsafe (RTL if nav valid; safe hold/land if nav invalid)
14. connection recovery behavior (restore normal operation, buffer flush)
15. removal of lidar and presence of RTK GNSS & Revogreen solid-state battery
"""

import pytest
import math
from pathlib import Path

from simulation.hardware.config import (
    BATTERY_SPECS,
    ELECTRICAL_LIMITS,
    FLEET_SIZE,
    HARDWARE_BOM,
    MAX_FLEET_AUW_KG,
    MAX_MISSION_TIME_SEC,
    MAX_TOTAL_THRUST_KGF,
    MIN_TW_RATIO_REQUIRED,
    MOTOR_TEST_DATA,
    PACKAGE_MASS_KG,
    PAYLOAD_ALLOCATION,
    TOTAL_PACKAGES,
    TOTAL_PAYLOAD_MASS_KG,
    get_drone_dry_mass_kg,
    get_drone_initial_auw_kg,
    get_fleet_initial_auw_kg,
)
from simulation.hardware.propulsion import (
    calculate_propulsion_state,
    validate_electrical_limits,
    PayloadTracker,
    BatterySOCIntegrator,
)
from simulation.hardware.network import (
    SwarmNetworkSimulator,
    NetworkCase,
    FailsafeAction,
    LinkStatus,
)


class TestHardwareIntegration:

    def test_01_initial_mass_calculation(self):
        """Test initial mass breakdown per drone and ensure positive, realistic values."""
        for drone_id in range(FLEET_SIZE):
            dry_mass = get_drone_dry_mass_kg(drone_id)
            initial_auw = get_drone_initial_auw_kg(drone_id)

            assert dry_mass > 5.0, f"Dry mass too low: {dry_mass} kg"
            assert dry_mass < 6.2, f"Dry mass too high: {dry_mass} kg"
            assert initial_auw > dry_mass
            expected_payload = PAYLOAD_ALLOCATION[drone_id] * PACKAGE_MASS_KG
            assert math.isclose(initial_auw, dry_mass + expected_payload, rel_tol=1e-4)

    def test_02_package_distribution(self):
        assert len(PAYLOAD_ALLOCATION) == 2
        assert PAYLOAD_ALLOCATION[0] == 5
        assert PAYLOAD_ALLOCATION[1] == 5
        assert sum(PAYLOAD_ALLOCATION) == TOTAL_PACKAGES
        assert TOTAL_PACKAGES == 10
        assert math.isclose(TOTAL_PAYLOAD_MASS_KG, 2.000, rel_tol=1e-5)

    def test_03_package_release_mass_reduction(self):
        tracker = PayloadTracker(drone_id=0)
        assert tracker.packages_remaining == 5
        initial_auw = tracker.current_auw_kg

        for expected_remaining in [4, 3, 2, 1, 0]:
            prop_state = tracker.release_package(f"parcel_{5 - expected_remaining}")
            assert tracker.packages_remaining == expected_remaining
            expected_mass = tracker.dry_mass_kg + (expected_remaining * PACKAGE_MASS_KG)
            assert math.isclose(tracker.current_auw_kg, expected_mass, rel_tol=1e-4)
            assert tracker.current_auw_kg < initial_auw
            assert prop_state.tw_ratio >= MIN_TW_RATIO_REQUIRED

        with pytest.raises(RuntimeError):
            tracker.release_package("extra_package")

    def test_04_final_empty_payload_mass(self):
        """Test aircraft mass when payload is completely released equals dry mass."""
        for drone_id in range(FLEET_SIZE):
            tracker = PayloadTracker(drone_id=drone_id)
            for _ in range(tracker.initial_packages):
                tracker.release_package()
            assert tracker.packages_remaining == 0
            assert tracker.current_payload_mass_kg == 0.0
            assert math.isclose(tracker.current_auw_kg, tracker.dry_mass_kg, rel_tol=1e-4)

    def test_05_fleet_combined_auw_limit(self):
        """Test maximum combined fleet AUW is strictly <= 25 kg."""
        fleet_auw = get_fleet_initial_auw_kg()
        assert fleet_auw <= MAX_FLEET_AUW_KG, f"Fleet AUW {fleet_auw} kg exceeds {MAX_FLEET_AUW_KG} kg limit"
        # Check specific calculated value: 2 x 6.582 kg = ~13.16 kg
        assert 12.5 <= fleet_auw <= 14.5

    def test_06_thrust_to_weight_ratio(self):
        """Test T/W ratio >= 1.5 across all drones at both initial AUW and empty payload."""
        for drone_id in range(FLEET_SIZE):
            # At initial full payload
            initial_auw = get_drone_initial_auw_kg(drone_id)
            init_prop = calculate_propulsion_state(initial_auw)
            assert init_prop.tw_ratio >= 1.5, f"Drone {drone_id+1} initial T/W {init_prop.tw_ratio} < 1.5"
            assert init_prop.is_tw_valid is True
            assert init_prop.thrust_reserve_pct > 30.0

            # At empty payload (post-drop)
            dry_mass = get_drone_dry_mass_kg(drone_id)
            empty_prop = calculate_propulsion_state(dry_mass)
            assert empty_prop.tw_ratio > init_prop.tw_ratio
            assert empty_prop.tw_ratio >= 1.5

    def test_07_motor_and_esc_current_limits(self):
        """Test motor and ESC current limits using interpolated test bench data."""
        for drone_id in range(FLEET_SIZE):
            auw = get_drone_initial_auw_kg(drone_id)
            prop = calculate_propulsion_state(auw)

            # Motor current must not exceed tested maximum of 17A
            assert prop.motor_current_a <= 17.0
            # Total propulsion current must not exceed 68A
            assert prop.total_propulsion_current_a <= 68.0

            # Electrical check against 40A ESC limit, PDB, connectors, wires
            elec = validate_electrical_limits(prop.total_propulsion_current_a)
            assert elec.all_ok is True
            assert elec.esc_limit_ok is True
            assert elec.motor_current_ok is True
            assert elec.battery_discharge_ok is True
            assert elec.pdb_capacity_ok is True
            assert elec.connector_capacity_ok is True
            assert elec.wiring_capacity_ok is True

    def test_08_battery_energy_and_reserve_separation(self):
        """Test nominal energy (501.6 Wh), 80% usable (401.28 Wh), and 20% reserve (100.32 Wh)."""
        assert math.isclose(BATTERY_SPECS.nominal_energy_wh, 501.6, rel_tol=1e-4)
        assert math.isclose(BATTERY_SPECS.usable_energy_wh, 401.28, rel_tol=1e-4)
        assert math.isclose(BATTERY_SPECS.reserve_energy_wh, 100.32, rel_tol=1e-4)
        assert math.isclose(
            BATTERY_SPECS.usable_energy_wh + BATTERY_SPECS.reserve_energy_wh,
            BATTERY_SPECS.nominal_energy_wh,
            rel_tol=1e-4,
        )

        integrator = BatterySOCIntegrator(drone_id=0)
        assert integrator.is_reserve_intact is True
        assert integrator.soc == 1.0
        assert integrator.usable_soc_remaining == 1.0

    def test_09_battery_soc_tracking(self):
        """Test dynamic SOC integration across different flight phases."""
        integrator = BatterySOCIntegrator(drone_id=0)
        auw = get_drone_initial_auw_kg(0)

        # Simulate 120s takeoff/climb
        integrator.update("TAKEOFF", auw, 120.0)
        assert integrator.soc < 1.0
        assert integrator.is_reserve_intact is True

        # Simulate 600s search cruise
        integrator.update("SEARCH", auw, 600.0)
        assert integrator.soc < 0.85
        assert integrator.is_reserve_intact is True

        # Ensure energy by phase is recorded
        assert "TAKEOFF" in integrator.energy_by_phase_wh
        assert "SEARCH" in integrator.energy_by_phase_wh

    def test_10_thirty_minute_maximum_rule_logic(self):
        """Test battery endurance logic:

        Mission is valid if actual mission duration <= battery-supported duration
        AND actual mission duration <= 30 minutes.
        (Does NOT require battery endurance >= 30 minutes).
        """
        integrator = BatterySOCIntegrator(drone_id=0)

        # Case A: 15-minute mission, 180 Wh consumed (within 401.28 Wh usable) -> VALID
        integrator.energy_consumed_wh = 180.0
        valid, msg = integrator.validate_mission_energy(total_mission_time_sec=15 * 60.0)
        assert valid is True

        # Case B: 31-minute mission -> EXCEEDED 30 minute limit -> INVALID
        integrator.energy_consumed_wh = 180.0
        valid, msg = integrator.validate_mission_energy(total_mission_time_sec=31 * 60.0)
        assert valid is False
        assert "30 minute maximum" in msg

        # Case C: 20-minute mission, but consumed 420 Wh (> 401.28 Wh usable, breached reserve) -> INVALID
        integrator.energy_consumed_wh = 420.0
        valid, msg = integrator.validate_mission_energy(total_mission_time_sec=20 * 60.0)
        assert valid is False
        assert "reserve breached" in msg

    def test_11_wifi_failure_case(self):
        """Test Case 2: Wi-Fi lost + RFD working -> Degrade video, continue critical telemetry on RFD."""
        net = SwarmNetworkSimulator(drone_id=0)
        case, action = net.set_link_state(wifi_connected=False, rfd_connected=True)

        assert case == NetworkCase.CASE_2_WIFI_LOST_RFD_OK
        assert action == FailsafeAction.DEGRADE_VIDEO_CONTINUE_RFD
        assert net.state.video_streaming_enabled is False
        assert net.state.telemetry_streaming_enabled is True
        assert net.state.telemetry_carrier == "RFD868x-IN"

    def test_12_rfd_failure_case(self):
        """Test Case 3: RFD lost + Wi-Fi working -> Backup telemetry on Wi-Fi, record primary failure."""
        net = SwarmNetworkSimulator(drone_id=0)
        case, action = net.set_link_state(wifi_connected=True, rfd_connected=False)

        assert case == NetworkCase.CASE_3_RFD_LOST_WIFI_OK
        assert action == FailsafeAction.SWITCH_TO_WIFI_BACKUP_TELEMETRY
        assert net.state.telemetry_carrier == "5GHz_Wi-Fi_UDP_Backup"
        assert any(e["event"] == "RFD_LOST" for e in net.state.event_log)

    def test_13_total_link_loss_deterministic_failsafe(self):
        """Test Case 4: Total link loss -> RTL if nav valid; safe hold/land if nav invalid."""
        # Scenario A: Navigation solution is valid
        net_a = SwarmNetworkSimulator(drone_id=0)
        case_a, action_a = net_a.set_link_state(
            wifi_connected=False, rfd_connected=False, nav_solution_valid=True
        )
        assert case_a == NetworkCase.CASE_4_TOTAL_LINK_LOSS
        assert action_a == FailsafeAction.AUTONOMOUS_RTL
        assert net_a.state.buffered_messages_count > 0

        # Scenario B: Navigation solution is invalid / degraded -> MUST NOT blindly RTL!
        net_b = SwarmNetworkSimulator(drone_id=0)
        case_b, action_b = net_b.set_link_state(
            wifi_connected=False, rfd_connected=False, nav_solution_valid=False
        )
        assert case_b == NetworkCase.CASE_4_TOTAL_LINK_LOSS
        assert action_b == FailsafeAction.SAFE_HOLD_AND_LAND

    def test_14_connection_restored_recovery(self):
        """Test Case 5: Connection restored -> Restore normal operation, flush buffer."""
        net = SwarmNetworkSimulator(drone_id=0)
        # First trigger total loss
        net.set_link_state(wifi_connected=False, rfd_connected=False)
        assert net.state.buffered_messages_count > 0

        # Now reconnect both links
        case, action = net.set_link_state(wifi_connected=True, rfd_connected=True)
        assert case == NetworkCase.CASE_5_CONNECTION_RESTORED
        assert action == FailsafeAction.RESTORE_NORMAL_OPERATION
        assert net.state.video_streaming_enabled is True
        assert net.state.telemetry_streaming_enabled is True
        assert net.state.buffered_messages_count == 0
        assert any(e["event"] == "LINK_RECOVERY" for e in net.state.event_log)

    def test_15_ordered_bom_components_and_lidar_removal(self):
        """Validate that LiDAR is removed and ordered components (RTK, CAN hub, VTX, SSD, Solid-State Battery) exist."""
        # 1. LiDAR must be removed
        assert "lidar" not in HARDWARE_BOM
        assert not any("lidar" in k.lower() or "lidar" in v.name.lower() for k, v in HARDWARE_BOM.items())

        # 2. RTK GNSS Rover must be present
        assert "rtk_gnss_rover" in HARDWARE_BOM
        assert "ZED-F9P" in HARDWARE_BOM["rtk_gnss_rover"].name
        assert math.isclose(HARDWARE_BOM["rtk_gnss_rover"].mass_kg, 0.041, rel_tol=1e-3)

        # 3. Holybro CAN Hub must be present
        assert "can_hub" in HARDWARE_BOM
        assert "Holybro CAN Hub" in HARDWARE_BOM["can_hub"].name
        assert math.isclose(HARDWARE_BOM["can_hub"].mass_kg, 0.018, rel_tol=1e-3)

        # 4. SpeedyBee TX800 VTX must be present
        assert "vtx" in HARDWARE_BOM
        assert "SpeedyBee TX800" in HARDWARE_BOM["vtx"].name

        # 5. Revogreen Solid-State Battery must be present
        assert "battery" in HARDWARE_BOM
        assert "Revogreen" in HARDWARE_BOM["battery"].name
        assert "Solid State" in HARDWARE_BOM["battery"].name
        assert math.isclose(HARDWARE_BOM["battery"].mass_kg, 1.430, rel_tol=1e-3)

        # 6. Hobbywing X6-SE motors + 2270 props
        assert "Hobbywing X6-SE" in HARDWARE_BOM["motors"].name
        assert "2270" in HARDWARE_BOM["propellers"].name

    def test_16_sdf_simulation_world_alignment(self):
        """Validate that Gazebo SDF file dual_rescue.sdf has LiDAR removed, RTK added, and correct battery visual."""
        sdf_path = Path(__file__).resolve().parent.parent / "simulation" / "dual" / "dual_rescue.sdf"
        assert sdf_path.exists(), f"dual_rescue.sdf not found at {sdf_path}"

        sdf_content = sdf_path.read_text(encoding="utf-8")

        # 1. LiDAR links, joints, or sensors must be absent
        assert "lidar" not in sdf_content.lower()

        # 2. RTK GNSS visual and CORS base station must be present
        assert "rtk_helix_antenna" in sdf_content
        assert "rtk_cors_base_station" in sdf_content
        assert "cors_choke_ring_antenna" in sdf_content

        # 3. Revogreen Solid-State Battery visual must be present
        assert "revogreen_solid_state_battery" in sdf_content

        # 4. SpeedyBee VTX visual must be present
        assert "speedybee_tx800" in sdf_content
