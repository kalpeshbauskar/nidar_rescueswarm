with open("../hardware/config.py", "r") as f:
    data = f.read()

new_item = """
    "camera_bracket": ComponentSpec(
        name="Extended Camera Mounting Bracket",
        mass_kg=0.015,
        source=DataSource.ESTIMATE,
        description="Carbon fiber bracket for forward-and-lower camera mounting",
    ),
"""
data = data.replace('    "gimbal": ComponentSpec(', new_item + '    "gimbal": ComponentSpec(')

with open("../hardware/config.py", "w") as f:
    f.write(data)
