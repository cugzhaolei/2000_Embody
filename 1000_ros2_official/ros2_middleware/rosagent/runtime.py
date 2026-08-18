# rosagent.runtime — 运行时管理器：后台进程起停 / 健康轮询 / 清理
from __future__ import annotations

import dataclasses
import os
import subprocess
import tempfile
import time

from .env import EnvironmentManager


@dataclasses.dataclass
class ProcHandle:
    name: str
    proc: subprocess.Popen
    cmd: str
    logfile: str | None = None
    started: float = dataclasses.field(default_factory=time.time)

    @property
    def alive(self) -> bool:
        return self.proc.poll() is None

    def stop(self, timeout: float = 5.0):
        if self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(timeout)
            except subprocess.TimeoutExpired:
                self.proc.kill()

    def __repr__(self):
        return f"<Proc {self.name}: {'running' if self.alive else 'exited(' + str(self.proc.returncode) + ')'}>"


class RuntimeManager:
    """负责在 [当前 distro 环境] 下执行命令、后台拉进程、轮询健康、清理。"""

    def __init__(self, envman: EnvironmentManager, log_dir: str | None = None):
        self.env = envman
        self.log_dir = log_dir or tempfile.mkdtemp(prefix="rosagent_")
        self._procs: dict[str, ProcHandle] = {}

    # ---------- 底层执行 ----------
    def run(self, cmd: str, include_ws: bool = True, block: bool = True,
            timeout: float = 60.0) -> tuple[int, str]:
        """在正确环境里执行一条命令。block=True 返回 (rc, stdout)。"""
        full = self.env.wrap(cmd, include_ws=include_ws)
        if block:
            r = subprocess.run(
                ["bash", "-lc", full],
                capture_output=True, text=True, timeout=timeout)
            return r.returncode, (r.stdout or "") + (r.stderr or "")
        # 后台
        return self._spawn(cmd, include_ws=include_ws)

    def start(self, cmd: str, name: str | None = None, include_ws: bool = True) -> ProcHandle:
        """后台启动，记录日志。返回句柄并登记。"""
        return self._spawn(cmd, include_ws=include_ws, name=name)

    def _spawn(self, cmd: str, include_ws: bool = True, name: str | None = None) -> ProcHandle:
        full = self.env.wrap(cmd, include_ws=include_ws)
        name = name or _cmd_stem(cmd)
        logfile = os.path.join(self.log_dir, f"{name}.log")
        f = open(logfile, "a", buffering=1)
        p = subprocess.Popen(
            ["bash", "-lc", full], stdout=f, stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL)
        ph = ProcHandle(name=name, proc=p, cmd=full, logfile=logfile)
        self._procs[name] = ph
        return ph

    # ---------- 进程管理 ----------
    def list_active(self) -> list[ProcHandle]:
        return [p for p in self._procs.values() if p.alive]

    def get(self, name: str) -> ProcHandle | None:
        return self._procs.get(name)

    def stop(self, name: str | None = None, pattern: str | None = None, timeout: float = 5.0):
        for ph in list(self._procs.values()):
            if name and ph.name != name:
                continue
            if pattern and pattern not in ph.cmd:
                continue
            ph.stop(timeout)

    def stop_all(self, timeout: float = 5.0):
        for ph in list(self._procs.values()):
            ph.stop(timeout)
        # 兜底：把脚本自己起的 shell 也清掉
        self._pkill_ros()

    # ---------- 健康轮询 ----------
    def wait_until(self, fn, timeout: float = 30.0, interval: float = 0.5) -> bool:
        t0 = time.time()
        while time.time() - t0 < timeout:
            try:
                if fn():
                    return True
            except Exception:
                pass
            time.sleep(interval)
        return False

    def wait_node(self, node: str, timeout: float = 30.0) -> bool:
        """等待某节点出现在 ros2 node list。"""
        return self.wait_until(lambda: node in self.node_list(), timeout)

    def node_list(self) -> list[str]:
        rc, out = self.run("ros2 node list 2>/dev/null", timeout=15)
        if rc != 0:
            return []
        return [ln.strip() for ln in out.splitlines() if ln.strip()]

    # ---------- 清理 ----------
    def _pkill_ros(self, patterns=("turtlesim", "turtle_teleop_key", "rqt",
                                    "rviz2", "gazebo", "rosbag2", "component_container")):
        for pat in patterns:
            subprocess.run(["pkill", "-f", pat],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def cleanup(self) -> str:
        """杀掉遗留 ROS 进程、重启 daemon、释放缓存。返回说明文本。"""
        self._pkill_ros()
        subprocess.run(["bash", "-lc", "ros2 daemon stop 2>/dev/null"],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run(["bash", "-lc", "ros2 daemon start 2>/dev/null"],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run(["bash", "-lc", "sync 2>/dev/null"],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run(["bash", "-lc",
                        "sudo -n tee /proc/sys/vm/drop_caches >/dev/null 2>&1 <<< 3"],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return "已清理遗留进程并重置 daemon"


def _cmd_stem(cmd: str) -> str:
    """从命令行里提炼简短的名字当作日志文件名。"""
    parts = cmd.split(" && ")[-1].split()
    for p in parts:
        if not p.startswith("--"):
            return p.replace("/", "_")[:60]
    return "rosjob"