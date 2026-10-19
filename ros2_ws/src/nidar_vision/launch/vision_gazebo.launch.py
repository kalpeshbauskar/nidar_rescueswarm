import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    config_dir = os.path.join(get_package_share_directory('nidar_vision'), 'config')
    
    bridge_node = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        arguments=['/rescue_0/camera@sensor_msgs/msg/Image[gz.msgs.Image'],
        remappings=[
            ('/rescue_0/camera', '/nidar/camera/image_raw')
        ],
        output='screen'
    )
    
    yolo_node = Node(
        package='nidar_vision',
        executable='yolo_person_node',
        name='yolo_person_node',
        parameters=[os.path.join(config_dir, 'yolo_sim.yaml')],
        output='screen'
    )
    
    return LaunchDescription([
        bridge_node,
        yolo_node
    ])
