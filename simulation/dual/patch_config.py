with open("../hardware/config.py", "r") as f:
    data = f.read()

new_item = """
    "landing_gear_ext": ComponentSpec(
        name="Extended CF Landing Skids",
        mass_kg=0.100,
        source=DataSource.ESTIMATE,
        description="Extended wide-track carbon fiber landing gear to prevent rollover in 5m/s wind",
    ),
"""
data = data.replace('    "gimbal": ComponentSpec(', new_item + '    "gimbal": ComponentSpec(')
with open("../hardware/config.py", "w") as f:
    f.write(data)
