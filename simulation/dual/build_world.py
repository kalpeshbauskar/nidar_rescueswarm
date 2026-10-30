"""World and Model Builder for NIDAR RescueSwarm Simulation.

Constructs dual_rescue.sdf with configurable multi-drone fleets (3-drone competition
[4, 4, 2] allocation or 2-drone legacy profile). All package masses and drone counts
are driven by the authoritative simulation.hardware.config module.
"""

from pathlib import Path
import copy, json, math, shutil, sys, xml.etree.ElementTree as E

ROOT = Path(__file__).resolve().parent
BASE = ROOT.parent
REPO_ROOT = BASE.parent
sys.path.insert(0, str(REPO_ROOT))

from simulation.hardware.config import (
    FLEET_SIZE,
    HARDWARE_BOM,
    MAX_THRUST_PER_MOTOR_KGF,
    PACKAGE_MASS_KG,
    PAYLOAD_ALLOCATION,
    TOTAL_PACKAGES,
    get_drone_dry_mass_kg,
    get_drone_initial_auw_kg,
)
from simulation.hardware.propulsion import calculate_propulsion_state

# Load config.json
cfg_path = ROOT / "config.json"
cfg = json.loads(cfg_path.read_text()) if cfg_path.exists() else {}
active_profile_name = cfg.get("active_profile", "competition_3drone")
profile = cfg.get("profiles", {}).get(active_profile_name, {})

drone_specs = profile.get("drones", [
    {"id": 0, "drone_num": 1, "packages": 4, "model_name": "rescue_0", "east_start": -100},
    {"id": 1, "drone_num": 2, "packages": 4, "model_name": "rescue_1", "east_start": 0},
    {"id": 2, "drone_num": 3, "packages": 2, "model_name": "rescue_2", "east_start": 100},
])

PKG_MASS = cfg.get("package_mass_kg", PACKAGE_MASS_KG)

# Zenith Unmanned Systems Heavy-Lift Airframe for 22-Inch (558.8 mm) Folding Props:
# Wheelbase: 980 mm motor-to-motor diagonal, giving 134 mm adjacent tip clearance
# and keeping the inner prop tip comfortably clear of the central avionics canopy.
WHEELBASE_M = 0.980
ROTOR_XY = round(WHEELBASE_M / 2 / math.sqrt(2), 4)   # 0.3465 m in X and Y
ARM_RADIUS_M = WHEELBASE_M / 2                          # 0.490 m centre to motor
PROP_DIAMETER_M = 0.5588                                # 22.0 inches (Hobbywing 2270)
ARM_MASS_KG = 0.360                                     # 4x 25mm CF arm tubes

# MulticopterMotorModel: thrust = motorConstant * omega^2, calibrated so 1000 rad/s gives
# the Hobbywing X6-SE 6.0 kgf peak (24 kgf total).
MAX_ROT_VELOCITY = 1000.0
MOTOR_CONSTANT = MAX_THRUST_PER_MOTOR_KGF * 9.80665 / MAX_ROT_VELOCITY**2
MOTOR_TIME_CONSTANT_UP = 0.020
MOTOR_TIME_CONSTANT_DOWN = 0.040

# Arducam IMX477 HQ with 6 mm CS lens: 63 deg horizontal FOV (30.6 m swath at 25 m vs 20 m lanes)
CAM_HFOV_RAD = round(math.radians(63.0), 4)

# Package inertia for emergency medical / survival canister (0.068m dia x 0.110m cylinder)
cr, ch = 0.034, 0.110
pkg_ixx = round(PKG_MASS / 12 * (3 * cr**2 + ch**2), 8)
pkg_iyy = pkg_ixx
pkg_izz = round(PKG_MASS / 2 * (cr**2), 8)

world = E.parse(BASE / "worlds/flood_zone.sdf")
w = world.getroot().find("world")
w.set("name", "dual_rescue")
w.find("physics/max_step_size").text = "0.004"
w.find("physics/real_time_factor").text = "1.0"

def sub(p, k, t):
    E.SubElement(p, k).text = str(t)

# Flood water surface 320 x 312.5 m (100,000 m2)
w.find("model[@name='flood_water']/link/visual/geometry/box/size").text = "320 312.5 0.1"
w.find("model[@name='flood_water']/link/collision/geometry/box/size").text = "320 312.5 0.1"

# Add bright daytime scene lighting, sky background, and grid for high visual contrast
scene = w.find("scene")
if scene is None:
    scene = E.SubElement(w, "scene")
for tag, val in [
    ("ambient", "0.72 0.72 0.76 1.0"),
    ("background", "0.62 0.76 0.90 1.0"),
    ("shadows", "true"),
    ("grid", "true"),
]:
    el = scene.find(tag)
    if el is not None:
        el.text = val
    else:
        sub(scene, tag, val)

sun = w.find("light[@name='sun']")
if sun is not None:
    d = sun.find("diffuse")
    if d is not None:
        d.text = "1.0 1.0 1.0 1"

# Optional custom survivor positioning from config.json (allows easy relocation)
custom_survivors = profile.get("survivors", cfg.get("survivors", None))
if custom_survivors:
    for s_info in custom_survivors:
        sid = s_info.get("id")
        s_east = s_info.get("east", 0.0)
        s_north = s_info.get("north", 0.0)
        s_z = s_info.get("z", 0.05)
        s_mod = w.find(f"model[@name='survivor_{sid}']")
        if s_mod is not None:
            p = s_mod.find("pose")
            if p is not None:
                parts = p.text.strip().split()
                rot_str = " ".join(parts[3:]) if len(parts) >= 6 else "0 0 0"
                p.text = f"{s_east} {s_north} {s_z} {rot_str}"

# Remove any pre-existing drone models, parcels, or debris pads from template world
for existing in list(w.findall("model")):
    m_name = existing.get("name", "")
    if m_name.startswith("rescue_") or m_name.startswith("parcel_") or m_name.startswith("debris_"):
        w.remove(existing)

total_parcels_built = 0

