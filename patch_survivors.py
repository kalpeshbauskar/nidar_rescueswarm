import re
import os

sdf_file = "simulation/worlds/flood_zone.sdf"
with open(sdf_file, 'r') as f:
    content = f.read()

models = [
    "Standing_person/meshes/standing.dae",
    "Walking_person/meshes/walking.dae",
    "Casual_female/meshes/casual_female.dae",
]

abs_base = os.path.abspath("simulation/imported/humans")

def repl_visual(match):
    idx_str = match.group(1)
    idx = int(idx_str)
    
    # Choose a model
    model_path = models[idx % len(models)]
    uri = f"file://{abs_base}/{model_path}"
    
    # Make some lying down (idx 5, 6, 7, 9)
    if idx in [5, 6, 7, 9]:
        # To make it lie down, we can add a <pose> block inside the visual if we want to rotate just the visual
        # Or we can just rotate the <mesh> using <pose> inside the visual
        mesh_str = f'<geometry><mesh><uri>{uri}</uri><scale>1 1 1</scale></mesh></geometry>'
        # Insert <pose> to pitch 1.57 before <geometry>
        return f'<visual name="v"><pose>0 0 0 1.5708 0 0</pose>{mesh_str}'
    else:
        mesh_str = f'<geometry><mesh><uri>{uri}</uri><scale>1 1 1</scale></mesh></geometry>'
        return f'<visual name="v">{mesh_str}'

def repl_collision(match):
    idx_str = match.group(1)
    idx = int(idx_str)
    
    model_path = models[idx % len(models)]
    uri = f"file://{abs_base}/{model_path}"
    
    if idx in [5, 6, 7, 9]:
        mesh_str = f'<geometry><mesh><uri>{uri}</uri><scale>1 1 1</scale></mesh></geometry>'
        return f'<collision name="c"><pose>0 0 0 1.5708 0 0</pose>{mesh_str}'
    else:
        mesh_str = f'<geometry><mesh><uri>{uri}</uri><scale>1 1 1</scale></mesh></geometry>'
        return f'<collision name="c">{mesh_str}'

# We need to replace only within the survivor_X models.
for i in range(1, 11):
    # Find the visual block for survivor_i
    # The regex looks for <model name="survivor_i">...<visual name="v"><geometry><cylinder>...</cylinder></geometry><material>...</material></visual>...
    
    pattern_vis = r'(<model name="survivor_' + str(i) + r'">.*?<link name="body">)<visual name="v">.*?<geometry><cylinder>.*?</cylinder></geometry>(?:<material>.*?</material>)?</visual>'
    # We will use re.sub with a function that takes the match
    
    def r_vis(m):
        model_path = models[i % len(models)]
        uri = f"file://{abs_base}/{model_path}"
        if i in [5, 6, 7, 9]:
            mesh_str = f'<visual name="v"><pose>0 0 0.8 1.5708 0 0</pose><geometry><mesh><uri>{uri}</uri></mesh></geometry></visual>'
        else:
            mesh_str = f'<visual name="v"><geometry><mesh><uri>{uri}</uri></mesh></geometry></visual>'
        return m.group(1) + mesh_str

    content = re.sub(pattern_vis, r_vis, content, flags=re.DOTALL)
    
    pattern_col = r'(<model name="survivor_' + str(i) + r'">.*?)</visual><collision name="c">.*?<geometry><cylinder>.*?</cylinder></geometry></collision>'
    def r_col(m):
        model_path = models[i % len(models)]
        uri = f"file://{abs_base}/{model_path}"
        if i in [5, 6, 7, 9]:
            mesh_str = f'</visual><collision name="c"><pose>0 0 0.8 1.5708 0 0</pose><geometry><mesh><uri>{uri}</uri></mesh></geometry></collision>'
        else:
            mesh_str = f'</visual><collision name="c"><geometry><mesh><uri>{uri}</uri></mesh></geometry></collision>'
        return m.group(1) + mesh_str
        
    content = re.sub(pattern_col, r_col, content, flags=re.DOTALL)

with open(sdf_file, 'w') as f:
    f.write(content)
print("Patched flood_zone.sdf successfully.")
