import yaml
import os

rviz_path = 'ros2_ws/src/nidar_vision/config/rviz/nidar_vision.rviz'
with open(rviz_path, 'r') as f:
    config = yaml.safe_load(f)

displays = config.get('Visualization Manager', {}).get('Displays', [])
has_drone_1 = False
for d in displays:
    if d.get('Name') == 'Raw Image 1':
        has_drone_1 = True
        break

if not has_drone_1:
    raw_0 = next(d for d in displays if d['Name'] == 'Raw Image')
    raw_0['Name'] = 'Raw Image 0'
    ann_0 = next(d for d in displays if d['Name'] == 'Annotated Image')
    ann_0['Name'] = 'Annotated Image 0'
    
    raw_1 = raw_0.copy()
    raw_1['Name'] = 'Raw Image 1'
    raw_1['Topic']['Value'] = '/rescue_1/camera/image_raw'
    
    ann_1 = ann_0.copy()
    ann_1['Name'] = 'Annotated Image 1'
    ann_1['Topic']['Value'] = '/rescue_1/yolo/image_annotated'
    
    displays.append(raw_1)
    displays.append(ann_1)

with open(rviz_path, 'w') as f:
    yaml.dump(config, f, default_flow_style=False)
