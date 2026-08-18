# 第 28 课 · Launch 教程 (ROS 2 Launch)

> 对应鱼香ROS官方教程：[Launch教程](http://dev.ros2.fishros.com/doc/Tutorials/Launch/Launch-Main.html)

## 目标
用 Python 编写 launch 文件，一次性启动/配置/编组多个节点。

## 代码位置
```
dev_ws/src/launch_tutorial/launch/turtlesim_mimic_launch.py
```
```python
from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    return LaunchDescription([
        Node(package='turtlesim', namespace='turtlesim1', executable='turtlesim_node', name='sim'),
        Node(package='turtlesim', namespace='turtlesim2', executable='turtlesim_node', name='sim'),
        Node(package='turtlesim', executable='mimic', name='mimic',
             remappings=[('/input/pose', '/turtlesim1/turtle1/pose'),
                         ('/output/cmd_vel', '/turtlesim2/turtle1/cmd_vel')]),
    ])
```

## 操作

```bash
source /opt/ros/foxy/setup.bash
cd ~/dev_ws
colcon build --packages-select launch_tutorial
source install/setup.bash

ros2 launch launch_tutorial turtlesim_mimic_launch.py
# 另开终端用键盘控制 turtlesim1，观察 turtlesim2 跟随
ros2 run turtlesim turtle_teleop_key --ros-args --remap turtle1/cmd_vel:=turtlesim1/turtle1/cmd_vel
```

## launch 核心概念
| 组件 | 作用 |
|------|------|
| `Node` | 启动一个节点，可设 namespace / name / remapping / parameters |
| `DeclareLaunchArgument` | 声明命令行参数（如 `model:=...`） |
| `LaunchConfiguration` | 读取参数值 |
| `IncludeLaunchDescription` | 嵌套其它 launch 文件 |
| `GroupAction` | 编组 + 统一加 namespace |
| `RegisterEventHandler` | 事件处理（如节点退出时做清理） |
| `ExecuteProcess` | 启动任意可执行程序 |

## 动手练习
1. 把 mimic 的 remapping 换一个话题方向。
2. 加一个 `DeclareLaunchArgument` 让 namespace 可通过命令行传入。
