# rosagent.modules.launch_run — 运行 launch 文件模块（第 8/28 课）
from __future__ import annotations

from .base import BaseModule


class LaunchRunModule(BaseModule):
    """通用模块：用 ros2 launch 启动任意 launch 文件/包。"""
    id = "launch_run"
    desc = "通用模块：ros2 launch 一个 launch 文件或包（自由组合用）"
    params_schema = {
        "package":   {"default": "launch_tutorial", "desc": "launch 所在的包"},
        "file":      {"default": "hello_world.launch.py", "desc": "launch 文件名"},
        "node_for_check": {"default": "", "desc": "健康检查等到的节点名（留空跳过）"},
    }

    def check(self):
        pkg = self.params["package"]
        rc, _ = self.rt.run(f"ros2 pkg prefix {pkg} >/dev/null 2>&1 && echo ok",
                            timeout=15)
        if rc != 0:
            return False, f"未找到包 {pkg}。请先: cd ~/dev_ws && colcon build --packages-select {pkg}"
        return True, f"包 {pkg} 已就绪"

    def start(self):
        pkg, file = self.params["package"], self.params["file"]
        self._spawn(f"ros2 launch {pkg} {file}", name=f"launch_{file}")
        return self._handles

    def health(self):
        ok_base, msg = super().health()
        node = self.params.get("node_for_check")
        if ok_base and node:
            present = self.rt.wait_node("/" + node.lstrip("/"), timeout=15)
            return present, f"launch 后节点 /{node} {'出现' if present else '未出现'}"
        return ok_base, msg