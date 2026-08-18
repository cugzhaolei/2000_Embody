# 第 8 课 · 使用 rqt_console 查看日志 (Using rqt_console)

> 对应鱼香ROS官方教程：[使用rqt_控制台](http://dev.ros2.fishros.com/doc/Tutorials/Rqt-Console/Using-Rqt-Console.html)

## 目标
用 `rqt_console` 查看节点日志，用 `rqt_logger_level` 调整日志级别。

## 操作

```bash
source /opt/ros/foxy/setup.bash

# 终端 1：启动 rqt_console（GUI）
rqt_console

# 终端 2：启动乌龟
ros2 run turtlesim turtlesim_node

# 终端 3：强制生成错误日志（把乌龟移到墙外）
ros2 topic pub -1 /turtle1/cmd_vel geometry_msgs/msg/Twist "{linear: {x: 2.0, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.0}}"

# rqt_console 窗口里会立刻出现红色 ERROR 日志 "Invalid velocity" 等
```

### 调整日志级别
```bash
rqt_logger_level
```
在窗口中选择 `/turtlesim`，把级别从 Info 调到 Warn，可以过滤低级别日志。

## 说明
日志级别：DEBUG < INFO < WARN < ERROR < FATAL。命令行也可用 `--ros-args --log-level WARN` 设置。
