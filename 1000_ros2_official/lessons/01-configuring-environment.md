# 第 1 课 · 配置 ROS 2 环境 (Configuring Environment)

> 对应鱼香ROS官方教程：[配置ROS 2环境](http://dev.ros2.fishros.com/doc/Tutorials/Configuring-ROS2-Environment.html)

## 目标
学会每次打开终端后正确加载 ROS 2 Foxy 环境，并会用 `echo` / `env` 检查。

## 操作（在 WSL 终端）

```bash
# 1. 手动加载环境（安装脚本已自动写入 ~/.bashrc，新终端会自动加载）
source /opt/ros/foxy/setup.bash

# 2. 验证
ros2 --version
echo "ROS_DISTRO=$ROS_DISTRO"
echo "ROS_VERSION=$ROS_VERSION"
```

## 说明
- 你的 WSL 是 **Ubuntu 20.04**，对应 ROS 2 **Foxy**，安装路径为 `/opt/ros/foxy/`。
- 所有课程命令都假设先 `source /opt/ros/foxy/setup.bash`。

## 常见问题
- `command not found: ros2` → 说明没 source 或没安装，运行 `bash scripts/setup_foxy_wsl.sh`。
