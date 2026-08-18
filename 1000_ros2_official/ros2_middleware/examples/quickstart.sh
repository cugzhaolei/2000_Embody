#!/bin/bash
# 快速上手：一键检测 + 检查 + 跑一个无 GUI 的组合场景（发布订阅）
set -e
MW=/mnt/c/Users/admin/Desktop/dev/2000_Embody/1000_ros2_official/ros2_middleware

echo "===== 1) 检测环境 ====="
(cd "$MW" && python3 -m rosagent detect)

echo ""
echo "===== 2) 运行检查 ====="
(cd "$MW" && python3 -m rosagent check --pkg turtlesim,tf2-tools)

echo ""
echo "===== 3) 跑发布订阅组合场景（无 GUI） ====="
(cd "$MW" && python3 -m rosagent run scenarios/pubsub_demo.json --watch 8)