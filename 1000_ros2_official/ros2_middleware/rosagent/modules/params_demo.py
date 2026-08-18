# rosagent.modules.params_demo — 参数节点模块（第 19/20 课）
from __future__ import annotations

from .base import BaseModule

# 逻辑语言 → (包, 可执行, 节点名, 参数名)
_IMPLS = {
    "py":  ("py_parameters", "minimal_param_node", "minimal_param_node", "my_parameter"),
    "cpp": ("cpp_parameters", "cpp_parameters_node", "cpp_parameters_node", "my_parameter"),
}


class ParamsDemoModule(BaseModule):
    """启动参数节点，在命令行设一个参数并验证可读，演示参数用法。"""
    id = "params_demo"
    desc = "参数节点 demo：启动并设置 my_parameter 后验证"
    requires = []
    params_schema = {
        "lang":   {"default": "py", "desc": "py 或 cpp"},
        "param":  {"default": "my_parameter", "desc": "要读取/设置的参数名"},
        "value":  {"default": "HELLO from rosagent", "desc": "设置的新参数值"},
    }

    def check(self):
        lang = self.params.get("lang")
        if lang not in _IMPLS:
            return False, f"lang 必须是 py/cpp，收到 {lang!r}"
        pkg = _IMPLS[lang][0]
        rc, _ = self.rt.run(f"ros2 pkg prefix {pkg} >/dev/null 2>&1 && echo ok",
                            timeout=15)
        if rc != 0:
            return False, f"未找到 {pkg}。请先: cd ~/dev_ws && colcon build --packages-select {pkg}"
        return True, f"包 {pkg} 已就绪"

    def start(self):
        lang = self.params["lang"]
        pkg, exe, node, pname = _IMPLS[lang]
        val = self.params["value"]
        self._spawn(
            f"ros2 run {pkg} {exe} --ros-args -p {pname}:=\"{val}\"",
            name="params_node")
        return self._handles

    def health(self):
        lang = self.params["lang"]
        pkg, exe, node, pname = _IMPLS[lang]
        if not self.rt.wait_node("/" + node.lstrip("/"), timeout=15):
            return False, f"参数节点 /{node} 未出现"
        rc, out = self.rt.run(
            f"ros2 param get {node} {pname} 2>/dev/null", timeout=15)
        if rc != 0:
            return False, f"参数 {pname} 读取失败"
        return True, f"/{node}.{pname} = {out.strip().splitlines()[-1]}"