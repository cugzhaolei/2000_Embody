# rosagent.modules.action_demo — Action 示例模块（第 24/25 课）
from __future__ import annotations

from .base import BaseModule

# 逻辑语言 → (服务器包, 服务器可执行, 客户端包, 客户端可执行)
_IMPLS = {
    "py":  ("action_tutorials_py", "fibonacci_action_server",
            "action_tutorials_py", "fibonacci_action_client"),
    "cpp": ("action_tutorials_cpp", "action_server_executable",
            "action_tutorials_cpp", "action_client_executable"),
}


class ActionDemoModule(BaseModule):
    """启动 Fibonacci Action 服务器 + 客户端，验证 action 通信。"""
    id = "action_demo"
    desc = "action_tutorials：Fibonacci 服务器 + 客户端（py/cpp 可切换）"
    requires = []
    params_schema = {
        "lang":        {"default": "py", "desc": "py 或 cpp"},
        "order":       {"default": 10, "desc": "Fibonacci 序列长度（order）"},
        "action_name": {"default": "fibonacci", "desc": "action 名（健康检查用）"},
    }

    def check(self):
        lang = self.params.get("lang")
        if lang not in _IMPLS:
            return False, f"lang 必须是 py/cpp，收到 {lang!r}"
        ifaces = "action_tutorials_interfaces"
        rc, _ = self.rt.run(f"ros2 pkg prefix {ifaces} >/dev/null 2>&1 && echo ok",
                            timeout=15)
        if rc != 0:
            return False, f"未找到 {ifaces}。请先: cd ~/dev_ws && colcon build --packages-select {ifaces}"
        srv_pkg = _IMPLS[lang][0]
        rc, _ = self.rt.run(f"ros2 pkg prefix {srv_pkg} >/dev/null 2>&1 && echo ok",
                            timeout=15)
        if rc != 0:
            return False, f"未找到 {srv_pkg}。请先: cd ~/dev_ws && colcon build --packages-select {srv_pkg}"
        return True, "action 接口与实现包均已就绪"

    def start(self):
        lang = self.params["lang"]
        srv_pkg, srv_exe, cli_pkg, cli_exe = _IMPLS[lang]
        self._spawn(f"ros2 run {srv_pkg} {srv_exe}", name="action_server")
        self._spawn(f"ros2 run {cli_pkg} {cli_exe}", name="action_client")
        return self._handles

    def health(self):
        action = self.params["action_name"]

        def _listed():
            rc, _ = self.rt.run(
                f"ros2 action list 2>/dev/null | grep -c {action}", timeout=15)
            return rc == 0

        listed = self.rt.wait_until(_listed, timeout=8, interval=1.0)
        if not listed:
            return False, f"action {action} 未列出"
        return True, f"action {action} 已注册，客户端在请求中"