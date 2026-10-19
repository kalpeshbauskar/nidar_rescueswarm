import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration, PythonExpression
from launch_ros.actions import Node


def generate_launch_description():
    config_dir = os.path.join(get_package_share_directory('nidar_vision'), 'config')
    
    detector_arg = DeclareLaunchArgument(
        'detector',
        default_value='ssd',
        choices=['ssd', 'yolo', 'both'],
        description='Vision detector backend to run: ssd, yolo, or both'
    )
    
    detector = LaunchConfiguration('detector')
    use_ssd = IfCondition(PythonExpression(["'", detector, "' in ['ssd', 'both']"]))
    use_yolo = IfCondition(PythonExpression(["'", detector, "' in ['yolo', 'both']"]))

    # Bridge for Drone 0
    bridge_0 = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        arguments=['/rescue_0/camera/image_raw@sensor_msgs/msg/Image[gz.msgs.Image'],
        output='screen'
    )
    
    # SSD Node for Drone 0
    ssd_0 = Node(
        package='nidar_vision',
        executable='ssd_person_node',
        name='ssd_person_node',
        namespace='rescue_0',
        parameters=[
            os.path.join(config_dir, 'ssd_sim.yaml'),
            {'image_topic': '/rescue_0/camera/image_raw'},
            {'annotated_image_topic': '/rescue_0/ssd/image_annotated'},
            {'detections_topic': '/rescue_0/ssd/detections'}
        ],
        condition=use_ssd,
        output='screen'
    )

    # YOLO Node for Drone 0
    yolo_0 = Node(
        package='nidar_vision',
        executable='yolo_person_node',
        name='yolo_person_node',
        namespace='rescue_0',
        parameters=[
            os.path.join(config_dir, 'yolo_sim.yaml'),
            {'image_topic': '/rescue_0/camera/image_raw'},
            {'annotated_image_topic': '/rescue_0/yolo/image_annotated'},
            {'detections_topic': '/rescue_0/yolo/detections'}
        ],
        condition=use_yolo,
        output='screen'
    )
    
    # Bridge for Drone 1
    bridge_1 = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        arguments=['/rescue_1/camera/image_raw@sensor_msgs/msg/Image[gz.msgs.Image'],
        output='screen'
    )

    # SSD Node for Drone 1
    ssd_1 = Node(
        package='nidar_vision',
        executable='ssd_person_node',
        name='ssd_person_node',
        namespace='rescue_1',
        parameters=[
            os.path.join(config_dir, 'ssd_sim.yaml'),
            {'image_topic': '/rescue_1/camera/image_raw'},
            {'annotated_image_topic': '/rescue_1/ssd/image_annotated'},
            {'detections_topic': '/rescue_1/ssd/detections'}
        ],
        condition=use_ssd,
        output='screen'
    )
    
    # YOLO Node for Drone 1
    yolo_1 = Node(
        package='nidar_vision',
        executable='yolo_person_node',
        name='yolo_person_node',
        namespace='rescue_1',
        parameters=[
            os.path.join(config_dir, 'yolo_sim.yaml'),
            {'image_topic': '/rescue_1/camera/image_raw'},
            {'annotated_image_topic': '/rescue_1/yolo/image_annotated'},
            {'detections_topic': '/rescue_1/yolo/detections'}
        ],
        condition=use_yolo,
        output='screen'
    )
    
    # Static TF for RViz (world -> base_link)
    tf_world_base = Node(
        package='tf2_ros',
        executable='static_transform_publisher',
        name='static_tf_pub_world_base',
        arguments=['--x', '0', '--y', '0', '--z', '0', '--yaw', '0', '--pitch', '0', '--roll', '0', '--frame-id', 'world', '--child-frame-id', 'base_link'],
        output='screen'
    )
    
    return LaunchDescription([
        detector_arg,
        bridge_0,
        ssd_0,
        yolo_0,
        bridge_1,
        ssd_1,
        yolo_1,
        tf_world_base
    ])
