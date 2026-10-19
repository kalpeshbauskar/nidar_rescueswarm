import xml.etree.ElementTree as E
import os

path = 'simulation/imported/PX4-Autopilot/Tools/simulation/gz/models/rescue_heavy/model.sdf'
tree = E.parse(path)
root = tree.getroot()
model = root.find('model')

# Plugins
for plug in model.findall("plugin[@name='gz::sim::systems::MulticopterMotorModel']"):
    plug.find('motorConstant').text = '2.5e-05'
    plug.find('rotorDragCoefficient').text = '1.5e-04'

# Rack link
rack = model.find("link[@name='rack_link']")
if rack is not None:
    rack.find('inertial/mass').text = '0.3'

tree.write(path, xml_declaration=True, encoding='UTF-8')
