import sys
sys.path.append('..')
from hardware.config import HARDWARE_BOM, get_drone_initial_auw_kg, get_drone_dry_mass_kg, FLEET_SIZE
import xml.etree.ElementTree as ET

original_dry = 5.215
original_auw = original_dry + 5 * 0.200

gimbal_mass = HARDWARE_BOM["gimbal"].mass_kg if "gimbal" in HARDWARE_BOM else 0
lg_mass = HARDWARE_BOM["landing_gear_ext"].mass_kg if "landing_gear_ext" in HARDWARE_BOM else 0

new_dry = get_drone_dry_mass_kg(0)
new_auw = get_drone_initial_auw_kg(0)
fleet_auw = sum(get_drone_initial_auw_kg(i) for i in range(FLEET_SIZE))

# Read SDF
tree = ET.parse('dual_rescue.sdf')
root = tree.getroot()
sdf_mass = 0.0
for model in root.findall('.//model'):
    if model.attrib.get('name') == 'rescue_0':
        for inertial in model.findall('.//inertial'):
            mass_node = inertial.find('mass')
            if mass_node is not None:
                sdf_mass += float(mass_node.text)

print("ORIGINAL EMPTY FLIGHT MASS: {:.3f} kg".format(original_dry))
print("ORIGINAL LOADED AUW: {:.3f} kg".format(original_auw))
print("GIMBAL ADDED MASS: {:.3f} kg".format(gimbal_mass))
print("LANDING-GEAR ADDED MASS: {:.3f} kg".format(lg_mass))
print("NEW EMPTY FLIGHT MASS: {:.3f} kg".format(new_dry))
print("NEW 5-PACKAGE LOADED AUW: {:.3f} kg".format(new_auw))
print("FLEET LOADED AUW: {:.3f} kg".format(fleet_auw))
print("SUM OF ALL SDF LINK MASSES: {:.3f} kg".format(sdf_mass))
print("SUM OF BOM MASSES: {:.3f} kg".format(new_dry))
print("DIFFERENCE: {:.3f} kg".format(abs(sdf_mass - new_dry)))
