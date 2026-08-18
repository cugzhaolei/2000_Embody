# 第 20 课 · 在类中使用参数 (Python) — Using Parameters in a Class (Python)

> 对应鱼香ROS官方教程：[在类中使用参数(Python)](http://dev.ros2.fishros.com/doc/Tutorials/Using-Parameters-In-A-Class-Python.html)

## 目标
写一个带参数 `my_parameter` 的 Python 节点，掌握声明/读取/设置参数。

## 代码位置
```
dev_ws/src/py_parameters/
├── py_parameters/parameters_python.py
├── setup.py
└── package.xml
```

## 操作

```bash
source /opt/ros/foxy/setup.bash
cd ~/dev_ws
colcon build --packages-select py_parameters
source install/setup.bash

# 终端 1
ros2 run py_parameters minimal_param_node       # 每 2 秒打印 Hello world

# 终端 2
ros2 param get /minimal_param_node my_parameter
ros2 param set /minimal_param_node my_parameter earth
```

### 用参数文件启动
```bash
ros2 run py_parameters minimal_param_node --ros-args --params-file params.yaml
```

## 核心 API
```python
self.declare_parameter('my_parameter', 'world')                 # 声明
self.get_parameter('my_parameter').get_parameter_value().string_value   # 读取
self.set_parameters([rclpy.parameter.Parameter('my_parameter', rclpy.Parameter.Type.STRING, 'world')])
```

## 动手练习
改 `parameters_python.py` 增加一个整型参数 `count`，每 2 秒打印并累加。
