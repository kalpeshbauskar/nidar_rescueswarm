with open("../hardware/config.py", "r") as f:
    data = f.read()

data = data.replace(
    'name="Quadcopter Carbon Fiber Frame"',
    'name="Rev-B Compact Quadcopter CF Frame (710mm)"'
)
data = data.replace(
    'mass_kg=1.300',
    'mass_kg=1.250'
)
data = data.replace(
    '650mm carbon fiber',
    '710mm diagonal carbon fiber'
)

with open("../hardware/config.py", "w") as f:
    f.write(data)
