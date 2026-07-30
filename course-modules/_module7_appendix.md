

---

## 🔧 工程实战代码附录

> 本附录收录模块七涉及的完整工程代码示例，所有代码均符合 ROS2 Humble 规范，可直接拷贝到工程包中使用。

### A. Python Nav2 完整配置示例

#### A.1 nav2_params.yaml 完整配置

```yaml
# nav2_params.yaml - Nav2 完整参数配置（ROS2 Humble）
amcl:
  ros__parameters:
    use_sim_time: false
    alpha1: 0.2                 # 旋转-旋转噪声
    alpha2: 0.2                 # 平移-旋转噪声
    alpha3: 0.2                 # 平移-平移噪声
    alpha4: 0.2                 # 旋转-平移噪声
    alpha5: 0.1
    base_frame_id: "base_footprint"
    odom_frame_id: "odom"
    global_frame_id: "map"
    scan_topic: "/scan"
    set_initial_pose: true
    initial_pose:
      x: 0.0
      y: 0.0
      z: 0.0
      yaw: 0.0
    min_particles: 500
    max_particles: 3000
    update_min_d: 0.20          # 触发更新的最小平移(m)
    update_min_a: 0.50          # 触发更新的最小旋转(rad)
    resample_interval: 1
    transform_tolerance: 1.0
    recovery_alpha_slow: 0.001
    recovery_alpha_fast: 0.1
    laser_model_type: "likelihood_field"
    z_hit: 0.5
    z_short: 0.05
    z_max: 0.05
    z_rand: 0.5
    sigma_hit: 0.2
    lambda_short: 0.1
    laser_max_range: -1.0       # -1 表示使用激光雷达上报值
    max_beams: 60
    save_pose_rate: 0.5

bt_navigator:
  ros__parameters:
    use_sim_time: false
    global_frame: map
    robot_base_frame: base_link
    odom_topic: /odom
    bt_loop_duration: 10        # 行为树tick周期(ms)
    default_server_timeout: 20
    wait_for_service_timeout: 1000
    action_server_result_timeout: 900.0
    navigators: ["navigate_to_pose", "navigate_through_poses"]
    navigate_to_pose:
      plugin: "nav2_bt_navigator::NavigateToPoseNavigator"
    navigate_through_poses:
      plugin: "nav2_bt_navigator::NavigateThroughPosesNavigator"
    default_nav_to_pose_bt: navigate_to_pose_w_replanning_and_recovery.xml
    default_nav_through_poses_bt: navigate_through_poses_w_replanning_and_recovery.xml
    plugin_lib_names:
      - nav2_goal_reached_condition_bt_node
      - nav2_goal_updated_condition_bt_node
      - nav2_initial_pose_received_condition_bt_node
      - nav2_is_battery_low_condition_bt_node
      - nav2_reinitialize_global_localization_service_bt_node
      - nav2_compute_path_to_pose_action_bt_node
      - nav2_compute_path_through_poses_action_bt_node
      - nav2_smooth_path_action_bt_node
      - nav2_follow_path_action_bt_node
      - nav2_spin_action_bt_node
      - nav2_wait_action_bt_node
      - nav2_assisted_teleop_action_bt_node
      - nav2_back_up_action_bt_node
      - nav2_drive_on_heading_bt_node
      - nav2_clear_costmap_service_bt_node
      - nav2_is_stuck_condition_bt_node
      - nav2_planner_selector_bt_node
      - nav2_controller_selector_bt_node
      - nav2_smoother_selector_bt_node
      - nav2_goal_checker_selector_bt_node
      - nav2_progress_checker_selector_bt_node

controller_server:
  ros__parameters:
    use_sim_time: false
    controller_frequency: 20.0
    min_x_velocity_threshold: 0.001
    min_y_velocity_threshold: 0.5
    min_theta_velocity_threshold: 0.001
    progress_checker_plugin: "progress_checker"
    goal_checker_plugins: ["general_goal_checker"]
    controller_plugins: ["FollowPath"]
    progress_checker:
      plugin: "nav2_controller::SimpleProgressChecker"
      required_movement_radius: 0.5
      movement_time_allowance: 10.0
    general_goal_checker:
      plugin: "nav2_controller::SimpleGoalChecker"
      xy_goal_tolerance: 0.15
      yaw_goal_tolerance: 0.15
      stateful: true
    # DWB Local Planner 配置
    FollowPath:
      plugin: "dwb_core::DWBLocalPlanner"
      debug_trajectory_details: true
      min_vel_x: 0.0
      min_vel_y: 0.0
      max_vel_x: 1.0
      max_vel_y: 0.0
      max_vel_theta: 1.0
      min_speed_xy: 0.0
      max_speed_xy: 1.0
      min_speed_theta: 0.0
      acc_lim_x: 2.5
      acc_lim_y: 0.0
      acc_lim_theta: 3.2
      decel_lim_x: -2.5
      decel_lim_y: 0.0
      decel_lim_theta: -3.2
      vx_samples: 20
      vy_samples: 0
      vtheta_samples: 40
      sim_time: 1.7
      linear_granularity: 0.05
      angular_granularity: 0.025
      transform_tolerance: 0.2
      xy_goal_tolerance: 0.15
      trans_stopped_velocity: 0.25
      short_circuit_trajectory_evaluation: true
      stateful: true
      critics: ["RotateToGoal", "Oscillation", "BaseObstacle", "GoalAlign", "PathAlign", "PathDist", "GoalDist"]
      BaseObstacle.scale: 0.02
      PathAlign.scale: 32.0
      GoalAlign.scale: 24.0
      PathDist.scale: 32.0
      GoalDist.scale: 24.0
      RotateToGoal.scale: 32.0
      RotateToGoal.slowing_factor: 5.0
      RotateToGoal.lookahead_time: -1.0

planner_server:
  ros__parameters:
    use_sim_time: false
    expected_planner_frequency: 5.0
    planner_plugins: ["GridBased"]
    GridBased:
      plugin: "nav2_smac_planner::SmacPlannerHybrid"
      downsample_costmap: false
      downsampling_factor: 1
      tolerance: 0.25                # 到目标点的容差(m)
      allow_unknown: false
      max_iterations: 1000000
      max_on_approach_iterations: 1000
      smooth_path: true
      hybrid_search: true            # Dubins vs Reeds-Shepp
      minimum_turning_radius: 0.40
      reverse_penalty: 2.0
      change_penalty: 0.0
      cost_penalty: 2.0
      retrospective_penalty: 0.015
      lookup_table_size: 20.0
      cache_obstacle_heuristic: false
      debug_visualizations: false

smoother_server:
  ros__parameters:
    use_sim_time: false
    smoother_plugins: ["simple_smoother"]
    simple_smoother:
      plugin: "nav2_smoother::SimpleSmoother"
      tolerance: 1.0e-10
      max_its: 1000
      do_refinement: true

behavior_server:
  ros__parameters:
    use_sim_time: false
    local_costmap_topic: local_costmap/costmap_raw
    global_costmap_topic: global_costmap/costmap_raw
    local_footprint_topic: local_costmap/published_footprint
    global_footprint_topic: global_costmap/published_footprint
    cycle_frequency: 10.0
    behavior_plugins: ["spin", "backup", "drive_on_heading", "assisted_teleop", "wait"]
    spin:
      plugin: "nav2_behaviors::Spin"
    backup:
      plugin: "nav2_behaviors::BackUp"
    drive_on_heading:
      plugin: "nav2_behaviors::DriveOnHeading"
    wait:
      plugin: "nav2_behaviors::Wait"
    assisted_teleop:
      plugin: "nav2_behaviors::AssistedTeleop"
    global_frame: odom
    robot_base_frame: base_link
    transform_tolerance: 0.1
    simulate_ahead_time: 2.0
    max_rotational_vel: 1.0
    min_rotational_vel: 0.4
    rotational_acc_lim: 3.2

local_costmap:
  local_costmap:
    ros__parameters:
      use_sim_time: false
      update_frequency: 5.0
      publish_frequency: 2.0
      global_frame: odom
      robot_base_frame: base_link
      rolling_window: true
      width: 3
      height: 3
      resolution: 0.05
      footprint: "[ [0.30, 0.20], [0.30, -0.20], [-0.30, -0.20], [-0.30, 0.20] ]"
      plugins: ["voxel_layer", "inflation_layer"]
      inflation_layer:
        plugin: "nav2_costmap_2d::InflationLayer"
        cost_scaling_factor: 3.0
        inflation_radius: 0.55
      voxel_layer:
        plugin: "nav2_costmap_2d::VoxelLayer"
        enabled: true
        publish_voxel_map: false
        origin_z: 0.0
        z_resolution: 0.05
        z_voxels: 16
        max_obstacle_height: 2.0
        mark_threshold: 0
        observation_sources: scan
        scan:
          topic: /scan
          max_obstacle_height: 2.0
          min_obstacle_height: 0.0
          clearing: true
          marking: true
          data_type: "LaserScan"
          raytrace_max_range: 3.0
          raytrace_min_range: 0.0
          obstacle_max_range: 2.5
          obstacle_min_range: 0.0
      static_layer:
        map_subscribe_transient_local: true
      always_send_full_costmap: true

global_costmap:
  global_costmap:
    ros__parameters:
      use_sim_time: false
      update_frequency: 1.0
      publish_frequency: 1.0
      global_frame: map
      robot_base_frame: base_link
      rolling_window: false
      footprint: "[ [0.30, 0.20], [0.30, -0.20], [-0.30, -0.20], [-0.30, 0.20] ]"
      resolution: 0.05
      plugins: ["static_layer", "obstacle_layer", "inflation_layer"]
      static_layer:
        plugin: "nav2_costmap_2d::StaticLayer"
        map_subscribe_transient_local: true
      obstacle_layer:
        plugin: "nav2_costmap_2d::ObstacleLayer"
        enabled: true
        observation_sources: scan
        scan:
          topic: /scan
          max_obstacle_height: 2.0
          min_obstacle_height: 0.0
          clearing: true
          marking: true
          data_type: "LaserScan"
          raytrace_max_range: 5.0
          raytrace_min_range: 0.0
          obstacle_max_range: 4.5
          obstacle_min_range: 0.0
      inflation_layer:
        plugin: "nav2_costmap_2d::InflationLayer"
        cost_scaling_factor: 3.0
        inflation_radius: 0.55
      always_send_full_costmap: true

map_server:
  ros__parameters:
    use_sim_time: false
    yaml_filename: "map.yaml"
    save_map_timeout: 5.0

lifecycle_manager:
  ros__parameters:
    use_sim_time: false
    autostart: true
    bond_timeout: 4.0
    node_names:
      - map_server
      - amcl
      - controller_server
      - planner_server
      - smoother_server
      - behavior_server
      - bt_navigator
      - velocity_smoother
    attempt_respawn_reconnection: true
    bond_respawn_max_duration: 10.0

velocity_smoother:
  ros__parameters:
    use_sim_time: false
    smoothing_frequency: 20.0
    scale_velocities: false
    feedback: "OPEN_LOOP"
    max_velocity: [0.8, 0.0, 1.0]
    min_velocity: [-0.5, 0.0, -1.0]
    deadband_velocity: [0.0, 0.0, 0.0]
    velocity_timeout: 1.0
```

