#!/bin/bash
# start_web_daemon.sh — 后台启动 rosagent web dashboard
PROGDIR="$(cd "$(dirname "$0")" && pwd)"
LOGFILE="/tmp/rosagent_web.log"

# Kill any existing instance
pkill -f "web_dashboard/server.py" 2>/dev/null
sleep 1

# Source ROS environment and start
(
  source /opt/ros/foxy/setup.bash
  source ~/dev_ws/install/setup.bash
  cd "$PROGDIR/.."
  python3 web_dashboard/server.py
) > "$LOGFILE" 2>&1 &

echo "PID: $!"
sleep 2

if kill -0 $! 2>/dev/null; then
  echo "Server running at http://localhost:5000"
  echo "WSL IP: $(hostname -I | awk '{print $1}')"
else
  echo "Failed to start. Log:"
  cat "$LOGFILE"
fi
