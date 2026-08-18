#!/bin/bash
# 每节课运行前的清理脚本：
#   1) 杀掉遗留的 ROS 进程（turtlesim/rqt/rviz/gazebo/ros2 节点等）
#   2) 重启 ros2 后台守护进程（避免旧通信缓存干扰）
#   3) 释放 Linux 页面缓存，给本课腾出干净内存
# 用法: bash /mnt/c/Users/admin/Desktop/dev/2000_Embody/1000_ros2_official/scripts/cleanup.sh

echo "===== 清理前内存 ====="
free -h

echo "[1/3] 停止所有遗留的 ROS 相关进程..."
pkill -f "turtlesim" 2>/dev/null || true
pkill -f "turtle_teleop_key" 2>/dev/null || true
pkill -f "rqt" 2>/dev/null || true
pkill -f "rviz2" 2>/dev/null || true
pkill -f "gazebo" 2>/dev/null || true
pkill -f "rosbag2" 2>/dev/null || true
pkill -f "component_container" 2>/dev/null || true
sleep 1

echo "[2/3] 重置 ros2 后台守护进程..."
ros2 daemon stop 2>/dev/null || true
ros2 daemon start 2>/dev/null || true

echo "[3/3] 释放页面缓存（不影响正在运行的程序）..."
sync 2>/dev/null || true
sudo -n tee /proc/sys/vm/drop_caches >/dev/null 2>&1 <<< "3" || \
  echo "(跳过缓存释放：需管理员权限，且对本次实验无影响)"

echo ""
echo "===== 清理后内存 ====="
free -h
echo ""
echo "清理完成，可以开始本课实验了。"
