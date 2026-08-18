# 第 17 课 · 创建自定义 ROS 2 msg 和 srv 文件 (Creating Custom msg/srv Files)

> 对应鱼香ROS官方教程：[创建自定义ROS 2 msg 和 srv 文件](http://dev.ros2.fishros.com/doc/Tutorials/Custom-ROS2-Interfaces.html)

## 目标
创建自己的消息(msg)与服务(srv)接口包 `tutorial_interfaces`，学会 `ros2 interface` 命令。

## 代码位置
```
dev_ws/src/tutorial_interfaces/
├── msg/Num.msg              int64 num
├── srv/AddThreeInts.srv     a/b/c → sum
├── CMakeLists.txt
└── package.xml
```

## 操作

```bash
source /opt/ros/foxy/setup.bash
cd ~/dev_ws
colcon build --packages-select tutorial_interfaces
source install/setup.bash

# 查看接口
ros2 interface show tutorial_interfaces/msg/Num
ros2 interface show tutorial_interfaces/srv/AddThreeInts

# 列出包含该前缀的所有接口
ros2 interface list | grep tutorial_interfaces
```

## 接口语法速查
**msg**（数据，一行一个字段）：
```
int64 num
```

**srv**（请求 `---` 响应）：
```
int64 a
int64 b
int64 c
---
int64 sum
```

## 如何在代码中使用
在 package.xml 里加 `<depend>tutorial_interfaces</depend>`，然后：

- Python：`from tutorial_interfaces.srv import AddThreeInts` / `from tutorial_interfaces.msg import Num`
- C++：`#include "tutorial_interfaces/srv/add_three_ints.hpp"`

> 第 18 课继续讲「在单一包里定义并使用接口」。
