#!/bin/bash
# 地图保存脚本
# 用法: ./save_map.sh [地图名称]

MAP_NAME=${1:-warehouse}
MAP_DIR=${HOME}/maps

mkdir -p "$MAP_DIR"

echo "===== 保存地图 ====="
echo "地图名称: $MAP_NAME"
echo "保存目录: $MAP_DIR"

source /opt/ros/jazzy/setup.bash 2>/dev/null
source ~/ros2_ws/install/setup.bash 2>/dev/null

ros2 run nav2_map_server map_saver_cli -f "${MAP_DIR}/${MAP_NAME}"

if [ -f "${MAP_DIR}/${MAP_NAME}.pgm" ]; then
    echo ""
    echo "===== 保存成功 ====="
    echo "PGM 文件: ${MAP_DIR}/${MAP_NAME}.pgm"
    echo "YAML 文件: ${MAP_DIR}/${MAP_NAME}.yaml"
    echo ""
    echo "--- 地图元数据 ---"
    cat "${MAP_DIR}/${MAP_NAME}.yaml"
    echo ""
    echo "--- 使用方法 ---"
    echo "ros2 launch myfirst_robot nav2_bringup.launch.py map:=${MAP_DIR}/${MAP_NAME}.yaml"
else
    echo "错误: 地图保存失败"
    exit 1
fi
