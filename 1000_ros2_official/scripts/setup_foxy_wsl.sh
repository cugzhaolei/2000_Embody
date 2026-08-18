#!/bin/bash
# ROS 2 Foxy 一键安装脚本（Ubuntu 20.04 WSL2）
# 用法: wsl -d Ubuntu-20.04 -- bash setup_foxy_wsl.sh
set -e

echo "===== ROS2 Foxy 环境搭建 (Ubuntu 20.04 / focal) ====="

# 1. 更新系统
echo "[1/6] 更新系统..."
sudo apt update && sudo apt upgrade -y

# 2. 添加 ROS2 软件源
echo "[2/6] 添加 ROS2 软件源..."
sudo apt install -y software-properties-common curl gnupg lsb-release
sudo curl -sSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.key \
  -o /usr/share/keyrings/ros-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] \
  http://packages.ros.org/ros2/ubuntu $(. /etc/os-release && echo $UBUNTU_CODENAME) main" \
  | sudo tee /etc/apt/sources.list.d/ros2.list > /dev/null
sudo apt update

# 3. 安装 ROS2 Foxy 桌面完整版（含 turtlesim、rqt、rosbag、colcon 等）
echo "[3/6] 安装 ROS2 Foxy..."
sudo apt install -y ros-foxy-desktop

# 4. 安装教程需要的额外包
echo "[4/6] 安装教程依赖包..."
sudo apt install -y \
  ros-foxy-turtlesim \
  ros-foxy-rqt-* \
  ros-foxy-ros2bag \
  ros-foxy-rosbag2-storage-default-plugins \
  ros-foxy-urdf-tutorial \
  ros-foxy-xacro \
  ros-foxy-tf-transformations \
  ros-foxy-robot-state-publisher \
  ros-foxy-joint-state-publisher \
  ros-foxy-gazebo-ros \
  ros-foxy-gazebo-ros-pkgs \
  ros-foxy-turtle-tf2-py \
  ros-foxy-turtle-tf2-cpp \
  ros-foxy-tf2-tools \
  ros-foxy-nav2-msgs

# 5. 安装开发工具
echo "[5/6] 安装开发工具..."
sudo apt install -y \
  python3-colcon-common-extensions \
  python3-rosdep \
  python3-vcstool \
  python3-pip \
  git

sudo rosdep init 2>/dev/null || true
rosdep update 2>/dev/null || true

# 6. 配置环境
echo "[6/6] 配置环境..."
grep -q "source /opt/ros/foxy/setup.bash" ~/.bashrc || \
  echo "source /opt/ros/foxy/setup.bash" >> ~/.bashrc
source /opt/ros/foxy/setup.bash

echo ""
echo "===== 安装完成 ====="
echo "ROS2 版本: $(ros2 --version 2>/dev/null || echo '待验证')"
echo ""
echo "下一步（打开新终端后会自动 source，也可手动执行）:"
echo "  source /opt/ros/foxy/setup.bash"
echo ""
echo "然后把本目录的 dev_ws 复制到 WSL 家目录并编译:"
echo "  cp -r /mnt/c/Users/admin/Desktop/dev/2000_Embody/1000_ros2_official/dev_ws ~/dev_ws"
echo "  cd ~/dev_ws && colcon build --symlink-install"
echo "  echo \"source ~/dev_ws/install/setup.bash\" >> ~/.bashrc"
echo "  source install/setup.bash"
echo "  ros2 run turtlesim turtlesim_node   # 验证安装"
