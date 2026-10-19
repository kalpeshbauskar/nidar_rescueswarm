import re

with open("build_world.py", "r") as f:
    data = f.read()

# We need to find the place where we clean up links/joints and insert our gimbal modifications.
# Currently it has:
#     # Clean default template parcel links/joints
#     for tag, name in [("link", "parcel_1_link"), ("joint", "parcel_1_joint")]:
gimbal_injection = """
    # Convert fixed camera_joint to a 2-axis gimbal
    cam_joint = m.find("joint[@name='camera_joint']")
    if cam_joint is not None:
        m.remove(cam_joint)
    
    # Gimbal Roll Link
    g_roll = E.SubElement(m, "link", name="gimbal_roll_link")
    E.SubElement(g_roll, "pose").text = "0.1 0 -0.05 0 0 0"
    g_roll_inertial = E.SubElement(g_roll, "inertial")
    E.SubElement(g_roll_inertial, "mass").text = "0.03"
    g_roll_inertia = E.SubElement(g_roll_inertial, "inertia")
    for axis, val in [("ixx", 1e-5), ("iyy", 1e-5), ("izz", 1e-5), ("ixy", 0), ("ixz", 0), ("iyz", 0)]:
        E.SubElement(g_roll_inertia, axis).text = str(val)
        
    # Visual for gimbal
    g_roll_vis = E.SubElement(g_roll, "visual", name="g_roll_vis")
    g_roll_geom = E.SubElement(g_roll_vis, "geometry")
    E.SubElement(g_roll_geom, "box").text = ""
    E.SubElement(E.SubElement(g_roll_geom, "box"), "size").text = "0.02 0.02 0.02"
    
    # Roll joint (base -> gimbal_roll)
    j_roll = E.SubElement(m, "joint", name="gimbal_roll_joint", type="revolute")
    E.SubElement(j_roll, "parent").text = "base_link"
    E.SubElement(j_roll, "child").text = "gimbal_roll_link"
    j_roll_axis = E.SubElement(j_roll, "axis")
    E.SubElement(j_roll_axis, "xyz").text = "1 0 0"
    j_roll_limit = E.SubElement(j_roll_axis, "limit")
    E.SubElement(j_roll_limit, "lower").text = "-0.349" # -20 deg
    E.SubElement(j_roll_limit, "upper").text = "0.349"
    E.SubElement(j_roll_axis, "dynamics").text = ""
    E.SubElement(E.SubElement(j_roll_axis, "dynamics"), "damping").text = "0.01"
    E.SubElement(E.SubElement(j_roll_axis, "dynamics"), "friction").text = "0.01"
    
    # Pitch joint (gimbal_roll -> camera_link)
    j_pitch = E.SubElement(m, "joint", name="gimbal_pitch_joint", type="revolute")
    E.SubElement(j_pitch, "parent").text = "gimbal_roll_link"
    E.SubElement(j_pitch, "child").text = "camera_link"
    j_pitch_axis = E.SubElement(j_pitch, "axis")
    E.SubElement(j_pitch_axis, "xyz").text = "0 1 0"
    j_pitch_limit = E.SubElement(j_pitch_axis, "limit")
    E.SubElement(j_pitch_limit, "lower").text = "-0.523" # -30 deg
    E.SubElement(j_pitch_limit, "upper").text = "0.523"
    E.SubElement(j_pitch_axis, "dynamics").text = ""
    E.SubElement(E.SubElement(j_pitch_axis, "dynamics"), "damping").text = "0.01"
    E.SubElement(E.SubElement(j_pitch_axis, "dynamics"), "friction").text = "0.01"
    
    # Update camera_link pose so it is relative to the gimbal, or keep it relative to model
    cam_link = m.find("link[@name='camera_link']")
    if cam_link is not None:
        p = cam_link.find("pose")
        if p is None:
            E.SubElement(cam_link, "pose").text = "0.1 0 -0.07 0 1.5708 0"
        else:
            p.text = "0.1 0 -0.07 0 1.5708 0"

    # Add Joint Position Controller plugins
    for jname in ["gimbal_roll_joint", "gimbal_pitch_joint"]:
        plug = E.SubElement(m, "plugin", filename="gz-sim-joint-position-controller-system", name="gz::sim::systems::JointPositionController")
        E.SubElement(plug, "joint_name").text = jname
        E.SubElement(plug, "p_gain").text = "2"
        E.SubElement(plug, "i_gain").text = "0.0"
        E.SubElement(plug, "d_gain").text = "0.1"
        E.SubElement(plug, "i_max").text = "1"
        E.SubElement(plug, "i_min").text = "-1"
        E.SubElement(plug, "cmd_max").text = "100"
        E.SubElement(plug, "cmd_min").text = "-100"

    # Clean default template parcel links/joints"""
data = re.sub(r'    # Clean default template parcel links/joints', gimbal_injection, data)

with open("build_world.py", "w") as f:
    f.write(data)
