import re

with open("simulation/dual/mission.py", "r") as f:
    data = f.read()

# Add JSON import if not present
if "import json" not in data:
    data = data.replace("import math", "import math\nimport json\nimport os")

# In the tick loop, read the fault file and set network state
tick_code = """
        now = self.get_clock().now().nanoseconds / 1e9
"""

new_tick_code = """
        now = self.get_clock().now().nanoseconds / 1e9

        # Read fault injection
        wifi_conn = True
        rfd_conn = True
        nav_valid = True
        try:
            if os.path.exists("../../faults.json"):
                with open("../../faults.json", "r") as f:
                    faults = json.load(f)
                if str(self.i) in faults:
                    f_drone = faults[str(self.i)]
                    wifi_conn = f_drone.get("wifi", True)
                    rfd_conn = f_drone.get("rfd", True)
                    nav_valid = f_drone.get("nav", True)
        except Exception:
            pass

        # Update network simulator
        case, failsafe_action = self.network_sim.set_link_state(
            wifi_connected=wifi_conn,
            rfd_connected=rfd_conn,
            nav_solution_valid=nav_valid
        )

        # Handle failsafes
        if failsafe_action == FailsafeAction.AUTONOMOUS_RTL:
            self.phase = 'RTL'
        elif failsafe_action == FailsafeAction.SAFE_HOLD_AND_LAND:
            self.phase = 'LAND'
        elif failsafe_action == FailsafeAction.RESTORE_NORMAL_OPERATION:
            if self.phase in ['RTL', 'LAND'] and not (wifi_conn and rfd_conn):
                # actually, normally it shouldn't resume delivery automatically without operator cmd
                pass

"""
data = data.replace(tick_code, new_tick_code)

with open("simulation/dual/mission.py", "w") as f:
    f.write(data)
