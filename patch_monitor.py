import re

with open("monitor_soak_v2.py", "r") as f:
    data = f.read()

data = data.replace('"/home/kalpeshbauskar/nidar_rescueswarm/simulation/dual"', 'os.path.join(os.path.dirname(os.path.abspath(__file__)), "simulation", "dual")')
data = data.replace('env_cmd = "source /opt/ros/jazzy/setup.bash && source /home/kalpeshbauskar/px4_ros2_ws/install/setup.bash && source /home/kalpeshbauskar/nidar_rescueswarm/ros2_ws/install/setup.bash && source /home/kalpeshbauskar/nidar_rescueswarm/venv/bin/activate"', 
    'env_cmd = "source /opt/ros/jazzy/setup.bash && source ~/px4_ros2_ws/install/setup.bash && source $(pwd)/ros2_ws/install/setup.bash && source $(pwd)/venv/bin/activate"')

with open("monitor_soak_v2.py", "w") as f:
    f.write(data)
