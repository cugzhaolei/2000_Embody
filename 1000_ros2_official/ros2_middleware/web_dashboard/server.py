#!/usr/bin/env python3
"""rosagent web — 单文件 Web Dashboard，无需 Socket.IO"""
import os, subprocess, threading, json, time
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

MIDDLEWARE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCENARIOS_DIR = os.path.join(MIDDLEWARE_DIR, "scenarios")
DASHBOARD_DIR = os.path.dirname(os.path.abspath(__file__))

SCENARIOS = [
    {"id": "pubsub",    "name": "发布订阅",    "file": "pubsub_demo.json",      "desc": "话题发布/订阅通信 (py/cpp)"},
    {"id": "service",   "name": "服务通信",    "file": "service_demo.json",     "desc": "add_two_ints 服务端+客户端"},
    {"id": "action",    "name": "动作通信",    "file": "action_demo.json",      "desc": "Fibonacci action 服务器+客户端"},
    {"id": "params",    "name": "参数节点",    "file": "params_demo.json",      "desc": "参数声明/读取/修改验证"},
    {"id": "bag",       "name": "Rosbag录制",  "file": "bag_record_demo.json",  "desc": "录制话题 → ros2 bag info 校验"},
    {"id": "turtlesim", "name": "乌龟仿真",    "file": "lesson2_turtlesim.json", "desc": "turtlesim + 遥控 (需GUI)"},
]

running_proc = None

class Handler(SimpleHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/" or path == "/index.html":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            with open(os.path.join(DASHBOARD_DIR, "index.html"), "rb") as f:
                self.wfile.write(f.read())
            return

        if path == "/api/scenarios":
            self.send_json(SCENARIOS)
            return

        if path == "/api/run":
            qs = parse_qs(parsed.query)
            fname = qs.get("file", [""])[0]
            self.run_scenario(fname)
            return

        if path == "/api/stop":
            global running_proc
            if running_proc and running_proc.poll() is None:
                running_proc.terminate()
                try:
                    running_proc.wait(5)
                except:
                    running_proc.kill()
            self.send_json({"ok": True})
            return

        self.send_error(404)

    def run_scenario(self, fname):
        global running_proc
        if running_proc and running_proc.poll() is None:
            self.send_json({"ok": False, "msg": "有场景正在运行"})
            return

        path = os.path.join(SCENARIOS_DIR, fname)
        if not os.path.isfile(path):
            self.send_json({"ok": False, "msg": f"场景不存在: {fname}"})
            return

        cmd = (
            f"source /opt/ros/foxy/setup.bash && "
            f"source ~/dev_ws/install/setup.bash && "
            f"cd {MIDDLEWARE_DIR} && "
            f"python3 -m rosagent run scenarios/{fname} --watch 8"
        )

        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.send_header("X-Accel-Buffering", "no")
        self.end_headers()

        def send_sse(data):
            self.wfile.write(f"data: {json.dumps(data, ensure_ascii=False)}\n\n".encode())
            self.wfile.flush()

        send_sse({"type": "start", "file": fname})

        proc = subprocess.Popen(
            ["bash", "-lc", cmd],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, bufsize=1, cwd=MIDDLEWARE_DIR)
        running_proc = proc

        for line in proc.stdout:
            send_sse({"type": "output", "line": line.rstrip("\n")})

        proc.wait()
        running_proc = None
        send_sse({"type": "done", "rc": proc.returncode})

    def send_json(self, obj):
        data = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, format, *args):
        pass  # 静默日志


def main():
    port = int(os.environ.get("PORT", 5000))
    server = HTTPServer(("0.0.0.0", port), Handler)
    print(f"rosagent web: http://localhost:{port}")
    print(f"WSL IP: check with 'hostname -I'")
    server.serve_forever()

if __name__ == "__main__":
    main()
