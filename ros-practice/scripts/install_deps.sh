#!/bin/bash
# 依赖一键安装脚本
# 用法: ./install_deps.sh

echo "===== ROS2 实战项目依赖安装 ====="

sudo apt update

echo "[1/4] 安装 ROS2 Jazzy 桌面完整版..."
sudo apt install -y ros-jazzy-desktop-full

echo "[2/4] 安装 Nav2 导航栈..."
sudo apt install -y \
    ros-jazzy-navigation2 \
    ros-jazzy-nav2-bringup \
    ros-jazzy-nav2-minimal-tb4* \
    ros-jazzy-turtlebot4-gazebo

echo "[3/4] 安装 SLAM 和地图工具..."
sudo apt install -y \
    ros-jazzy-slam-toolbox \
    ros-jazzy-nav2-map-server

echo "[4/4] 安装开发工具和视频录制..."
sudo apt install -y \
    python3-colcon-common-extensions \
    python3-rosdep \
    python3-vcstool \
    ffmpeg \
    xterm \
    gnome-terminal

echo ""
echo "===== 安装完成 ====="
echo "请确保已执行:"
echo "  source /opt/ros/jazzy/setup.bash"
echo "  sudo rosdep init && rosdep update"
