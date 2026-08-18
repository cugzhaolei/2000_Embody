# 第 27 课 · 使用 colcon 构建包 (Using colcon to Build Packages)

> 对应鱼香ROS官方教程：[使用colcon构建包](http://dev.ros2.fishros.com/doc/Tutorials/Colcon-Tutorial.html)

## 目标
熟练使用 `colcon` 编译 ROS 2 包并理解输出目录。

## 操作

```bash
source /opt/ros/foxy/setup.bash
cd ~/dev_ws

# 编译全部包
colcon build

# 只编译某个包
colcon build --packages-select examples_rclpy_minimal_publisher

# 忽略某个包
colcon build --packages-ignore examples_rclcpp_minimal_publisher

# 符号链接模式（改 python 代码不用重新 build）
colcon build --symlink-install

# 调试输出
colcon build --event-handlers console_direct+ --cmake-args -DCMAKE_BUILD_TYPE=RelWithDebInfo

# 清理后重建
rm -rf build install log
colcon build
```

## 输出目录
| 目录 | 内容 |
|------|------|
| `build/` | 中间编译产物 |
| `install/` | 安装结果，`setup.bash` 在这里 |
| `log/` | 编译日志 |

## 加载环境
```bash
source install/setup.bash   # 覆盖/叠加到 ROS 环境
```

## 说明
- 编译前必须 `source /opt/ros/foxy/setup.bash`。
- 本仓库的 `dev_ws` 已包含全部教程包，`colcon build` 一次即可全部编译。