#### A.2 行为树 XML（navigate_to_pose_w_replanning_and_recovery.xml）

```xml
<root main_tree_to_execute="MainTree">
  <BehaviorTree ID="MainTree">
    <RecoveryNode number_of_retries="6" name="NavigateRecovery">
      <PipelineSequence name="NavigateWithReplanning">
        <RateController hz="1.0">
          <Fallback>
            <GoalUpdated/>
            <ComputePathToPose goal="{goal}" path="{path}" planner_id="GridBased"/>
          </Fallback>
        </RateController>
        <RecoveryNode number_of_retries="1" name="FollowPathRecovery">
          <FollowPath path="{path}" controller_id="FollowPath"/>
          <SequenceStar name="ClearingActions">
            <ClearEntireCostmap name="ClearLocalCostmap-Context"
              service_name="local_costmap/clear_entirely_local_costmap"/>
            <ClearEntireCostmap name="ClearGlobalCostmap-Context"
              service_name="global_costmap/clear_entirely_global_costmap"/>
          </SequenceStar>
        </RecoveryNode>
      </PipelineSequence>
      <ReactiveFallback name="RecoveryFallback">
        <GoalUpdated/>
        <SequenceStar name="RecoveryActions">
          <ClearEntireCostmap name="ClearLocalCostmap-Subtree"
            service_name="local_costmap/clear_entirely_local_costmap"/>
          <ClearEntireCostmap name="ClearGlobalCostmap-Subtree"
            service_name="global_costmap/clear_entirely_global_costmap"/>
          <Spin spin_dist="1.57"/>
          <Wait wait_duration="1.0"/>
          <BackUp backup_dist="0.30" backup_speed="0.05"/>
        </SequenceStar>
      </ReactiveFallback>
    </RecoveryNode>
  </BehaviorTree>
</root>
```

#### A.3 Nav2 启动 Python Launch 文件

```python
# nav2_bringup_launch.py - Nav2 完整启动
import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, GroupAction
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node, PushRosNamespace
from nav2_common.launch import RewrittenYaml


def generate_launch_description():
    namespace = LaunchConfiguration('namespace')
    params_file = LaunchConfiguration('params_file')
    use_sim_time = LaunchConfiguration('use_sim_time')
    autostart = LaunchConfiguration('autostart')

    # 参数重写：use_sim_time 注入
    configured_params = RewrittenYaml(
        source_file=params_file,
        param_rewrites={'use_sim_time': use_sim_time},
        convert_types=True,
    )

    lifecycle_nodes = [
        'map_server', 'amcl', 'controller_server', 'planner_server',
        'smoother_server', 'behavior_server', 'bt_navigator', 'velocity_smoother',
    ]

    return LaunchDescription([
        DeclareLaunchArgument('namespace', default_value=''),
        DeclareLaunchArgument('params_file',
                              default_value=os.path.join(
                                  get_package_share_directory('nav2_bringup'),
                                  'params', 'nav2_params.yaml')),
        DeclareLaunchArgument('use_sim_time', default_value='false'),
        DeclareLaunchArgument('autostart', default_value='true'),

        # Lifecycle 管理器
        Node(package='nav2_lifecycle_manager', executable='lifecycle_manager',
             name='lifecycle_manager_navigation',
             output='screen',
             parameters=[{'use_sim_time': use_sim_time,
                          'autostart': autostart,
                          'node_names': lifecycle_nodes}]),
        # map_server
        Node(package='nav2_map_server', executable='map_server',
             name='map_server', output='screen',
             parameters=[configured_params]),
        # amcl
        Node(package='nav2_amcl', executable='amcl',
             name='amcl', output='screen',
             parameters=[configured_params]),
        # planner
        Node(package='nav2_planner', executable='planner_server',
             name='planner_server', output='screen',
             parameters=[configured_params]),
        # controller
        Node(package='nav2_controller', executable='controller_server',
             name='controller_server', output='screen',
             parameters=[configured_params]),
        # behavior
        Node(package='nav2_behaviors', executable='behavior_server',
             name='behavior_server', output='screen',
             parameters=[configured_params]),
        # smoother
        Node(package='nav2_smoother', executable='smoother_server',
             name='smoother_server', output='screen',
             parameters=[configured_params]),
        # bt_navigator
        Node(package='nav2_bt_navigator', executable='bt_navigator',
             name='bt_navigator', output='screen',
             parameters=[configured_params]),
    ])
```

---

### B. Python MoveIt2 机械臂规划完整示例

#### B.1 moveit_configs.yaml

```yaml
# moveit_configs.yaml - MoveIt2 配置入口
moveit_servo:
  move_group_name: arm_group
  publish_period: 0.034
  parent_frame: base_link
  linear_jump_threshold: 0.75
  rotational_jump_threshold: 1.57

moveit_controller_manager:
  controller_names:
    - arm_controller
    - gripper_controller
  arm_controller:
    type: FollowJointTrajectory
    action_ns: /arm_controller/follow_joint_trajectory
    joints: [joint_1, joint_2, joint_3, joint_4, joint_5, joint_6]
  gripper_controller:
    type: FollowJointTrajectory
    action_ns: /gripper_controller/follow_joint_trajectory
    joints: [finger_joint]

moveit_simple_controller_manager:
  controller_names: [arm_controller, gripper_controller]

moveit_ros_control_interface:
  controllers:
    - name: arm_controller
      action_ns: /arm_controller/follow_joint_trajectory
      type: FollowJointTrajectory
      joints: [joint_1, joint_2, joint_3, joint_4, joint_5, joint_6]
```

#### B.2 SRDF 机器人语义描述（excerpt）

```xml
<?xml version="1.0" ?>
<!-- robot.srdf: 机器人语义描述，定义规划组、碰撞白名单、虚拟关节 -->
<robot name="six_dof_arm">
  <!-- 规划组 arm_group: 6个转动关节 -->
  <group name="arm_group">
    <chain base_link="base_link" tip_link="tool0"/>
    <group_state name="home">
      <joint name="joint_1" value="0"/>
      <joint name="joint_2" value="0"/>
      <joint name="joint_3" value="0"/>
      <joint name="joint_4" value="0"/>
      <joint name="joint_5" value="0"/>
      <joint name="joint_6" value="0"/>
    </group_state>
    <group_state name="ready">
      <joint name="joint_1" value="0"/>
      <joint name="joint_2" value="-1.2"/>
      <joint name="joint_3" value="1.5"/>
      <joint name="joint_4" value="0"/>
      <joint name="joint_5" value="1.5"/>
      <joint name="joint_6" value="0"/>
    </group_state>
  </group>

  <group name="gripper">
    <joint name="finger_joint"/>
  </group>

  <!-- 虚拟关节: base_link 固定到 world -->
  <virtual_joint name="virtual_joint" type="fixed"
                 parent_frame="world" child_link="base_link"/>

  <!-- 禁用碰撞对：永远不会碰撞的连杆对，提升规划性能 -->
  <disable_collisions link1="base_link" link2="link_1" reason="Adjacent"/>
  <disable_collisions link1="link_1" link2="link_2" reason="Adjacent"/>
  <disable_collisions link1="link_2" link2="link_3" reason="Adjacent"/>
  <disable_collisions link1="link_3" link2="link_4" reason="Adjacent"/>
  <disable_collisions link1="link_4" link2="link_5" reason="Adjacent"/>
  <disable_collisions link1="link_5" link2="link_6" reason="Adjacent"/>
  <disable_collisions link1="link_6" link2="tool0" reason="Default"/>
</robot>
```

#### B.3 kinematics.yaml 运动学求解器配置

```yaml
# kinematics.yaml - IK 求解器配置
arm_group:
  kinematics_solver: kdl_kinematics_plugin/KDLKinematicsPlugin
  kinematics_solver_search_resolution: 0.005
  kinematics_solver_timeout: 0.005
  kinematics_solver_attempts: 3
  # 若使用 IKFast 解析解：
  # kinematics_solver: six_dof_arm_arm_group_kinematics/IKFastKinematicsPlugin
  # kinematics_solver_attempts: 1
  # kinematics_solver_timeout: 0.001
```

#### B.4 joint_limits.yaml

```yaml
# joint_limits.yaml - 关节限位与速度加速度限制
joint_limits:
  joint_1:
    has_velocity_limits: true
    max_velocity: 3.14
    has_acceleration_limits: true
    max_acceleration: 5.0
    has_position_limits: true
    min_position: -3.14
    max_position: 3.14
  joint_2:
    has_velocity_limits: true
    max_velocity: 3.14
    has_acceleration_limits: true
    max_acceleration: 5.0
    has_position_limits: true
    min_position: -2.09
    max_position: 2.09
  joint_3:
    has_velocity_limits: true
    max_velocity: 3.14
    has_acceleration_limits: true
    max_acceleration: 5.0
    has_position_limits: true
    min_position: -3.14
    max_position: 3.14
  joint_4:
    has_velocity_limits: true
    max_velocity: 3.93
    has_acceleration_limits: true
    max_acceleration: 8.0
    has_position_limits: true
    min_position: -3.14
    max_position: 3.14
  joint_5:
    has_velocity_limits: true
    max_velocity: 3.93
    has_acceleration_limits: true
    max_acceleration: 8.0
    has_position_limits: true
    min_position: -2.09
    max_position: 2.09
  joint_6:
    has_velocity_limits: true
    max_velocity: 6.28
    has_acceleration_limits: true
    max_acceleration: 12.0
    has_position_limits: true
    min_position: -6.28
    max_position: 6.28
```

#### B.5 move_group.launch.py

```python
# move_group.launch.py - MoveIt2 move_group 启动
import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    pkg_share = get_package_share_directory('six_dof_arm_moveit_config')

    use_sim_time = LaunchConfiguration('use_sim_time')

    return LaunchDescription([
        DeclareLaunchArgument('use_sim_time', default_value='false'),

        # move_group 节点
        Node(
            package='moveit_ros_move_group',
            executable='move_group',
            name='move_group',
            output='screen',
            parameters=[
                {'use_sim_time': use_sim_time,
                 'robot_description_kinematics':
                     os.path.join(pkg_share, 'config', 'kinematics.yaml')},
                {'robot_description_semantic':
                     open(os.path.join(pkg_share, 'config', 'robot.srdf')).read()},
                os.path.join(pkg_share, 'config', 'moveit_controllers.yaml'),
                os.path.join(pkg_share, 'config', 'joint_limits.yaml'),
                os.path.join(pkg_share, 'config', 'ompl_planning.yaml'),
                {'planning_plugin': 'ompl_interface/OMPLPlanner'},
                {'request_adapters': """default_planner_request_adapters/AddTimeOptimalParameterization
default_planner_request_adapters/FixWorkspaceBounds
default_planner_request_adapters/FixStartStateBounds
default_planner_request_adapters/FixStartStateCollision
default_planner_request_adapters/FixStartStatePathConstraints"""},
                {'start_state_max_bounds_error': 0.1},
            ],
        ),
        # RViz with MotionPlanning 插件
        Node(
            package='rviz2',
            executable='rviz2',
            name='rviz2',
            output='screen',
            arguments=['-d', os.path.join(pkg_share, 'config', 'moveit.rviz')],
        ),
    ])
```

