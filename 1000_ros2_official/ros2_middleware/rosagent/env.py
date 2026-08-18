# rosagent.env — 环境管理器：把逻辑操作转成对应当前 distro 的 bash 命令
from __future__ import annotations

from . import registry as _reg
from .detector import EnvInfo


class EnvironmentManager:
    """基于探测到的 EnvInfo，生成正确的 source / apt 包名 / 环境变量命令。"""

    def __init__(self, env: EnvInfo, reg: _reg.Registry | None = None):
        self.env = env
        self.reg = reg or _reg.default_registry()

    # ---------- 基础命令 ----------
    @property
    def is_ready(self) -> bool:
        return bool(self.env.distro and self.env.setup_bash)

    def base_source(self) -> str:
        """source 纯 ROS 基础环境，如 `source /opt/ros/foxy/setup.bash`"""
        return f"source {self.env.setup_bash}"

    def ws_source(self) -> str:
        """若探测到已编译工作空间，返回其 setup 命令；否则为空串。"""
        if self.env.ws_install:
            return f"source {self.env.ws_install}"
        return ""

    def source_prefix(self, include_ws: bool = True) -> str:
        parts = [self.base_source()]
        if include_ws:
            ws = self.ws_source()
            if ws:
                parts.append(ws)
        if self.env.domain_id not in ("", "0"):
            parts.append(f"export ROS_DOMAIN_ID={self.env.domain_id}")
        return "; ".join(parts)

    def wrap(self, cmd: str, include_ws: bool = True) -> str:
        """把一条 shell 命令包上正确的环境前缀。"""
        return f"{self.source_prefix(include_ws)} && {cmd}"

    # ---------- 包名翻译 ----------
    def apt_pkg(self, logical: str) -> str:
        """逻辑名 → 本 distro 的 apt 包名：apt_pkg('turtlesim') -> 'ros-foxy-turtlesim'"""
        if not self.env.distro:
            raise RuntimeError("未检测到 ROS distro，无法翻译包名")
        return self.reg.apt_pkg(self.env.distro, logical)

    def apt_pkg_available(self, logical: str) -> bool:
        if not self.env.distro:
            return False
        return self.reg.apt_pkg_available(self.env.distro, logical)

    def python_version_req(self) -> str:
        if not self.env.distro:
            return "?"
        req = self.reg.config(self.env.distro, "python", (0, 0))
        return f"{req[0]}.{req[1]}"

    def distro_note(self) -> str:
        return self.reg.config(self.env.distro, "note", "") if self.env.distro else ""

    # ---------- 组合检查 ----------
    def describe(self) -> str:
        title = f"环境 [{self.env.distro or '(none)'}]"
        if self.is_ready:
            note = self.distro_note()
            title += f" — {note}" if note else ""
        elif self.env.distro:
            title += " （未在注册表中找到配置）"
        return title