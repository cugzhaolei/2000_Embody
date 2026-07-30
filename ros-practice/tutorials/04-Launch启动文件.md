# 04 ROS2 Launch 启动文件

## 4.1 Launch 文件概述

ROS2 Launch 系统用于编排多个节点、加载参数文件、桥接话题，实现一键启动完整系统。

### Launch 文件格式对比

| 格式 | 优点 | 缺点 | 推荐场景 |
|------|------|------|---------|
| Python (.launch.py) | 最灵活，支持逻辑判断 | 语法较复杂 | 复杂启动逻辑 |
| XML (.launch.xml) | 简洁直观 | 无逻辑判断 | 简单场景 |
| YAML (.launch.yaml) | 配置友好 | 功能有限 | 纯参数加载 |

> 本项目使用 Python 格式，支持条件启动和参数覆盖。

## 4.2 gz_sim.launch.py — Gazebo 仿真启动

```python
"""
启动 Gazebo 仿真环境并加载差速驱动机器人
用法: ros2 launch myfirst_robot gz_sim.launch.py
"""
import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    IncludeLaunchDescription,
    ExecuteProcess,
    SetEnvironmentVariable,
)
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    # 获取包路径
    pkg_share = get_package_share_directory('myfirst_robot')

    # 世界文件路径
    world_file = os.path.join(pkg_share, 'worlds', 'warehouse.sdf')
    model_file = os.path.join(pkg_share, 'model', 'vehicle_blue.sdf')

    # Gazebo 启动（包含 ros_gz 桥接）
    gz_sim_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(
                get_package_share_directory('ros_gz_sim'),
                'launch',
                'gz_sim.launch.py'
            )
        ),
        launch_arguments={
            'gz_args': ['-r -v 4 ', world_file],
            'on_exit_shutdown': 'true'
        }.items()
    )

    # 生成机器人（spawn）
    spawn_robot = Node(
        package='ros_gz_sim',
        executable='create',
        name='spawn_vehicle',
        arguments=[
            '-name', 'vehicle_blue',
            '-file', model_file,
            '-x', '0', '-y', '0', '-z', '0.1',
        ],
        output='screen'
    )

    # ros_gz 参数桥接（话题映射）
    bridge_params = os.path.join(pkg_share, 'config', 'bridge.yaml')
    ros_gz_bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        name='gz_bridge',
        parameters=[{'config_file': bridge_params}],
        output='screen'
    )

    # RViz2 可视化
    rviz_config = os.path.join(pkg_share, 'config', 'default.rviz')
    rviz2 = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        arguments=['-d', rviz_config],
        condition=IfCondition(LaunchConfiguration('use_rviz', default='true')),
        output='screen'
    )

    return LaunchDescription([
        # 环境变量：确保使用 Gazebo 的 DDS
        SetEnvironmentVariable('GZ_SIM_VERBOSE', '2'),
        gz_sim_launch,
        spawn_robot,
        ros_gz_bridge,
        rviz2,
    ])
```

### bridge.yaml — 话题桥接配置

```yaml
# Gazebo <-> ROS2 话题桥接配置
- topic_name: /scan
  ros_type_name: sensor_msgs/msg/LaserScan
  gz_type_name: gz.msgs.LaserScan
  direction: GZ_TO_ROS

- topic_name: /cmd_vel
  ros_type_name: geometry_msgs/msg/Twist
  gz_type_name: gz.msgs.Twist
  direction: ROS_TO_GZ

- topic_name: /odom
  ros_type_name: nav_msgs/msg/Odometry
  gz_type_name: gz.msgs.Odometry
  direction: GZ_TO_ROS

- topic_name: /tf
  ros_type_name: tf2_msgs/msg/TFMessage
  gz_type_name: gz.msgs.Pose_V
  direction: GZ_TO_ROS

- topic_name: /joint_states
  ros_type_name: sensor_msgs/msg/JointState
  gz_type_name: gz.msgs.Model
  direction: GZ_TO_ROS

- topic_name: /clock
  ros_type_name: rosgraph_msgs/msg/Clock
  gz_type_name: gz.msgs.Clock
  direction: GZ_TO_ROS
```

## 4.3 slam.launch.py — SLAM 建图启动

```python
"""
启动 SLAM 建图（slam_toolbox online_async）
用法: ros2 launch myfirst_robot slam.launch.py
"""
import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    use_sim_time = LaunchConfiguration('use_sim_time')

    # slam_toolbox 参数文件
    slam_params_file = os.path.join(
        get_package_share_directory('myfirst_robot'),
        'config',
        'slam_params.yaml'
    )

    # slam_toolbox 在线异步建图节点
    slam_toolbox = Node(
        package='slam_toolbox',
        executable='sync_slam_toolbox_node',  # 同步模式（更精确）
        name='slam_toolbox',
        output='screen',
        parameters=[
            slam_params_file,
            {'use_sim_time': use_sim_time}
        ]
    )

    # 键盘遥控节点
    teleop = Node(
        package='myfirst_robot',
        executable='teleop_keyboard',
        name='teleop_keyboard',
        output='screen',
        prefix='xterm -e'  # 在独立终端打开
    )

    return LaunchDescription([
        DeclareLaunchArgument(
            'use_sim_time',
            default_value='true',
            description='使用仿真时钟'
        ),
        slam_toolbox,
        teleop,
    ])
```

### slam_params.yaml — SLAM 参数