#### B.6 Python move_group 接口示例

```python
#!/usr/bin/env python3
# arm_planner.py - MoveIt2 Python 完整规划接口
"""
MoveIt2 Python API 示例（Humble）
功能：
  1. 关节空间规划到 'home' / 'ready' 预设位姿
  2. 笛卡尔空间规划到目标位姿
  3. 笛卡尔路径规划（直线插值）
  4. 抓取-放置任务
"""
import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient
from geometry_msgs.msg import PoseStamped, Pose
from moveit_msgs.action import MoveGroup
from moveit_msgs.msg import (
    MotionPlanRequest,
    Constraints,
    JointConstraint,
    PositionConstraint,
    OrientationConstraint,
    BoundingVolume,
    RobotState,
)
from shape_msgs.msg import SolidPrimitive
from moveit_py.planning import MoveItPy
from moveit_py.core import RobotModel, PlanningScene
import numpy as np


class ArmPlanner(Node):
    def __init__(self):
        super().__init__('arm_planner')
        # MoveItPy 实例
        self.moveit = MoveItPy(node_name="moveit_py")
        self.arm = self.moveit.get_planning_component('arm_group')
        self.gripper = self.moveit.get_planning_component('gripper')
        self.get_logger().info('ArmPlanner 初始化完成')

    # ---------- 1. 关节空间规划 ----------
    def move_joints(self, joint_values: list):
        """规划到给定关节角度（rad）"""
        self.arm.set_start_state_to_current_state()
        goal_state = RobotState()
        goal_state.joint_state.name = [
            'joint_1', 'joint_2', 'joint_3',
            'joint_4', 'joint_5', 'joint_6'
        ]
        goal_state.joint_state.position = joint_values
        self.arm.set_goal_state(robot_state=goal_state)
        plan = self.arm.plan()
        if plan:
            self.moveit.execute(plan.trajectory)
            self.get_logger().info('关节空间规划执行完成')
            return True
        self.get_logger().error('关节空间规划失败')
        return False

    # ---------- 2. 笛卡尔空间规划到 Pose ----------
    def move_to_pose(self, target_pose: PoseStamped):
        """规划到目标位姿（笛卡尔空间）"""
        self.arm.set_start_state_to_current_state()
        self.arm.set_goal_state(pose_stamped_msg=target_pose,
                                model_group='arm_group')
        plan = self.arm.plan()
        if plan:
            self.moveit.execute(plan.trajectory)
            self.get_logger().info('位姿规划执行完成')
            return True
        self.get_logger().error('位姿规划失败')
        return False

    # ---------- 3. 笛卡尔直线插值规划 ----------
    def move_cartesian(self, waypoints: list, eef_step: float = 0.01):
        """沿给定路径点直线插值（Cartesian Path）"""
        # 注意：Humble 中 Cartesian 需通过 MoveGroup action 的
        # path_constraints 或 motion_sequence 实现，此处展示思路
        self.arm.set_start_state_to_current_state()
        # 简化：用第一个 waypoint 作为目标，业务中可用 sequence
        if not waypoints:
            return False
        return self.move_to_pose(waypoints[0])

    # ---------- 4. 抓取-放置任务 ----------
    def pick_and_place(self, pick_pose: PoseStamped, place_pose: PoseStamped):
        """完整 pick-and-place 流程"""
        self.get_logger().info('=== Pick & Place 开始 ===')
        # 1) 张开夹爪
        self.gripper.set_start_state_to_current_state()
        gs = RobotState()
        gs.joint_state.name = ['finger_joint']
        gs.joint_state.position = [0.04]   # 张开
        self.gripper.set_goal_state(robot_state=gs)
        plan = self.gripper.plan()
        if plan:
            self.moveit.execute(plan.trajectory)

        # 2) 移动到抓取位姿
        self.move_to_pose(pick_pose)

        # 3) 闭合夹爪
        gs.joint_state.position = [0.0]     # 闭合
        self.gripper.set_goal_state(robot_state=gs)
        plan = self.gripper.plan()
        if plan:
            self.moveit.execute(plan.trajectory)

        # 4) 移动到放置位姿
        self.move_to_pose(place_pose)

        # 5) 张开夹爪释放
        gs.joint_state.position = [0.04]
        self.gripper.set_goal_state(robot_state=gs)
        plan = self.gripper.plan()
        if plan:
            self.moveit.execute(plan.trajectory)

        self.get_logger().info('=== Pick & Place 完成 ===')


def main():
    rclpy.init()
    node = ArmPlanner()

    # 目标位姿（base_link 坐标系）
    pick_pose = PoseStamped()
    pick_pose.header.frame_id = 'base_link'
    pick_pose.pose.position.x = 0.40
    pick_pose.pose.position.y = 0.10
    pick_pose.pose.position.z = 0.20
    pick_pose.pose.orientation.w = 1.0

    place_pose = PoseStamped()
    place_pose.header.frame_id = 'base_link'
    place_pose.pose.position.x = 0.40
    place_pose.pose.position.y = -0.20
    place_pose.pose.position.z = 0.30
    place_pose.pose.orientation.w = 1.0

    node.pick_and_place(pick_pose, place_pose)
    rclpy.shutdown()


if __name__ == '__main__':
    main()
```

---

### C. C++ Nav2 自定义插件

#### C.1 自定义 Global Planner 插件

```cpp
// custom_global_planner.hpp
#ifndef CUSTOM_GLOBAL_PLANNER_HPP_
#define CUSTOM_GLOBAL_PLANNER_HPP_

#include <string>
#include <memory>
#include <vector>

#include "rclcpp/rclcpp.hpp"
#include "nav2_core/global_planner.hpp"
#include "nav_msgs/msg/path.hpp"
#include "nav2_util/geometry_utils.hpp"
#include "nav2_util/lifecycle_node.hpp"

namespace custom_planner
{
// 自定义全局规划器：直线插值 + 简化 A*
class StraightLinePlanner : public nav2_core::GlobalPlanner
{
public:
  StraightLinePlanner() = default;
  ~StraightLinePlanner() = default;

  // 插件初始化
  void configure(
    const rclcpp_lifecycle::LifecycleNode::WeakPtr & parent,
    std::string name, std::shared_ptr<tf2_ros::Buffer> tf,
    std::shared_ptr<nav2_costmap_2d::Costmap2DROS> costmap_ros) override;

  void cleanup() override;
  void activate() override;
  void deactivate() override;

  // 核心规划接口
  nav_msgs::msg::Path createPlan(
    const geometry_msgs::msg::PoseStamped & start,
    const geometry_msgs::msg::PoseStamped & goal) override;

private:
  std::string _name;                                  // 插件名
  std::shared_ptr<tf2_ros::Buffer> _tf;               // TF 缓冲
  nav2_util::LifecycleNode::SharedPtr _node;          // 节点指针
  std::shared_ptr<nav2_costmap_2d::Costmap2DROS> _costmap_ros;
  double _interpolation_resolution;                   // 插值分辨率(m)
};

}  // namespace custom_planner

#endif  // CUSTOM_GLOBAL_PLANNER_HPP_
```

```cpp
// custom_global_planner.cpp
#include "custom_planner/custom_global_planner.hpp"

namespace custom_planner
{

void StraightLinePlanner::configure(
  const rclcpp_lifecycle::LifecycleNode::WeakPtr & parent,
  std::string name, std::shared_ptr<tf2_ros::Buffer> tf,
  std::shared_ptr<nav2_costmap_2d::Costmap2DROS> costmap_ros)
{
  _node = parent.lock();
  _name = name;
  _tf = tf;
  _costmap_ros = costmap_ros;
  // 插值分辨率参数
  _node->declare_parameter(_name + ".interpolation_resolution", 0.05);
  _node->get_parameter(_name + ".interpolation_resolution",
                       _interpolation_resolution);
  RCLCPP_INFO(_node->get_logger(),
              "StraightLinePlanner 配置成功，分辨率=%.3f", _interpolation_resolution);
}

void StraightLinePlanner::cleanup()
{
  RCLCPP_INFO(_node->get_logger(), "StraightLinePlanner 清理");
}

void StraightLinePlanner::activate() {}
void StraightLinePlanner::deactivate() {}

nav_msgs::msg::Path StraightLinePlanner::createPlan(
  const geometry_msgs::msg::PoseStamped & start,
  const geometry_msgs::msg::PoseStamped & goal)
{
  nav_msgs::msg::Path global_path;
  global_path.header.stamp = _node->now();
  global_path.header.frame_id = _costmap_ros->getGlobalFrameID();

  // 计算起点到终点距离
  double dx = goal.pose.position.x - start.pose.position.x;
  double dy = goal.pose.position.y - start.pose.position.y;
  double distance = std::hypot(dx, dy);
  int steps = std::max(1, static_cast<int>(distance / _interpolation_resolution));

  for (int i = 0; i <= steps; ++i) {
    double alpha = static_cast<double>(i) / steps;
    geometry_msgs::msg::PoseStamped pose;
    pose.header = global_path.header;
    pose.pose.position.x = start.pose.position.x + alpha * dx;
    pose.pose.position.y = start.pose.position.y + alpha * dy;
    pose.pose.position.z = 0.0;
    pose.pose.orientation = goal.pose.orientation;
    global_path.poses.push_back(pose);
  }
  return global_path;
}

}  // namespace custom_planner

// 注册插件宏
#include "pluginlib/class_list_macros.hpp"
PLUGINLIB_EXPORT_CLASS(custom_planner::StraightLinePlanner, nav2_core::GlobalPlanner)
```

#### C.2 自定义 Controller 插件