for d_spec in drone_specs:
    i = d_spec["id"]
    east = d_spec["east_start"]
    pkg_count = d_spec["packages"]
    total_parcels_built += pkg_count

    raw_m = E.parse(BASE / "imported/PX4-Autopilot/Tools/simulation/gz/models/rescue_heavy/model.sdf").getroot().find("model")
    base_m = E.parse(BASE / "imported/PX4-Autopilot/Tools/simulation/gz/models/rescue_heavy_base/model.sdf").getroot().find("model")

    m = E.Element("model", name=f"rescue_{i}", canonical_link="base_link")
    sub(m, "pose", f"{east} -5 0.24 0 0 0")
    sub(m, "self_collide", "false")
    sub(m, "static", "false")

    # 1. Base link and rotors from base_m (base_link MUST be first for physics stability)
    base_link = copy.deepcopy(base_m.find("link[@name='base_link']"))
    m.append(base_link)
    for r_idx in range(4):
        rl = base_m.find(f"link[@name='rotor_{r_idx}']")
        rj = base_m.find(f"joint[@name='rotor_{r_idx}_joint']")
        if rl is not None:
            m.append(copy.deepcopy(rl))
        if rj is not None:
            m.append(copy.deepcopy(rj))

    # 2. Rack link and joint from raw_m
    rack_l = raw_m.find("link[@name='rack_link']")
    rack_j = raw_m.find("joint[@name='rack_joint']")
    if rack_l is not None:
        m.append(copy.deepcopy(rack_l))
    if rack_j is not None:
        m.append(copy.deepcopy(rack_j))

    # 3. Camera link and joint from raw_m
    cam_l = raw_m.find("link[@name='camera_link']")
    cam_j = raw_m.find("joint[@name='camera_joint']")
    if cam_l is not None:
        m.append(copy.deepcopy(cam_l))
    if cam_j is not None:
        m.append(copy.deepcopy(cam_j))

    # 4. Plugins from raw_m (MulticopterMotorModel 0..3, MotorFailureSystem)
    for plug in raw_m.findall("plugin"):
        m.append(copy.deepcopy(plug))

    for elem in list(m.iter()):
        for gzf in [c for c in list(elem) if c.tag == "gz_frame_id"]:
            elem.remove(gzf)

    # Authoritative hardware masses from simulation.hardware.config
    dry_mass = get_drone_dry_mass_kg(min(i, FLEET_SIZE - 1))
    rack_mass = (
        HARDWARE_BOM["payload_drop_rack_4slot"].mass_kg
        if pkg_count > 2
        else HARDWARE_BOM["payload_drop_rack_2slot"].mass_kg
    )
    cam_mass = HARDWARE_BOM["camera"].mass_kg
    rotor_mass = HARDWARE_BOM["propellers"].mass_kg / 4.0
    # Every link's mass comes out of dry_mass so the SDF total equals the hardware config.
    # Note: LiDAR is removed from the ordered BOM; base_mass absorbs frame, avionics, battery, RTK.
    base_mass = round(dry_mass - (rack_mass + cam_mass + 4 * rotor_mass), 4)

    # base_link inertia: motors+ESCs as point masses at the arm tips, arms as rods
    # from 0.10 m to the motor, everything else as the 0.38 x 0.34 x 0.12 m core box
    base_link = m.find("link[@name='base_link']")
    base_link.find("inertial/mass").text = str(base_mass)
    motor_mass = HARDWARE_BOM["motors"].mass_kg
    core_mass = base_mass - motor_mass - ARM_MASS_KG
    r_in, r_out = 0.10, ARM_RADIUS_M
    arm_r2 = (r_out**3 - r_in**3) / (3 * (r_out - r_in))
    izz = motor_mass * r_out**2 + ARM_MASS_KG * arm_r2 + core_mass * (0.38**2 + 0.34**2) / 12
    ixx = motor_mass * r_out**2 / 2 + ARM_MASS_KG * arm_r2 / 2 + core_mass * (0.34**2 + 0.12**2) / 12
    iyy = motor_mass * r_out**2 / 2 + ARM_MASS_KG * arm_r2 / 2 + core_mass * (0.38**2 + 0.12**2) / 12
    for axis, val in [("ixx", ixx), ("iyy", iyy), ("izz", izz)]:
        base_link.find(f"inertial/inertia/{axis}").text = str(round(val, 6))

    # Remove all untextured, dark, or legacy visuals from base_link
    for vname in [
        "base_link_visual",
        "5010_motor_base_0", "5010_motor_base_1", "5010_motor_base_2", "5010_motor_base_3",
        "NXP_FMUK66_FRONT", "NXP_FMUK66_TOP", "RDDRONE_FMUK66_TOP"
    ]:
        v_el = base_link.find(f"visual[@name='{vname}']")
        if v_el is not None:
            base_link.remove(v_el)

    # Fleet distinction: Drone 0 is Safety Orange, Drone 1 is Arctic Cyan, Drone 2 is Lime
    if i == 0:
        canopy_color = "1.0 0.40 0.0 1"
        canopy_spec = "1.0 0.55 0.1 1"
    elif i == 1:
        canopy_color = "0.0 0.75 1.0 1"
        canopy_spec = "0.2 0.85 1.0 1"
    else:
        canopy_color = "0.85 1.0 0.0 1"
        canopy_spec = "0.9 1.0 0.2 1"

    # 1. Main Fuselage Lower Hull (0.38 x 0.34 x 0.065 m) - High-Visibility Search & Rescue White
    fuse_lower = E.SubElement(base_link, "visual", name="fuselage_lower_hull")
    sub(fuse_lower, "pose", "0 0 0.020 0 0 0")
    g = E.SubElement(fuse_lower, "geometry")
    sub(E.SubElement(g, "box"), "size", "0.38 0.34 0.065")
    mat = E.SubElement(fuse_lower, "material")
    sub(mat, "ambient", "0.88 0.88 0.92 1")
    sub(mat, "diffuse", "0.95 0.95 0.98 1")
    sub(mat, "specular", "0.6 0.6 0.6 1")

    # 2. Aerodynamic Upper Canopy (0.32 x 0.28 x 0.055 m) - International Fleet Colors
    fuse_canopy = E.SubElement(base_link, "visual", name="fuselage_upper_canopy")
    sub(fuse_canopy, "pose", "0 0 0.065 0 0 0")
    g = E.SubElement(fuse_canopy, "geometry")
    sub(E.SubElement(g, "box"), "size", "0.32 0.28 0.055")
    mat = E.SubElement(fuse_canopy, "material")
    sub(mat, "ambient", canopy_color)
    sub(mat, "diffuse", canopy_color)
    sub(mat, "specular", canopy_spec)

    # 3. Aerodynamic Nose Fairing & Cockpit Glass
    nose_fairing = E.SubElement(base_link, "visual", name="nose_fairing")
    sub(nose_fairing, "pose", "0.19 0 0.035 0 0 0")
    g = E.SubElement(nose_fairing, "geometry")
    sub(E.SubElement(g, "box"), "size", "0.09 0.22 0.048")
    mat = E.SubElement(nose_fairing, "material")
    sub(mat, "ambient", canopy_color)
    sub(mat, "diffuse", canopy_color)

    windshield = E.SubElement(base_link, "visual", name="cockpit_windshield")
    sub(windshield, "pose", "0.14 0 0.065 0 0 0")
    g = E.SubElement(windshield, "geometry")
    sub(E.SubElement(g, "box"), "size", "0.08 0.18 0.030")
    mat = E.SubElement(windshield, "material")
    sub(mat, "ambient", "0.12 0.14 0.18 1")
    sub(mat, "diffuse", "0.18 0.20 0.25 1")
    sub(mat, "specular", "0.95 0.95 0.95 1")

    # 4. Identification Fleet Decal / Racing Stripe
    stripe = E.SubElement(base_link, "visual", name="canopy_id_stripe")
    sub(stripe, "pose", "0 0 0.095 0 0 0")
    g = E.SubElement(stripe, "geometry")
    sub(E.SubElement(g, "box"), "size", "0.26 0.08 0.006")
    mat = E.SubElement(stripe, "material")
    sub(mat, "ambient", "1.0 1.0 1.0 1")
    sub(mat, "diffuse", "1.0 1.0 1.0 1")

    # 4b. Revogreen 22.8V 22000mAh Solid-State 6S Battery Pack (170 x 70 x 70 mm)
    batt_vis = E.SubElement(base_link, "visual", name="revogreen_solid_state_battery")
    sub(batt_vis, "pose", "-0.01 0 0.020 0 0 0")
    g_b = E.SubElement(batt_vis, "geometry")
    sub(E.SubElement(g_b, "box"), "size", "0.170 0.070 0.070")
    m_b = E.SubElement(batt_vis, "material")
    sub(m_b, "ambient", "0.10 0.45 0.20 1")  # Revogreen Green
    sub(m_b, "diffuse", "0.15 0.60 0.25 1")
    sub(m_b, "specular", "0.6 0.6 0.6 1")

    # 4c. SpeedyBee TX800 5.8GHz Video Transmitter & MMCX Antenna
    vtx_box = E.SubElement(base_link, "visual", name="speedybee_tx800")
    sub(vtx_box, "pose", "0.08 0 0.092 0 0 0")
    g_vtx = E.SubElement(vtx_box, "geometry")
    sub(E.SubElement(g_vtx, "box"), "size", "0.028 0.028 0.012")
    m_vtx = E.SubElement(vtx_box, "material")
    sub(m_vtx, "ambient", "0.90 0.75 0.10 1")
    sub(m_vtx, "diffuse", "0.95 0.80 0.15 1")

    vtx_ant = E.SubElement(base_link, "visual", name="speedybee_antenna")
    sub(vtx_ant, "pose", "0.08 0 0.115 0 0 0")
    g_va = E.SubElement(vtx_ant, "geometry")
    cyl_va = E.SubElement(g_va, "cylinder")
    sub(cyl_va, "radius", "0.003")
    sub(cyl_va, "length", "0.035")
    m_va = E.SubElement(vtx_ant, "material")
    sub(m_va, "ambient", "0.15 0.15 0.18 1")
    sub(m_va, "diffuse", "0.20 0.20 0.25 1")

    # 5. GenX High-Gain RTK GNSS Rover Helix Antenna (LH-105A2-B Multi-Band L1+L2+L5)
    # Total mast height 0.12 m above chassis, helical antenna diameter 28mm x 58.5mm
    mast = E.SubElement(base_link, "visual", name="rtk_mast")
    sub(mast, "pose", "-0.08 0 0.100 0 0 0")
    g = E.SubElement(mast, "geometry")
    cyl = E.SubElement(g, "cylinder")
    sub(cyl, "radius", "0.006")
    sub(cyl, "length", "0.070")
    mat = E.SubElement(mast, "material")
    sub(mat, "ambient", "0.20 0.20 0.24 1")
    sub(mat, "diffuse", "0.25 0.25 0.30 1")

    # Gold/brass SMA-J connector collar
    sma_collar = E.SubElement(base_link, "visual", name="rtk_sma_collar")
    sub(sma_collar, "pose", "-0.08 0 0.138 0 0 0")
    g_sma = E.SubElement(sma_collar, "geometry")
    cyl_sma = E.SubElement(g_sma, "cylinder")
    sub(cyl_sma, "radius", "0.008")
    sub(cyl_sma, "length", "0.012")
    mat_sma = E.SubElement(sma_collar, "material")
    sub(mat_sma, "ambient", "0.90 0.75 0.20 1")
    sub(mat_sma, "diffuse", "0.95 0.80 0.25 1")
    sub(mat_sma, "specular", "0.9 0.9 0.9 1")

    # Helical antenna cylindrical body (Φ28 mm × 58.5 mm length)
    helix_body = E.SubElement(base_link, "visual", name="rtk_helix_antenna")
    sub(helix_body, "pose", "-0.08 0 0.173 0 0 0")
    g_helix = E.SubElement(helix_body, "geometry")
    cyl_helix = E.SubElement(g_helix, "cylinder")
    sub(cyl_helix, "radius", "0.014")
    sub(cyl_helix, "length", "0.0585")
    mat_helix = E.SubElement(helix_body, "material")
    sub(mat_helix, "ambient", "0.15 0.15 0.18 1")
    sub(mat_helix, "diffuse", "0.22 0.22 0.26 1")
    sub(mat_helix, "specular", "0.8 0.8 0.8 1")

    # 6. Heavy-Duty Zenith 22-Inch Carbon-Fiber Arms (25mm structural carbon tubes)
    a = ROTOR_XY / 2
    for arm_idx, (ax, ay, yaw) in enumerate([
        (a, -a, -0.7854),
        (-a, a, -0.7854),
        (a, a, 0.7854),
        (-a, -a, 0.7854),
    ]):
        arm_v = E.SubElement(base_link, "visual", name=f"cf_arm_{arm_idx}")
        sub(arm_v, "pose", f"{ax} {ay} 0.025 0 0 {yaw}")
        g = E.SubElement(arm_v, "geometry")
        sub(E.SubElement(g, "box"), "size", f"{ARM_RADIUS_M + 0.010:.3f} 0.038 0.028")
        mat = E.SubElement(arm_v, "material")
        sub(mat, "ambient", "0.26 0.26 0.30 1")
        sub(mat, "diffuse", "0.34 0.34 0.38 1")
        sub(mat, "specular", "0.6 0.6 0.6 1")

    # 7. Safety Warning Arm Identification Sleeves
    sl = round(0.8 * ROTOR_XY, 4)
    for s_idx, (sx, sy, syaw, s_color) in enumerate([
        (sl, -sl, -0.7854, "1.0 0.85 0.0 1"), # Front Left Yellow
        (sl, sl, 0.7854, "1.0 0.85 0.0 1"),   # Front Right Yellow
        (-sl, sl, -0.7854, "1.0 0.20 0.20 1"), # Rear Right Red
        (-sl, -sl, 0.7854, "1.0 0.20 0.20 1"), # Rear Left Red
    ]):
        sleeve = E.SubElement(base_link, "visual", name=f"arm_safety_sleeve_{s_idx}")
        sub(sleeve, "pose", f"{sx} {sy} 0.025 0 0 {syaw}")
        g = E.SubElement(sleeve, "geometry")
        sub(E.SubElement(g, "box"), "size", "0.080 0.042 0.032")
        mat = E.SubElement(sleeve, "material")
        sub(mat, "ambient", s_color)
        sub(mat, "diffuse", s_color)

    # 8. Hobbywing X6-SE 280KV Motor Pods (integrated FOC ESC) & Bells at (±ROTOR_XY, ±ROTOR_XY)
    rxy = ROTOR_XY
    for m_idx, (mx, my) in enumerate([(rxy, -rxy), (-rxy, rxy), (rxy, rxy), (-rxy, -rxy)]):
        mpod = E.SubElement(base_link, "visual", name=f"heavy_motor_pod_{m_idx}")
        sub(mpod, "pose", f"{mx} {my} 0.032 0 0 0")
        g = E.SubElement(mpod, "geometry")
        cyl = E.SubElement(g, "cylinder")
        sub(cyl, "radius", "0.038")
        sub(cyl, "length", "0.045")
        mat = E.SubElement(mpod, "material")
        sub(mat, "ambient", "0.40 0.40 0.45 1")
        sub(mat, "diffuse", "0.50 0.50 0.55 1")
        sub(mat, "specular", "0.8 0.8 0.8 1")

        mbell = E.SubElement(base_link, "visual", name=f"motor_bell_{m_idx}")
        sub(mbell, "pose", f"{mx} {my} 0.052 0 0 0")
        g_bell = E.SubElement(mbell, "geometry")
        cyl_b = E.SubElement(g_bell, "cylinder")
        sub(cyl_b, "radius", "0.036")
        sub(cyl_b, "length", "0.015")
        mat_b = E.SubElement(mbell, "material")
        sub(mat_b, "ambient", "0.75 0.75 0.80 1")
        sub(mat_b, "diffuse", "0.85 0.85 0.90 1")
        sub(mat_b, "specular", "0.95 0.95 0.95 1")

    # 9. Ultra-Bright Navigation Beacon Pods (Front=Green, Rear=Red with Emissive Glow)
    for led_idx, (lx, ly, led_color) in enumerate([
        (rxy, rxy, "0.0 1.0 0.3 1"),   # Front Right (Green)
        (rxy, -rxy, "0.0 1.0 0.3 1"),  # Front Left (Green)
        (-rxy, rxy, "1.0 0.1 0.1 1"),  # Rear Right (Red)
        (-rxy, -rxy, "1.0 0.1 0.1 1"), # Rear Left (Red)
    ]):
        led = E.SubElement(base_link, "visual", name=f"nav_led_{led_idx}")
        sub(led, "pose", f"{lx} {ly} 0.068 0 0 0")
        g = E.SubElement(led, "geometry")
        sub(E.SubElement(g, "sphere"), "radius", "0.016")
        mat = E.SubElement(led, "material")
        sub(mat, "ambient", led_color)
        sub(mat, "diffuse", led_color)
        sub(mat, "emissive", led_color)

    # 10. Heavy-Duty Landing Gear Skids & Angled Struts (Wide 780mm track width)
    for s_name, sy in [("left", -0.39), ("right", 0.39)]:
        skid = E.SubElement(base_link, "visual", name=f"landing_skid_{s_name}")
        sub(skid, "pose", f"0 {sy} -0.2195 0 0 0")
        g = E.SubElement(skid, "geometry")
        sub(E.SubElement(g, "box"), "size", "0.62 0.024 0.024")
        mat = E.SubElement(skid, "material")
        sub(mat, "ambient", "0.85 0.85 0.90 1")
        sub(mat, "diffuse", "0.92 0.92 0.96 1")

        for f_idx, fx in enumerate([-0.20, 0.20]):
            foot = E.SubElement(base_link, "visual", name=f"skid_foot_{s_name}_{f_idx}")
            sub(foot, "pose", f"{fx} {sy} -0.2195 0 0 0")
            g_f = E.SubElement(foot, "geometry")
            sub(E.SubElement(g_f, "box"), "size", "0.080 0.028 0.028")
            mat_f = E.SubElement(foot, "material")
            sub(mat_f, "ambient", "1.0 0.85 0.0 1")
            sub(mat_f, "diffuse", "1.0 0.90 0.0 1")

    # 4 Angled leg struts connecting chassis (y=±0.10, z=0.005) to skids (y=±0.39, z=-0.2195)
    for strut_idx, (sx, sy, s_roll) in enumerate([
        (0.14, -0.245, -0.912),
        (-0.14, -0.245, -0.912),
        (0.14, 0.245, 0.912),
        (-0.14, 0.245, 0.912),
    ]):
        st = E.SubElement(base_link, "visual", name=f"landing_strut_{strut_idx}")
        sub(st, "pose", f"{sx} {sy} -0.107 {s_roll} 0 0")
        g = E.SubElement(st, "geometry")
        sub(E.SubElement(g, "box"), "size", "0.024 0.024 0.367")
        mat = E.SubElement(st, "material")
        sub(mat, "ambient", "0.80 0.80 0.85 1")
        sub(mat, "diffuse", "0.88 0.88 0.92 1")

    # 11. Sleek Carbon Payload Drop Rails on rack_link
    rack_link = m.find("link[@name='rack_link']")
    if rack_link is not None:
        rack_link.find("inertial/mass").text = str(rack_mass)
        r_scale = rack_mass / 0.300
        for axis, orig_val in [("ixx", 0.0003), ("iyy", 0.0003), ("izz", 0.0005)]:
            rack_link.find(f"inertial/inertia/{axis}").text = str(round(orig_val * r_scale, 6))

        for old_v in list(rack_link.findall("visual")):
            rack_link.remove(old_v)

        # Dual carbon mounting rails
        for r_idx, ry in enumerate([-0.10, 0.10]):
            rv = E.SubElement(rack_link, "visual", name=f"rack_rail_{r_idx}")
            sub(rv, "pose", f"0 {ry} 0 0 0 0")
            g = E.SubElement(rv, "geometry")
            sub(E.SubElement(g, "box"), "size", "0.36 0.020 0.016")
            mat = E.SubElement(rv, "material")
            sub(mat, "ambient", "0.25 0.25 0.28 1")
            sub(mat, "diffuse", "0.32 0.32 0.36 1")
            sub(mat, "specular", "0.6 0.6 0.6 1")

        # Transverse structural ribs connecting rails and central spine
        for c_idx, cx in enumerate([-0.12, 0.0, 0.12]):
            cv = E.SubElement(rack_link, "visual", name=f"rack_cross_{c_idx}")
            sub(cv, "pose", f"{cx} 0 0 0 0 0")
            g = E.SubElement(cv, "geometry")
            sub(E.SubElement(g, "box"), "size", "0.016 0.24 0.014")
            mat = E.SubElement(cv, "material")
            sub(mat, "ambient", "0.25 0.25 0.28 1")
            sub(mat, "diffuse", "0.32 0.32 0.36 1")

        # 5 Micro-Servo Release Actuators and Armed Indicator LEDs (Bay 0..4)
        bay_coords = [
            ( 0.090, -0.075),  # Bay 0: Front-Left
            ( 0.090,  0.075),  # Bay 1: Front-Right
            ( 0.000,  0.000),  # Bay 2: Center
            (-0.090, -0.075),  # Bay 3: Aft-Left
            (-0.090,  0.075),  # Bay 4: Aft-Right
        ]
        for b_idx, (bx, by) in enumerate(bay_coords[:pkg_count]):
            # Micro-servo body (anodized black aluminum/polycarbonate)
            s_vis = E.SubElement(rack_link, "visual", name=f"drop_servo_{b_idx}")
            sub(s_vis, "pose", f"{bx} {by} 0.014 0 0 0")
            g_s = E.SubElement(s_vis, "geometry")
            sub(E.SubElement(g_s, "box"), "size", "0.026 0.018 0.022")
            m_s = E.SubElement(s_vis, "material")
            sub(m_s, "ambient", "0.15 0.15 0.18 1")
            sub(m_s, "diffuse", "0.22 0.22 0.25 1")

            # Servo metallic release pin & latch horn
            p_vis = E.SubElement(rack_link, "visual", name=f"servo_pin_{b_idx}")
            sub(p_vis, "pose", f"{bx} {by} -0.005 0 0 0")
            g_p = E.SubElement(p_vis, "geometry")
            cyl_p = E.SubElement(g_p, "cylinder")
            sub(cyl_p, "radius", "0.004")
            sub(cyl_p, "length", "0.018")
            m_p = E.SubElement(p_vis, "material")
            sub(m_p, "ambient", "0.80 0.80 0.85 1")
            sub(m_p, "diffuse", "0.90 0.90 0.95 1")

            # Latch retention collar ring
            c_vis = E.SubElement(rack_link, "visual", name=f"latch_collar_{b_idx}")
            sub(c_vis, "pose", f"{bx} {by} -0.012 0 0 0")
            g_c = E.SubElement(c_vis, "geometry")
            cyl_c = E.SubElement(g_c, "cylinder")
            sub(cyl_c, "radius", "0.038")
            sub(cyl_c, "length", "0.008")
            m_c = E.SubElement(c_vis, "material")
            sub(m_c, "ambient", "0.30 0.30 0.35 1")
            sub(m_c, "diffuse", "0.40 0.40 0.45 1")

            # Green armed/latched status LED indicator
            led_drop = E.SubElement(rack_link, "visual", name=f"bay_status_led_{b_idx}")
            sub(led_drop, "pose", f"{bx} {by + (0.022 if by >= 0 else -0.022)} 0.016 0 0 0")
            g_led = E.SubElement(led_drop, "geometry")
            sub(E.SubElement(g_led, "sphere"), "radius", "0.008")
            m_led = E.SubElement(led_drop, "material")
            sub(m_led, "ambient", "0.0 1.0 0.2 1")
            sub(m_led, "diffuse", "0.0 1.0 0.2 1")
            sub(m_led, "emissive", "0.0 0.8 0.2 1")

    # 12. Rotor Links & 23-Inch MF2311P Propeller Blades with High-Visibility White Tips
    # Blade inertia as a thin rod of length PROP_DIAMETER_M spinning about z
    blade_i = rotor_mass * PROP_DIAMETER_M**2 / 12
    for r in range(4):
        rl = m.find(f"link[@name='rotor_{r}']")
        if rl is not None:
            rl.find("inertial/mass").text = str(rotor_mass)
            for axis, val in [("ixx", rotor_mass * 0.05**2 / 12), ("iyy", blade_i), ("izz", blade_i)]:
                rl.find(f"inertial/inertia/{axis}").text = f"{val:.6e}"
            for old_v in list(rl.findall("visual")):
                rl.remove(old_v)

            hub = E.SubElement(rl, "visual", name=f"prop_hub_{r}")
            sub(hub, "pose", "0 0 0.010 0 0 0")
            g_hub = E.SubElement(hub, "geometry")
            cyl_hub = E.SubElement(g_hub, "cylinder")
            sub(cyl_hub, "radius", "0.020")
            sub(cyl_hub, "length", "0.022")
            m_hub = E.SubElement(hub, "material")
            sub(m_hub, "ambient", "0.75 0.75 0.80 1")
            sub(m_hub, "diffuse", "0.85 0.85 0.90 1")

            pv = E.SubElement(rl, "visual", name=f"prop_blade_{r}")
            sub(pv, "pose", "0 0 0.010 0 0 0")
            g = E.SubElement(pv, "geometry")
            sub(E.SubElement(g, "box"), "size", f"{PROP_DIAMETER_M} 0.040 0.004")
            mat = E.SubElement(pv, "material")
            sub(mat, "ambient", "0.20 0.20 0.22 1")
            sub(mat, "diffuse", "0.26 0.26 0.30 1")
            sub(mat, "specular", "0.6 0.6 0.6 1")

            tip_r = round(PROP_DIAMETER_M / 2 - 0.026, 4)
            for tip_idx, tip_x in enumerate([-tip_r, tip_r]):
                tip = E.SubElement(rl, "visual", name=f"prop_tip_{r}_{tip_idx}")
                sub(tip, "pose", f"{tip_x} 0 0.0105 0 0 0")
                g_tip = E.SubElement(tip, "geometry")
                sub(E.SubElement(g_tip, "box"), "size", "0.052 0.036 0.005")
                m_tip = E.SubElement(tip, "material")
                sub(m_tip, "ambient", "0.95 0.95 0.98 1")
                sub(m_tip, "diffuse", "1.0 1.0 1.0 1")
                sub(m_tip, "emissive", "0.3 0.3 0.3 1")

    # Calibrate MulticopterMotorModel to the A6-M 6.0 kgf peak static thrust per motor (24 kgf total)
    for plug in m.findall("plugin[@name='gz::sim::systems::MulticopterMotorModel']"):
        for tag, val in [
            ("motorConstant", f"{MOTOR_CONSTANT:.4e}"),
            ("maxRotVelocity", f"{MAX_ROT_VELOCITY}"),
            ("timeConstantUp", f"{MOTOR_TIME_CONSTANT_UP}"),
            ("timeConstantDown", f"{MOTOR_TIME_CONSTANT_DOWN}"),
        ]:
            el = plug.find(tag)
            if el is not None:
                el.text = val

    # Set 980mm Zenith wheelbase (ROTOR_XY in X/Y) for 134mm tip clearance with 22in props
    for i_rotor in range(4):
        rl = m.find(f"link[@name='rotor_{i_rotor}']")
        if rl is not None:
            p = rl.find("pose")
            if p is not None:
                x = ROTOR_XY if i_rotor in [0, 2] else -ROTOR_XY
                y = ROTOR_XY if i_rotor in [1, 2] else -ROTOR_XY
                p.text = f"{x} {y} 0.06 0 0 0"

    # Set enlarged frame body collision (0.42 x 0.42 x 0.05m) for real avionics, battery, and payload rack clearance
    c0 = base_link.find("collision[@name='base_link_collision_0']")
    if c0 is not None:
        c0.find('geometry/box/size').text = '0.42 0.42 0.05'

    # Remove old diagonal strut collisions that stick down at y = ±0.098 and cause tipping/rocking
    for old_c in ["base_link_collision_1", "base_link_collision_2"]:
        c_el = base_link.find(f"collision[@name='{old_c}']")
        if c_el is not None:
            base_link.remove(c_el)

    # Set wide, full-length landing gear skid collisions (0.62 x 0.030 x 0.028m at y = ±0.39m)
    # matching visual skids and pads exactly for rock-solid 4-point ground stability
    for skid_name, sy in [("base_link_collision_3", -0.39), ("base_link_collision_4", 0.39)]:
        cs = base_link.find(f"collision[@name='{skid_name}']")
        if cs is not None:
            p_el = cs.find("pose")
            if p_el is not None:
                p_el.text = f"0 {sy} -0.2195 0 0 0"
            s_el = cs.find("geometry/box/size")
            if s_el is not None:
                s_el.text = "0.62 0.030 0.028"
            surf = cs.find("surface")
            if surf is None:
                surf = E.SubElement(cs, "surface")
            fric = surf.find("friction")
            if fric is None:
                fric = E.SubElement(surf, "friction")
            ode_f = fric.find("ode")
            if ode_f is None:
                ode_f = E.SubElement(fric, "ode")
            mu = ode_f.find("mu")
            if mu is None:
                sub(ode_f, "mu", "1.0")
            else:
                mu.text = "1.0"
            mu2 = ode_f.find("mu2")
            if mu2 is None:
                sub(ode_f, "mu2", "1.0")
            else:
                mu2.text = "1.0"
            cont = surf.find("contact")
            if cont is None:
                cont = E.SubElement(surf, "contact")
            ode_c = cont.find("ode")
            if ode_c is None:
                ode_c = E.SubElement(cont, "ode")
            for k, v in [("min_depth", "0.002"), ("max_vel", "0.0"), ("kp", "100000.0"), ("kd", "1.0")]:
                item = ode_c.find(k)
                if item is None:
                    sub(ode_c, k, v)
                else:
                    item.text = v

    # 13. High-Resolution Nadir Search Camera (Fixed Rock-Solid Frame Mount)
    cam_joint = m.find("joint[@name='camera_joint']")
    if cam_joint is None:
        cam_joint = E.SubElement(m, "joint", name="camera_joint", type="fixed")
        E.SubElement(cam_joint, "parent").text = "base_link"
        E.SubElement(cam_joint, "child").text = "camera_link"
    else:
        cam_joint.set("type", "fixed")
        p_el = cam_joint.find("parent")
        if p_el is not None:
            p_el.text = "base_link"
        else:
            E.SubElement(cam_joint, "parent").text = "base_link"
        c_el_j = cam_joint.find("child")
        if c_el_j is not None:
            c_el_j.text = "camera_link"
        else:
            E.SubElement(cam_joint, "child").text = "camera_link"

    # Remove any old gimbal links or joints if present
    for g_item in ["gimbal_roll_link", "gimbal_pitch_link"]:
        gl = m.find(f"link[@name='{g_item}']")
        if gl is not None:
            m.remove(gl)
    for gj in ["gimbal_roll_joint", "gimbal_pitch_joint"]:
        j = m.find(f"joint[@name='{gj}']")
        if j is not None:
            m.remove(j)

    # Update camera_link
    cam_link = m.find("link[@name='camera_link']")
    if cam_link is not None:
        cam_link.find("inertial/mass").text = str(cam_mass)
        p = cam_link.find("pose")
        if p is None:
            E.SubElement(cam_link, "pose").text = "0.15 0 -0.06 0 1.3090 0"
        else:
            p.text = "0.15 0 -0.06 0 1.3090 0"
        for coll in cam_link.findall("collision"):
            cam_link.remove(coll)
        for old_v in cam_link.findall("visual"):
            cam_link.remove(old_v)

        c_vis = E.SubElement(cam_link, "visual", name="camera_body_visual")
        sub(c_vis, "pose", "0 0 0 0 0 0")
        cg = E.SubElement(c_vis, "geometry")
        sub(E.SubElement(cg, "box"), "size", "0.03 0.08 0.025")
        cmat = E.SubElement(c_vis, "material")
        sub(cmat, "ambient", "0.20 0.22 0.26 1")
        sub(cmat, "diffuse", "0.30 0.32 0.38 1")

        l_vis = E.SubElement(cam_link, "visual", name="camera_lens_visual")
        sub(l_vis, "pose", "0 0 -0.015 0 0 0")
        lg = E.SubElement(l_vis, "geometry")
        lcyl = E.SubElement(lg, "cylinder")
        sub(lcyl, "radius", "0.012")
        sub(lcyl, "length", "0.010")
        lmat = E.SubElement(l_vis, "material")
        sub(lmat, "ambient", "0.0 0.8 1.0 1")
        sub(lmat, "diffuse", "0.0 0.8 1.0 1")
        sub(lmat, "emissive", "0.0 0.2 0.3 1")


    for tag, name in [("link", "parcel_1_link"), ("joint", "parcel_1_joint")]:
        el = m.find(f"{tag}[@name='{name}']")
        if el is not None:
            m.remove(el)

    cam = m.find("link[@name='camera_link']/sensor")
    if cam is not None:
        cam.find("topic").text = f"/rescue_{i}/camera/image_raw"
        cam.find("update_rate").text = "30"
        cam.find("camera/image/width").text = "1280"
        cam.find("camera/image/height").text = "960"
        cam_fmt = cam.find("camera/image/format")
        if cam_fmt is not None:
            cam_fmt.text = "R8G8B8"
        else:
            sub(cam.find("camera/image"), "format", "R8G8B8")
        clip_el = cam.find("camera/clip")
        if clip_el is not None:
            if clip_el.find("near") is not None:
                clip_el.find("near").text = "0.05"
            if clip_el.find("far") is not None:
                clip_el.find("far").text = "350.0"
        hfov = cam.find("camera/horizontal_fov")
        if cam.find("gz_frame_id") is None:
            sub(cam, "gz_frame_id", f"rescue_{i}/camera_link")
        else:
            cam.find("gz_frame_id").text = f"rescue_{i}/camera_link"
        if cam.find("frame_id") is None:
            sub(cam, "frame_id", f"rescue_{i}/camera_link")
        else:
            cam.find("frame_id").text = f"rescue_{i}/camera_link"
        if hfov is None:
            E.SubElement(cam.find("camera"), "horizontal_fov").text = str(CAM_HFOV_RAD)
        else:
            hfov.text = str(CAM_HFOV_RAD)

    # 13b. High-Precision GenX Ublox ZED-F9P RTK GNSS Sensor Configuration
    # Configures RTK Fix centimeter-grade positioning (1cm horizontal CEP)
    navsat = base_link.find("sensor[@name='navsat_sensor']")
    if navsat is not None:
        navsat.find("update_rate").text = "20"
        pos_sense = navsat.find("position_sensing")
        if pos_sense is None:
            pos_sense = E.SubElement(navsat, "position_sensing")
        horiz_sense = pos_sense.find("horizontal")
        if horiz_sense is None:
            horiz_sense = E.SubElement(pos_sense, "horizontal")
        h_noise = horiz_sense.find("noise")
        if h_noise is None:
            h_noise = E.SubElement(horiz_sense, "noise", type="gaussian")
            sub(h_noise, "mean", "0.0")
            sub(h_noise, "stddev", "0.01")  # 1 cm RTK precision
        vert_sense = pos_sense.find("vertical")
        if vert_sense is None:
            vert_sense = E.SubElement(pos_sense, "vertical")
        v_noise = vert_sense.find("noise")
        if v_noise is None:
            v_noise = E.SubElement(vert_sense, "noise", type="gaussian")
            sub(v_noise, "mean", "0.0")
            sub(v_noise, "stddev", "0.02")

    # Remove any residual LiDAR links or joints (LiDAR is removed from final ordered BOM)
    for lidar_tag, lidar_item in [("link", "lidar_link"), ("joint", "lidar_joint")]:
        old_lidar = m.find(f"{lidar_tag}[@name='{lidar_item}']")
        if old_lidar is not None:
            m.remove(old_lidar)

    # 14. Emergency Medical / Humanitarian Survival Canisters (High-Visibility 5-Canister Array)
    if pkg_count == 5:
        bay_positions = [
            ( 0.090, -0.075),  # Bay 0: Front-Left
            ( 0.090,  0.075),  # Bay 1: Front-Right
            ( 0.000,  0.000),  # Bay 2: Center
            (-0.090, -0.075),  # Bay 3: Aft-Left
            (-0.090,  0.075),  # Bay 4: Aft-Right
        ]
    else:
        cols = math.ceil(pkg_count / 2) if pkg_count > 0 else 1
        col_spacing = 0.11
        col_start = -(cols - 1) * col_spacing / 2
        bay_positions = []
        for j in range(pkg_count):
            row = j % 2
            col = j // 2
            dx = [-0.10, 0.10][row]
            dy = col_start + col * col_spacing
            bay_positions.append((dx, dy))

    for j in range(pkg_count):
        name = f"parcel_{i}_{j}"
        dx, dy = bay_positions[j]

        plug = E.SubElement(
            m,
            "plugin",
            filename="gz-sim-detachable-joint-system",
            name="gz::sim::systems::DetachableJoint",
        )
        for k, v in [
            ("parent_link", "base_link"),
            ("child_model", name),
            ("child_link", "body"),
            ("detach_topic", f"/{name}/detach"),
            ("attach_topic", f"/{name}/attach"),
            ("output_topic", f"/{name}/state"),
        ]:
            sub(plug, k, v)

        pkg = E.SubElement(w, "model", name=name)
        sub(pkg, "pose", f"{east + dx} {-5 + dy} 0.130 0 0 0")
        link = E.SubElement(pkg, "link", name="body")
        inert = E.SubElement(link, "inertial")
        sub(inert, "mass", PKG_MASS)
        I = E.SubElement(inert, "inertia")
        for k, v in [
            ("ixx", pkg_ixx),
            ("iyy", pkg_iyy),
            ("izz", pkg_izz),
            ("ixy", 0),
            ("ixz", 0),
            ("iyz", 0),
        ]:
            sub(I, k, v)

        # Collision box (68mm x 68mm x 110mm) - ODE/DART stable, prevents cylinder rolling/AABB singularities
        c_el = E.SubElement(link, "collision", name="collision")
        cg = E.SubElement(c_el, "geometry")
        box_c = E.SubElement(cg, "box")
        sub(box_c, "size", f"{cr * 2:.3f} {cr * 2:.3f} {ch:.3f}")
        surface = E.SubElement(c_el, "surface")
        friction = E.SubElement(surface, "friction")
        ode_f = E.SubElement(friction, "ode")
        sub(ode_f, "mu", "1.0")
        sub(ode_f, "mu2", "1.0")
        bounce = E.SubElement(surface, "bounce")
        sub(bounce, "restitution_coefficient", "0.1")
        sub(bounce, "threshold", "100000.0")
        contact = E.SubElement(surface, "contact")
        ode_c = E.SubElement(contact, "ode")
        sub(ode_c, "soft_cfm", "0.001")
        sub(ode_c, "soft_erp", "0.2")
        sub(ode_c, "kp", "1e5")
        sub(ode_c, "kd", "1.0")
        sub(ode_c, "max_vel", "0.1")
        sub(ode_c, "min_depth", "0.001")

        # 1. Main Capsule Shell: Vivid High-Gloss International Rescue Orange
        v_body = E.SubElement(link, "visual", name="canister_body")
        vg = E.SubElement(v_body, "geometry")
        cyl_body = E.SubElement(vg, "cylinder")
        sub(cyl_body, "radius", f"{cr}")
        sub(cyl_body, "length", f"{ch}")
        v_mat = E.SubElement(v_body, "material")
        sub(v_mat, "ambient", "1.0 0.35 0.0 1")
        sub(v_mat, "diffuse", "1.0 0.42 0.0 1")
        sub(v_mat, "specular", "0.8 0.8 0.8 1")

        # 2. Central Reflective Medical Band: Brilliant Pure White
        v_band = E.SubElement(link, "visual", name="canister_medical_band")
        sub(v_band, "pose", "0 0 0 0 0 0")
        v_bg = E.SubElement(v_band, "geometry")
        cyl_band = E.SubElement(v_bg, "cylinder")
        sub(cyl_band, "radius", f"{cr + 0.001}")
        sub(cyl_band, "length", "0.040")
        v_bmat = E.SubElement(v_band, "material")
        sub(v_bmat, "ambient", "0.95 0.95 0.98 1")
        sub(v_bmat, "diffuse", "1.0 1.0 1.0 1")
        sub(v_bmat, "specular", "0.9 0.9 0.9 1")

        # 3. Bold Red Cross Medical Emblem (Horizontal & Vertical)
        v_cross_h = E.SubElement(link, "visual", name="canister_cross_h")
        sub(v_cross_h, "pose", "0 0 0 0 0 0")
        v_chg = E.SubElement(v_cross_h, "geometry")
        sub(E.SubElement(v_chg, "box"), "size", f"{cr * 2 + 0.003} 0.024 0.008")
        v_crmat = E.SubElement(v_cross_h, "material")
        sub(v_crmat, "ambient", "1.0 0.05 0.05 1")
        sub(v_crmat, "diffuse", "1.0 0.08 0.08 1")

        v_cross_v = E.SubElement(link, "visual", name="canister_cross_v")
        sub(v_cross_v, "pose", "0 0 0 0 0 0")
        v_cvg = E.SubElement(v_cross_v, "geometry")
        sub(E.SubElement(v_cvg, "box"), "size", f"0.024 {cr * 2 + 0.003} 0.008")
        v_cvmat = E.SubElement(v_cross_v, "material")
        sub(v_cvmat, "ambient", "1.0 0.05 0.05 1")
        sub(v_cvmat, "diffuse", "1.0 0.08 0.08 1")

        # 4. Top Quick-Release Suspension Lug (locks directly into servo latch)
        v_lug = E.SubElement(link, "visual", name="canister_release_lug")
        sub(v_lug, "pose", f"0 0 {ch / 2 + 0.010} 0 0 0")
        v_lg = E.SubElement(v_lug, "geometry")
        cyl_lug = E.SubElement(v_lg, "cylinder")
        sub(cyl_lug, "radius", "0.018")
        sub(cyl_lug, "length", "0.020")
        v_lmat = E.SubElement(v_lug, "material")
        sub(v_lmat, "ambient", "0.80 0.80 0.85 1")
        sub(v_lmat, "diffuse", "0.90 0.90 0.95 1")
        sub(v_lmat, "specular", "0.9 0.9 0.9 1")

        # 5. Bottom Shock-Absorbing Rubber Bumper
        v_bump = E.SubElement(link, "visual", name="canister_bottom_bumper")
        sub(v_bump, "pose", f"0 0 {-ch / 2 - 0.006} 0 0 0")
        v_bmg = E.SubElement(v_bump, "geometry")
        cyl_bm = E.SubElement(v_bmg, "cylinder")
        sub(cyl_bm, "radius", f"{cr - 0.002}")
        sub(cyl_bm, "length", "0.012")
        v_bmmat = E.SubElement(v_bump, "material")
        sub(v_bmmat, "ambient", "0.20 0.20 0.24 1")
        sub(v_bmmat, "diffuse", "0.25 0.25 0.30 1")

    w.append(m)

    # Initial AUW and Gazebo SITL actuator hover throttle calculation
    initial_auw = dry_mass + pkg_count * PKG_MASS
    w_total_n = initial_auw * 9.80665
    f_per_motor_n = w_total_n / 4.0
    omega_req = math.sqrt(f_per_motor_n / MOTOR_CONSTANT)
    u_sitl_hover = max(0.2, min(0.9, (omega_req - 150.0) / 850.0))

    # Instantiate runtime directory for each drone instance
    runtime = ROOT / f"runtime_{i}"
    if not (runtime / "etc").exists():
        shutil.copytree(BASE / "px4-runtime/etc", runtime / "etc")

    for pfile in (runtime / "fs").glob("parameters*.bson"):
        try:
            pfile.unlink()
        except Exception:
            pass

    af = runtime / "etc/init.d-posix/airframes/4026_gz_rescue_heavy"
    text = (BASE / "px4-runtime/etc/init.d-posix/airframes/4026_gz_rescue_heavy").read_text()
    text = text.replace("param set-default MPC_THR_HOVER 0.45\n", "")
    text += (
        "\n# Hardware-aware SITL search configuration\n"
        f"param set-default MPC_THR_HOVER {u_sitl_hover:.3f}\n"
        f"param set MPC_THR_HOVER {u_sitl_hover:.3f}\n"
        "param set-default MPC_THR_MAX 1.0\n"
        "param set-default MPC_TKO_RAMP_T 2.0\n"
        "param set-default MPC_TKO_SPEED 2.5\n"
        "param set MPC_TKO_SPEED 2.5\n"
        "param set-default MPC_XY_CRUISE 12.0\n"
        "param set MPC_XY_CRUISE 12.0\n"
        "param set-default MPC_XY_VEL_MAX 14.0\n"
        "param set MPC_XY_VEL_MAX 14.0\n"
        "param set-default MPC_ACC_HOR 5.0\n"
        "param set MPC_ACC_HOR 5.0\n"
        "param set-default MPC_ACC_HOR_MAX 6.0\n"
        "param set MPC_ACC_HOR_MAX 6.0\n"
        "param set-default MPC_Z_V_AUTO_UP 4.0\n"
        "param set MPC_Z_V_AUTO_UP 4.0\n"
        "param set-default MPC_Z_VEL_MAX_UP 4.5\n"
        "param set MPC_Z_VEL_MAX_UP 4.5\n"
        "param set-default MPC_Z_V_AUTO_DN 3.2\n"
        "param set MPC_Z_V_AUTO_DN 3.2\n"
        "param set-default MPC_Z_VEL_MAX_DN 3.6\n"
        "param set MPC_Z_VEL_MAX_DN 3.6\n"
        "param set-default MPC_ACC_UP_MAX 5.5\n"
        "param set MPC_ACC_UP_MAX 5.5\n"
        "param set-default MPC_ACC_DOWN_MAX 4.5\n"
        "param set MPC_ACC_DOWN_MAX 4.5\n"
        "param set-default MPC_LAND_ALT1 2.5\n"
        "param set MPC_LAND_ALT1 2.5\n"
        "param set-default MPC_LAND_ALT2 1.0\n"
        "param set MPC_LAND_ALT2 1.0\n"
        "param set-default MPC_LAND_SPEED 1.2\n"
        "param set MPC_LAND_SPEED 1.2\n"
        "\n# Control allocation geometry for the 980mm Zenith wheelbase (FRD body frame)\n"
        f"param set-default CA_ROTOR0_PX {ROTOR_XY}\n"
        f"param set-default CA_ROTOR0_PY {ROTOR_XY}\n"
        f"param set-default CA_ROTOR1_PX {-ROTOR_XY}\n"
        f"param set-default CA_ROTOR1_PY {-ROTOR_XY}\n"
        f"param set-default CA_ROTOR2_PX {ROTOR_XY}\n"
        f"param set-default CA_ROTOR2_PY {-ROTOR_XY}\n"
        f"param set-default CA_ROTOR3_PX {-ROTOR_XY}\n"
        f"param set-default CA_ROTOR3_PY {ROTOR_XY}\n"
    )
    af.write_text(text)

