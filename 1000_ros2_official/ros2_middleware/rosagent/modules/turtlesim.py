# rosagent.modules.turtlesim — turtlesim 多乌龟模块
from __future__ import annotations

from .base import BaseModule


class TurtlesimModule(BaseModule):
    """启动 turtlesim 仿真，可选键盘控制 / 再生成若干乌龟。"""
    id = "turtlesim"
    desc = "turtlesim 仿真：启动乌龟窗口、可选遥控、可选额外乌龟"
    requires = ["turtlesim"]
    params_schema = {
        "node_name":   {"default": "turtlesim", "desc": "ros2 run 的节点名"},
        "keyboard":    {"default": True, "desc": "是否同时启动 teleop 键盘控制"},
        "extra_names": {"default": ["turtle2"], "desc": "额外 spawn 的乌龟名列表"},
        "monitor":     {"default": True, "desc": "是否等 /turtlesim 节点出现并 spawn 额外乌龟"},
    }

    def start(self):
        node_name = self.params["node_name"]
        self._spawn(f"ros2 run turtlesim turtlesim_node", name=node_name)

        if self.params.get("keyboard"):
            self._spawn("ros2 run turtlesim turtle_teleop_key", name="teleop")

        if self.params.get("monitor"):
            self.rt.wait_node(f"/{node_name}", timeout=20)
            for i, tname in enumerate(self.params.get("extra_names") or []):
                x = 3.0 + 1.0 * i
                self._run(
                    f"ros2 service call /spawn turtlesim/srv/Spawn "
                    f"\"{{x: {x}, y: 3.0, theta: 0.0, name: '{tname}'}}\"",
                    timeout=15)
        return self._handles

    def health(self):
        node = f"/{self.params['node_name']}"
        if self.rt.wait_node(node, timeout=10):
            return True, f"节点 {node} 在线"
        return False, "乌龟节点未出现"