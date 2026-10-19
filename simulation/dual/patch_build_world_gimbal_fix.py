import re

with open("build_world.py", "r") as f:
    data = f.read()

# I will add code to remove the collision tag from camera_link
fix = """
    cam_link = m.find("link[@name='camera_link']")
    if cam_link is not None:
        p = cam_link.find("pose")
        if p is None:
            E.SubElement(cam_link, "pose").text = "0.1 0 -0.07 0 1.5708 0"
        else:
            p.text = "0.1 0 -0.07 0 1.5708 0"
        # Remove collisions to prevent ODE explosions
        for coll in cam_link.findall("collision"):
            cam_link.remove(coll)
"""
data = re.sub(r'    cam_link = m\.find\("link\[@name=\'camera_link\'\]"\)\s+if cam_link is not None:\s+p = cam_link\.find\("pose"\)\s+if p is None:\s+E\.SubElement\(cam_link, "pose"\)\.text = "0\.1 0 -0\.07 0 1\.5708 0"\s+else:\s+p\.text = "0\.1 0 -0\.07 0 1\.5708 0"', fix, data)

with open("build_world.py", "w") as f:
    f.write(data)