```cpp
// custom_controller.hpp
#ifndef CUSTOM_CONTROLLER_HPP_
#define CUSTOM_CONTROLLER_HPP_

#include <string>
#include <memory>
#include <vector>

#include "rclcpp/rclcpp.hpp"
#include "nav2_core/controller.hpp"
#include "nav2_costmap_2d/costmap_2d_ros.hpp"
#include "geometry_msgs/msg/pose2_d.hpp"
#include "nav_msgs/msg/path.hpp"
#include "geometry_msgs/msg/twist.hpp"
#include "geometry_msgs/msg/pose_stamped.hpp"
#include "tf2/LinearMath/Quaternion.h"

namespace custom_controller
{
// Pure Pursuit 风格自定义控制器
class CustomPurePursuit : public nav2_core::Controller
{
public:
  CustomPurePursuit() = default;
  ~CustomPurePursuit() = default;

  void configure(
    const rclcpp_lifecycle::LifecycleNode::WeakPtr & parent,
    std::string name, std::shared_ptr<tf2_ros::Buffer> tf,
    std::shared_ptr<nav2_costmap_2d::Costmap2DROS> costmap_ros) override;
  void cleanup() override;
  void activate() override;
  void deactivate() override;

  // 核心接口：根据当前位姿和全局路径计算速度指令
  geometry_msgs::msg::TwistStamped computeVelocityCommands(
    const geometry_msgs::msg::PoseStamped & pose,
    const geometry_msgs::msg::Twist & velocity,
    nav2_core::GoalChecker * goal_checker) override;

  // 设置全局路径
  void setPlan(const nav_msgs::msg::Path & path) override;

  // 速度限幅
  void setSpeedLimit(const double & speed_limit,
                     const bool & percentage) override;

private:
  std::string _name;
  std::shared_ptr<tf2_ros::Buffer> _tf;
  nav2_util::LifecycleNode::SharedPtr _node;
  nav_msgs::msg::Path _global_plan;
  std::shared_ptr<nav2_costmap_2d::Costmap2DROS> _costmap_ros;

  double _lookahead_gain;       // 前瞻增益
  double _lookahead_min;        // 最小前瞻距离
  double _max_linear_vel;       // 最大线速度
  double _max_angular_vel;      // 最大角速度
  double _wheelbase;            // 轴距

  geometry_msgs::msg::PoseStamped _findLookaheadPoint(
    const geometry_msgs::msg::PoseStamped & current_pose, double lookahead);
};

}  // namespace custom_controller

#endif
```

```cpp
// custom_controller.cpp
#include "custom_planner/custom_controller.hpp"
#include "nav2_util/geometry_utils.hpp"
#include <algorithm>

namespace custom_controller
{

void CustomPurePursuit::configure(
  const rclcpp_lifecycle::LifecycleNode::WeakPtr & parent,
  std::string name, std::shared_ptr<tf2_ros::Buffer> tf,
  std::shared_ptr<nav2_costmap_2d::Costmap2DROS> costmap_ros)
{
  _node = parent.lock();
  _name = name;
  _tf = tf;
  _costmap_ros = costmap_ros;

  _node->declare_parameter(_name + ".lookahead_gain", 0.5);
  _node->declare_parameter(_name + ".lookahead_min", 0.3);
  _node->declare_parameter(_name + ".max_linear_vel", 1.0);
  _node->declare_parameter(_name + ".max_angular_vel", 1.0);
  _node->declare_parameter(_name + ".wheelbase", 0.35);

  _node->get_parameter(_name + ".lookahead_gain", _lookahead_gain);
  _node->get_parameter(_name + ".lookahead_min", _lookahead_min);
  _node->get_parameter(_name + ".max_linear_vel", _max_linear_vel);
  _node->get_parameter(_name + ".max_angular_vel", _max_angular_vel);
  _node->get_parameter(_name + ".wheelbase", _wheelbase);
}

void CustomPurePursuit::cleanup() { _global_plan.poses.clear(); }
void CustomPurePursuit::activate() {}
void CustomPurePursuit::deactivate() {}

void CustomPurePursuit::setPlan(const nav_msgs::msg::Path & path)
{
  _global_plan = path;
}

void CustomPurePursuit::setSpeedLimit(const double & speed_limit,
                                       const bool & percentage) {}

geometry_msgs::msg::PoseStamped CustomPurePursuit::_findLookaheadPoint(
  const geometry_msgs::msg::PoseStamped & current_pose, double lookahead)
{
  // 找路径上最近点，再向前累加到前瞻距离
  double min_dist = std::numeric_limits<double>::max();
  size_t nearest_idx = 0;
  for (size_t i = 0; i < _global_plan.poses.size(); ++i) {
    double dx = _global_plan.poses[i].pose.position.x - current_pose.pose.position.x;
    double dy = _global_plan.poses[i].pose.position.y - current_pose.pose.position.y;
    double d = std::hypot(dx, dy);
    if (d < min_dist) {
      min_dist = d;
      nearest_idx = i;
    }
  }
  // 累加到 lookahead
  double acc = 0.0;
  for (size_t i = nearest_idx; i + 1 < _global_plan.poses.size(); ++i) {
    acc += std::hypot(
      _global_plan.poses[i+1].pose.position.x - _global_plan.poses[i].pose.position.x,
      _global_plan.poses[i+1].pose.position.y - _global_plan.poses[i].pose.position.y);
    if (acc >= lookahead) return _global_plan.poses[i+1];
  }
  return _global_plan.poses.back();
}

geometry_msgs::msg::TwistStamped CustomPurePursuit::computeVelocityCommands(
  const geometry_msgs::msg::PoseStamped & pose,
  const geometry_msgs::msg::Twist & velocity,
  nav2_core::GoalChecker * goal_checker)
{
  geometry_msgs::msg::TwistStamped cmd_vel;
  cmd_vel.header.stamp = _node->now();
  cmd_vel.header.frame_id = "base_link";

  // 当前速度估计前瞻距离
  double curr_speed = std::hypot(velocity.linear.x, velocity.linear.y);
  double lookahead = std::max(_lookahead_min, _lookahead_gain * curr_speed);

  auto goal_pt = _findLookaheadPoint(pose, lookahead);
  double dx = goal_pt.pose.position.x - pose.pose.position.x;
  double dy = goal_pt.pose.position.y - pose.pose.position.y;

  // 当前航向
  tf2::Quaternion q(pose.pose.orientation.x, pose.pose.orientation.y,
                    pose.pose.orientation.z, pose.pose.orientation.w);
  double yaw = q.getEulerYPR().z;  // yaw
  double alpha = std::atan2(dy, dx) - yaw;
  // 归一化到 [-pi, pi]
  while (alpha > M_PI) alpha -= 2 * M_PI;
  while (alpha < -M_PI) alpha += 2 * M_PI;

  // 曲率 κ = 2 sin(α) / l_d
  double kappa = 2.0 * std::sin(alpha) / std::max(1e-6, lookahead);

  cmd_vel.twist.linear.x = std::min(_max_linear_vel, 0.5 + 0.5 * std::cos(alpha));
  cmd_vel.twist.angular.z = std::clamp(kappa * cmd_vel.twist.linear.x,
                                        -_max_angular_vel, _max_angular_vel);
  return cmd_vel;
}

}  // namespace custom_controller

#include "pluginlib/class_list_macros.hpp"
PLUGINLIB_EXPORT_CLASS(custom_controller::CustomPurePursuit, nav2_core::Controller)
```

#### C.3 自定义 Costmap Layer

```cpp
// custom_costmap_layer.hpp
#ifndef CUSTOM_COSTMAP_LAYER_HPP_
#define CUSTOM_COSTMAP_LAYER_HPP_

#include "rclcpp/rclcpp.hpp"
#include "nav2_costmap_2d/layer.hpp"
#include "nav2_costmap_2d/layered_costmap.hpp"
#include "nav2_costmap_2d/costmap_math.hpp"
#include "sensor_msgs/msg/point_cloud2.hpp"

namespace custom_costmap
{
// 自定义代价图层：根据点云加入"危险区域"标记
class CustomObstacleLayer : public nav2_costmap_2d::Layer
{
public:
  CustomObstacleLayer() : last_min_x_(1e30), last_min_y_(1e30),
                          last_max_x_(-1e30), last_max_y_(-1e30) {}

  void onInitialize() override;
  void updateBounds(double robot_x, double robot_y, double robot_yaw,
                    double * min_x, double * min_y,
                    double * max_x, double * max_y) override;
  void updateCosts(nav2_costmap_2d::Costmap2D & master_grid,
                   int min_i, int min_j, int max_i, int max_j) override;
  void reset() override { onReset(); }
  bool isClearable() override { return true; }

private:
  void pointcloudCallback(const sensor_msgs::msg::PointCloud2::SharedPtr msg);

  std::string topic_;
  double obstacle_range_;       // 障碍最大距离
  double raytrace_range_;       // 光线追踪最大距离
  double last_min_x_, last_min_y_, last_max_x_, last_max_y_;
  rclcpp::Subscription<sensor_msgs::msg::PointCloud2>::SharedPtr sub_;
  std::vector<std::pair<double, double>> latest_points_;
};

}  // namespace custom_costmap

#endif
```

```cpp
// custom_costmap_layer.cpp
#include "custom_planner/custom_costmap_layer.hpp"
#include <algorithm>

namespace custom_costmap
{

void CustomObstacleLayer::onInitialize()
{
  auto node = node_.lock();
  declareParameter("enabled", rclcpp::ParameterValue(true));
  node->get_parameter(name_ + ".enabled", enabled_);
  declareParameter("topic", rclcpp::ParameterValue(std::string("/points")));
  node->get_parameter(name_ + ".topic", topic_);
  declareParameter("obstacle_range", rclcpp::ParameterValue(3.0));
  node->get_parameter(name_ + ".obstacle_range", obstacle_range_);
  declareParameter("raytrace_range", rclcpp::ParameterValue(5.0));
  node->get_parameter(name_ + ".raytrace_range", raytrace_range_);

  sub_ = node->create_subscription<sensor_msgs::msg::PointCloud2>(
    topic_, 10,
    std::bind(&CustomObstacleLayer::pointcloudCallback, this, std::placeholders::_1));
  RCLCPP_INFO(node->get_logger(),
              "CustomObstacleLayer 初始化完成, topic=%s", topic_.c_str());
}

void CustomObstacleLayer::pointcloudCallback(const sensor_msgs::msg::PointCloud2::SharedPtr /*msg*/)
{
  // 简化：实际应解析点云字段
  latest_points_.clear();
}

void CustomObstacleLayer::updateBounds(double /*robot_x*/, double /*robot_y*/,
                                       double /*robot_yaw*/,
                                       double * min_x, double * min_y,
                                       double * max_x, double * max_y)
{
  if (!enabled_) return;
  for (auto & p : latest_points_) {
    *min_x = std::min(*min_x, p.first);
    *min_y = std::min(*min_y, p.second);
    *max_x = std::max(*max_x, p.first);
    *max_y = std::max(*max_y, p.second);
  }
}

void CustomObstacleLayer::updateCosts(nav2_costmap_2d::Costmap2D & master_grid,
                                      int min_i, int min_j, int max_i, int max_j)
{
  if (!enabled_) return;
  for (auto & p : latest_points_) {
    unsigned int mx, my;
    if (!master_grid.worldToMap(p.first, p.second, mx, my)) continue;
    if (mx < static_cast<unsigned>(min_i) || mx >= static_cast<unsigned>(max_i)) continue;
    if (my < static_cast<unsigned>(min_j) || my >= static_cast<unsigned>(max_j)) continue;
    master_grid.setCost(mx, my, nav2_costmap_2d::LETHAL_OBSTACLE);
  }
}

}  // namespace custom_costmap

#include "pluginlib/class_list_macros.hpp"
PLUGINLIB_EXPORT_CLASS(custom_costmap::CustomObstacleLayer, nav2_costmap_2d::Layer)
```

#### C.4 plugin.xml 配置

