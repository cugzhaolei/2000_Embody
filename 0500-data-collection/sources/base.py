"""
数据源抽象基类
==============
定义 Recorder 期望的 Source 接口：

  reset(**kwargs)       重置/初始化场景
  frame() -> dict       返回当前观测: {"image_*": np.ndarray 或 state: np.ndarray}
  step(action)          使环境前进一步（记录相对动作）
  close()               清理资源

约定:
  frame() 返回 dict，其中:
    - 键以 "image" 开头:  视为相机图像 [H, W, 3]
    - 键 "state" 或 "joint_positions": 本体状态向量
"""

from __future__ import annotations

from typing import Any, Dict

import numpy as np


class DataSource:
    """所有数据源的基类。"""

    name = "base"

    def reset(self, **kwargs) -> Dict[str, np.ndarray]:
        """重置环境初始状态，返回首帧观测。"""
        raise NotImplementedError

    def frame(self) -> Dict[str, np.ndarray]:
        """返回当前观测帧 dict。"""
        raise NotImplementedError

    def step(self, action: np.ndarray) -> None:
        """执行动作步。"""
        raise NotImplementedError

    def close(self):
        """释放资源。"""
        pass


class ScriptedExpertSource(DataSource):
    """脚本化专家源: 自动生成抓取轨迹，无需人工。

    通过 callback 注入专家策略动作序列生成器，
    便于复用 0200-vla-imitation/envs 里的 ScriptedExpert。
    """

    name = "scripted"

    def __init__(
        self,
        expert_actions_fn,
        frame_fn,
        step_fn,
        reset_fn=None,
        close_fn=None,
        action_dim: int = 7,
    ):
        """
        Args:
            expert_actions_fn: () -> list[np.ndarray] 生成一条完整动作序列
            frame_fn: () -> dict  取当前帧
            step_fn: callable(action)  步进
            reset_fn: () -> None      重置
        """
        self._gen = expert_actions_fn
        self._frame = frame_fn
        self._step = step_fn
        self._reset = reset_fn or (lambda: None)
        self._close = close_fn or (lambda: None)
        self.action_dim = action_dim
        self._actions: list = []

    def reset(self, **kwargs) -> Dict[str, np.ndarray]:
        self._reset()
        self._actions = list(self._gen())
        return self.frame()

    def frame(self) -> Dict[str, np.ndarray]:
        return self._frame()

    def step(self, action: np.ndarray) -> None:
        self._step(action)


class DummySource(DataSource):
    """纯随机源（冒烟测试用），模拟固定频率的观测与动作流。"""

    name = "dummy"

    def __init__(self, image_size=(64, 64), state_dim=6, action_dim=7, seed=0):
        self.image_size = image_size
        self.state_dim = state_dim
        self.action_dim = action_dim
        self.rng = np.random.default_rng(seed)
        self._action = np.zeros(action_dim, dtype=np.float32)
        self._state = np.zeros(state_dim, dtype=np.float32)

    def reset(self, **kwargs) -> Dict[str, np.ndarray]:
        self._state = self.rng.uniform(-1, 1, size=self.state_dim).astype(np.float32)
        self._action = np.zeros(self.action_dim, dtype=np.float32)
        return self.frame()

    def frame(self) -> Dict[str, np.ndarray]:
        return {
            "image_wrist": self.rng.integers(0, 255, (*self.image_size, 3), dtype=np.uint8),
            "state": self._state.copy(),
        }

    def step(self, action: np.ndarray) -> None:
        self._action = np.asarray(action, dtype=np.float32)
        self._state = self._state + self.rng.normal(0, 0.01, size=self.state_dim)