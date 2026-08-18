# 第 2 课 · 介绍 turtlesim 和 rqt (Introducing turtlesim & rqt)

> 对应鱼香ROS官方教程：[介绍turtlesim和rqt](http://dev.ros2.fishros.com/doc/Tutorials/Turtlesim/Introducing-Turtlesim.html)

## 目标
用 `turtlesim` 小乌龟仿真 + `rqt` 图形界面，直观认识 ROS 2 图。

## 准备
`turtlesim` 和 `rqt` 随 `ros-foxy-desktop` 一起安装。WSL2 需要 WSLg（Win10 21H2+ / Win11）才能显示 GUI。

## 操作

```bash
source /opt/ros/foxy/setup.bash

# 终端 1：启动小乌龟
ros2 run turtlesim turtlesim_node

# 终端 2：启动键盘控制
ros2 run turtlesim turtle_teleop_key

# 终端 3：启动 rqt
rqt
```

在 rqt 菜单 **Plugins → Visualization → Plot**，选择 `/turtle1/pose` 下的 x/y，用方向键遥控乌龟，即可看到曲线实时变化。

## 附加功能
`turtlesim` 包还自带几个演示节点：

```bash
ros2 run turtlesim draw_square    # 乌龟走正方形
ros2 run turtlesim mimic          # 模仿另一只乌龟
```

## 说明
GUI 需要 WSLg。若黑屏：`wsl --update` 或安装 `sudo apt install -y x11-apps` 后使用 `export DISPLAY=:0`。