# Ground RTK Survey Grade CORS Base Station Antenna (RoboKits LS-125-A) on launch pad
rtk_base_station = E.SubElement(w, "model", name="rtk_cors_base_station")
sub(rtk_base_station, "pose", "0 -10 0 0 0 0")
sub(rtk_base_station, "static", "true")
base_st_link = E.SubElement(rtk_base_station, "link", name="base_station_link")

# Survey Tripod (3 yellow tubular legs)
for tr_idx, (tx, ty, t_pitch, t_yaw) in enumerate([
    (0.0, -0.35, -0.25, 0.0),
    (0.30, 0.20, 0.15, 2.094),
    (-0.30, 0.20, 0.15, -2.094),
]):
    leg = E.SubElement(base_st_link, "visual", name=f"tripod_leg_{tr_idx}")
    sub(leg, "pose", f"{tx} {ty} 0.70 {t_pitch} 0 {t_yaw}")
    lg = E.SubElement(leg, "geometry")
    cyl_l = E.SubElement(lg, "cylinder")
    sub(cyl_l, "radius", "0.018")
    sub(cyl_l, "length", "1.45")
    mat_l = E.SubElement(leg, "material")
    sub(mat_l, "ambient", "1.0 0.80 0.0 1")  # Safety Survey Yellow
    sub(mat_l, "diffuse", "1.0 0.85 0.0 1")

