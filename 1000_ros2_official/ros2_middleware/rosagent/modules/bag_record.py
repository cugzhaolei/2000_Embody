# rosagent.modules.bag_record — rosbag 录制/回放模块（第 10 课）
from __future__ import annotations

import time

from .base import BaseModule


class BagRecordModule(BaseModule):
    """后台录制指定话题 N 秒，超时自动停录，随后 ros2 bag info 校验内容。"""
    id = "bag_record"
    desc = "rosbag 录制：录 N 秒（timeout 优雅停）→ ros2 bag info 校验"
    requires = []
    params_schema = {
        "topics":    {"default": ["/chatter"], "desc": "要录制的话题列表"},
        "duration":  {"default": 6, "desc": "录制秒数"},
        "outdir":    {"default": "/tmp/rosagent_bag", "desc": "bag 输出目录"},
        "all_topics": {"default": False, "desc": "true 时用 -a 录制全部话题"},
    }

    def check(self):
        rc, _ = self.rt.run("ros2 bag --help >/dev/null 2>&1 && echo ok", timeout=10)
        if rc != 0:
            return False, "未找到 ros2 bag（需安装 ros-foxy-ros2bag 等组件）"
        return True, "ros2 bag 可用"

    def start(self):
        import shutil
        out = self.params["outdir"]
        shutil.rmtree(out, ignore_errors=True)  # -o 要求目录不存在
        dur = int(float(self.params["duration"]))
        if self.params.get("all_topics"):
            self._spawn(f"timeout {dur} ros2 bag record -o {out} -a",
                        name="bag_recorder")
        else:
            topics = " ".join(self.params["topics"])
            self._spawn(f"timeout {dur} ros2 bag record -o {out} {topics}",
                        name="bag_recorder")
        self._record_since = time.time()
        return self._handles

    def health(self):
        dur = float(self.params["duration"])
        elapsed = time.time() - self._record_since
        alive = [h for h in self._handles if h.alive]
        if alive:
            return True, f"录制中 {elapsed:.0f}/{dur:.0f}s"
        # 已超时停录 → info 校验
        out = self.params["outdir"]
        rc, info = self.rt.run(f"ros2 bag info {out} 2>&1", timeout=30)
        if rc != 0:
            return False, f"bag 校验失败: {info.strip()[:200]}"
        lines = [ln.strip() for ln in info.splitlines()
                 if ln.strip() and not ln.startswith("[INFO]")]
        return True, "停录完成: " + (" | ".join(lines[-6:]))