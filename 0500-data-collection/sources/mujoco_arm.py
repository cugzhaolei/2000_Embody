"""
MuJoCo 仿真数据源适配器
======================
复用 0200-vla-imitation/envs/mujoco_env.py 的 MuJoCoArmEnv，
但把动作语义统一为 7 维增量控制。若该环境不可用（缺 mujoco），
自动退化为 DummySource 以便链路验证。
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Dict, Optional

import numpy as np

from .base import DataSource


def _import_env() -> Optional[object]:
    """惰性导入 0200-vla-imitation 的 env（防止缺依赖报错污染入口）。"""
    try:
        candidates = _env_search_paths()
        import importlib.util

        for base in candidates:
            env_file = base / "envs" / "mujoco_env.py"
            if env_file.exists():
                spec = importlib.util.spec_from_file_location(
                    "dc_env_mujoco", str(env_file))
                module = importlib.util.module_from_spec(spec)
                sys.modules["dc_env_mujoco"] = module
                if spec.loader:
                    spec.loader.exec_module(module)
                return module.MuJoCoArmEnv
        return None
    except Exception:
        return None


def _env_search_paths():
    """候选的 envs 宿主目录：仓库根目录(如果放根级) 或 0200-vla-imitation。"""
    here = Path(__file__).resolve().parent.parent.parent  # 2000_Embody
    return [here, here / "0200-vla-imitation"]


class MuJoCoArmSource(DataSource):
    """包装现有 MuJoCo 机械臂环境为数据源。"""

    name = "mujoco"

    def __init__(self, render: bool = False, image_size=(160, 160), max_steps=200):
        self._env_cls = _import_env()
        self._env = None
        self.render = render
        self.image_size = image_size
        self.max_steps = max_steps
        self._step_count = 0

    def _ensure_env(self):
        if self._env is None:
            if self._env_cls is None:
                raise RuntimeError(
                    "MuJoCo 环境不可用。请安装 mujoco（pip install mujoco）"
                    "或改用 --source dummy / scripted。"
                )
            self._env = self._env_cls(
                render=self.render,
                image_size=self.image_size,
                max_steps=self.max_steps,
            )
            self._env.reset()

    def reset(self, **kwargs) -> Dict[str, np.ndarray]:
        self._ensure_env()
        if self._env is not None:
            self._env.reset()
        self._step_count = 0
        return self.frame()

    def frame(self) -> Dict[str, np.ndarray]:
        self._ensure_env()
        if self._env is None:
            return {"image_wrist": np.zeros((*self.image_size, 3), np.uint8),
                    "state": np.zeros(6, np.float32)}
        obs = self._env._get_obs() if hasattr(self._env, "_get_obs") else self._env.reset()
        out: Dict[str, np.ndarray] = {"image_wrist": obs["image"], "state": obs["joint_positions"]}
        return out

    def step(self, action: np.ndarray) -> None:
        self._ensure_env()
        act = np.clip(np.asarray(action, dtype=np.float32), -1.0, 1.0)
        if self._env is not None and hasattr(self._env, "step"):
            self._env.step(act)
        self._step_count += 1

    def close(self):
        if self._env is not None and hasattr(self._env, "close"):
            self._env.close()
        self._env = None