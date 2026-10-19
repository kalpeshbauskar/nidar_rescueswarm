import re
with open("../hardware/config.py", "r") as f:
    data = f.read()

gimbal_entry = """    "gimbal": ComponentSpec(
        name="2-Axis Camera Gimbal",
        mass_kg=0.065,
        source=DataSource.ESTIMATE,
        description="Lightweight 2-axis stabilized mount for OAK-D Lite. ESTIMATE.",
    ),
    "battery": ComponentSpec("""

data = re.sub(r'    "battery": ComponentSpec\(', gimbal_entry, data)
data = re.sub(r'avionics_power_nominal_w: float = 30\.0(.*?)# Jetson', r'avionics_power_nominal_w: float = 32.0\1# Jetson (15W) + Gimbal (2W)', data)

with open("../hardware/config.py", "w") as f:
    f.write(data)
