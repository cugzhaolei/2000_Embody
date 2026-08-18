#!/bin/bash
# 检查 ROS2 Foxy 环境是否就绪（在 WSL 终端中运行）
set -e

echo "===== 环境检查 ====="

# 1. 检查 ROS_DISTRO
if [ -z "$ROS_DISTRO" ]; then
  echo "[x] 未检测到 ROS 环境，请先执行: source /opt/ros/foxy/setup.bash"
  exit 1
fi
echo "[ok] ROS_DISTRO = $ROS_DISTRO (需要 foxy)"

if [ "$ROS_DISTRO" != "foxy" ]; then
  echo "[x] 当前 distro 是 $ROS_DISTRO，本教程针对 foxy 定制"
fi

# 2. 检查关键命令
for cmd in ros2 colcon rosbag2 rqt; do
  if command -v $cmd >/dev/null 2>&1; then
    echo "[ok] $cmd: $(command -v $cmd)"
  else
    echo "[--] $cmd: 未找到（部分课程需要）"
  fi
done

# 3. 检查关键包是否可用
for pkg in turtlesim rqt_graph rqt_console; do
  if ros2 pkg prefix $pkg >/dev/null 2>&1; then
    echo "[ok] 包 $pkg 已安装"
  else
    echo "[--] 包 $pkg 未安装 (sudo apt install ros-foxy-$pkg)"
  fi
done

# 4. 检查工作区
if [ -d ~/dev_ws/install ]; then
  echo "[ok] 工作区 ~/dev_ws 已编译"
else
  echo "[--] 工作区 ~/dev_ws 尚未编译（见 README.md 第 2 步）"
fi

echo ""
echo "===== 检查完成 ====="
