with open("build_world.py", "r") as f:
    data = f.read()

# Replace gimbal_roll_link pose
data = data.replace(
    'E.SubElement(g_roll, "pose").text = "0.1 0 -0.05 0 0 0"',
    'E.SubElement(g_roll, "pose").text = "0.22 0 -0.18 0 0 0"'
)

# Replace camera_link pose
data = data.replace(
    'E.SubElement(cam_link, "pose").text = "0.1 0 -0.07 0 1.5708 0"',
    'E.SubElement(cam_link, "pose").text = "0.22 0 -0.20 0 1.5708 0"'
)
data = data.replace(
    'p.text = "0.1 0 -0.07 0 1.5708 0"',
    'p.text = "0.22 0 -0.20 0 1.5708 0"'
)

with open("build_world.py", "w") as f:
    f.write(data)
