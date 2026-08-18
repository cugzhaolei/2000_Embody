# 第 9 课 · 介绍 ROS 2 launch (CLI Intro to launch)

> 对应鱼香ROS官方教程：[介绍ROS 2launch](http://dev.ros2.fishros.com/doc/Tutorials/Launch/CLI-Intro.html)

## 目标
用 `ros2 launch` 一条命令同时启动多个节点（替代手工开多个终端）。

## 操作

```bash
source /opt/ros/foxy/setup.bash

# 场景：让一只乌龟模仿另一只乌龟的轨迹（3 个节点一起启动）
# 启动工作区里自带的 launch 文件（先编译 launch_tutorial）
cd ~/dev_ws
colcon build --packages-select launch_tutorial
source install/setup.bash

ros2 launch launch_tutorial turtlesim_mimic_launch.py
```

此时会自动启动：
1. `turtlesim1` 中的 `turtlesim_node`
2. `turtlesim2` 中的 `turtlesim_node`
3. `mimic`（把 turtlesim1 的 pose 映射为 turtlesim2 的 cmd_vel）

再开一个终端用键盘控制 turtlesim1，turtlesim2 就会跟着动。

```bash
ros2 run turtlesim turtle_teleop_key --ros-args --remap turtle1/cmd_vel:=turtlesim1/turtle1/cmd_vel
```

## launch 文件位置
`dev_ws/src/launch_tutorial/launch/turtlesim_mimic_launch.py`（Python 编写的 LaunchDescription）

## 小结
| 命令 | 作用 |
|------|------|
| `ros2 launch <包名> <launch文件>` | 启动一组节点 |
| `--show-args` | 查看 launch 参数 |
