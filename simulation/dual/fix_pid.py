import re
with open("build_world.py", "r") as f:
    data = f.read()
data = data.replace('E.SubElement(plug, "p_gain").text = "2"', 'E.SubElement(plug, "p_gain").text = "0.05"')
data = data.replace('E.SubElement(plug, "d_gain").text = "0.1"', 'E.SubElement(plug, "d_gain").text = "0.005"')
with open("build_world.py", "w") as f:
    f.write(data)
