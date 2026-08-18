# 第 19 课 · 在类中使用参数 (C++) — Using Parameters in a Class (C++)

> 对应鱼香ROS官方教程：[在类(C++)中使用参数](http://dev.ros2.fishros.com/doc/Tutorials/Using-Parameters-In-A-Class-CPP.html)

## 目标
写一个带参数 `my_parameter` 的 C++ 节点，支持命令行/运行时/文件三种改参方式。

## 代码位置
```
dev_ws/src/cpp_parameters/
├── src/cpp_parameters_node.cpp   # 声明参数 my_parameter，定时打印 Hello xxx
├── CMakeLists.txt
└── package.xml
```

## 操作

```bash
source /opt/ros/foxy/setup.bash
cd ~/dev_ws
colcon build --packages-select cpp_parameters
source install/setup.bash

# 终端 1：启动节点（默认参数 world）
ros2 run cpp_parameters cpp_parameters_node

# 终端 2：查看/修改
ros2 param get /cpp_parameters_node my_parameter
ros2 param set /cpp_parameters_node my_parameter earth    # 终端1 立刻变成 Hello earth!
```

### 用 YAML 文件启动
```yaml
# turtlesim 风格的参数文件，保存为 params.yaml
cpp_parameters_node:
  ros__parameters:
    my_parameter: "world"
```
```bash
ros2 run cpp_parameters cpp_parameters_node --ros-args --params-file params.yaml
```

## 核心 API
```cpp
this->declare_parameter<std::string>("my_parameter", "world");  // 声明+默认值
this->get_parameter("my_parameter").as_string();                // 读取
```
