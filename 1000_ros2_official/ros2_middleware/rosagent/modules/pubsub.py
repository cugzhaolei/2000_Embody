# rosagent.modules.pubsub — 官方发布订阅示例模块（可 py / cpp，可换话题名）
from __future__ import annotations

from .base import BaseModule

# 逻辑语言 → (发布包, 发布可执行, 订阅包, 订阅可执行)
_IMPLS = {
    "py":  ("examples_rclpy_minimal_publisher",  "publisher_member_function",
            "examples_rclpy_minimal_subscriber", "subscriber_member_function"),
    "cpp": ("examples_rclcpp_minimal_publisher", "publisher_member_function",
            "examples_rclcpp_minimal_subscriber", "subscriber_member_function"),
}


class PubSubModule(BaseModule):
    """跑一份官方发布订阅示例：发布者 + 订阅者 + 可选 echo，验证话题通信。"""
    id = "pubsub"
    desc = "官方 examples 发布订阅 demo（py/cpp 可切换、话题名可改）"
    requires = []  # 不依赖 apt 包，依赖工作空间编译产物（由 check 检查）
    params_schema = {
        "lang":   {"default": "py", "desc": "py 或 cpp"},
        "topic":  {"default": "topic", "desc": "发布订阅的话题名"},
        "echo":   {"default": True, "desc": "是否额外起一个 ros2 topic echo"},
        "hz":     {"default": False, "desc": "是否额外统计话题频率"},
    }

    def check(self):
        lang = self.params.get("lang")
        if lang not in _IMPLS:
            return False, f"lang 必须是 py/cpp，收到 {lang!r}"
        pub_pkg = _IMPLS[lang][0]
        rc, _ = self.rt.run(f"ros2 pkg prefix {pub_pkg} >/dev/null 2>&1 && echo ok",
                            timeout=15)
        if rc != 0:
            return False, f"未找到 {pub_pkg}。请先: cd ~/dev_ws && colcon build --packages-select {pub_pkg} {_IMPLS[lang][2]}"
        return True, "示例包已在环境中（源码或工作空间）"

    def start(self):
        lang = self.params["lang"]
        pub_pkg, pub_exe, sub_pkg, sub_exe = _IMPLS[lang]
        topic = self.params["topic"]
        remap = f" --ros-args --remap topic:={topic}" if topic != "topic" else ""
        self._spawn(f"ros2 run {pub_pkg} {pub_exe}{remap}", name="publisher")
        self._spawn(f"ros2 run {sub_pkg} {sub_exe}{remap}", name="subscriber")
        if self.params.get("echo"):
            self._spawn(f"ros2 topic echo {topic}", name=f"echo_{topic.strip('/')}")
        if self.params.get("hz"):
            self._spawn(f"ros2 topic hz {topic}", name=f"hz_{topic.strip('/')}")
        return self._handles

    def health(self):
        topic = "/" + self.params["topic"].lstrip("/")
        rc, out = self.rt.run(f"ros2 topic info {topic} 2>/dev/null | grep -c 'Publisher count'",
                              timeout=15)
        if rc != 0:
            return False, f"话题 {topic} 不可见"
        return True, f"话题 {topic} 正常收发"