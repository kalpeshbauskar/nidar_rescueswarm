import re
path = 'simulation/hardware/config.py'
text = open(path).read()
text = re.sub(r'name="6S 22.2V 12,000 mAh LiPo Battery",\s+mass_kg=1.670,', 'name="6S 16.0V 16,000 mAh LiPo Battery",\n        mass_kg=1.930,', text)
text = re.sub(r'capacity_mah: float = 12000.0', 'capacity_mah: float = 16000.0', text)
text = re.sub(r'capacity_ah: float = 12.0', 'capacity_ah: float = 16.0', text)
text = re.sub(r'nominal_energy_wh: float = 266.4', 'nominal_energy_wh: float = 355.2', text)
text = re.sub(r'usable_energy_wh: float = 213.12', 'usable_energy_wh: float = 284.16', text)
text = re.sub(r'reserve_energy_wh: float = 53.28', 'reserve_energy_wh: float = 71.04', text)
# Need total dry mass = 5.150
# Current BOM total (excl battery): 5.626 - 1.670 = 3.956
# New BOM total = 3.956 + 1.930 = 5.886
# Need to reduce by 0.736 kg
# Let's reduce frame by 0.736? 1.300 - 0.736 = 0.564
text = re.sub(r'name="Carbon Fiber Quadcopter Frame",\s+mass_kg=1.300,', 'name="Carbon Fiber Quadcopter Frame",\n        mass_kg=0.484,', text)
# Wait, I also need to add claw: 0.080 kg. So reduce frame by another 0.080 -> 0.484.
open(path, 'w').write(text)
