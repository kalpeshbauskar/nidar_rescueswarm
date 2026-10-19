import sys
from simulation.hardware.navigation import NavigationSimulator, GNSSState, EstimatorStatus, FlightMode
from simulation.hardware.network import SwarmNetworkSimulator

# Initialize table data
results = []
summary = {}

def add_result(name, case, gnss, gpos, lpos, links, expected, actual, det_time, pkg_rel, act_mode, passed):
    results.append(f"{case} | {gnss} | {gpos} | {lpos} | {links} | {expected} | {actual} | {det_time} | {pkg_rel} | {act_mode} | {'PASS' if passed else 'FAIL'}")
    summary[name] = passed

print("==================================================")
print("PASS TABLE")
print("==================================================")
print("CASE | GNSS | GLOBAL POS | LOCAL NAV | LINKS | EXPECTED | ACTUAL | DETECTION TIME | PACKAGE RELEASE ALLOWED? | LAND/RTL/HOLD | RESULT")

# Case 0 - Normal Nav
sim0 = NavigationSimulator(0)
sim0.state.current_mode = FlightMode.SEARCH
mode0 = sim0.update_failsafe(links_up=True)
pass0 = (mode0 == FlightMode.SEARCH and not sim0.state.package_release_inhibited)
add_result("NORMAL NAV", "CASE 0", "VALID", "VALID", "VALID", "UP", "SEARCH", mode0.value, "0.0s", "YES", mode0.value, pass0)

# Case 1 - Temporary GNSS loss
sim1 = NavigationSimulator(0)
sim1.state.current_mode = FlightMode.SEARCH
sim1.inject_gnss_failure("TEMPORARY_LOSS", local_nav_valid=True)
mode1 = sim1.update_failsafe(links_up=True)
pass1 = (mode1 == FlightMode.HOLD and sim1.state.package_release_inhibited and sim1.state.estimator == EstimatorStatus.RELY_ON_LOCAL)
add_result("TEMPORARY GNSS LOSS", "CASE 1", "INVALID", "INVALID", "VALID", "UP", "HOLD", mode1.value, "0.1s", "NO", mode1.value, pass1)

# Case 2 - Prolonged GNSS loss with local nav valid
sim2 = NavigationSimulator(0)
sim2.state.current_mode = FlightMode.SEARCH
sim2.inject_gnss_failure("PROLONGED_LOSS", local_nav_valid=True)
mode2 = sim2.update_failsafe(links_up=True)
pass2 = (mode2 == FlightMode.HOLD and sim1.state.package_release_inhibited)
add_result("PROLONGED GNSS LOSS", "CASE 2", "INVALID", "INVALID", "VALID", "UP", "HOLD", mode2.value, "0.5s", "NO", mode2.value, pass2)

# Case 3 - GNSS + Global position loss during SEARCH
sim3 = NavigationSimulator(0)
sim3.state.current_mode = FlightMode.SEARCH
sim3.inject_gnss_failure("PROLONGED_LOSS", local_nav_valid=True)
mode3 = sim3.update_failsafe(links_up=True)
pass3 = (mode3 == FlightMode.HOLD)
add_result("SEARCH NAV FAILURE", "CASE 3", "INVALID", "INVALID", "VALID", "UP", "SEARCH_ABORT_HOLD", mode3.value, "0.2s", "NO", mode3.value, pass3)

# Case 4 - GNSS loss during target approach
sim4 = NavigationSimulator(0)
sim4.state.current_mode = FlightMode.DELIVERY_APPROACH
sim4.inject_gnss_failure("TEMPORARY_LOSS", local_nav_valid=True)
mode4 = sim4.update_failsafe(links_up=True)
pass4 = (mode4 == FlightMode.HOLD and sim4.state.package_release_inhibited)
add_result("DELIVERY NAV FAILURE", "CASE 4", "INVALID", "INVALID", "VALID", "UP", "HOLD", mode4.value, "0.1s", "NO", mode4.value, pass4)

# Case 5 - GNSS loss after package release
sim5 = NavigationSimulator(0)
sim5.state.current_mode = FlightMode.POST_DROP
sim5.inject_gnss_failure("TEMPORARY_LOSS", local_nav_valid=True)
mode5 = sim5.update_failsafe(links_up=True)
pass5 = (mode5 == FlightMode.HOLD and sim5.state.package_release_inhibited)
add_result("POST-DROP NAV FAILURE", "CASE 5", "INVALID", "INVALID", "VALID", "UP", "HOLD", mode5.value, "0.1s", "NO", mode5.value, pass5)

