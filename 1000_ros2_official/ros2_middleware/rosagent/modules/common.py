# rosagent.modules.common — 通用小模块：清理 / 监视话题 / 动作示例
from __future__ import annotations

from .base import BaseModule


class CleanModule(BaseModule):
    """清理残留进程与内存（场景 pre 步骤常用，也可作独立模块）。"""
    id = "clean"
    desc = "杀掉遗留 ROS 进程、重置 daemon、释放缓存"
    params_schema = {}

    def check(self):
        return True, "始终可用"

    def start(self):
        self.rt.cleanup()
        return []


class TopicViewModule(BaseModule):
    """后台监视指定话题：echo 或统计频率。"""
    id = "topic_view"
    desc = "对每个话题起一个 ros2 topic echo 进程并检查其活跃"
    params_schema = {
        "topics": {"default": ["/turtle1/pose"], "desc": "要监视的话题列表"},
        "hz":     {"default": False, "desc": "true 时用 ros2 topic hz 统计频率"},
    }

    def start(self):
        for t in self.params["topics"]:
            if self.params.get("hz"):
                self._spawn(f"ros2 topic hz {t}", name=f"hz_{t.strip('/')}")
            else:
                self._spawn(f"ros2 topic echo {t} --once", name=f"echo_{t.strip('/')}")
        return self._handles


class RobotStateModule(BaseModule):
    """示例：参数化启停任意 ros2 run 命令的通用模块（自由组合的'万能模块'）。"""
    id = "ros_run"
    desc = "通用模块：用参数指定 package/executable/args，启动任意 ROS 节点"
    params_schema = {
        "package":    {"default": "turtlesim", "desc": "ros2 run 的包名"},
        "executable": {"default": "turtlesim_node", "desc": "可执行名"},
        "args":       {"default": "", "desc": "附加参数（含 --ros-args ...）"},
        "node_for_check": {"default": "", "desc": "用于健康检查的节点名（留空则跳过）"},
    }

    def start(self):
        pkg, exe = self.params["package"], self.params["executable"]
        args = self.params.get("args") or ""
        self._spawn(f"ros2 run {pkg} {exe} {args}", name=exe)
        return self._handles

    def health(self):
        ok_base, msg = super().health()
        node = self.params.get("node_for_check")
        if ok_base and node:
            present = self.rt.wait_node("/" + node.lstrip("/"), timeout=10)
            return present, f"节点 /{node} {'出现' if present else '未出现'}"
        return ok_base, msg