# rosagent.registry — ROS 版本注册表（适配的唯一数据源）
"""Distro 注册表：集中存放各 ROS 版本的环境事实与 API 差异。

新增一个 ROS 发行版时，只需在这里加一项，Agent 其余代码无需改动。
允许通过环境变量 ROSAGENT_REGISTRY_JSON 指向一个 JSON 文件覆盖/扩展默认值。
"""
from __future__ import annotations

import json
import os

# 逻辑包名 → 各 distro 的实际 apt 包名后缀
# （形如 ros-<distro>-<suffix>；None 表示无对应包）
_PKGS = {
    "desktop":         {"foxy": "desktop", "humble": "desktop", "jazzy": "desktop"},
    "turtlesim":       {"foxy": "turtlesim", "humble": "turtlesim", "jazzy": "turtlesim"},
    "urdf-tutorial":   {"foxy": "urdf-tutorial", "humble": "urdf-tutorial", "jazzy": "urdf"},
    "tf-transformations": {
        "foxy": "tf-transformations",
        "humble": "tf-transformations",
        "jazzy": "tf-transformations",
    },
    "turtle-tf2":      {"foxy": "turtle-tf2-py", "humble": "turtle-tf2-py", "jazzy": "turtle-tf2-py"},
    "tf2-tools":       {"foxy": "tf2-tools", "humble": "tf2-tools", "jazzy": "tf2-tools"},
    "rviz":            {"foxy": "rviz2", "humble": "rviz2", "jazzy": "rviz2"},
    "xacro":           {"foxy": "xacro", "humble": "xacro", "jazzy": "xacro"},
}

DISTROS = {
    "foxy": {
        "codename": "Foxy Fitzroy",
        "ubuntu": ["20.04"],
        "python": (3, 8),
        "eol": "2023-05",
        "setup": "/opt/ros/foxy/setup.bash",
        "apt_prefix": "ros-foxy",
        "default_dds": "rmw_fastrtps_cpp",
        "note": "已 EOL。tf2 C++ 用 tf2::TimePointZero；lookup_transform 传 rclpy.time.Time()",
        "pkgs": _PKGS,
    },
    "humble": {
        "codename": "Humble Hawksbill",
        "ubuntu": ["22.04"],
        "python": (3, 10),
        "eol": "2027-05",
        "setup": "/opt/ros/humble/setup.bash",
        "apt_prefix": "ros-humble",
        "default_dds": "rmw_fastrtps_cpp",
        "note": "维护中 LTS",
        "pkgs": _PKGS,
    },
    "jazzy": {
        "codename": "Jazzy Jalisco",
        "ubuntu": ["24.04"],
        "python": (3, 12),
        "eol": "2029-05",
        "setup": "/opt/ros/jazzy/setup.bash",
        "apt_prefix": "ros-jazzy",
        "default_dds": "rmw_fastrtps_cpp",
        "note": "活跃 LTS。tf2 lookup_transform 需显式 Tolerance",
        "pkgs": _PKGS,
    },
}


class Registry:
    """持有各 distro 配置并暴露查询方法。"""

    def __init__(self, distros: dict | None = None):
        self._distros = distros if distros is not None else DISTROS
        self._apply_overrides()

    def _apply_overrides(self):
        path = os.environ.get("ROSAGENT_REGISTRY_JSON")
        if path and os.path.isfile(path):
            with open(path, encoding="utf-8") as f:
                overrides = json.load(f)
            self._distros.update(overrides)   # 顶层覆盖

    @property
    def distros(self):
        return self._distros

    def has(self, distro: str) -> bool:
        return distro in self._distros

    def get(self, distro: str) -> dict:
        if distro not in self._distros:
            raise KeyError(f"未知的 ROS distro: {distro!r}")
        return self._distros[distro]

    def config(self, distro: str, key: str, default=None):
        return self.get(distro).get(key, default)

    def apt_pkg(self, distro: str, logical: str):
        """逻辑包名 → 该 distro 的完整 apt 包名，如 apt_pkg('foxy','turtlesim') -> 'ros-foxy-turtlesim'"""
        cfg = self.get(distro)
        prefix = cfg.get("apt_prefix")
        pkgs = cfg.get("pkgs", {})
        suffix = pkgs.get(logical, {}).get(distro)
        if not suffix:
            raise KeyError(f"distro {distro} 没有逻辑包 {logical!r}")
        return f"{prefix}-{suffix}"

    def apt_pkg_available(self, distro: str, logical: str) -> bool:
        """该逻辑包在当前 distro 是否有定义。"""
        pkgs = self.get(distro).get("pkgs", {})
        return logical in pkgs and pkgs[logical].get(distro) is not None

    def python_ok(self, distro: str, current: tuple) -> bool:
        req = self.config(distro, "python")
        return current >= req

    def summary(self) -> str:
        lines = []
        for name, cfg in self._distros.items():
            lines.append(
                f"  {name:<8} {cfg.get('codename',''):<22} "
                f"Ubuntu{','.join(cfg.get('ubuntu',[])):<8} "
                f"EOL {cfg.get('eol','?')}"
            )
        return "\n".join(lines)


_default = Registry()


def default_registry() -> Registry:
    return _default