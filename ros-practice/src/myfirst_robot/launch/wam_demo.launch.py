"""
WAM Demo Launch — 启动 Gazebo + Nav2 + WAM 安全过滤
"""
import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    pkg_share = get_package_share_directory('myfirst_robot')

    # Gazebo 仿真
    gz_sim = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_share, 'launch', 'gz_sim.launch.py')),
        launch_arguments={'use_rviz': 'true'}.items())

    # WAM 节点
    wam_node = Node(
        package='myfirst_robot',
        executable='wam_node',
        name='wam_node',
        parameters=[{
            'model_path': os.path.expanduser('~/wam_model.pt'),
            'horizon': 20,
            'collision_threshold': 0.3,
            'use_safety_filter': True,
            'prediction_rate': 10.0,
        }],
        output='screen',
        remappings=[
            ('/cmd_vel_raw', '/cmd_vel'),      # Nav2输出→WAM输入
            ('/cmd_vel', '/cmd_vel_safe'),      # WAM输出→重命名
        ])

    # RViz 配置（显示WAM预测）
    wam_rviz = Node(
        package='rviz2',
        executable='rviz2',
        name='wam_rviz',
        arguments=['-d', os.path.join(pkg_share, 'config', 'wam.rviz')],
        output='screen')

    return LaunchDescription([
        gz_sim,
        wam_node,
        DeclareLaunchArgument(
            'use_wam_safety',
            default_value='true',
            description='是否启用WAM安全过滤'),
    ])
