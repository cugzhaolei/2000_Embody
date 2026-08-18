# 第 12 课 · 创建您的第一个 ROS 2 包 (Creating Your First Package)

> 对应鱼香ROS官方教程：[创建您的第一个ROS 2包](http://dev.ros2.fishros.com/doc/Tutorials/Creating-Your-First-ROS2-Package.html)

## 目标
用 `ros2 pkg create` 创建 Python 和 C++ 两种包，了解包的基本文件结构。

## 操作

```bash
source /opt/ros/foxy/setup.bash
cd ~/dev_ws/src

# 创建 Python 包
ros2 pkg create --build-type ament_python my_python_pkg

# 创建 C++ 包
ros2 pkg create --build-type ament_cmake my_cpp_pkg

# 编译
cd ~/dev_ws
colcon build --packages-select my_python_pkg my_cpp_pkg
source install/setup.bash
```

## 包结构说明
**Python 包 (`my_python_pkg`)**：
```
my_python_pkg/
├── package.xml      # 包元信息 + 依赖
├── setup.py         # 打包配置 + 可执行入口(console_scripts)
├── setup.cfg        # 安装脚本目录
└── my_python_pkg/   # 真正的 Python 模块（放 .py）
    └── __init__.py
```

**C++ 包 (`my_cpp_pkg`)**：
```
my_cpp_pkg/
├── package.xml
├── CMakeLists.txt   # 编译规则
├── include/my_cpp_pkg/  # 头文件
└── src/             # 源文件
```

## 常用命令
```bash
ros2 pkg list                      # 列出已安装包
ros2 pkg prefix <包名>             # 查看包安装路径
```

## 说明
- `--dependencies <依赖1> <依赖2>` 可一次性把依赖写进 package.xml。
- 第 13-20 课的全部代码已放在 `~/dev_ws/src/examples/` 及各课程包中，无需手工创建。