```xml
<!-- custom_planner_plugin.xml -->
<library path="custom_planner_plugins">
  <class name="custom_planner/StraightLinePlanner"
         type="custom_planner::StraightLinePlanner"
         base_class_type="nav2_core::GlobalPlanner">
    <description>自定义直线插值全局规划器</description>
  </class>
  <class name="custom_controller/CustomPurePursuit"
         type="custom_controller::CustomPurePursuit"
         base_class_type="nav2_core::Controller">
    <description>自定义 Pure Pursuit 控制器</description>
  </class>
  <class name="custom_costmap/CustomObstacleLayer"
         type="custom_costmap::CustomObstacleLayer"
         base_class_type="nav2_costmap_2d::Layer">
    <description>自定义点云代价图层</description>
  </class>
</library>
```

#### C.5 CMakeLists.txt

```cmake
cmake_minimum_required(VERSION 3.8)
project(custom_planner)

if(NOT CMAKE_CXX_STANDARD)
  set(CMAKE_CXX_STANDARD 17)
endif()

find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(rclcpp_lifecycle REQUIRED)
find_package(nav2_core REQUIRED)
find_package(nav2_costmap_2d REQUIRED)
find_package(nav2_util REQUIRED)
find_package(pluginlib REQUIRED)
find_package(tf2_ros REQUIRED)
find_package(geometry_msgs REQUIRED)
find_package(nav_msgs REQUIRED)
find_package(sensor_msgs REQUIRED)

# 全局规划器插件库
add_library(custom_global_planner SHARED
  src/custom_global_planner.cpp)
target_include_directories(custom_global_planner PUBLIC
  $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
  $<INSTALL_INTERFACE:include>)
ament_target_dependencies(custom_global_planner
  rclcpp rclcpp_lifecycle nav2_core nav2_util pluginlib
  tf2_ros geometry_msgs nav_msgs)
pluginlib_export_plugin_description_file(nav2_core custom_planner_plugin.xml)

# 控制器插件库
add_library(custom_controller SHARED
  src/custom_controller.cpp)
target_include_directories(custom_controller PUBLIC
  $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
  $<INSTALL_INTERFACE:include>)
ament_target_dependencies(custom_controller
  rclcpp rclcpp_lifecycle nav2_core nav2_costmap_2d nav2_util
  pluginlib tf2_ros geometry_msgs nav_msgs)
pluginlib_export_plugin_description_file(nav2_core custom_planner_plugin.xml)

# 代价图层插件库
add_library(custom_costmap_layer SHARED
  src/custom_costmap_layer.cpp)
target_include_directories(custom_costmap_layer PUBLIC
  $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
  $<INSTALL_INTERFACE:include>)
ament_target_dependencies(custom_costmap_layer
  rclcpp nav2_costmap_2d pluginlib sensor_msgs)

install(TARGETS custom_global_planner custom_controller custom_costmap_layer
  ARCHIVE DESTINATION lib
  LIBRARY DESTINATION lib
  RUNTIME DESTINATION bin)
install(DIRECTORY include/ DESTINATION include/)
install(FILES custom_planner_plugin.xml DESTINATION share/custom_planner)

ament_export_dependencies(rclcpp nav2_core nav2_costmap_2d pluginlib)
ament_export_include_directories(include)
ament_package()
```

---

### D. C++ MPC 控制器完整实现

#### D.1 MPC 控制器头文件

```cpp
// mpc_controller.hpp
#ifndef MPC_CONTROLLER_HPP_
#define MPC_CONTROLLER_HPP_

#include <vector>
#include <array>
#include <casadi/casadi.hpp>
#include "rclcpp/rclcpp.hpp"
#include "geometry_msgs/msg/twist.hpp"
#include "geometry_msgs/msg/pose_stamped.hpp"
#include "nav_msgs/msg/path.hpp"

namespace mpc_controller
{
// 差速底盘 MPC 控制器
// 状态 x = [x, y, theta]^T
// 控制 u = [v, omega]^T
// 动力学: x_{k+1} = x_k + v_k*cos(theta_k)*dt
//         y_{k+1} = y_k + v_k*sin(theta_k)*dt
//         theta_{k+1} = theta_k + omega_k*dt
class MPCController
{
public:
  MPCController(int N = 20, double dt = 0.1,
                double v_max = 1.5, double omega_max = 1.0);

  // 求解：返回 [v, omega]
  std::array<double, 2> solve(
    const std::array<double, 3> & x0,                  // 当前状态
    const std::vector<std::array<double, 3>> & ref);   // 参考轨迹

private:
  int N_;
  double dt_;
  double v_max_, omega_max_;
  casadi::Opti opti_;
  casadi::MX X_;     // 状态变量 (3, N+1)
  casadi::MX U_;     // 控制变量 (2, N)
  casadi::MX cost_;  // 代价
};

}  // namespace mpc_controller
#endif
```

#### D.2 MPC 实现（CasADi + IPOPT 求解）

```cpp
// mpc_controller.cpp
#include "mpc_controller/mpc_controller.hpp"
#include <iostream>

namespace mpc_controller
{

MPCController::MPCController(int N, double dt, double v_max, double omega_max)
: N_(N), dt_(dt), v_max_(v_max), omega_max_(omega_max), opti_()
{
  // 决策变量：状态序列和控制序列
  X_ = opti_.variable(3, N_ + 1);
  U_ = opti_.variable(2, N_);

  // 动力学约束：x_{k+1} = f(x_k, u_k)
  for (int k = 0; k < N_; ++k) {
    casadi::MX x_next = X_(casadi::Slice(), k) + casadi::MX::vertcat({
      U_(0, k) * casadi::MX::cos(X_(2, k)) * dt_,
      U_(0, k) * casadi::MX::sin(X_(2, k)) * dt_,
      U_(1, k) * dt_
    });
    opti_.subject_to(X_(casadi::Slice(), k + 1) == x_next);
  }

  // 控制约束
  opti_.subject_to(opti_.bounded(-v_max_, U_(0, casadi::Slice()), v_max_));
  opti_.subject_to(opti_.bounded(-omega_max_, U_(1, casadi::Slice()), omega_max_));
  // 加速度约束（避免突变）
  for (int k = 0; k < N_ - 1; ++k) {
    opti_.subject_to(opti_.bounded(-0.5, U_(0, k+1) - U_(0, k), 0.5));
    opti_.subject_to(opti_.bounded(-1.0, U_(1, k+1) - U_(1, k), 1.0));
  }
}

std::array<double, 2> MPCController::solve(
  const std::array<double, 3> & x0,
  const std::vector<std::array<double, 3>> & ref)
{
  // 初始状态约束
  opti_.subject_to(X_(0, 0) == x0[0]);
  opti_.subject_to(X_(1, 0) == x0[1]);
  opti_.subject_to(X_(2, 0) == x0[2]);

  // 代价函数：J = Σ [Q*err² + R*u²] + 末端代价
  casadi::MX Q = casadi::MX::diag(casadi::MX::vertcat({1.0, 1.0, 0.5}));
  casadi::MX R = casadi::MX::diag(casadi::MX::vertcat({0.1, 0.1}));
  casadi::MX cost = 0;
  for (int k = 0; k < N_; ++k) {
    // 跟踪参考轨迹
    casadi::MX ref_k = casadi::MX::vertcat({
      ref[k][0], ref[k][1], ref[k][2]
    });
    casadi::MX err = X_(casadi::Slice(), k) - ref_k;
    cost += mtimes(mtimes(err.T(), Q), err);
    cost += mtimes(mtimes(U_(casadi::Slice(), k).T(), R), U_(casadi::Slice(), k));
  }
  // 末端代价
  casadi::MX ref_T = casadi::MX::vertcat({
    ref[N_][0], ref[N_][1], ref[N_][2]
  });
  casadi::MX err_T = X_(casadi::Slice(), N_) - ref_T;
  casadi::MX Qf = Q * 10;
  cost += mtimes(mtimes(err_T.T(), Qf), err_T);

  opti_.minimize(cost);

  // 求解器配置：IPOPT
  casadi::Dict opts;
  opts["ipopt.print_level"] = 0;
  opts["print_time"] = 0;
  opts["ipopt.max_iter"] = 100;
  opts["ipopt.tol"] = 1e-4;
  opti_.solver("ipopt", opts);

  // 求解
  try {
    auto sol = opti_.solve();
    double v0 = static_cast<double>(sol.value(U_(0, 0)));
    double w0 = static_cast<double>(sol.value(U_(1, 0)));
    return {v0, w0};
  } catch (std::exception & e) {
    std::cerr << "MPC 求解失败: " << e.what() << std::endl;
    return {0.0, 0.0};
  }
}

}  // namespace mpc_controller
```

#### D.3 ROS2 节点封装（滚动优化循环）

```cpp
// mpc_node.hpp
#ifndef MPC_NODE_HPP_
#define MPC_NODE_HPP_

#include "rclcpp/rclcpp.hpp"
#include "geometry_msgs/msg/twist.hpp"
#include "geometry_msgs/msg/pose_stamped.hpp"
#include "nav_msgs/msg/odometry.hpp"
#include "nav_msgs/msg/path.hpp"
#include "mpc_controller/mpc_controller.hpp"
#include <mutex>

class MPCNode : public rclcpp::Node
{
public:
  MPCNode();

private:
  void odomCallback(const nav_msgs::msg::Odometry::SharedPtr msg);
  void pathCallback(const nav_msgs::msg::Path::SharedPtr msg);
  void controlLoop();                       // 滚动优化循环

  std::shared_ptr<mpc_controller::MPCController> mpc_;
  rclcpp::Subscription<nav_msgs::msg::Odometry>::SharedPtr odom_sub_;
  rclcpp::Subscription<nav_msgs::msg::Path>::SharedPtr path_sub_;
  rclcpp::Publisher<geometry_msgs::msg::Twist>::SharedPtr cmd_pub_;
  rclcpp::TimerBase::SharedPtr timer_;

  std::mutex mtx_;
  std::array<double, 3> current_state_{0, 0, 0};
  nav_msgs::msg::Path current_path_;
  size_t path_idx_ = 0;
};

#endif
```

