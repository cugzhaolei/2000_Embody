# 第 25 课 · 编写动作服务器和客户端 (Python) — Writing an Action Server/Client (Python)

> 对应鱼香ROS官方教程：[编写动作服务器和客户端 (Python)](http://dev.ros2.fishros.com/doc/Tutorials/Actions/Writing-a-Py-Action-Server-Client.html)

## 目标
用 rclpy.action 实现 Fibonacci 动作服务器与客户端。

## 代码位置
```
dev_ws/src/action_tutorials_py/
└── action_tutorials_py/
    ├── fibonacci_action_server.py
    └── fibonacci_action_client.py
```

## 操作

```bash
source /opt/ros/foxy/setup.bash
cd ~/dev_ws
colcon build --packages-select action_tutorials_interfaces action_tutorials_py
source install/setup.bash

# 终端 1：动作服务器
ros2 run action_tutorials_py fibonacci_action_server

# 终端 2：动作客户端（send_goal(10)）
ros2 run action_tutorials_py fibonacci_action_client
```

## 服务器要点
```python
self._action_server = ActionServer(self, Fibonacci, 'fibonacci', self.execute_callback)

def execute_callback(self, goal_handle):
    # 循环里 goal_handle.publish_feedback(feedback_msg)
    # 结束 goal_handle.succeed() 并 return result
```

## 客户端要点
```python
self._action_client = ActionClient(self, Fibonacci, 'fibonacci')
self._action_client.wait_for_server()
self._send_goal_future = self._action_client.send_goal_async(goal_msg)
# future.add_done_callback(goal_response_callback) → 再 get_result_async()
```

## 观察
客户端先打印 `Goal accepted :)`，随后服务器逐条发布反馈，最后打印 `Result: [0, 1, 1, 2, ...]`。
