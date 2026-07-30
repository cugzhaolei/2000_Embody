#!/bin/bash
# 视频录制脚本：录制 Gazebo + RViz 仿真过程
# 用法: ./record_video.sh [时长秒数] [输出文件名]

DURATION=${1:-60}
OUTPUT=${2:-ros_sim_$(date +%Y%m%d_%H%M%S)}
OUTPUT_DIR=~/ros_practice_videos

mkdir -p "$OUTPUT_DIR"

echo "========================================"
echo "  ROS2 仿真视频录制"
echo "  时长: ${DURATION}秒"
echo "  输出: ${OUTPUT_DIR}/${OUTPUT}.mp4"
echo "========================================"

# 检查 ffmpeg
if ! command -v ffmpeg &> /dev/null; then
    echo "错误: 未安装 ffmpeg，正在安装..."
    sudo apt update && sudo apt install -y ffmpeg
fi

# 获取屏幕分辨率
if command -v xdpyinfo &> /dev/null; then
    RESOLUTION=$(xdpyinfo | grep dimensions | awk '{print $2}')
else
    RESOLUTION="1920x1080"
fi
echo "屏幕分辨率: $RESOLUTION"

# 检查 DISPLAY
if [ -z "$DISPLAY" ]; then
    export DISPLAY=:0
fi

echo "[$(date +%H:%M:%S)] 开始录制..."
echo "请在 ${DURATION} 秒内操作仿真"

ffmpeg -y \
    -f x11grab \
    -framerate 30 \
    -video_size "$RESOLUTION" \
    -i "$DISPLAY" \
    -c:v libx264 \
    -preset fast \
    -crf 23 \
    -t "$DURATION" \
    "${OUTPUT_DIR}/${OUTPUT}.mp4" 2>&1 | tail -5

echo ""
echo "[$(date +%H:%M:%S)] 录制完成！"
echo "文件: ${OUTPUT_DIR}/${OUTPUT}.mp4"

if [ -f "${OUTPUT_DIR}/${OUTPUT}.mp4" ]; then
    FILESIZE=$(du -h "${OUTPUT_DIR}/${OUTPUT}.mp4" | awk '{print $1}')
    echo "大小: $FILESIZE"

    # 生成缩略图
    ffmpeg -y -i "${OUTPUT_DIR}/${OUTPUT}.mp4" \
        -ss 00:00:05 -frames:v 1 \
        "${OUTPUT_DIR}/${OUTPUT}_thumb.png" 2>/dev/null
    echo "缩略图: ${OUTPUT_DIR}/${OUTPUT}_thumb.png"

    # 复制到 web 目录
    WEB_DIR="$(dirname "$(dirname "$0")")/web/assets/videos"
    if [ -d "$WEB_DIR" ]; then
        cp "${OUTPUT_DIR}/${OUTPUT}.mp4" "$WEB_DIR/"
        cp "${OUTPUT_DIR}/${OUTPUT}_thumb.png" "$WEB_DIR/" 2>/dev/null
        echo "已复制到 web 目录: $WEB_DIR"
    fi
else
    echo "错误: 录制文件未生成"
    exit 1
fi