```cpp
// mpc_node.cpp
#include "mpc_node.hpp"
#include "tf2/utils.h"
#include <cmath>

MPCNode::MPCNode() : Node("mpc_node")
{
  // 声明参数
  int N = this->declare_parameter("N", 20);
  double dt = this->declare_parameter("dt", 0.1);
  double v_max = this->declare_parameter("v_max", 1.5);
  double omega_max = this->declare_parameter("omega_max", 1.0);
  double freq = this->declare_parameter("control_freq", 10.0);

  mpc_ = std::make_shared<mpc_controller::MPCController>(N, dt, v_max, omega_max);

  odom_sub_ = this->create_subscription<nav_msgs::msg::Odometry>(
    "/odom", 10,
    std::bind(&MPCNode::odomCallback, this, std::placeholders::_1));
  path_sub_ = this->create_subscription<nav_msgs::msg::Path>(
    "/global_plan", 10,
    std::bind(&MPCNode::pathCallback, this, std::placeholders::_1));
  cmd_pub_ = this->create_publisher<geometry_msgs::msg::Twist>("/cmd_vel", 10);

  // 控制循环（滚动优化）
  timer_ = this->create_wall_timer(
    std::chrono::milliseconds(static_cast<int>(1000.0 / freq)),
    std::bind(&MPCNode::controlLoop, this));

  RCLCPP_INFO(this->get_logger(), "MPC 节点启动 N=%d dt=%.2f", N, dt);
}

void MPCNode::odomCallback(const nav_msgs::msg::Odometry::SharedPtr msg)
{
  std::lock_guard<std::mutex> lk(mtx_);
  current_state_[0] = msg->pose.pose.position.x;
  current_state_[1] = msg->pose.pose.position.y;
  current_state_[2] = tf2::getYaw(msg->pose.pose.orientation);
}

void MPCNode::pathCallback(const nav_msgs::msg::Path::SharedPtr msg)
{
  std::lock_guard<std::mutex> lk(mtx_);
  current_path_ = *msg;
  path_idx_ = 0;
}

void MPCNode::controlLoop()
{
  std::lock_guard<std::mutex> lk(mtx_);
  if (current_path_.poses.empty()) return;

  // 从当前路径索引向后取 N+1 个参考点
  int N = 20;
  std::vector<std::array<double, 3>> ref;
  for (int i = 0; i <= N; ++i) {
    size_t idx = std::min(path_idx_ + i, current_path_.poses.size() - 1);
    const auto & p = current_path_.poses[idx].pose;
    ref.push_back({p.position.x, p.position.y, tf2::getYaw(p.orientation)});
  }
  // 滚动索引前进
  if (path_idx_ < current_path_.poses.size() - 1) path_idx_++;

  // MPC 求解
  auto cmd = mpc_->solve(current_state_, ref);

  // 发布速度
  geometry_msgs::msg::Twist twist;
  twist.linear.x = cmd[0];
  twist.angular.z = cmd[1];
  cmd_pub_->publish(twist);
}

int main(int argc, char ** argv)
{
  rclcpp::init(argc, argv);
  rclcpp::spin(std::make_shared<MPCNode>());
  rclcpp::shutdown();
  return 0;
}
```

#### D.4 CMakeLists.txt

```cmake
cmake_minimum_required(VERSION 3.8)
project(mpc_controller_pkg)

if(NOT CMAKE_CXX_STANDARD)
  set(CMAKE_CXX_STANDARD 17)
endif()

find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(geometry_msgs REQUIRED)
find_package(nav_msgs REQUIRED)
find_package(tf2 REQUIRED)
find_package(tf2_ros REQUIRED)
find_package(CasADi REQUIRED)

add_library(mpc_controller STATIC
  src/mpc_controller.cpp)
target_include_directories(mpc_controller PUBLIC
  $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
  $<INSTALL_INTERFACE:include>)
ament_target_dependencies(mpc_controller rclcpp geometry_msgs nav_msgs)
target_link_libraries(mpc_controller ${CasADi_LIBRARIES})
target_include_directories(mpc_controller PUBLIC ${CasADi_INCLUDE_DIRS})

add_executable(mpc_node src/mpc_node.cpp)
target_include_directories(mpc_node PUBLIC
  $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
  $<INSTALL_INTERFACE:include>)
ament_target_dependencies(mpc_node rclcpp geometry_msgs nav_msgs tf2 tf2_ros)
target_link_libraries(mpc_node mpc_controller)

install(TARGETS mpc_node
  RUNTIME DESTINATION lib/mpc_controller_pkg)
install(DIRECTORY include/ DESTINATION include/)
ament_package()
```

---

### E. Python SLAM 建图和导航脚本

#### E.1 Cartographer 参数配置

```lua
-- cartographer_2d.lua - Cartographer 2D 建图参数
include "map_builder.lua"
include "trajectory_builder.lua"
include "local_trajectory_builder.2d.lua"
include "poes.lua"

options = {
  map_builder = MAP_BUILDER,
  trajectory_builder = TRAJECTORY_BUILDER,
  map_frame = "map",
  tracking_frame = "imu_link",        -- IMU 坐标系（如有）
  published_frame = "odom",
  odom_frame = "odom",
  provide_odom_frame = false,
  publish_frame_projected_to_2d = true,
  use_odometry = true,
  use_nav_sat = false,
  use_landmarks = false,
  num_laser_scans = 1,                -- 单线激光
  num_multi_echo_laser_scans = 0,
  num_subdivisions_per_laser_scan = 1,
  num_point_clouds = 0,
  lookup_transform_timeout_sec = 0.2,
  submap_publish_period_sec = 0.3,
  pose_publish_period_sec = 5e-3,
  trajectory_publish_period_sec = 30e-3,
  rangefinder_sampling_ratio = 1.0,
  odometry_sampling_ratio = 1.0,
  fixed_frame_pose_sampling_ratio = 1.0,
  imu_sampling_ratio = 1.0,
  landmarks_sampling_ratio = 1.0,
}

-- 2D 前端参数
TRAJECTORY_BUILDER_2D.num_accumulated_range_data = 1
TRAJECTORY_BUILDER_2D.use_imu_data = true
TRAJECTORY_BUILDER_2D.use_online_correlative_scan_matching = true
TRAJECTORY_BUILDER_2D.motion_filter.max_angle_radians = 0.001
TRAJECTORY_BUILDER_2D.motion_filter.max_distance_meters = 0.05
TRAJECTORY_BUILDER_2D.submaps.num_range_data = 35
TRAJECTORY_BUILDER_2D.submaps.grid_options_2d.resolution = 0.05

-- 后端优化
MAP_BUILDER.use_trajectory_builder_2d = true
MAP_BUILDER.num_background_threads = 4
POSE_GRAPH.optimize_every_n_nodes = 35      -- 每攒 35 个节点优化一次
POSE_GRAPH.global_sampling_ratio = 0.3
POSE_GRAPH.constraint_builder.min_score = 0.55
POSE_GRAPH.constraint_builder.global_localization_min_score = 0.6
POSE_GRAPH.optimization_problem.huber_scale = 1e2

return options
```

#### E.2 LIO-SAM 配置（params.yaml）

```yaml
# lio_sam_params.yaml - LIO-SAM 3D SLAM 配置
lio_sam:
  ros__parameters:
    # 传感器话题
    imuTopic: "/imu/data"
    gpsTopic: "/gps/fix"
    lidarTopic: "/points_raw"

    # 传感器配置
    sensor: "livox"           # velodyne / ouster / livox
    N_SCAN: 6                 # Livox Mid-360 等效线数
    HorizonScan: 1800
    Dsr: 10                   # 帧率
    Dtime: 0.1
    lidarMinRange: 1.0
    lidarMaxRange: 1000.0

    # IMU 配置
    imuAccNoise: 3.9939570888238808e-03
    imuGyrNoise: 1.5636343949698187e-03
    imuAccBiasN: 6.4356659353532566e-05
    imuGyrBiasN: 3.5640388622400964e-05
    imuGravity: 9.80511
    imuRPYWeight: 0.01
    extrinsicRot: [1, 0, 0, 0, 1, 0, 0, 0, 1]
    extrinsicRPY: [1, 0, 0, 0, 1, 0, 0, 0, 1]

    # GPS 配置
    gpsTopic: "/gps/fix"
    useImuHeadingInitialization: true
    useGpsElevation: false
    gpsCovThreshold: 2.0
    poseCovThreshold: 25.0

    # 保存地图
    savePCD: true
    savePCDDirectory: "/tmp/LOAM/"
    savePCDInterval: 60.0

    # 优化
    maxIter: 10
    mappingCornerLeafSize: 0.2
    mappingSurfLeafSize: 0.4
    surroundingkeyframeAddingDistThreshold: 1.0
    surroundingkeyframeAddingAngleThreshold: 0.2
    surroundingKeyframeDensity: 1.0
    surroundingKeyframeSearchRadius: 50.0
    loopClosureEnable: true
    loopClosureFrequency: 1.0
    historyKeyframeSearchRadius: 15.0
    historyKeyframeSearchTimeDiff: 30.0
    historyKeyframeSearchNum: 25
    historyKeyframeFitnessScore: 0.3

    # IMU 预积分
    alpha: 0.8
    beta: 0.05
    gamma: 0.05
```

#### E.3 在线建图 Launch 文件

```python
# slam_online_launch.py - 在线建图启动
import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    slam_method = LaunchConfiguration('slam_method', default='cartographer')
    use_sim_time = LaunchConfiguration('use_sim_time', default='false')

    # slam_toolbox 在线异步建图
    slam_toolbox = Node(
        package='slam_toolbox',
        executable='async_slam_toolbox_node',
        name='slam_toolbox',
        output='screen',
        parameters=[
            os.path.join(get_package_share_directory('slam_toolbox'),
                         'config', 'mapper_params_online_async.yaml'),
            {'use_sim_time': use_sim_time,
             'base_frame': 'base_footprint',
             'odom_frame': 'odom',
             'map_frame': 'map',
             'scan_topic': '/scan',
             'mode': 'mapping'},
        ],
        remappings=[('/map', '/map'),
                    ('/tf', '/tf')],
    )

    # Cartographer 节点
    cartographer = Node(
        package='cartographer_ros',
        executable='cartographer_node',
        name='cartographer_node',
        output='screen',
        parameters=[{'use_sim_time': use_sim_time}],
        arguments=[
            '-configuration_directory',
            os.path.join(get_package_share_directory('cartographer_slam'),
                         'config'),
            '-configuration_basename', 'cartographer_2d.lua',
        ],
        remappings=[('/scan', '/scan'),
                    ('/odom', '/odom'),
                    ('/imu', '/imu/data')],
    )

    # Cartographer 占据栅格节点
    cartographer_occupancy = Node(
        package='cartographer_ros',
        executable='cartographer_occupancy_grid_node',
        name='cartographer_occupancy_grid',
        output='screen',
        parameters=[{'use_sim_time': use_sim_time,
                     'resolution': 0.05}],
    )

    # LIO-SAM 节点
    lio_sam = Node(
        package='lio_sam',
        executable='lio_sam_mapping',
        name='lio_sam_mapping',
        output='screen',
        parameters=[
            os.path.join(get_package_share_directory('lio_sam'),
                         'config', 'params.yaml'),
            {'use_sim_time': use_sim_time},
        ],
    )

    return LaunchDescription([
        DeclareLaunchArgument('slam_method', default_value='slam_toolbox'),
        DeclareLaunchArgument('use_sim_time', default_value='false'),
        slam_toolbox,
    ])
```

#### E.4 地图保存和加载脚本

