# rosagent.checks — 运行检查：环境 / 依赖 / 工作空间 / 节点话题
from __future__ import annotations

import dataclasses
import os

from .env import EnvironmentManager
from .runtime import RuntimeManager


@dataclasses.dataclass
class CheckItem:
    name: str
    ok: bool
    detail: str = ""

    def line(self) -> str:
        mark = "[ok]" if self.ok else "[xx]"
        return f"  {mark} {self.name:<28} {self.detail}"


class Reporter:
    def __init__(self):
        self.items: list[CheckItem] = []

    def add(self, name: str, ok: bool, detail: str = ""):
        self.items.append(CheckItem(name, ok, detail))

    def passed(self) -> bool:
        return all(i.ok for i in self.items)

    def render(self) -> str:
        lines = [i.line() for i in self.items]
        lines.append("")
        lines.append(f"总检查项：{len(self.items)}，通过：{sum(1 for i in self.items if i.ok)}，"
                     f"失败：{sum(1 for i in self.items if not i.ok)}")
        return "\n".join(lines)


class Checks:
    def __init__(self, envman: EnvironmentManager, runtime: RuntimeManager | None = None):
        self.env = envman
        self.rt = runtime or RuntimeManager(envman)
        self.reporter = Reporter()

    def environment(self) -> Reporter:
        r = self.reporter
        e = self.env.env
        r.add("ROS distro 已检测到", bool(e.distro), e.distro or "未找到")
        r.add("setup 文件存在", bool(e.setup_bash and os.path.isfile(e.setup_bash)),
              e.setup_bash)
        ok_text = '在注册表内' if e.distro_ok else '(需注册表补充该版本配置)'
        r.add("distro 在注册表内", e.distro_ok, ok_text)
        py = e.python_major_minor
        req = self.env.python_version_req()
        r.add(f"Python 版本满足要求(≥{req})", self.env.reg.python_ok(e.distro, py)
              if e.distro else False, f"当前 {py[0]}.{py[1]}")
        if e.distro:
            r.add("ros2 命令可用", self._which("ros2"), self._which("ros2") or "")
        r.add("工作空间已编译", bool(e.ws_install), e.ws_install or "未检测到 install/setup.bash")
        return r

    def apt_pkgs(self, logicals) -> Reporter:
        for lp in logicals:
            if not self.env.apt_pkg_available(lp):
                self.reporter.add(f"逻辑包 {lp}", False, "注册表未定义")
                continue
            pkg = self.env.apt_pkg(lp)
            ok = self._apt_installed(pkg)
            self.reporter.add(f"apt 包 {lp} ({pkg})", ok,
                              "已安装" if ok else f"sudo apt install {pkg}")
        return self.reporter

    def topic_exists(self, topic: str, timeout: float = 15.0) -> bool:
        target = topic.lstrip("/")
        def fn():
            rc, out = self.rt.run(f"ros2 topic list 2>/dev/null | grep -x '/{target}'",
                                  timeout=15)
            return rc == 0 and "/" + target in out
        return self.rt.wait_until(fn, timeout)

    def node_exists(self, node: str, timeout: float = 15.0) -> bool:
        return self.rt.wait_node(node, timeout)

    # ---------- 内部 ----------
    def _which(self, name: str) -> str:
        out = self.rt.run(f"command -v {name}", timeout=10)
        _, s = out
        return s.strip()

    def _apt_installed(self, pkg: str) -> bool:
        rc, _ = self.rt.run(f"dpkg -s {pkg} >/dev/null 2>&1 && echo yes", timeout=10,
                            include_ws=False)
        return rc == 0