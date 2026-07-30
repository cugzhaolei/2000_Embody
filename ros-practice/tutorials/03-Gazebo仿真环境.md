# 03 Gazebo 仿真环境搭建

## 3.1 Gazebo Harmonic 概述

Gazebo 8.x (Harmonic) 是新一代仿真引擎，与旧版 Gazebo Classic 差异显著：

| 特性 | Gazebo Classic (<=11) | Gazebo Harmonic (8.x) |
|------|----------------------|----------------------|
| 启动命令 | `gazebo` | `gz sim` |
| GUI 框架 | Qt5 | Qt6 + qml |
| 物理引擎 | ODE/Bullet | DART/ODE/TPE 可选 |
| 插件系统 | 编译时绑定 | 运行时动态加载 |
| ROS2 集成 | gazebo_ros_pkgs | ros_gz (gz_ros2_bridge) |
| SDF 版本 | 1.6 | 1.7+ |

## 3.2 创建仿真世界

### 仓库世界模型 (warehouse.sdf)

```xml
<?xml version="1.0"?>
<sdf version="1.7">
  <world name="warehouse">
    <!-- 物理引擎配置 -->
    <physics name="1ms" type="ignored">
      <max_step_size>0.001</max_step_size>
      <real_time_factor>1.0</real_time_factor>
    </physics>

    <!-- 插件：场景广播 -->
    <plugin filename="gz-sim-scene-broadcaster-system"
            name="gz::sim::systems::SceneBroadcaster">
      <publish_tf>true</publish_tf>
    </plugin>

    <!-- 插件：联系人管理 -->
    <plugin filename="gz-sim-contact-system"
            name="gz::sim::systems::Contact">
    </plugin>

    <!-- 环境光照 -->
    <scene>
      <ambient>0.4 0.4 0.4 1</ambient>
      <background>0.7 0.7 0.7 1</background>
      <shadows>true</shadows>
    </scene>

    <!-- 太阳光 -->
    <light type="directional" name="sun">
      <cast_shadows>true</cast_shadows>
      <pose>0 0 10 0 0 0</pose>
      <diffuse>0.8 0.8 0.8 1</diffuse>
      <specular>0.2 0.2 0.2 1</specular>
      <direction>-0.5 0.5 -1</direction>
    </light>

    <!-- 地面 -->
    <model name="ground_plane">
      <static>true</static>
      <link name="visual">
        <visual name="visual">
          <geometry>
            <plane><normal>0 0 1</normal><size>50 50</size></plane>
          </geometry>
          <material>
            <ambient>0.8 0.8 0.8 1</ambient>
            <diffuse>0.8 0.8 0.8 1</diffuse>
          </material>
        </visual>
        <collision name="collision">
          <geometry>
            <plane><normal>0 0 1</normal><size>50 50</size></plane>
          </geometry>
        </collision>
      </link>
      <plugin filename="gz-sim-contact-system"
              name="gz::sim::systems::Contact"/>
    </model>

    <!-- 货架 1 -->
    <model name="shelf_1">
      <static>true</static>
      <pose>3 0 0 0 0 0</pose>
      <link name="link">
        <visual name="visual">
          <geometry>
            <box><size>0.5 3.0 2.0</size></box>
          </geometry>
          <material>
            <ambient>0.6 0.3 0.1 1</ambient>
            <diffuse>0.6 0.3 0.1 1</diffuse>
          </material>
        </visual>
        <collision name="collision">
          <geometry>
            <box><size>0.5 3.0 2.0</size></box>
          </geometry>
        </collision>
      </link>
    </model>

    <!-- 货架 2 -->
    <model name="shelf_2">
      <static>true</static>
      <pose>3 5 0 0 0 0</pose>
      <link name="link">
        <visual name="visual">
          <geometry>
            <box><size>0.5 3.0 2.0</size></box>
          </geometry>
          <material>
            <ambient>0.6 0.3 0.1 1</ambient>
            <diffuse>0.6 0.3 0.1 1</diffuse>
          </material>
        </visual>
        <collision name="collision">
          <geometry>
            <box><size>0.5 3.0 2.0</size></box>
          </geometry>
        </collision>
      </link>
    </model>

    <!-- 障碍箱 -->
    <model name="box_1">
      <static>true</static>
      <pose>-2 -2 0.5 0 0 0</pose>
      <link name="link">
        <visual name="visual">
          <geometry>
            <box><size>1 1 1</size></box>
          </geometry>
          <material>
            <ambient>0.8 0.8 0.1 1</ambient>
            <diffuse>0.8 0.8 0.1 1</diffuse>
          </material>
        </visual>
        <collision name="collision">
          <geometry>
            <box><size>1 1 1</size></box>
          </geometry>
        </collision>
      </link>
    </model>

    <!-- 墙壁（构建封闭测试区域） -->
    <model name="wall_north">
      <static>true</static>
      <pose>0 8 1 0 0 0</pose>
      <link name="link">
        <collision name="collision">
          <geometry>
            <box><size>20 0.2 2</size></box>
          </geometry>
        </collision>
        <visual name="visual">
          <geometry>
            <box><size>20 0.2 2</size></box>
          </geometry>
          <material>
            <ambient>0.5 0.5 0.5 1</ambient>
            <diffuse>0.5 0.5 0.5 1</diffuse>
          </material>
        </visual>
      </link>
    </model>

    <model name="wall_south">
      <static>true</static>
      <pose>0 -8 1 0 0 0</pose>
      <link name="link">
        <collision name="collision">
          <geometry><box><size>20 0.2 2</size></box></geometry>
        </collision>
        <visual name="visual">
          <geometry><box><size>20 0.2 2</size></box></geometry>
          <material><ambient>0.5 0.5 0.5 1</ambient><diffuse>0.5 0.5 0.5 1</diffuse></material>
        </visual>
      </link>
    </model>

    <model name="wall_east">
      <static>true</static>
      <pose>8 0 1 0 0 0</pose>
      <link name="link">
        <collision name="collision">
          <geometry><box><size>0.2 16 2</size></box></geometry>
        </collision>
        <visual name="visual">
          <geometry><box><size>0.2 16 2</size></box></geometry>
          <material><ambient>0.5 0.5 0.5 1</ambient><diffuse>0.5 0.5 0.5 1</diffuse></material>
        </visual>
      </link>
    </model>

    <model name="wall_west">
      <static>true</static>
      <pose>-8 0 1 0 0 0</pose>
      <link name="link">
        <collision name="collision">
          <geometry><box><size>0.2 16 2</size></box></geometry>
        </collision>
        <visual name="visual">
          <geometry><box><size>0.2 16 2</size></box></geometry>
          <material><ambient>0.5 0.5 0.5 1</ambient><diffuse>0.5 0.5 0.5 1</diffuse></material>
        </visual>
      </link>
    </model>
  </world>
</sdf>
```

