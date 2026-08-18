# 第 7 课 · 理解 ROS 2 动作 (Understanding ROS 2 Actions)

> 对应鱼香ROS官方教程：[理解ROS 2动作](http://dev.ros2.fishros.com/doc/Tutorials/Understanding-ROS2-Actions.html)

## 目标
理解「动作」= 目标(goal) + 反馈(feedback) + 结果(result)，适合长时间任务。学会用 `ros2 action` 命令。

## 操作

```bash
source /opt/ros/foxy/setup.bash

# 终端 1：启动乌龟
ros2 run turtlesim turtlesim_node

# 终端 2：启动动作客户端（绕正方形旋转）
ros2 run turtlesim turtle_teleop_key   # 保持开一窗
ros2 action list                       # 列出动作：/turtle1/rotate_absolute
ros2 action list -t                    # 带类型
ros2 action info /turtle1/rotate_absolute   # 查看详情
ros2 action show turtlesim/action/RotateAbsolute   # 查看接口定义
```

### 通过动作让乌龟转向
```bash
# 向 /turtle1/rotate_absolute 发送一个 theta=1.57(90°) 的目标
ros2 action send_goal /turtle1/rotate_absolute turtlesim/action/RotateAbsolute "{theta: 1.57}" --feedback
```

## 说明
动作在底层由 2 个话题 + 1 个服务组成（goal、result、cancel）。后面第 23-25 课会自己实现动作服务器/客户端。

## 小结
| 命令 | 作用 |
|------|------|
| `ros2 action list [-t]` | 列动作 |
| `ros2 action info <action>` | 查看详情 |
| `ros2 action send_goal <action> <type> <args> --feedback` | 发送目标并看反馈 |