# Tripod center column and tribrach mount
tribrach = E.SubElement(base_st_link, "visual", name="tribrach_mount")
sub(tribrach, "pose", "0 0 1.40 0 0 0")
tb_g = E.SubElement(tribrach, "geometry")
sub(E.SubElement(tb_g, "box"), "size", "0.15 0.15 0.08")
tb_m = E.SubElement(tribrach, "material")
sub(tb_m, "ambient", "0.25 0.25 0.28 1")
sub(tb_m, "diffuse", "0.35 0.35 0.40 1")

# Survey-Grade CORS Choke-Ring Antenna (LS-125-A) - 150mm dia flying-saucer disk
cors_ant = E.SubElement(base_st_link, "visual", name="cors_choke_ring_antenna")
sub(cors_ant, "pose", "0 0 1.48 0 0 0")
ca_g = E.SubElement(cors_ant, "geometry")
cyl_ca = E.SubElement(ca_g, "cylinder")
sub(cyl_ca, "radius", "0.075")
sub(cyl_ca, "length", "0.045")
ca_m = E.SubElement(cors_ant, "material")
sub(ca_m, "ambient", "0.92 0.92 0.96 1")  # Brilliant Survey White
sub(ca_m, "diffuse", "1.0 1.0 1.0 1")
sub(ca_m, "specular", "0.9 0.9 0.9 1")

