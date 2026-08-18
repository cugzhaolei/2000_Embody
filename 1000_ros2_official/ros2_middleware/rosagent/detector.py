# rosagent.detector — 环境探测（OS / WSL / ROS distro / 工作空间 / Python）
from __future__ import annotations

import dataclasses
import distutils.spawn as ds  # noqa  (兼容无 shutil.which 的场景)
import os
import platform
import shutil
import sys

from . import registry as _reg


@dataclasses.dataclass
class EnvInfo:
    os_name: str = ""
    os_version: str = ""
    is_wsl: bool = False
    distro: str = ""
    distro_ok: bool = False
    setup_bash: str = ""
    ws_src: str = ""            # 工作空间源码目录 ~/dev_ws/src
    ws_install: str = ""        # 工作空间安装目录 ~/dev_ws/install
    python_major_minor: tuple = (0, 0)
    domain_id: str = os.environ.get("ROS_DOMAIN_ID", "0")

    def summary(self) -> str:
        lines = [
            f"OS            : {self.os_name} {self.os_version}" + ("  (WSL)" if self.is_wsl else ""),
            f"Python        : {self.python_major_minor[0]}.{self.python_major_minor[1]}",
            f"ROS distro    : {self.distro or '(not found)'}",
            f"Source 命令   : {self.setup_bash or '(none)'}",
            f"工作空间 src  : {self.ws_src or '(none)'}",
            f"工作空间 ins  : {self.ws_install or '(none)'}",
            f"ROS_DOMAIN_ID : {self.domain_id}",
        ]
        return "\n".join(lines)


def _os_release() -> dict:
    d = {}
    for path in ("/etc/os-release", "/usr/lib/os-release"):
        if os.path.isfile(path):
            with open(path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if "=" in line:
                        k, _, v = line.partition("=")
                        d[k.strip()] = v.strip().strip('"')
            break
    return d


def is_wsl() -> bool:
    try:
        with open("/proc/version", encoding="utf-8", errors="ignore") as f:
            return "microsoft" in f.read().lower()
    except OSError:
        return False


def _detect_distro(reg: _reg.Registry) -> tuple:
    """返回 (distro, setup_bash, ok)。优先环境变量，其次扫描 /opt/ros。"""
    env_d = os.environ.get("ROS_DISTRO", "").strip().lower()
    if env_d and reg.has(env_d):
        return env_d, reg.config(env_d, "setup"), True
    if os.path.isdir("/opt/ros"):
        try:
            names = sorted(os.listdir("/opt/ros"))
        except OSError:
            names = []
        for name in names:
            if reg.has(name):
                return name, reg.config(name, "setup"), True
        # 可识别但没有注册表条的版本
        for name in names:
            if name:
                return name, f"/opt/ros/{name}/setup.bash", False
    return "", "", False


def _detect_workspace() -> tuple:
    """检测工作空间：优先 ~/dev_ws，其次 ~/ros2_ws，再扫描 home 下含 src 且安装过 setup 的目录。"""
    home = os.path.expanduser("~")
    candidates = ["dev_ws", "ros2_ws", "ros_ws"]
    for cand in candidates:
        base = os.path.join(home, cand)
        install = os.path.join(base, "install", "setup.bash")
        if os.path.isfile(install):
            return os.path.join(base, "src"), install
    try:
        for name in sorted(os.listdir(home)):
            base = os.path.join(home, name)
            if not name.startswith(".") and os.path.isdir(base):
                install = os.path.join(base, "install", "setup.bash")
                if os.path.isfile(install):
                    return os.path.join(base, "src"), install
    except OSError:
        pass
    return "", ""


def detect(reg: _reg.Registry | None = None) -> EnvInfo:
    reg = reg or _reg.default_registry()
    rel = _os_release()
    distro, setup_bash, ok = _detect_distro(reg)
    ws_src, ws_install = _detect_workspace()
    cur_py = (sys.version_info.major, sys.version_info.minor)
    env = EnvInfo(
        os_name=rel.get("NAME", platform.system()),
        os_version=rel.get("VERSION_ID", platform.release()),
        is_wsl=is_wsl(),
        distro=distro,
        distro_ok=ok,
        setup_bash=setup_bash,
        ws_src=ws_src,
        ws_install=ws_install,
        python_major_minor=cur_py,
        domain_id=os.environ.get("ROS_DOMAIN_ID", "0"),
    )
    return env