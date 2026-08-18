# 第 15 课 · 编写简单的服务和客户端 (C++) — Writing a Simple Service/Client (C++)

> 对应鱼香ROS官方教程：[编写简单的服务和客户端 (C++)](http://dev.ros2.fishros.com/doc/Tutorials/Writing-A-Simple-Cpp-Service-And-Client.html)

## 目标
看懂 C++ 服务端/客户端，构建并运行 `examples_rclcpp_minimal_service/client`。

## 代码位置
```
dev_ws/src/examples/rclcpp/services/minimal_service/
dev_ws/src/examples/rclcpp/services/minimal_client/
```

## 操作

```bash
source /opt/ros/foxy/setup.bash
cd ~/dev_ws
colcon build --packages-select examples_rclcpp_minimal_service examples_rclcpp_minimal_client
source install/setup.bash

# 终端 1：服务端（监听 add_two_ints，返回 a+b）
ros2 run examples_rclcpp_minimal_service service

# 终端 2：客户端（请求 a=4, b=2）
ros2 run examples_rclcpp_minimal_client client

# 终端 3 查看
ros2 service list
ros2 service type /add_two_ints
```

## 核心代码讲解

**服务端** `service_main.cpp`：
```cpp
this->create_service<std_srvs::srv::AddTwoInts>("add_two_ints", 回调);
// 回调里计算 response.sum = request.a + request.b
```

**客户端** `client_main.cpp`：
```cpp
create_client<std_srvs::srv::AddTwoInts>("add_two_ints");
client->wait_for_service();          // 等服务端上线
client->async_send_request(request); // 异步发请求
```

## 说明
- 服务端可同时启动多个客户端；服务端也可用 `add_one` 等不同服务名。
- 客户端在收到响应前会一直等待（`wait_for_service`）。
