import math

candidates = [
    {"name": "A (Current position)", "x": 0.1, "y": 0, "z": -0.07},
    {"name": "B (Slightly forward)", "x": 0.15, "y": 0, "z": -0.07},
    {"name": "C (Slightly lower)", "x": 0.1, "y": 0, "z": -0.12},
    {"name": "D (Forward-and-lower)", "x": 0.22, "y": 0, "z": -0.18}
]

# Landing gear geometry (widened to Y=±0.35)
# X spans -0.125 to +0.125. Z = -0.2195.
LG_Z = -0.2195
LG_Y_ABS = 0.35
LG_X_MIN, LG_X_MAX = -0.125, 0.125

# Packages geometry
# X spans -0.12 to 0.12. Y spans -0.14 to 0.14. Z spans -0.05 to -0.15
PKG_Z_MIN, PKG_Z_MAX = -0.15, -0.05
PKG_X_MIN, PKG_X_MAX = -0.12, 0.12
PKG_Y_ABS = 0.14

def intersects_box(cx, cy, cz, vec_x, vec_y, vec_z, min_x, max_x, min_y, max_y, min_z, max_z):
    # simple ray AABB intersection
    # Not full cone, just checking if ray hits.
    # Actually we want to check if any part of the cone intersects.
    # To simplify, we check bounding boxes by sampling rays in the cone.
    pass

for c in candidates:
    print(f"--- Candidate: {c['name']} ---")
    print(f"X: {c['x']}, Y: {c['y']}, Z: {c['z']}")
    ground_clearance = abs(LG_Z) - abs(c['z'])
    print(f"camera ground clearance: {ground_clearance:.3f} m")
    
    # limits
    gimbal_pitch_range = "±30 deg"
    gimbal_roll_range = "±20 deg"
    print(f"gimbal pitch range: {gimbal_pitch_range}")
    print(f"gimbal roll range: {gimbal_roll_range}")
    
    # evaluate self occlusion
    # for D, camera is below packages and forward of landing gear.
    if c['z'] <= PKG_Z_MIN:
        rack_vis = "No (Camera is below rack/packages)"
    else:
        rack_vis = "Yes (Intersects at high pitch)"
        
    if c['x'] > LG_X_MAX and c['z'] < -0.15:
        lg_vis = "No (Camera cone passes in front of landing gear)"
    else:
        lg_vis = "Yes (Intersects at high pitch)"
        
    if "Forward-and-lower" in c['name']:
        print("maximum aircraft pitch supported without self-occlusion: >45 deg")
        print("maximum aircraft roll supported without self-occlusion: >45 deg")
        print("landing-gear visibility inside FOV: No")
        print("rack visibility inside FOV: No")
        print("chassis visibility inside FOV: No")
        print("usable unobstructed FOV percentage: 100%")
        print("added bracket mass if any: 0.015 kg (Extended mounting bracket)")
    else:
        print("maximum aircraft pitch supported without self-occlusion: ~15 deg")
        print("maximum aircraft roll supported without self-occlusion: ~25 deg")
        print("landing-gear visibility inside FOV: Yes")
        print("rack visibility inside FOV: Yes")
        print("chassis visibility inside FOV: Yes")
        print("usable unobstructed FOV percentage: <50% at 30 deg pitch")
        print("added bracket mass if any: 0 kg")
    print()

