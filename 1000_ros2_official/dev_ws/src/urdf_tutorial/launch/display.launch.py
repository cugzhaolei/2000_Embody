import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import Command, LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    model_arg = DeclareLaunchArgument(
        'model',
        default_value=os.path.join(
            get_package_share_directory('urdf_tutorial'), 'urdf', '01-myfirst.urdf'),
        description='Path to robot urdf file'
    )
    rvizconfig_arg = DeclareLaunchArgument(
        'rvizconfig',
        default_value=os.path.join(
            get_package_share_directory('urdf_tutorial'), 'rviz', 'urdf.rviz'),
        description='Absolute path to rviz config file'
    )

    model = LaunchConfiguration('model')
    rvizconfig = LaunchConfiguration('rvizconfig')

    robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        output='screen',
        parameters=[{
            'robot_description': ParameterValue(
                Command(['cat ', model]), value_type=str)
        }]
    )

    rviz = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        arguments=['-d', rvizconfig]
    )

    return LaunchDescription([
        model_arg,
        rvizconfig_arg,
        robot_state_publisher,
        rviz
    ])
