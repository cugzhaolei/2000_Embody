# 第 3 课 · 了解 ROS 2 节点 (Understanding ROS 2 Nodes)

> 对应鱼香ROS官方教程：[了解ROS 2节点](http://dev.ros2.fishros.com/doc/Tutorials/Understanding-ROS2-Nodes.html)

## 目标
理解「节点」是 ROS 2 图中执行计算的进程，学会用 `ros2 node` 系列命令。

## 操作

```bash
source /opt/ros/foxy/setup.bash

# 终端 1
ros2 run turtlesim turtlesim_node

# 终端 2
ros2 node list                          # 列出所有节点：/turtlesim
ros2 node info /turtlesim               # 查看节点信息（订阅/发布的话题、服务、动作）
```

### 重映射（Remapping）
同一个包可以起多个不同名字的节点：

```bash
ros2 run turtlesim turtlesim_node --ros-args --remap __node:=my_turtle
# 另一个终端
ros2 node list                          # 会看到 /my_turtle 和 /turtlesim
```

## 对应你仓库里的官方示例
```bash
ros2 run examples_rclpy_minimal_publisher publisher_member_function   # 一个发布者节点
ros2 node info /minimal_publisher
```

## 小结
| 命令 | 作用 |
|------|------|
| `ros2 node list` | 列出活动节点 |
| `ros2 node info <node>` | 查看节点详情 |
| `--remap __node:=名字` | 给节点改名 |
