with open("build_world.py", "r") as f:
    data = f.read()

# Add gimbal_mass to base_mass subtraction
data = data.replace(
    'cam_mass = HARDWARE_BOM["oak_d_lite"].mass_kg',
    'cam_mass = HARDWARE_BOM["oak_d_lite"].mass_kg\n    gimbal_mass = HARDWARE_BOM["gimbal"].mass_kg if "gimbal" in HARDWARE_BOM else 0.065'
)
data = data.replace(
    'base_mass = round(dry_mass - (rack_mass + cam_mass + 4 * rotor_mass), 4)',
    'base_mass = round(dry_mass - (rack_mass + cam_mass + gimbal_mass + 4 * rotor_mass), 4)'
)

# Set camera_link mass to 0.061 and gimbal_roll_link mass to 0.065
data = data.replace(
    'E.SubElement(g_roll_inertial, "mass").text = "0.03"',
    'E.SubElement(g_roll_inertial, "mass").text = str(gimbal_mass)'
)

with open("build_world.py", "w") as f:
    f.write(data)
