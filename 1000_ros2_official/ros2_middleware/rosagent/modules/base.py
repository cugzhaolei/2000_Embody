# rosagent.modules.base — 模块基类：每个模块 = 一个可自由组合的最小功能组件
from __future__ import annotations

from ..env import EnvironmentManager
from ..runtime import ProcHandle, RuntimeManager


class BaseModule:
    """所有功能模块的基类。

    生命周期：check() → start() →（可选）反复 health() → stop()
    模块通过 params_schema 声明可配置参数；场景脚本里用不同参数即"适配"不同情况。
    """

    id: str = "base"
    desc: str = ""
    params_schema: dict = {}
    requires: list = []   # 逻辑包名（会按当前 distro 自动翻译/检查）

    def __init__(self, params: dict | None = None,
                 envman: EnvironmentManager | None = None,
                 runtime: RuntimeManager | None = None):
        self.params = {**self.default_params(), **(params or {})}
        self.env: EnvironmentManager = envman
        self.rt: RuntimeManager = runtime
        self._handles: list[ProcHandle] = []

    # ---------- 参数 ----------
    @classmethod
    def default_params(cls) -> dict:
        return {k: v.get("default") for k, v in cls.params_schema.items()}

    @classmethod
    def param_docs(cls) -> str:
        if not cls.params_schema:
            return "  （无参数）"
        return "\n".join(
            f"  {k:<16} 默认={v.get('default')}  {v.get('desc', '')}"
            for k, v in cls.params_schema.items())

    # ---------- 生命周期 ----------
    def check(self):
        """预检：依赖是否满足。返回 (ok, detail)。"""
        missing = []
        for lp in self.requires:
            if not self.env.apt_pkg_available(lp):
                missing.append(f"逻辑包[{lp}]注册表未定义")
                continue
            pkg = self.env.apt_pkg(lp)
            rc, _ = self.rt.run(f"dpkg -s {pkg} >/dev/null 2>&1 && echo ok", timeout=10,
                                include_ws=False)
            if rc != 0:
                missing.append(f"未安装 {pkg}（sudo apt install {pkg}）")
        if missing:
            return False, "; ".join(missing)
        return True, "就绪"

    def start(self) -> list[ProcHandle]:
        """启动模块（可起多个后台进程）。不实现则视为无进程模块。"""
        return []

    def health(self):
        """运行中健康检查，返回 (ok, msg)。"""
        alive = [h for h in self._handles if h.alive]
        dead = [h for h in self._handles if not h.alive]
        if dead:
            return False, f"有 {len(dead)} 个进程退出: {[d.name for d in dead]}"
        if not alive and not self._handles:
            return True, "无后台进程（本模块超时/退出型）"
        return True, f"{len(alive)} 个进程运行中"

    def stop(self):
        for h in self._handles:
            h.stop()
        self._handles.clear()

    # ---------- 工具 ----------
    def _spawn(self, cmd: str, name: str | None = None) -> ProcHandle:
        h = self.rt.start(cmd, name=name)
        self._handles.append(h)
        return h

    def _run(self, cmd: str, timeout: float = 30.0) -> str:
        rc, out = self.rt.run(cmd, timeout=timeout)
        return out

    def summary(self) -> str:
        return f"{self.id} {self.params}"