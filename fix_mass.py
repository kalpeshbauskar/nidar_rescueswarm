import re
path = 'simulation/hardware/config.py'
text = open(path).read()
text = re.sub(r'name="Engineering Allowance & Hardware Margin",\n\s+mass_kg=[0-9.-]+,', 'name="Engineering Allowance & Hardware Margin",\n        mass_kg=-0.516,', text)
open(path, 'w').write(text)
