# rosagent.modules.service_client — Service 客户端/服务器模块（第 7/15/16 课）
from __future__ import annotations

from .base import BaseModule

# 逻辑语言 → (服务端包, 服务端可执行, 客户端包, 客户端可执行)
_IMPLS = {
    "py":  ("examples_rclpy_minimal_service",  "service_member_function",
            "examples_rclpy_minimal_client",  "client_async_member_function"),
    "cpp": ("examples_rclcpp_minimal_service",  "service_main",
            "examples_rclcpp_minimal_client",  "client_main"),
}


class ServiceClientModule(BaseModule):
    """启动官方 add_two_ints 服务端 + 自动请求的客户端，验证服务通信。"""
    id = "service_client"
    desc = "官方 service demo：add_two_ints 服务端 + 客户端（py/cpp 可切换）"
    requires = []
    params_schema = {
        "lang":           {"default": "py", "desc": "py 或 cpp"},
        "start_client":   {"default": True, "desc": "是否连客户端一起启动"},
        "service_name":   {"default": "add_two_ints", "desc": "服务名（健康检查用）"},
    }

    def check(self):
        lang = self.params.get("lang")
        if lang not in _IMPLS:
            return False, f"lang 必须是 py/cpp，收到 {lang!r}"
        srv_pkg = _IMPLS[lang][0]
        rc, _ = self.rt.run(f"ros2 pkg prefix {srv_pkg} >/dev/null 2>&1 && echo ok",
                            timeout=15)
        if rc != 0:
            return False, f"未找到 {srv_pkg}。请先: cd ~/dev_ws && colcon build --packages-select {srv_pkg} {_IMPLS[lang][2]}"
        return True, "示例包已在环境中"

    def start(self):
        lang = self.params["lang"]
        srv_pkg, srv_exe, cli_pkg, cli_exe = _IMPLS[lang]
        self._spawn(f"ros2 run {srv_pkg} {srv_exe}", name="service_server")
        if self.params.get("start_client"):
            self._spawn(f"ros2 run {cli_pkg} {cli_exe}", name="service_client")
        return self._handles

    def health(self):
        service = self.params["service_name"]
        rc, out = self.rt.run(f"ros2 service list 2>/dev/null | grep -c {service}",
                              timeout=15)
        if rc != 0:
            return False, f"服务 {service} 未列出"
        return True, f"服务 {service} 已就绪，客户端在请求中"