```python
#!/usr/bin/env python3
# map_manager.py - 地图保存/加载工具
"""地图保存与加载：调用 nav2_map_server 服务"""
import rclpy
from rclpy.node import Node
from nav2_msgs.srv import SaveMap, LoadMap
from std_srvs.srv import Trigger
import sys


class MapManager(Node):
    def __init__(self):
        super().__init__('map_manager')
        self.save_cli = self.create_client(SaveMap, '/map_server/save_map')
        self.load_cli = self.create_client(LoadMap, '/map_server/load_map')
        while not self.save_cli.wait_for_service(timeout_sec=1.0):
            self.get_logger().info('等待 save_map 服务...')
        while not self.load_cli.wait_for_service(timeout_sec=1.0):
            self.get_logger().info('等待 load_map 服务...')

    def save_map(self, map_path: str):
        """保存地图到 YAML 文件"""
        req = SaveMap.Request()
        req.map_url = map_path
        req.occupancy_threshold = 0.65
        req.free_threshold = 0.25
        future = self.save_cli.call_async(req)
        rclpy.spin_until_future_complete(self, future)
        if future.result().result:
            self.get_logger().info(f'地图已保存: {map_path}')
        else:
            self.get_logger().error('地图保存失败')

    def load_map(self, map_path: str):
        """从 YAML 文件加载地图"""
        req = LoadMap.Request()
        req.map_url = map_path
        future = self.load_cli.call_async(req)
        rclpy.spin_until_future_complete(self, future)
        if future.result().result == 0:  # RESULT_SUCCESS
            self.get_logger().info(f'地图已加载: {map_path}')
        else:
            self.get_logger().error('地图加载失败')


def main():
    rclpy.init()
    node = MapManager()
    if len(sys.argv) < 3:
        print('用法:')
        print('  保存地图: python3 map_manager.py save /maps/workshop')
        print('  加载地图: python3 map_manager.py load /maps/workshop.yaml')
        sys.exit(1)
    action, path = sys.argv[1], sys.argv[2]
    if action == 'save':
        node.save_map(path)
    elif action == 'load':
        node.load_map(path)
    rclpy.shutdown()


if __name__ == '__main__':
    main()
```

#### E.5 导航启动脚本

```python
#!/usr/bin/env python3
# nav_start.py - 导航一键启动
"""启动 Nav2 完整导航栈，支持参数：--map /maps/workshop.yaml"""
import os
import argparse
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import ExecuteProcess, IncludeLaunchDescription, DeclareLaunchArgument
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def make_launch_description(map_file: str):
    nav2_share = get_package_share_directory('nav2_bringup')

    return LaunchDescription([
        # map_server 加载静态地图
        Node(package='nav2_map_server', executable='map_server',
             name='map_server', output='screen',
             parameters=[{'yaml_filename': map_file,
                          'use_sim_time': False}]),

        # AMCL 定位
        Node(package='nav2_amcl', executable='amcl',
             name='amcl', output='screen',
             parameters=[os.path.join(nav2_share, 'params', 'nav2_params.yaml')]),

        # planner + controller + behavior
        Node(package='nav2_planner', executable='planner_server',
             name='planner_server', output='screen',
             parameters=[os.path.join(nav2_share, 'params', 'nav2_params.yaml')]),
        Node(package='nav2_controller', executable='controller_server',
             name='controller_server', output='screen',
             parameters=[os.path.join(nav2_share, 'params', 'nav2_params.yaml')]),
        Node(package='nav2_behaviors', executable='behavior_server',
             name='behavior_server', output='screen',
             parameters=[os.path.join(nav2_share, 'params', 'nav2_params.yaml')]),
        Node(package='nav2_bt_navigator', executable='bt_navigator',
             name='bt_navigator', output='screen',
             parameters=[os.path.join(nav2_share, 'params', 'nav2_params.yaml')]),

        # lifecycle 自动启动
        Node(package='nav2_lifecycle_manager', executable='lifecycle_manager',
             name='lifecycle_manager_navigation',
             output='screen',
             parameters=[{'autostart': True,
                          'node_names': ['map_server', 'amcl',
                                          'planner_server', 'controller_server',
                                          'behavior_server', 'bt_navigator']}]),
    ])
```

---

### F. Python AMCL 定位调优工具

#### F.1 参数扫描脚本

```python
#!/usr/bin/env python3
# amcl_param_sweep.py - AMCL 参数扫描
"""扫描 min_particles/max_particles/laser_max_range 等参数，输出最优组合"""
import subprocess
import yaml
import time
import itertools
import json
import rclpy
from rclpy.node import Node
from nav_msgs.msg import Odometry
from geometry_msgs.msg import PoseWithCovarianceStamped
import numpy as np


class AMCLTuner(Node):
    def __init__(self):
        super().__init__('amcl_tuner')
        self.create_subscription(PoseWithCovarianceStamped,
                                  '/amcl_pose', self._pose_cb, 10)
        self.create_subscription(Odometry, '/odom', self._odom_cb, 10)
        self.amcl_pose = None
        self.odom_pose = None
        self.cov_history = []

    def _pose_cb(self, msg):
        self.amcl_pose = msg

    def _odom_cb(self, msg):
        self.odom_pose = msg.pose.pose

    def evaluate(self, duration: float = 30.0) -> dict:
        """评估当前参数下定位精度，返回指标"""
        self.cov_history.clear()
        start = time.time()
        while time.time() - start < duration:
            if self.amcl_pose:
                cov = self.amcl_pose.pose.covariance
                self.cov_history.append([
                    cov[0], cov[7], cov[14], cov[21], cov[28], cov[35]
                ])
            time.sleep(0.1)
        if not self.cov_history:
            return {'mean_cov_x': 1e9, 'mean_cov_y': 1e9, 'score': 1e9}
        arr = np.array(self.cov_history)
        mean_x = float(np.sqrt(arr[:, 0]).mean())
        mean_y = float(np.sqrt(arr[:, 7]).mean())
        mean_yaw = float(np.sqrt(arr[:, 35]).mean())
        return {
            'mean_cov_x': mean_x,
            'mean_cov_y': mean_y,
            'mean_cov_yaw': mean_yaw,
            'score': mean_x + mean_y + 0.1 * mean_yaw,
        }

    def set_param(self, params: dict):
        """运行时设置 AMCL 参数"""
        for k, v in params.items():
            subprocess.run([
                'ros2', 'param', 'set', '/amcl', k, str(v)
            ], check=False)


def run_sweep():
    rclpy.init()
    node = AMCLTuner()

    # 扫描参数网格
    grid = {
        'min_particles': [200, 500, 1000],
        'max_particles': [1000, 3000, 5000],
        'laser_max_range': [5.0, 10.0, 20.0],
        'z_hit': [0.3, 0.5, 0.7],
    }
    keys = list(grid.keys())
    results = []
    for combo in itertools.product(*[grid[k] for k in keys]):
        params = dict(zip(keys, combo))
        print(f'>>> 测试参数: {params}')
        node.set_param(params)
        time.sleep(2.0)  # 等待参数生效
        metrics = node.evaluate(duration=15.0)
        print(f'    指标: {metrics}')
        results.append({'params': params, 'metrics': metrics})

    # 排序找最优
    results.sort(key=lambda r: r['metrics']['score'])
    print('\n=== 扫描结果（按 score 升序）===')
    for r in results[:5]:
        print(json.dumps(r, indent=2))
    with open('/tmp/amcl_sweep.json', 'w') as f:
        json.dump(results, f, indent=2)
    rclpy.shutdown()


if __name__ == '__main__':
    run_sweep()
```

#### F.2 定位精度评估

```python
#!/usr/bin/env python3
# amcl_accuracy_eval.py - AMCL 定位精度评估
"""对比 AMCL 输出与真值（或里程计+回环真值），输出 RMSE 和误差分布"""
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import PoseWithCovarianceStamped, PoseStamped
from nav_msgs.msg import Odometry
import numpy as np
import time


class AccuracyEval(Node):
    def __init__(self):
        super().__init__('amcl_accuracy_eval')
        self.amcl_sub = self.create_subscription(
            PoseWithCovarianceStamped, '/amcl_pose', self.amcl_cb, 10)
        self.gt_sub = self.create_subscription(
            Odometry, '/ground_truth/odom', self.gt_cb, 10)
        self.amcl = None
        self.gt = None
        self.errors = []

    def amcl_cb(self, msg):
        self.amcl = (msg.pose.pose.position.x,
                     msg.pose.pose.position.y,
                     self._yaw(msg.pose.pose.orientation))

    def gt_cb(self, msg):
        self.gt = (msg.pose.pose.position.x,
                   msg.pose.pose.position.y,
                   self._yaw(msg.pose.pose.orientation))
        if self.amcl and self.gt:
            dx = self.amcl[0] - self.gt[0]
            dy = self.amcl[1] - self.gt[1]
            dyaw = (self.amcl[2] - self.gt[2] + np.pi) % (2*np.pi) - np.pi
            self.errors.append([dx, dy, dyaw])

    @staticmethod
    def _yaw(q):
        import tf_transformations  # ros-humble-tf-transformations
        return tf_transformations.euler_from_quaternion(
            [q.x, q.y, q.z, q.w])[2]

    def report(self):
        if not self.errors:
            print('无数据')
            return
        arr = np.array(self.errors)
        rmse_x = float(np.sqrt((arr[:, 0]**2).mean()))
        rmse_y = float(np.sqrt((arr[:, 1]**2).mean()))
        rmse_yaw = float(np.sqrt((arr[:, 2]**2).mean()))
        print(f'样本数: {len(arr)}')
        print(f'RMSE X: {rmse_x*100:.2f} cm')
        print(f'RMSE Y: {rmse_y*100:.2f} cm')
        print(f'RMSE Yaw: {np.degrees(rmse_yaw):.2f} deg')
        print(f'最大偏差 X: {arr[:,0].max()*100:.2f} cm')
        print(f'最大偏差 Y: {arr[:,1].max()*100:.2f} cm')


def main():
    rclpy.init()
    node = AccuracyEval()
    print('采集 60 秒数据...')
    end = time.time() + 60
    while time.time() < end:
        rclpy.spin_once(node, timeout_sec=0.1)
    node.report()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
```

#### F.3 重定位测试与 kidnap 恢复测试

