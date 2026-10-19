import sys
sys.path.append('..')
from hardware.config import HARDWARE_BOM, get_drone_initial_auw_kg, get_drone_dry_mass_kg, FLEET_SIZE
import xml.etree.ElementTree as ET

gimbal_mass = HARDWARE_BOM["gimbal"].mass_kg if "gimbal" in HARDWARE_BOM else 0
lg_mass = HARDWARE_BOM["landing_gear_ext"].mass_kg if "landing_gear_ext" in HARDWARE_BOM else 0
cam_br = HARDWARE_BOM["camera_bracket"].mass_kg if "camera_bracket" in HARDWARE_BOM else 0

new_dry = get_drone_dry_mass_kg(0)
new_auw = get_drone_initial_auw_kg(0)
fleet_auw = sum(get_drone_initial_auw_kg(i) for i in range(FLEET_SIZE))

tree = ET.parse('dual_rescue.sdf')
root = tree.getroot()
sdf_mass = 0.0
for model in root.findall('.//model'):
    if model.attrib.get('name') == 'rescue_0':
        for inertial in model.findall('.//inertial'):
            mass_node = inertial.find('mass')
            if mass_node is not None:
                sdf_mass += float(mass_node.text)

print(f"EMPTY FLIGHT MASS: {new_dry:.3f} kg")
print(f"LOADED AUW WITH 5 PACKAGES: {new_auw:.3f} kg")
print(f"FLEET LOADED AUW: {fleet_auw:.3f} kg")
print(f"GIMBAL MASS: {gimbal_mass:.3f} kg")
print(f"LANDING-GEAR MASS: {lg_mass:.3f} kg")
print(f"CAMERA BRACKET MASS: {cam_br:.3f} kg")
print(f"T/W: {((4 * 3.5) / new_auw):.2f}") # roughly 3.5kg max thrust per motor for MN501-S
print("BATTERY: 6S 16Ah")
print("CG: X=0, Y=0, Z approx -0.05m")
print("WHEELBASE: 780 mm")
print("OVERALL LENGTH: 780 mm + 457.2 mm = 1237 mm (approx diagonal envelope)")
print("OVERALL WIDTH: 1237 mm")
print("OVERALL HEIGHT: 450 mm")

print("\n--- MASS RECONCILIATION ---")
print(f"BOM MASS: {new_dry:.3f} kg")
print(f"SDF MASS: {sdf_mass:.3f} kg")
print(f"DIFFERENCE: {abs(new_dry - sdf_mass):.3f} kg")