## 3.3 Gazebo 常用命令

```bash
# 启动仿真（GUI模式）
gz sim warehouse.sdf

# 启动仿真（无头模式，节省资源）
gz sim -s warehouse.sdf  # -s 仅服务端

# 暂停/继续
gz sim -s  # 查看服务端状态

# 生成模型（在运行中的Gazebo中添加模型）
gz sim -r  # 运行

# 查看话题（需 ros_gz 桥接）
ros2 topic list
```

## 3.4 ros_gz 桥接配置

Gazebo 话题与 ROS2 话题需要通过 `ros_gz_bridge` 桥接：

| Gazebo 话题 | ROS2 话题 | 消息类型 | 方向 |
|-------------|-----------|---------|------|
| /scan | /scan | sensor_msgs/LaserScan | Gazebo→ROS2 |
| /cmd_vel | /cmd_vel | geometry_msgs/Twist | ROS2→Gazebo |
| /odom | /odom | nav_msgs/Odometry | Gazebo→ROS2 |
| /tf | /tf | tf2_msgs/TFMessage | Gazebo→ROS2 |
| /joint_states | /joint_states | sensor_msgs/JointState | Gazebo→ROS2 |
| /clock | /clock | rosgraph_msgs/Clock | Gazebo→ROS2 |

## 3.5 启动仿真验证

```bash
# 启动 Gazebo（加载世界 + 机器人）
ros2 launch myfirst_robot gz_sim.launch.py

# 验证话题
ros2 topic list
# 应看到: /scan, /cmd_vel, /odom, /tf, /joint_states, /clock

# 查看激光数据
ros2 topic echo /scan --once

# 手动控制移动
ros2 topic pub /cmd_vel geometry_msgs/Twist \
  "{linear: {x: 0.3}, angular: {z: 0.0}}"
# 机器人应向前移动
```

---

**下一课**：[04-Launch启动文件](04-Launch启动文件.md) — 编写 ROS2 launch 文件编排全流程
