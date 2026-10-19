import re
with open("build_world.py", "r") as f:
    data = f.read()

# Replace y offset 0.132 with 0.35
data = data.replace('E.SubElement(c3_pose, "text").text = "0 -0.132 -.2195 0 0 0"', 'E.SubElement(c3_pose, "text").text = "0 -0.35 -.2195 0 0 0"')
data = data.replace('E.SubElement(c4_pose, "text").text = "0 0.132 -.2195 0 0 0"', 'E.SubElement(c4_pose, "text").text = "0 0.35 -.2195 0 0 0"')

# Do the same for visuals
data = data.replace('E.SubElement(v3_pose, "text").text = "0 -0.132 -.2195 0 0 0"', 'E.SubElement(v3_pose, "text").text = "0 -0.35 -.2195 0 0 0"')
data = data.replace('E.SubElement(v4_pose, "text").text = "0 0.132 -.2195 0 0 0"', 'E.SubElement(v4_pose, "text").text = "0 0.35 -.2195 0 0 0"')

with open("build_world.py", "w") as f:
    f.write(data)