# Antenna Dome / Radome
cors_dome = E.SubElement(base_st_link, "visual", name="cors_radome")
sub(cors_dome, "pose", "0 0 1.51 0 0 0")
cd_g = E.SubElement(cors_dome, "geometry")
sub(E.SubElement(cd_g, "sphere"), "radius", "0.055")
cd_m = E.SubElement(cors_dome, "material")
sub(cd_m, "ambient", "0.95 0.95 1.0 1")
sub(cd_m, "diffuse", "1.0 1.0 1.0 1")

# Clean Gazebo person models (no pads, no box overlays)

# Ensure Gazebo GUI camera has a panoramic overview of both drones on the launch pad
gui_elem = w.find("gui")
if gui_elem is None:
    gui_elem = E.SubElement(w, "gui", fullscreen="0")
cam_elem = gui_elem.find("camera[@name='user_camera']")
if cam_elem is None:
    cam_elem = E.SubElement(gui_elem, "camera", name="user_camera")
    sub(cam_elem, "pose", "0 -14 3.8 0 0.22 1.5708")
    sub(cam_elem, "view_controller", "orbit")

raw_xml = E.tostring(w, encoding="unicode")
cleaned_lines = [line.rstrip() for line in raw_xml.splitlines()]
full_sdf = (
    "<?xml version='1.0' encoding='utf-8'?>\n<sdf version=\"1.9\">\n"
    + "\n".join(cleaned_lines)
    + "\n</sdf>\n"
)
(ROOT / "dual_rescue.sdf").write_text(full_sdf)

print(
    f"Built {active_profile_name} world with {len(drone_specs)} drones, "
    f"{total_parcels_built} total packages ({PKG_MASS} kg each)."
)
