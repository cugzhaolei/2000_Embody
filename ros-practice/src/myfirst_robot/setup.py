from setuptools import setup

package_name = 'myfirst_robot'

setup(
    name=package_name,
    version='0.1.0',
    packages=[package_name, package_name + '.wam'],
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/launch', [
            'launch/gz_sim.launch.py',
            'launch/slam.launch.py',
            'launch/nav2_bringup.launch.py',
            'launch/wam_demo.launch.py',
        ]),
        ('share/' + package_name + '/config', [
            'config/nav2_params.yaml',
            'config/slam_params.yaml',
            'config/bridge.yaml',
            'config/wam_params.yaml',
        ]),
        ('share/' + package_name + '/model', [
            'model/vehicle_blue.sdf',
        ]),
        ('share/' + package_name + '/worlds', [
            'worlds/warehouse.sdf',
        ]),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='ROS2 Practice',
    maintainer_email='user@example.com',
    description='差速驱动机器人 SLAM Nav2 + World Action Model 实战包',
    license='MIT',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'teleop_keyboard = myfirst_robot.teleop_keyboard:main',
            'wam_node = myfirst_robot.wam_node:main',
            'wam_trainer = myfirst_robot.wam.trainer:main',
        ],
    },
)
