# 第 5 课 · 了解 ROS 2 服务 (Understanding ROS 2 Services)

> 对应鱼香ROS官方教程：[了解ROS 2服务](http://dev.ros2.fishros.com/doc/Tutorials/Services/Understanding-ROS2-Services.html)

## 目标
理解「服务」是一问一答的同步通信，学会用 `ros2 service` 系列命令。

## 操作

```bash
source /opt/ros/foxy/setup.bash

# 终端 1：启动乌龟
ros2 run turtlesim turtlesim_node

# 终端 2
ros2 service list                        # 列出所有服务
ros2 service type /clear                 # 查看某个服务类型
ros2 service list -t                    # 带类型列出
ros2 service find std_srvs/srv/Empty     # 查找某类型的所有服务
ros2 service show std_srvs/srv/Empty     # 查看接口定义

# 调用服务（清空画布）
ros2 service call /clear std_srvs/srv/Empty

# 调用 spawn 服务（生成新乌龟），需要传参
ros2 service call /spawn turtlesim/srv/Spawn "{x: 2, y: 2, theta: 0.2, name: 'turtle2'}"
```

## 对应官方示例（构建后运行）
```bash
# 终端 1（服务端）
ros2 run examples_rclpy_minimal_service service
# 终端 2（客户端）
ros2 run examples_rclpy_minimal_client client
```

代码位置：`dev_ws/src/examples/rclpy/services/minimal_service/` 与 `minimal_client/`

## 小结
| 命令 | 作用 |
|------|------|
| `ros2 service list [-t]` | 列服务 |
| `ros2 service type /show` | 查看服务类型/接口 |
| `ros2 service call <srv> <type> <args>` | 调用服务 |
