# 第 6 课 · 理解 ROS 2 参数 (Understanding ROS 2 Parameters)

> 对应鱼香ROS官方教程：[理解ROS 2参数](http://dev.ros2.fishros.com/doc/Tutorials/Parameters/Understanding-ROS2-Parameters.html)

## 目标
理解「参数」是节点的可配置值，学会用 `ros2 param` 系列命令。

## 操作

```bash
source /opt/ros/foxy/setup.bash

# 终端 1：启动乌龟
ros2 run turtlesim turtlesim_node

# 终端 2
ros2 param list                          # 列出参数
ros2 param get /turtlesim background_r   # 获取参数值
ros2 param set /turtlesim background_r 150   # 设置参数（背景变红）
ros2 param dump /turtlesim               # 导出参数到文件 ./turtlesim.yaml
ros2 param load /turtlesim turtlesim.yaml # 从文件加载
```

## 对应官方示例（构建后运行）
```bash
# Python 参数节点（每 2 秒打印 Hello world）
ros2 run py_parameters minimal_param_node
ros2 param get /minimal_param_node my_parameter

# 运行时修改
ros2 run py_parameters minimal_param_node --ros-args -p my_parameter:=earth
```

代码位置：`dev_ws/src/py_parameters/` 与 `dev_ws/src/cpp_parameters/`

## 小结
| 命令 | 作用 |
|------|------|
| `ros2 param list / get` | 列出 / 获取参数 |
| `ros2 param set <node> <param> <val>` | 设置参数 |
| `ros2 param dump / load` | 导出 / 导入参数文件 |
