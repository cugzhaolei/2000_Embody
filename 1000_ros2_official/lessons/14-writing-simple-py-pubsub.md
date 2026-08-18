# 第 14 课 · 编写简单的发布者和订阅者 (Python) — Writing a Simple Publisher/Subscriber (Python)

> 对应鱼香ROS官方教程：[编写简单的发布者和订阅者 (Python)](http://dev.ros2.fishros.com/doc/Tutorials/Writing-A-Simple-Py-Publisher-And-Subscriber.html)

## 目标
看懂 Python 发布者/订阅者，构建并运行 `examples_rclpy_minimal_publisher/subscriber`。

## 代码位置
```
dev_ws/src/examples/rclpy/topics/minimal_publisher/   (publisher_member_function.py)
dev_ws/src/examples/rclpy/topics/minimal_subscriber/  (subscriber_member_function.py)
```

## 操作

```bash
source /opt/ros/foxy/setup.bash
cd ~/dev_ws
colcon build --packages-select examples_rclpy_minimal_publisher examples_rclpy_minimal_subscriber
source install/setup.bash

# 终端 1：发布者
ros2 run examples_rclpy_minimal_publisher publisher_member_function

# 终端 2：订阅者
ros2 run examples_rclpy_minimal_subscriber subscriber_member_function

# 终端 3
ros2 topic echo /topic
ros2 topic info /topic -v     # 看完整的发布/订阅 QoS
```

## 核心代码讲解

**发布者** `publisher_member_function.py`：
```python
self.publisher_ = self.create_publisher(String, 'topic', 10)   # 建发布者
self.timer = self.create_timer(0.5, self.timer_callback)       # 定时 0.5s
self.publisher_.publish(msg)                                   # 发布
```

**订阅者** `subscriber_member_function.py`：
```python
self.subscription = self.create_subscription(String, 'topic', self.listener_callback, 10)
```

## 两种编程风格对比
| 文件 | 风格 |
|------|------|
| `publisher_member_function.py` | 类 + 成员方法（教程主推） |
| `publisher_local_function.py` | 局部函数 + 计时器 |
| `publisher_old_school.py` | 最简写法 |

## 动手练习
改 `publisher_member_function.py`：把 `Hello World: %d` 改成你自己的文字 → 重新 `colcon build` → 运行。
