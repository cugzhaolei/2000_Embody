# 第 24 课 · 编写动作服务器和客户端 (C++) — Writing an Action Server/Client (C++)

> 对应鱼香ROS官方教程：[编写动作服务器和客户端 (C++)](http://dev.ros2.fishros.com/doc/Tutorials/Actions/Writing-a-Cpp-Action-Server-Client.html)

## 目标
用 rclcpp_action 实现 Fibonacci 动作服务器与客户端。

## 代码位置
```
dev_ws/src/action_tutorials_cpp/
├── src/fibonacci_action_server.cpp
├── src/fibonacci_action_client.cpp
├── include/action_tutorials_cpp/visibility_control.h
└── CMakeLists.txt
```

## 操作

```bash
source /opt/ros/foxy/setup.bash
cd ~/dev_ws
colcon build --packages-select action_tutorials_interfaces action_tutorials_cpp
source install/setup.bash

# 终端 1：动作服务器
ros2 run action_tutorials_cpp action_server_executable

# 终端 2：动作客户端（order=10）
ros2 run action_tutorials_cpp action_client_executable

# 终端 3 也可用命令行发目标：
ros2 action send_goal fibonacci action_tutorials_interfaces/action/Fibonacci "{order: 5}" --feedback
```

## 服务器要点
```cpp
rclcpp_action::create_server<Fibonacci>(this, "fibonacci", 处理goal, 处理cancel, 处理accepted);
// 处理accepted 里起新线程执行，循环发布 feedback，最后 goal_handle->succeed(result);
```

## 客户端要点
```cpp
rclcpp_action::create_client<Fibonacci>(this, "fibonacci");
client->async_send_goal(goal_msg, send_goal_options);  // 带 goal_response/feedback/result 三个回调
```

## 观察
客户端窗口会不断打印 `Next number in sequence received: ...`，最后 `Result received: ...`。
