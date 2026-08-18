# 第 23 课 · 创建动作 (Creating an Action)

> 对应鱼香ROS官方教程：[创建动作](http://dev.ros2.fishros.com/doc/Tutorials/Actions/Creating-an-Action.html)

## 目标
定义自定义 action 接口 `Fibonacci.action`，学会 `ros2 interface` / `ros2 action` 查看。

## 代码位置
```
dev_ws/src/action_tutorials_interfaces/
└── action/Fibonacci.action
```
```text
int32 order                       # 目标：求第 order 项斐波那契
---
int32[] sequence                  # 结果：完整序列
---
int32[] partial_sequence          # 反馈：到目前的部分序列
```

## 操作

```bash
source /opt/ros/foxy/setup.bash
cd ~/dev_ws
colcon build --packages-select action_tutorials_interfaces
source install/setup.bash

# 查看 action 定义
ros2 interface show action_tutorials_interfaces/action/Fibonacci

# 列出（需要先有动作服务器在跑，见第 24/25 课）
ros2 action list
```

## action 文件语法
```text
目标字段
---
结果字段
---
反馈字段
```

## 下一步
第 24 课（C++）/ 第 25 课（Python）实现动作服务器与客户端。
