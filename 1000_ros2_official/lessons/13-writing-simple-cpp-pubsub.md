# 第 13 课 · 编写简单的发布者和订阅者 (C++) — Writing a Simple Publisher/Subscriber (C++)

> 对应鱼香ROS官方教程：[编写简单的发布者和订阅者 (C++)](http://dev.ros2.fishros.com/doc/Tutorials/Writing-A-Simple-Cpp-Publisher-And-Subscriber.html)

## 目标
看懂 C++ 发布者/订阅者，构建并运行 `examples_rclcpp_minimal_publisher/subscriber`。

## 代码位置
```
dev_ws/src/examples/rclcpp/topics/minimal_publisher/   (talker)
dev_ws/src/examples/rclcpp/topics/minimal_subscriber/  (listener)
```

## 操作

```bash
source /opt/ros/foxy/setup.bash
cd ~/dev_ws
colcon build --packages-select examples_rclcpp_minimal_publisher examples_rclcpp_minimal_subscriber
source install/setup.bash

# 终端 1：发布者（timer 每 500ms 发布 "Hello World: N"）
ros2 run examples_rclcpp_minimal_publisher publisher_member_function

# 终端 2：订阅者
ros2 run examples_rclcpp_minimal_subscriber subscriber_member_function

# 终端 3：查看话题
ros2 topic echo /topic
```

## 核心代码讲解

**发布者** `member_function.cpp` 关键点：
```cpp
this->publisher_ = this->create_publisher<std_msgs::msg::String>("topic", 10);  // 建发布者
this->timer_ = this->create_wall_timer(500ms, ...);                             // 定时回调
this->publisher_->publish(msg);                                                 // 发布
```

**订阅者** `member_function.cpp` 关键点：
```cpp
this->create_subscription<std_msgs::msg::String>("topic", 10, callback);  // 订阅并绑定回调
```

## 动手练习
- 把发布频率 500ms 改成 100ms，重新编译，用 `ros2 topic hz /topic` 看频率变化。
- 把话题名 `topic` 改成 `chatter`（发布者、订阅者都要改），用 `ros2 topic echo /chatter` 验证。
