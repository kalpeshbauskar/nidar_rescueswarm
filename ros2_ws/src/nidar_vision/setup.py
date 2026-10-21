from setuptools import find_packages, setup

package_name = 'nidar_vision'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/launch', ['launch/vision_gazebo.launch.py', 'launch/vision_oak.launch.py', 'launch/vision_rviz.launch.py', 'launch/vision_fleet.launch.py']),
        ('share/' + package_name + '/config', ['config/yolo_sim.yaml', 'config/yolo_hardware.yaml', 'config/ssd_sim.yaml']),
        ('share/' + package_name + '/config/rviz', ['config/rviz/nidar_vision.rviz']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='kalpeshbauskar',
    maintainer_email='kalpeshbauskar@users.noreply.github.com',
    description='TODO: Package description',
    license='TODO: License declaration',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
            'yolo_person_node = nidar_vision.yolo_person_node:main',
            'ssd_person_node = nidar_vision.ssd_person_node:main',
            'metrics_node = nidar_vision.metrics_node:main',
            'rviz_telemetry_node = nidar_vision.rviz_telemetry_node:main',
        ],
    },
)
