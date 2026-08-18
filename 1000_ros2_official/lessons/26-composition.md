# 第 26 课 · 在单个进程中组合多个节点 (Composition)

> 对应鱼香ROS官方教程：[在单个进程中组合多个节点](http://dev.ros2.fishros.com/doc/Tutorials/Composition.html)

## 目标
理解「组合(Composition)」：把多个节点放进**一个进程**，降低通信开销与内存占用。

## 代码位置
```
dev_ws/src/examples/rclcpp/composition/minimal_composition/
├── src/standalone_publisher.cpp   # 独立进程的发布者（对照组）
├── src/standalone_subscriber.cpp  # 独立进程的订阅者
└── src/composed.cpp               # 组合进程：发布者+订阅者在同一进程
```

## 操作

```bash
source /opt/ros/foxy/setup.bash
cd ~/dev_ws
colcon build --packages-select examples_rclcpp_minimal_composition
source install/setup.bash

# 方案 A：两个独立进程（两个节点各占一个进程）
ros2 run examples_rclcpp_minimal_composition composition_publisher
ros2 run examples_rclcpp_minimal_composition composition_subscriber

# 方案 B：组合 —— 发布者和订阅者在同一个进程
ros2 run examples_rclcpp_minimal_composition composition_composed

# 对比：用 ros2 node list 观察
ros2 node list
# 方案 A 出现 /publisher 和 /subscriber 两个节点（可能同机器不同 pid）
# 方案 B 里两个节点在同一个 pid
ps -ef | grep composition    # 观察进程数量差异
```

## 手动组合（ros2 component）
```bash
ros2 component types                          # 列出可用组件
ros2 run rclcpp_components component_container  # 启动容器进程
# 另一终端
ros2 component load /ComponentManager examples_rclcpp_minimal_composition composition::Talker
ros2 component load /ComponentManager examples_rclcpp_minimal_composition composition::Listener
ros2 component list /ComponentManager
```

## 为什么重要
- 减少进程数 → 内存/启动开销小
- 进程内通信零拷贝 → 吞吐高
- 工业界（导航、MoveIt）大量使用

## 说明
该包中节点通过 `rclcpp_components` 注册为组件，CMake 里用 `add_library(... SHARED)` 编译为动态库。
