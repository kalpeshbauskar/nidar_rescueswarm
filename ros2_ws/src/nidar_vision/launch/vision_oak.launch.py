import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource

def generate_launch_description():
    config_dir = os.path.join(get_package_share_directory('nidar_vision'), 'config')
    
    # YOLO Node
    yolo_node = Node(
        package='nidar_vision',
        executable='yolo_person_node',
        name='yolo_person_node',
        parameters=[
            os.path.join(config_dir, 'yolo_hardware.yaml'),
            # Overwrite image topic for oak
            {'image_topic': '/oak/rgb/image_raw'}
        ],
        remappings=[
            ('/oak/rgb/image_raw', '/nidar/camera/image_raw')
        ],
        output='screen'
    )
    
    # This is a placeholder for actual OAK-D launch when installed
    # oak_launch = IncludeLaunchDescription(
    #     PythonLaunchDescriptionSource([os.path.join(
    #         get_package_share_directory('depthai_ros_driver'), 'launch', 'camera.launch.py')]),
    # )
    
    print('Resolved OAK-D YOLO config path:', os.path.join(config_dir, 'yolo_hardware.yaml'))
    return LaunchDescription([
        # oak_launch,
        yolo_node
    ])
