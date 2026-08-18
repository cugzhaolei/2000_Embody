# 第 16 课 · 编写简单的服务和客户端 (Python) — Writing a Simple Service/Client (Python)

> 对应鱼香ROS官方教程：[编写简单的服务和客户端 (Python)](http://dev.ros2.fishros.com/doc/Tutorials/Writing-A-Simple-Py-Service-And-Client.html)

## 目标
看懂 Python 服务端/客户端，构建并运行 `examples_rclpy_minimal_service/client`。

## 代码位置
```
dev_ws/src/examples/rclpy/services/minimal_service/
dev_ws/src/examples/rclpy/services/minimal_client/
```

## 操作

```bash
source /opt/ros/foxy/setup.bash
cd ~/dev_ws
colcon build --packages-select examples_rclpy_minimal_service examples_rclpy_minimal_client
source install/setup.bash

# 终端 1：服务端
ros2 run examples_rclpy_minimal_service service

# 终端 2：客户端（发 a=4, b=2 请求）
ros2 run examples_rclpy_minimal_client client
```

## 核心代码讲解

**服务端** `service.py`：
```python
self.srv = self.create_service(AddTwoInts, 'add_two_ints', self.add_two_ints_callback)

def add_two_ints_callback(self, request, response):
    response.sum = request.a + request.b
    return response
```

**客户端** `client.py`：
```python
self.cli = self.create_client(AddTwoInts, 'add_two_ints')
while not self.cli.wait_for_service(timeout_sec=1.0):   # 等服务端
    ...
req = AddTwoInts.Request(); req.a = 4; req.b = 2
self.future = self.cli.call_async(req)                  # 异步调用
```

## 说明
- Python 客户端用 `call_async()` 返回 `Future`，用 `add_done_callback` 取结果。
- 对应 C++ 教程在第 15 课。

## 动手练习
改服务端把 `a + b` 改成 `a * b`，重新编译运行，观察客户端结果变化。
