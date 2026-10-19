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

# Remove any pre-existing drone models and parcels from template world
for existing in list(w.findall("model")):
    m_name = existing.get("name", "")
    if m_name.startswith("rescue_") or m_name.startswith("parcel_"):
        w.remove(existing)

total_parcels_built = 0

for d_spec in drone_specs:
    i = d_spec["id"]
    east = d_spec["east_start"]
    pkg_count = d_spec["packages"]
    total_parcels_built += pkg_count

    m = E.parse(BASE / "imported/PX4-Autopilot/Tools/simulation/gz/models/rescue_heavy/model.sdf").getroot().find("model")
    m.set("name", f"rescue_{i}")
    sub(m, "pose", f"{east} -5 0.24 0 0 0")

    # Merge rescue_heavy_base links and joints directly into model so masses are authoritative
    base_m = E.parse(BASE / "imported/PX4-Autopilot/Tools/simulation/gz/models/rescue_heavy_base/model.sdf").getroot().find("model")
    inc = m.find("include")
    if inc is not None:
        m.remove(inc)
    for child in list(base_m):
        if child.tag in ("link", "joint"):
            m.append(copy.deepcopy(child))

    # Authoritative hardware masses from simulation.hardware.config
    dry_mass = get_drone_dry_mass_kg(min(i, FLEET_SIZE - 1))
    rack_mass = (
        HARDWARE_BOM["payload_drop_rack_4slot"].mass_kg
        if pkg_count > 2
        else HARDWARE_BOM["payload_drop_rack_2slot"].mass_kg
    )
    cam_mass = HARDWARE_BOM["oak_d_lite"].mass_kg
    gimbal_mass = HARDWARE_BOM["gimbal"].mass_kg if "gimbal" in HARDWARE_BOM else 0.065
    rotor_mass = HARDWARE_BOM["propellers"].mass_kg / 4.0
    base_mass = round(dry_mass - (rack_mass + cam_mass + gimbal_mass + 4 * rotor_mass), 4)

    # Set base_link mass and scale inertia
    base_link = m.find("link[@name='base_link']")
    base_link.find("inertial/mass").text = str(base_mass)
    scale = (base_mass / 3.2) * (0.850 / 0.710) ** 2
    for axis, orig_val in [("ixx", 0.077), ("iyy", 0.077), ("izz", 0.133)]:
        base_link.find(f"inertial/inertia/{axis}").text = str(round(orig_val * scale, 6))

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

    # 5. RTK GNSS Antenna Mast & Dome (Total height 0.18 m above chassis)
    mast = E.SubElement(base_link, "visual", name="rtk_mast")
    sub(mast, "pose", "-0.08 0 0.125 0 0 0")
    g = E.SubElement(mast, "geometry")
    cyl = E.SubElement(g, "cylinder")
    sub(cyl, "radius", "0.008")
    sub(cyl, "length", "0.090")
    mat = E.SubElement(mast, "material")
    sub(mat, "ambient", "0.85 0.85 0.90 1")
    sub(mat, "diffuse", "0.95 0.95 1.0 1")

    dome = E.SubElement(base_link, "visual", name="rtk_antenna_dome")
    sub(dome, "pose", "-0.08 0 0.175 0 0 0")
    g = E.SubElement(dome, "geometry")
    cyl = E.SubElement(g, "cylinder")
    sub(cyl, "radius", "0.040")
    sub(cyl, "length", "0.018")
    mat = E.SubElement(dome, "material")
    sub(mat, "ambient", "0.95 0.95 0.98 1")
    sub(mat, "diffuse", "1.0 1.0 1.0 1")
    sub(mat, "specular", "0.8 0.8 0.8 1")

    # 6. Heavy-Duty 850mm Carbon-Fiber Arms (42mm x 32mm structural carbon tubes)
    for arm_idx, (ax, ay, yaw) in enumerate([
        (0.150, -0.150, -0.7854),
        (-0.150, 0.150, -0.7854),
        (0.150, 0.150, 0.7854),
        (-0.150, -0.150, 0.7854),
    ]):
        arm_v = E.SubElement(base_link, "visual", name=f"cf_arm_{arm_idx}")
        sub(arm_v, "pose", f"{ax} {ay} 0.025 0 0 {yaw}")
        g = E.SubElement(arm_v, "geometry")
        sub(E.SubElement(g, "box"), "size", "0.435 0.042 0.032")
        mat = E.SubElement(arm_v, "material")
        sub(mat, "ambient", "0.26 0.26 0.30 1")
        sub(mat, "diffuse", "0.34 0.34 0.38 1")
        sub(mat, "specular", "0.6 0.6 0.6 1")

    # 7. Safety Warning Arm Identification Sleeves
    for s_idx, (sx, sy, syaw, s_color) in enumerate([
        (0.24, -0.24, -0.7854, "1.0 0.85 0.0 1"), # Front Left Yellow
        (0.24, 0.24, 0.7854, "1.0 0.85 0.0 1"),   # Front Right Yellow
        (-0.24, 0.24, -0.7854, "1.0 0.20 0.20 1"), # Rear Right Red
        (-0.24, -0.24, 0.7854, "1.0 0.20 0.20 1"), # Rear Left Red
    ]):
        sleeve = E.SubElement(base_link, "visual", name=f"arm_safety_sleeve_{s_idx}")
        sub(sleeve, "pose", f"{sx} {sy} 0.025 0 0 {syaw}")
        g = E.SubElement(sleeve, "geometry")
        sub(E.SubElement(g, "box"), "size", "0.080 0.046 0.036")
        mat = E.SubElement(sleeve, "material")
        sub(mat, "ambient", s_color)
        sub(mat, "diffuse", s_color)

    # 8. Heavy-Lift Motor Nacelles & Bells at (±0.300, ±0.300)
    for m_idx, (mx, my) in enumerate([(0.300, -0.300), (-0.300, 0.300), (0.300, 0.300), (-0.300, -0.300)]):
        mpod = E.SubElement(base_link, "visual", name=f"heavy_motor_pod_{m_idx}")
        sub(mpod, "pose", f"{mx} {my} 0.035 0 0 0")
        g = E.SubElement(mpod, "geometry")
        cyl = E.SubElement(g, "cylinder")
        sub(cyl, "radius", "0.040")
        sub(cyl, "length", "0.048")
        mat = E.SubElement(mpod, "material")
        sub(mat, "ambient", "0.45 0.45 0.50 1")
        sub(mat, "diffuse", "0.58 0.58 0.64 1")
        sub(mat, "specular", "0.8 0.8 0.8 1")

        mbell = E.SubElement(base_link, "visual", name=f"motor_bell_{m_idx}")
        sub(mbell, "pose", f"{mx} {my} 0.056 0 0 0")
        g_bell = E.SubElement(mbell, "geometry")
        cyl_b = E.SubElement(g_bell, "cylinder")
        sub(cyl_b, "radius", "0.038")
        sub(cyl_b, "length", "0.016")
        mat_b = E.SubElement(mbell, "material")
        sub(mat_b, "ambient", "0.75 0.75 0.80 1")
        sub(mat_b, "diffuse", "0.85 0.85 0.90 1")
        sub(mat_b, "specular", "0.95 0.95 0.95 1")

    # 9. Ultra-Bright Navigation Beacon Pods (Front=Green, Rear=Red with Emissive Glow)
    for led_idx, (lx, ly, led_color) in enumerate([
        (0.300, 0.300, "0.0 1.0 0.3 1"),   # Front Right (Green)
        (0.300, -0.300, "0.0 1.0 0.3 1"),  # Front Left (Green)
        (-0.300, 0.300, "1.0 0.1 0.1 1"),  # Rear Right (Red)
        (-0.300, -0.300, "1.0 0.1 0.1 1"), # Rear Left (Red)
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

    # 12. Rotor Links & 13-Inch Spinning Propeller Blades with High-Visibility White Tips
    for r in range(4):
        rl = m.find(f"link[@name='rotor_{r}']")
        if rl is not None:
            rl.find("inertial/mass").text = str(rotor_mass)
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
            sub(E.SubElement(g, "box"), "size", "0.33 0.034 0.004")
            mat = E.SubElement(pv, "material")
            sub(mat, "ambient", "0.20 0.20 0.22 1")
            sub(mat, "diffuse", "0.26 0.26 0.30 1")
            sub(mat, "specular", "0.6 0.6 0.6 1")

            for tip_idx, tip_x in enumerate([-0.14, 0.14]):
                tip = E.SubElement(rl, "visual", name=f"prop_tip_{r}_{tip_idx}")
                sub(tip, "pose", f"{tip_x} 0 0.0105 0 0 0")
                g_tip = E.SubElement(tip, "geometry")
                sub(E.SubElement(g_tip, "box"), "size", "0.052 0.036 0.005")
                m_tip = E.SubElement(tip, "material")
                sub(m_tip, "ambient", "0.95 0.95 0.98 1")
                sub(m_tip, "diffuse", "1.0 1.0 1.0 1")
                sub(m_tip, "emissive", "0.3 0.3 0.3 1")

    # Calibrate MulticopterMotorModel to 2.600 kgf peak static thrust per motor (10.4 kgf total)
    for plug in m.findall("plugin[@name='gz::sim::systems::MulticopterMotorModel']"):
        mc = plug.find("motorConstant")
        if mc is not None:
            mc.text = "2.55e-05"

    # Set exact 850mm wheelbase (0.300m in X/Y, <900mm limit) for optimal real-drone propeller clearance (142.8mm)
    for i_rotor in range(4):
        rl = m.find(f"link[@name='rotor_{i_rotor}']")
        if rl is not None:
            p = rl.find("pose")
            if p is not None:
                x = 0.300 if i_rotor in [0, 2] else -0.300
                y = 0.300 if i_rotor in [1, 2] else -0.300
                p.text = f"{x} {y} 0.06 0 0 0"

    # Set enlarged frame body collision (0.42 x 0.42 x 0.05m) for real avionics, battery, and payload rack clearance
    c0 = base_link.find("collision[@name='base_link_collision_0']")
    if c0 is not None:
        c0.find('geometry/box/size').text = '0.42 0.42 0.05'

    # Set wide landing gear track (780mm track width) for crosswind touchdown stability
    c3 = base_link.find("collision[@name='base_link_collision_3']")
    if c3 is not None:
        c3.find('pose').text = '0 -0.39 -.2195 0 0 0'
    c4 = base_link.find("collision[@name='base_link_collision_4']")
    if c4 is not None:
        c4.find('pose').text = '0 0.39 -.2195 0 0 0'

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
        cam.find("update_rate").text = "20"
        cam.find("camera/image/width").text = "960"
        cam.find("camera/image/height").text = "720"
        hfov = cam.find("camera/horizontal_fov")
        if hfov is None:
            E.SubElement(cam.find("camera"), "horizontal_fov").text = "1.5708"
        else:
            hfov.text = "1.5708"

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
    omega_req = math.sqrt(f_per_motor_n / 2.55e-05)
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
        "param set-default MPC_XY_CRUISE 10\n"
        "param set-default MPC_XY_VEL_MAX 10\n"
        "param set-default MPC_Z_VEL_MAX_UP 4\n"
        "param set-default MPC_Z_VEL_MAX_DN 2\n"
    )
    af.write_text(text)

# Equip all 10 flood survivors with high-visibility international orange SOLAS rescue vests
for s_idx in range(1, 11):
    s_mod = w.find(f"model[@name='survivor_{s_idx}']")
    if s_mod is not None:
        b_link = s_mod.find("link[@name='body']")
        if b_link is not None:
            if b_link.find("visual[@name='rescue_life_jacket']") is None:
                vest = E.SubElement(b_link, "visual", name="rescue_life_jacket")
                sub(vest, "pose", "0 0 0.45 0 0 0")
                g = E.SubElement(vest, "geometry")
                sub(E.SubElement(g, "box"), "size", "0.50 0.40 0.60")
                mat = E.SubElement(vest, "material")
                sub(mat, "ambient", "1.0 0.35 0.0 1")
                sub(mat, "diffuse", "1.0 0.45 0.0 1")
                sub(mat, "emissive", "0.25 0.08 0.0 1")

                tape = E.SubElement(b_link, "visual", name="solas_retro_tape")
                sub(tape, "pose", "0 0 0.65 0 0 0")
                g_t = E.SubElement(tape, "geometry")
                sub(E.SubElement(g_t, "box"), "size", "0.52 0.42 0.10")
                mat_t = E.SubElement(tape, "material")
                sub(mat_t, "ambient", "0.95 0.95 0.95 1")
                sub(mat_t, "diffuse", "1.0 1.0 1.0 1")
                sub(mat_t, "emissive", "0.4 0.4 0.4 1")

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
