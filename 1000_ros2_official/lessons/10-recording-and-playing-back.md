# 第 10 课 · 记录和回放数据 (Recording and Playing Back Data)

> 对应鱼香ROS官方教程：[记录和回放数据](http://dev.ros2.fishros.com/doc/Tutorials/Ros2bag/Recording-And-Playing-Back-Data.html)

## 目标
用 `ros2 bag` 记录话题数据到磁盘，之后再回放。

## 操作

```bash
source /opt/ros/foxy/setup.bash

# 终端 1：启动乌龟
ros2 run turtlesim turtlesim_node
# 终端 2：启动键盘控制
ros2 run turtlesim turtle_teleop_key

# 终端 3：开始录制（所有话题）
ros2 bag record /turtle1/cmd_vel
# 或用 -a 录制所有话题
ros2 bag record -a

# 用键盘控制乌龟画几圈，然后 Ctrl+C 停止录制
# 当前目录会生成如 rosbag2_2025_01_01-00_00_00 文件夹

# 查看 bag 信息
ros2 bag info rosbag2_2025_01_01-00_00_00

# 回放（需要先重启一个干净的 turtlesim）
ros2 bag play rosbag2_2025_01_01-00_00_00
```

## 只记录指定话题
```bash
ros2 bag record /turtle1/cmd_vel /turtle1/pose
```

## 说明
Foxy 的 bag 存储格式为 **SQLite3**（`rosbag2_*` 文件夹）。回放时按录制的时间节奏发送话题。
