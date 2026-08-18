# rosagent.runner — 场景引擎：把"模块 + 参数"自由组合成一次运行
from __future__ import annotations

import dataclasses
import json
import time

from . import registry as _reg
from .checks import Checks
from .detector import detect
from .env import EnvironmentManager
from .modules import get_module_class
from .runtime import ProcHandle, RuntimeManager


@dataclasses.dataclass
class ScenarioResult:
    scenario: str
    distro: str
    ok: bool = True
    steps: list[str] = dataclasses.field(default_factory=list)
    module_states: dict = dataclasses.field(default_factory=dict)

    def render(self) -> str:
        lines = [f"===== 场景 [{self.scenario}] @ {self.distro} ====="]
        lines += [f"  • {s}" for s in self.steps]
        lines.append("  -- 模块状态 --")
        for mid, state in self.module_states.items():
            okm = "ok " if state.get("ok") else "FAIL"
            lines.append(f"    [{okm}] {mid}: {state.get('detail', '')}")
        lines.append("  =====================")
        lines.append("  整体结果: " + ("PASS" if self.ok else "FAIL"))
        return "\n".join(lines)


class ScenarioRunner:
    def __init__(self, envman: EnvironmentManager | None = None,
                 reg: _reg.Registry | None = None):
        self.reg = reg or _reg.default_registry()
        self.result = ScenarioResult(scenario="?", distro="?")
        if envman is None:
            env = detect(self.reg)
            envman = EnvironmentManager(env, self.reg)
        self.env = envman
        self.rt = RuntimeManager(envman)
        self.rt.cleanup()   # 每次场景前先清理（幂等、安全）

    # ---------- 加载 ----------
    def load(self, path: str) -> dict:
        with open(path, encoding="utf-8") as f:
            return json.load(f)

    # ---------- 执行 ----------
    def run(self, scenario: dict, watch: float = 0.0, fail_fast: bool = True):
        self.result = ScenarioResult(
            scenario=scenario.get("name", "unnamed"),
            distro=self.env.env.distro or "(none)")
        steps = self.result.steps

        # 1. distro 核对
        req = scenario.get("distro", "auto")
        if req != "auto" and req != self.env.env.distro:
            steps.append(f"distro 不匹配：要求 {req}，实际 {self.env.env.distro}")
            self.result.ok = False
            return self.result

        # 2. pre 步骤
        pre = scenario.get("pre", [])
        if "clean" in pre:
            self.rt.cleanup()
            steps.append("已清理环境")

        # 3. 模块组合
        run_modules = []
        for spec in scenario.get("modules", []):
            mid = spec["name"]
            params = spec.get("params", {})
            try:
                cls = get_module_class(mid)
            except KeyError as ex:
                steps.append(str(ex))
                if fail_fast:
                    self.result.ok = False
                    return self.result
                continue
            mod = cls(params=params, envman=self.env, runtime=self.rt)
            ok, detail = mod.check()
            self.result.module_states[mid] = {"ok": False, "detail": detail}
            if not ok:
                steps.append(f"模块 {mid} 预检失败: {detail}")
                if fail_fast:
                    self.result.ok = False
                    return self.result
                continue
            handles = mod.start()
            self.result.module_states[mid] = {
                "ok": True, "detail": f"启动 {len(handles)} 个进程 -> 健康"
            }
            steps.append(f"模块 {mid} 已启动")
            run_modules.append(mod)

        # 4. 运行观察
        if watch and watch > 0:
            end = time.time() + watch
            while time.time() < end:
                for mod in run_modules:
                    okm, msg = mod.health()
                    st = self.result.module_states.get(mod.id, {})
                    st["detail"] = msg
                    st["ok"] = okm
                    if not okm:
                        steps.append(f"[{mod.id}] 异常: {msg}")
                time.sleep(2)

        # 5. 断言
        chk = Checks(self.env, self.rt)
        for node in scenario.get("assert_nodes", []):
            okn = self.rt.wait_node(node, timeout=20)
            steps.append(f"断言节点 /{node}: {'存在' if okn else '不存在'}")
            if not okn:
                self.result.ok = False
        for topic in scenario.get("assert_topics", []):
            okt = chk.topic_exists(topic, timeout=20)
            steps.append(f"断言话题 /{topic}: {'存在' if okt else '不存在'}")
            if not okt:
                self.result.ok = False

        # 6. 收尾
        if scenario.get("teardown", True):
            for mod in reversed(run_modules):
                mod.stop()
            steps.append("已停止全部模块")

        return self.result