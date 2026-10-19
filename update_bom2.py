import sys; sys.path.insert(0, '.')
from simulation.hardware.config import HARDWARE_BOM, get_drone_dry_mass_kg
current = get_drone_dry_mass_kg(0)
diff = 5.150 - current
path = 'simulation/hardware/config.py'
text = open(path).read()
import re
match = re.search(r'name="Engineering Allowance & Hardware Margin",\s+mass_kg=([0-9.]+),', text)
old_val = float(match.group(1))
new_val = old_val + diff
text = text.replace(f'mass_kg={old_val},', f'mass_kg={new_val:.3f},')
open(path, 'w').write(text)
print(f"Adjusted misc from {old_val} to {new_val:.3f}")
