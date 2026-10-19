import re

with open("simulation/dual/mission.py", "r") as f:
    data = f.read()

# Add final telemetry to status
data = re.sub(
    r"'elapsed_s': time.monotonic\(\) - self\.start,",
    """'elapsed_s': time.monotonic() - self.start,
            'final_alt': float(-self.global_p[2]) if self.global_p else None,
            'final_vz': float(-self.p.vz) if self.p else None,
            'final_roll': float(math.degrees(self.att_euler()[0])) if self.att else None,
            'final_pitch': float(math.degrees(self.att_euler()[1])) if self.att else None,
            'final_arming_state': int(self.s.arming_state) if self.s else None,""",
    data
)

# wait, att_euler doesn't exist, we need to compute it inline
# Let's write a safe getter
replacement = """'elapsed_s': time.monotonic() - self.start,
            'final_alt': float(-self.global_p[2]) if self.global_p else None,
            'final_vz': float(-self.p.vz) if self.p else None,
            'final_arming_state': int(self.s.arming_state) if self.s else None,
"""
data = re.sub(r"'elapsed_s': time.monotonic\(\) - self\.start,", replacement, data)

with open("simulation/dual/mission.py", "w") as f:
    f.write(data)
