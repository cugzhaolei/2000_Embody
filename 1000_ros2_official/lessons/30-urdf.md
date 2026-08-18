# 第 30 课 · URDF 教程 (URDF)

> 对应鱼香ROS官方教程：[URDF教程](http://dev.ros2.fishros.com/doc/Tutorials/URDF/URDF-Main.html)

## 目标
用 URDF 描述机器人（link + joint），并在 RViz 中可视化。

## 代码位置
```
dev_ws/src/urdf_tutorial/urdf/
├── 01-myfirst.urdf          视觉模型（单个 box）
├── 02-multipleshapes.urdf   多个 link + 固定 joint
├── 03-origins.urdf          origin（xyz + rpy）控制位置/姿态
├── 04-materials.urdf        材质颜色
└── 05-visual.urdf           可动模型（wheel 连续旋转关节）
```

## 操作

```bash
source /opt/ros/foxy/setup.bash
sudo apt install -y ros-foxy-robot-state-publisher ros-foxy-joint-state-publisher ros-foxy-rviz2
cd ~/dev_ws
colcon build --packages-select urdf_tutorial
source install/setup.bash

# 查看第 1 个模型（需要 WSLg 显示 GUI）
ros2 launch urdf_tutorial display.launch.py model:=urdf/01-myfirst.urdf
# 依次换 02 / 03 / 04 / 05
ros2 launch urdf_tutorial display.launch.py model:=urdf/05-visual.urdf
```

在 RViz 里把 **Fixed Frame** 设为 `base_link`，即可看到机器人。

### 命令行检查
```bash
# 检查 URDF 是否合法（需 ros-foxy-joint-state-publisher 等）
ros2 run xacro xacro urdf/05-visual.urdf > /tmp/out.urdf
check_urdf /tmp/out.urdf      # 如果装了 urdfdom 的话
```

## URDF 语法速查
```xml
<robot name="xx">
  <link name="base_link">
    <visual>
      <geometry><box size="0.2 0.2 0.2"/></geometry>
      <origin xyz="0 0 0" rpy="0 0 0"/>
      <material name="blue"><color rgba="0 0 0.8 1"/></material>
    </visual>
  </link>
  <joint name="base_to_wheel" type="continuous">
    <parent link="base_link"/>
    <child link="wheel"/>
    <origin xyz="0 -0.2 0"/>
    <axis xyz="0 0 1"/>
  </joint>
</robot>
```

| joint 类型 | 说明 |
|-----------|------|
| `fixed` | 固定 |
| `revolute` | 旋转（限位） |
| `continuous` | 无限旋转（车轮） |
| `prismatic` | 平移（限位） |
| `floating` / `planar` | 自由/平面 |

## 进一步
- **Xacro**：用宏/变量简化重复的 URDF（`ros-foxy-xacro`）。
- **robot_state_publisher**：发布 `robot_description` 参数 → TF，让关节动起来。
