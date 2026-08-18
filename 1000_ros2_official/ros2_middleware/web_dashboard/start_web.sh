#!/bin/bash
# start_web.sh — 在 WSL 中启动 rosagent web dashboard
set -e
cd "$(dirname "$0")/.."
source /opt/ros/foxy/setup.bash
source ~/dev_ws/install/setup.bash
echo "Starting rosagent web on http://localhost:5000"
exec python3 web_dashboard/server.py
