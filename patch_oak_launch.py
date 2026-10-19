import os

launch_file = "ros2_ws/src/nidar_vision/launch/vision_oak.launch.py"
with open(launch_file, 'r') as f:
    content = f.read()

# Add a print statement before the Return
if "print('Resolved OAK-D YOLO config path:'" not in content:
    content = content.replace("return LaunchDescription([", "print('Resolved OAK-D YOLO config path:', os.path.join(config_dir, 'yolo_hardware.yaml'))\n    return LaunchDescription([")
    
with open(launch_file, 'w') as f:
    f.write(content)

launch_file_sim = "ros2_ws/src/nidar_vision/launch/vision_fleet.launch.py"
with open(launch_file_sim, 'r') as f:
    content_sim = f.read()

if "print('Resolved Gazebo YOLO config path:'" not in content_sim:
    content_sim = content_sim.replace("return LaunchDescription([", "print('Resolved Gazebo YOLO config path:', os.path.join(config_dir, 'yolo_sim.yaml'))\n    return LaunchDescription([")

with open(launch_file_sim, 'w') as f:
    f.write(content_sim)

print("Launch files patched with print statements.")
