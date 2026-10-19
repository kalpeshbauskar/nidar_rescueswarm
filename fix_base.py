import xml.etree.ElementTree as E
import os

path = 'simulation/imported/PX4-Autopilot/Tools/simulation/gz/models/rescue_heavy_base/model.sdf'
tree = E.parse(path)
root = tree.getroot()
model = root.find('model')

# Base link
base_link = model.find("link[@name='base_link']")
inertial = base_link.find('inertial')
inertial.find('mass').text = '3.2'
inertia = inertial.find('inertia')
# Scaled for 850mm wheelbase (arm length increased to 850mm, strictly not exceeding 900mm)
inertia.find('ixx').text = '0.110'
inertia.find('iyy').text = '0.110'
inertia.find('izz').text = '0.190'

# Frame body collision size (increased to 0.42 x 0.42 x 0.05 m for real drone avionics and payload clearance)
c0 = base_link.find("collision[@name='base_link_collision_0']")
if c0 is not None:
    c0.find('geometry/box/size').text = '0.42 0.42 0.05'

# Landing gear collisions (wide-track 780mm landing stance)
c3 = base_link.find("collision[@name='base_link_collision_3']")
if c3 is not None:
    c3.find('pose').text = '0 -0.39 -.2195 0 0 0'

c4 = base_link.find("collision[@name='base_link_collision_4']")
if c4 is not None:
    c4.find('pose').text = '0 0.39 -.2195 0 0 0'

# Update motor visual poses for 850mm diagonal wheelbase (0.300m in X/Y)
for i, (dx, dy) in enumerate([(0.300, 0.300), (-0.300, 0.300), (0.300, -0.300), (-0.300, -0.300)]):
    vis = base_link.find(f"visual[@name='5010_motor_base_{i}']")
    if vis is not None:
        vis.find('pose').text = f"{dx} {dy} .032 0 0 -.45"

# Update rotors for 850mm diagonal wheelbase (0.300m in X/Y)
# Rotor order:
# rotor_0: 0.300, -0.300
# rotor_1: -0.300, 0.300
# rotor_2: 0.300, 0.300
# rotor_3: -0.300, -0.300
for i, (dx, dy) in enumerate([(0.300, -0.300), (-0.300, 0.300), (0.300, 0.300), (-0.300, -0.300)]):
    rotor = model.find(f"link[@name='rotor_{i}']")
    if rotor is not None:
        rotor.find('pose').text = f"{dx} {dy} 0.06 0 0 0"
        rinertial = rotor.find('inertial')
        rinertial.find('mass').text = '0.025'

tree.write(path, xml_declaration=True, encoding='UTF-8')
print("Successfully updated rescue_heavy_base model.sdf to 850mm wheelbase and widened frame body.")