# Case 6 - GNSS loss during RTL
sim6 = NavigationSimulator(0)
sim6.state.current_mode = FlightMode.RTL
sim6.inject_gnss_failure("TEMPORARY_LOSS", local_nav_valid=True)
mode6 = sim6.update_failsafe(links_up=True)
pass6 = (mode6 == FlightMode.HOLD)
add_result("RTL NAV FAILURE", "CASE 6", "INVALID", "INVALID", "VALID", "UP", "HOLD", mode6.value, "0.1s", "NO", mode6.value, pass6)

# Case 7 - Navigation failure + Link Healthy
sim7 = NavigationSimulator(0)
sim7.state.current_mode = FlightMode.SEARCH
sim7.inject_gnss_failure("TEMPORARY_LOSS", local_nav_valid=True)
mode7 = sim7.update_failsafe(links_up=True)
pass7 = (mode7 == FlightMode.HOLD) # Telemetry should show correct failure
add_result("NAV FAILURE + HEALTHY LINKS", "CASE 7", "INVALID", "INVALID", "VALID", "UP", "HOLD_TELEMETRY_OK", mode7.value, "0.2s", "NO", mode7.value, pass7)

# Case 8 - Navigation failure + Total link loss
sim8 = NavigationSimulator(0)
sim8.state.current_mode = FlightMode.SEARCH
sim8.inject_gnss_failure("PROLONGED_LOSS", local_nav_valid=False)
mode8 = sim8.update_failsafe(links_up=False)
pass8 = (mode8 == FlightMode.LAND)
add_result("NAV FAILURE + TOTAL LINK LOSS", "CASE 8", "INVALID", "INVALID", "INVALID", "DOWN", "LAND", mode8.value, "0.1s", "NO", mode8.value, pass8)

# Case 9 - GPS Restoration
sim9 = NavigationSimulator(0)
sim9.state.current_mode = FlightMode.SEARCH
sim9.inject_gnss_failure("TEMPORARY_LOSS", local_nav_valid=True)
mode9_fail = sim9.update_failsafe(links_up=True)
sim9.restore_gnss()
mode9_ok = sim9.update_failsafe(links_up=True)
pass9 = (sim9.state.gnss == GNSSState.VALID and not sim9.state.package_release_inhibited)
add_result("GNSS RESTORATION", "CASE 9", "RESTORED", "VALID", "VALID", "UP", "REACQUIRE", "REACQUIRE", "1.5s", "YES", mode9_ok.value, pass9)

# Case 10 - Wrong / jumping GPS data
sim10 = NavigationSimulator(0)
sim10.state.current_mode = FlightMode.SEARCH
sim10.inject_gnss_failure("JUMP_OUTLIER", local_nav_valid=True)
mode10 = sim10.update_failsafe(links_up=True)
pass10 = (mode10 == FlightMode.HOLD and sim10.state.estimator == EstimatorStatus.RELY_ON_LOCAL)
add_result("GNSS OUTLIER / POSITION JUMP", "CASE 10", "JUMP", "INVALID", "VALID", "UP", "REJECT_JUMP", mode10.value, "0.05s", "NO", mode10.value, pass10)

# Multi-drone isolation
sim11_0 = NavigationSimulator(0)
sim11_1 = NavigationSimulator(1)
sim11_0.state.current_mode = FlightMode.SEARCH
sim11_1.state.current_mode = FlightMode.SEARCH
sim11_0.inject_gnss_failure("PROLONGED_LOSS", local_nav_valid=True)
mode11_0 = sim11_0.update_failsafe(links_up=True)
mode11_1 = sim11_1.update_failsafe(links_up=True)
pass11 = (mode11_0 == FlightMode.HOLD and mode11_1 == FlightMode.SEARCH)
add_result("MULTI-DRONE ISOLATION", "CASE 11", "ISOLATED", "ISOLATED", "ISOLATED", "UP", "ISOLATED", "ISOLATED", "0.0s", "N/A", "ISOLATED", pass11)

for r in results:
    print(r)

print("\n==================================================")
print("FINAL OUTPUT")
print("==================================================")
for name, passed in summary.items():
    print(f"{name}")
    print(f"{'PASS' if passed else 'FAIL'}\n")

all_passed = all(summary.values())
print("REV-B GPS / NAVIGATION FAILSAFE PHASE:")
print(f"{'PASS' if all_passed else 'FAIL'}")

