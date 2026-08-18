# 第 4 课 · 理解 ROS 2 话题 (Understanding ROS 2 Topics)

> 对应鱼香ROS官方教程：[理解ROS 2话题](http://dev.ros2.fishros.com/doc/Tutorials/Topics/Understanding-ROS2-Topics.html)

## 目标
理解「话题」是节点间异步通信的通道，学会用 `ros2 topic` 系列命令。

## 操作

```bash
source /opt/ros/foxy/setup.bash

# 终端 1：启动乌龟
ros2 run turtlesim turtlesim_node

# 终端 2
ros2 topic list                          # 列出所有话题
ros2 topic list -t                      # 带类型列出
ros2 topic echo /turtle1/pose            # 实时打印话题内容

# 终端 3：键盘控制（让乌龟动起来，echo 窗口才有输出）
ros2 run turtlesim turtle_teleop_key

# 终端 2 继续
ros2 topic info /turtle1/cmd_vel         # 查看话题类型与订阅者/发布者数量
ros2 topic hz /turtle1/pose              # 查看发布频率
ros2 topic bw /turtle1/pose              # 查看带宽
```

### 发布者/订阅者关系
`/turtle1/cmd_vel`：teleop_key 发布，turtlesim 订阅
`/turtle1/pose`：turtlesim 发布，echo 订阅

### rqt_graph 可视化
```bash
rqt_graph
```
拖动节点即可看到话题连接关系。

## 对应官方示例（构建后运行）
```bash
# 终端 1（发布者）
ros2 run examples_rclpy_minimal_publisher publisher_member_function
# 终端 2（订阅者）
ros2 run examples_rclpy_minimal_subscriber subscriber_member_function
# 终端 3
ros2 topic echo /topic
```

代码位置：`dev_ws/src/examples/rclpy/topics/minimal_publisher/` 与 `minimal_subscriber/`

## 小结
| 命令 | 作用 |
|------|------|
| `ros2 topic list [-t]` | 列话题（含类型） |
| `ros2 topic echo <topic>` | 打印话题 |
| `ros2 topic info <topic>` | 查看详情 |
| `ros2 topic hz / bw <topic>` | 查看频率 / 带宽 |