```yaml
# slam_toolbox 参数配置
slam_toolbox:
  ros__parameters:
    # 传感器配置
    solver_plugin: solver_plugins::CeresSolver
    mode: mapping  # mapping(建图) / localization(定位)

    # 地图分辨率与范围
    resolution: 0.05  # 5cm/格
    max_laser_range: 20.0  # 与 LiDAR 量程一致

    # 地图大小（格子数）
    map_file_name: ''
    map_start_at_dock: true

    # 扫描匹配参数
    minimum_time_interval: 0.5
    transform_publish_period: 0.02
    map_update_interval: 1.0

    # 优化参数
    ceres_linear_solver: SPARSE_NORMAL_CHOLESKY
    ceres_preconditioner: SCHUR_JACOBI
    ceres_problem_type: SPARSE_NORMAL_CHOLESKY

    # 回环检测
    loop_search_maximum_distance: 3.0
    loop_match_minimum_chain_size: 3
    loop_match_maximum_variance: 0.08
```

## 4.4 nav2_bringup.launch.py — 导航启动

```python
"""
启动 Nav2 导航栈
用法: ros2 launch myfirst_robot nav2_bringup.launch.py map:=~/map.yaml
"""
import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
import yaml


def generate_launch_description():
    # 参数
    map_file = LaunchConfiguration('map')
    params_file = LaunchConfiguration('params_file')
    use_sim_time = LaunchConfiguration('use_sim_time', default='true')

    # Nav2 默认参数文件
    default_params = os.path.join(
        get_package_share_directory('myfirst_robot'),
        'config',
        'nav2_params.yaml'
    )
    default_map = os.path.expanduser('~/map.yaml')

    # 加载地图
    lifecycle_nodes = ['map_server', 'amcl', 'controller_server',
                       'planner_server', 'behavior_server', 'bt_navigator']

    return LaunchDescription([
        DeclareLaunchArgument('map', default_value=default_map),
        DeclareLaunchArgument('params_file', default_value=default_params),
        DeclareLaunchArgument('use_sim_time', default_value='true'),

        # Map Server
        Node(
            package='nav2_map_server',
            executable='map_server',
            name='map_server',
            parameters=[
                {'yaml_filename': map_file},
                {'use_sim_time': use_sim_time}
            ]
        ),

        # AMCL 定位
        Node(
            package='nav2_amcl',
            executable='amcl',
            name='amcl',
            parameters=[params_file, {'use_sim_time': use_sim_time}]
        ),

        # Controller Server（局部规划）
        Node(
            package='nav2_controller',
            executable='controller_server',
            name='controller_server',
            parameters=[params_file, {'use_sim_time': use_sim_time}]
        ),

        # Planner Server（全局规划）
        Node(
            package='nav2_planner',
            executable='planner_server',
            name='planner_server',
            parameters=[params_file, {'use_sim_time': use_sim_time}]
        ),

        # Behavior Server（恢复行为）
        Node(
            package='nav2_behaviors',
            executable='behavior_server',
            name='behavior_server',
            parameters=[params_file, {'use_sim_time': use_sim_time}]
        ),

        # BT Navigator（行为树导航器）
        Node(
            package='nav2_bt_navigator',
            executable='bt_navigator',
            name='bt_navigator',
            parameters=[params_file, {'use_sim_time': use_sim_time}]
        ),

        # Lifecycle Manager（管理节点生命周期）
        Node(
            package='nav2_lifecycle_manager',
            executable='lifecycle_manager',
            name='lifecycle_manager',
            parameters=[{
                'use_sim_time': use_sim_time,
                'autostart': True,
                'node_names': lifecycle_nodes
            }]
        ),

        # RViz2（导航可视化）
        Node(
            package='rviz2',
            executable='rviz2',
            name='rviz2',
            arguments=['-d', os.path.join(
                get_package_share_directory('nav2_bringup'),
                'rviz', 'nav2_default_view.rviz')],
            parameters=[{'use_sim_time': use_sim_time}],
            output='screen'
        ),
    ])
```

## 4.5 Launch 文件调用关系

```
gz_sim.launch.py
├── ros_gz_sim/gz_sim.launch.py  (Gazebo 世界)
├── ros_gz_sim/create             (生成机器人)
├── ros_gz_bridge/parameter_bridge (话题桥接)
└── rviz2                          (可视化)

slam.launch.py
├── slam_toolbox/sync_slam_toolbox_node  (SLAM建图)
└── myfirst_robot/teleop_keyboard       (键盘遥控)

nav2_bringup.launch.py
├── map_server         (地图加载)
├── amcl               (自适应蒙特卡洛定位)
├── controller_server  (局部规划 DWB)
├── planner_server     (全局规划 Navfn)
├── behavior_server    (恢复行为)
├── bt_navigator       (行为树导航)
├── lifecycle_manager  (生命周期管理)
└── rviz2              (导航可视化)
```

## 4.6 常用启动参数

```bash
# 启动仿真（不带 RViz）
ros2 launch myfirst_robot gz_sim.launch.py use_rviz:=false

# 启动 SLAM（自定义参数）
ros2 launch myfirst_robot slam.launch.py use_sim_time:=true

# 启动导航（指定地图）
ros2 launch myfirst_robot nav2_bringup.launch.py map:=~/maps/warehouse.yaml

# 仅启动 Gazebo（无头模式）
ros2 launch myfirst_robot gz_sim.launch.py headless:=true
```

---

**下一课**：[05-SLAM建图实战](05-SLAM建图实战.md) — 控制机器人建图并保存