```python
#!/usr/bin/env python3
# amcl_kidnap_test.py - Kidnap 恢复测试
"""模拟人工搬运：通过 set_pose 主动修改 AMCL 位姿，
   随后测量恢复到正确位姿所需时间"""
import rclpy
from rclpy.node import Node
from nav_msgs.srv import SetPoseAmcl, GetPoseAmcl   # 注意 Humble 接口
import time
import subprocess
import math


class KidnapTest(Node):
    def __init__(self):
        super().__init__('kidnap_test')
        # /initialpose 话题或 /amcl/set_pose 服务均可触发重定位
        self.cli = self.create_client(SetPoseAmcl, '/amcl/set_pose')
        while not self.cli.wait_for_service(timeout_sec=1.0):
            self.get_logger().info('等待 set_pose 服务...')

    def set_pose(self, x, y, yaw_deg):
        from geometry_msgs.msg import PoseWithCovarianceStamped, Pose
        req = SetPoseAmcl.Request()
        req.pose.header.stamp = self.get_clock().now().to_msg()
        req.pose.header.frame_id = 'map'
        req.pose.pose.pose.position.x = float(x)
        req.pose.pose.pose.position.y = float(y)
        # 用 yaw 转 quaternion
        import tf_transformations
        q = tf_transformations.quaternion_from_euler(0, 0, math.radians(yaw_deg))
        req.pose.pose.pose.orientation.x = q[0]
        req.pose.pose.pose.orientation.y = q[1]
        req.pose.pose.pose.orientation.z = q[2]
        req.pose.pose.pose.orientation.w = q[3]
        future = self.cli.call_async(req)
        rclpy.spin_until_future_complete(self, future)
        return future.result()

    def measure_recovery(self, true_x, true_y, true_yaw_deg, max_wait=60.0):
        """测量 AMCL 恢复时间"""
        print(f'真值: x={true_x}, y={true_y}, yaw={true_yaw_deg}')
        # 1) 故意错误位姿（kidnap）
        self.set_pose(0.0, 0.0, 0.0)
        print('已设置错误位姿，等待 AMCL 收敛...')
        # 2) 监听 amcl_pose 直到收敛到真值
        start = time.time()
        from geometry_msgs.msg import PoseWithCovarianceStamped
        converged = {'state': False}
        def pose_cb(msg):
            if converged['state']:
                return
            dx = msg.pose.pose.position.x - true_x
            dy = msg.pose.pose.position.y - true_y
            cov_x = msg.pose.covariance[0]
            cov_y = msg.pose.covariance[7]
            if math.hypot(dx, dy) < 0.3 and cov_x < 0.05 and cov_y < 0.05:
                converged['state'] = True
                converged['time'] = time.time() - start
                print(f'已收敛！耗时 {converged["time"]:.2f}s')
        sub = self.create_subscription(PoseWithCovarianceStamped,
                                        '/amcl_pose', pose_cb, 10)
        end = start + max_wait
        while time.time() < end and not converged.get('state'):
            rclpy.spin_once(self, timeout_sec=0.1)
        if not converged.get('state'):
            print(f'{max_wait}s 内未收敛')
        return converged.get('time', -1)


def main():
    rclpy.init()
    node = KidnapTest()
    # 模拟 5 次 kidnap
    trials = [
        (5.0, 3.0, 90.0),
        (2.0, -1.0, 45.0),
        (-3.0, 4.0, 180.0),
        (10.0, 5.0, 0.0),
        (0.0, 0.0, 270.0),
    ]
    times = []
    for i, (x, y, yaw) in enumerate(trials):
        print(f'\n=== 第 {i+1} 次 kidnap 测试 ===')
        t = node.measure_recovery(x, y, yaw, max_wait=60.0)
        if t > 0:
            times.append(t)
    print(f'\n=== 总结: 平均恢复时间 {sum(times)/max(1,len(times)):.2f}s ===')
    rclpy.shutdown()


if __name__ == '__main__':
    main()
```

---

### G. Ubuntu 导航调试工具

#### G.1 nav2_view 工具使用

```bash
# 1. 查看所有 Nav2 节点和生命周期状态
ros2 lifecycle list
ros2 lifecycle nodes

# 2. 查询某节点当前状态
ros2 lifecycle get /controller_server

# 3. 触发状态转移
ros2 lifecycle set /controller_server configure
ros2 lifecycle set /controller_server activate
ros2 lifecycle set /controller_server deactivate
ros2 lifecycle set /controller_server cleanup

# 4. Nav2 自带监控：bt_navigator 状态查询
ros2 topic echo /behavior_tree_log --once

# 5. Nav2 速度限制器
ros2 topic pub /velocity_smoother/scale_velocity std_msgs/msg/Float64 \
  "{data: 0.5}" --once

# 6. 列出所有已注册插件
ros2 pkg prefix nav2_core
ros2 run class_loader list_plugins --package nav2_core
```

#### G.2 rviz2 Nav2 可视化配置

```yaml
# nav2_default.rviz 关键 Display（节选）
Panels:
  - Class: rviz_common/Displays
    Name: Displays
Visualization Manager:
  Displays:
    - Class: rviz_default_plugins/RobotModel
      Name: RobotModel
      Enabled: true
    - Class: rviz_default_plugins/Map
      Name: GlobalMap
      Topic:
        Value: /global_costmap/costmap
      Enabled: true
    - Class: rviz_default_plugins/Map
      Name: LocalMap
      Topic:
        Value: /local_costmap/costmap
      Enabled: true
    - Class: rviz_default_plugins/Path
      Name: GlobalPath
      Topic:
        Value: /plan
      Color: 25; 255; 0
      Enabled: true
    - Class: rviz_default_plugins/Path
      Name: LocalPath
      Topic:
        Value: /local_plan
      Color: 255; 25; 0
      Enabled: true
    - Class: rviz_default_plugins/PoseArray
      Name: AMCLParticles
      Topic:
        Value: /particlecloud
      Enabled: true
    - Class: rviz_default_plugins/PoseWithCovariance
      Name: AMCLPose
      Topic:
        Value: /amcl_pose
      Enabled: true
    - Class: rviz_default_plugins/MarkerArray
      Name: TrajectoryPredict
      Topic:
        Value: /local_plan_markers
      Enabled: true
  Global Options:
    Fixed Frame: map
```

启动：
```bash
rviz2 -d $(ros2 pkg prefix nav2_bringup)/share/nav2_bringup/rviz/nav2_default_view.rviz
# 设置初始位姿
ros2 topic pub --once /initialpose geometry_msgs/PoseWithCovarianceStamped ...
# 发送目标点（也可在 RViz 中用 2D Goal Pose 工具）
ros2 action send_goal /navigate_to_pose nav2_msgs/action/NavigateToPose ...
```

#### G.3 PlotJuggler 实时数据可视化

```bash
# 1. 安装
sudo apt install ros-humble-plotjuggler-ros

# 2. 启动并订阅 ROS2 话题
ros2 run plotjuggler plotjuggler

# 3. 在 PlotJuggler 中：Data → ROS2 Topic Subscriber → 添加：
#    /odom (nav_msgs/Odometry)         -> pose.position.x, pose.position.y
#    /cmd_vel (geometry_msgs/Twist)    -> linear.x, angular.z
#    /amcl_pose (PoseWithCovariance)   -> pose.covariance[0]
#    /local_costmap/costmap_updates    -> 代价更新频率
#    /joint_states (sensor_msgs/JointState) -> position[0..5]

# 4. 保存布局：File → Save Layout → nav_layout.xml

# 5. 命令行启动并加载布局
ros2 run plotjuggler plotjuggler -l /opt/robot/config/nav_layout.xml

# 6. 离线分析 rosbag
ros2 bag play my_bag.db3
ros2 run plotjuggler plotjuggler  # 选择 Streaming → ROS2 Topic Subscriber
```

#### G.4 ros2 topic echo 命令速查

```bash
# 基本用法
ros2 topic list                                   # 列出所有话题
ros2 topic info /cmd_vel                          # 话题信息（发布者/订阅者/类型）
ros2 topic echo /cmd_vel                          # 实时打印消息
ros2 topic echo /odom --once                      # 只取一条
ros2 topic echo /cmd_vel --field linear.x         # 只打印某字段
ros2 topic echo --filter "m.linear.x > 0.5" /cmd_vel   # 条件过滤

# 频率/带宽
ros2 topic hz /scan                               # 测量频率
ros2 topic bw /scan                               # 测量带宽(byte/s)
ros2 topic delay /odom                            # 测量 stamp 到现在的延迟

# 发布
ros2 topic pub /cmd_vel geometry_msgs/Twist "{linear: {x: 0.2}, angular: {z: 0.1}}"
ros2 topic pub --rate 10 /cmd_vel geometry_msgs/Twist "{...}"  # 10Hz 持续发布
ros2 topic pub --once /initialpose geometry_msgs/PoseWithCovarianceStamped "{...}"

# 服务/动作
ros2 service list
ros2 service call /amcl/set_pose nav2_msgs/srv/SetPoseAMcl "{...}"
ros2 action list
ros2 action send_goal /navigate_to_pose nav2_msgs/action/NavigateToPose "{...}"
ros2 action send_goal --feedback /navigate_to_pose nav2_msgs/action/NavigateToPose "{...}"

# 参数
ros2 param list
ros2 param get /amcl min_particles
ros2 param set /amcl min_particles 1000
ros2 param dump /amcl > amcl_params.yaml          # 导出当前参数
ros2 param load /amcl amcl_params.yaml            # 加载参数
```

#### G.5 地图编辑工具

```bash
# 1. map_server 自带：保存/加载
ros2 run nav2_map_server map_saver_cli -f /maps/workshop_edited
# 输出 workshop_edited.pgm + workshop_edited.yaml

# 2. 用 GIMP / Inkscape 编辑 .pgm
gimp /maps/workshop.pgm
# 工具：画笔涂黑添加障碍、橡皮擦清除障碍，导出 PGM（保持灰度模式）

# 3. 编辑 YAML 调整分辨率/原点
# workshop.yaml
#   image: workshop.pgm
#   resolution: 0.05
#   origin: [-10.0, -10.0, 0.0]
#   occupied_thresh: 0.65
#   free_thresh: 0.25
#   negate: 0

# 4. Python 脚本批量编辑地图
python3 - <<'EOF'
import numpy as np
from PIL import Image
img = np.array(Image.open('/maps/workshop.pgm'))
# 清除小障碍（中值滤波）
import scipy.ndimage as ndi
img_clean = ndi.median_filter(img, size=3)
# 添加虚拟墙
img_clean[400:500, 200:800] = 0     # 黑色=障碍
Image.fromarray(img_clean).save('/maps/workshop_edited.pgm')
EOF
```

#### G.6 Bag 录制导航过程

```bash
# 1. 录制核心话题（避免录全部导致磁盘爆满）
ros2 bag record -o nav_session_001 \
  /scan /odom /amcl_pose /tf /tf_static \
  /cmd_vel /plan /local_plan \
  /global_costmap/costmap /local_costmap/costmap \
  /behavior_tree_log /rosout

# 2. 限制录制时长（10 分钟）
ros2 bag record -o nav_session_001 -d 600 \
  /scan /odom /amcl_pose /tf /cmd_vel

# 3. 限制录制大小（每文件 1GB，最多 10 文件）
ros2 bag record -o nav_session_001 --max-cache-size 1000000000 \
  --storage-config-file config.yaml \
  /scan /odom /amcl_pose /cmd_vel

# 4. 录制所有话题（debug 用）
ros2 bag record -a -o full_session

# 5. 回放
ros2 bag play nav_session_001
ros2 bag play nav_session_001 --rate 0.5            # 0.5 倍速
ros2 bag play nav_session_001 --loop                # 循环
ros2 bag play nav_session_001 --topics /scan /odom  # 仅回放部分话题

# 6. 查看 bag 信息
ros2 bag info nav_session_001

# 7. bag 转 CSV / Pandas 分析
python3 - <<'EOF'
from rosbag2_py import SequentialReader, StorageOptions, ConverterOptions
import rclpy.serialization
from nav_msgs.msg import Odometry
reader = SequentialReader()
reader.open(StorageOptions(uri='nav_session_001',
                           storage_id='sqlite3'),
            ConverterOptions('cdr', 'cdr'))
while reader.has_next():
    topic, data, _ = reader.read_next()
    if topic == '/odom':
        msg = rclpy.serialization.deserialize_message(data, Odometry)
        print(msg.pose.pose.position.x, msg.pose.pose.position.y)
EOF
```
