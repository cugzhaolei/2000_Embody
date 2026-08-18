"""
动作阶段识别
============
对 Ego 操作片段进行动作阶段识别：

- IDLE        空闲/静止
- REACH       伸手接近目标（手张开、快速移动、接近目标）
- GRASP       抓取（手部闭合过程）
- MANIPULATE  操作/持握（手闭合、小幅调整）
- RELEASE     释放（手部张开过程）
- RETREAT     缩回（手张开、远离目标）

基于确定性状态机 + 启发式规则，输入为逐帧手部速度、手部开合度
（可选）以及目标接近度（可选）。
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

import numpy as np


class PhaseType(str, Enum):
    IDLE = "idle"
    REACH = "reach"
    GRASP = "grasp"
    MANIPULATE = "manipulate"
    RELEASE = "release"
    RETREAT = "retreat"


@dataclass
class PhaseSpan:
    """识别出的阶段片段"""
    phase: PhaseType
    start_idx: int
    end_idx: int
    start_time: float = 0.0
    end_time: float = 0.0
    confidence: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def num_steps(self) -> int:
        return self.end_idx - self.start_idx + 1

    def to_dict(self) -> dict:
        return {
            "phase": self.phase.value,
            "start_idx": self.start_idx,
            "end_idx": self.end_idx,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "confidence": self.confidence,
            "metadata": self.metadata,
        }


class ActionPhaseRecognizer:
    """动作阶段识别器

    启发式规则:
    1. 速度低于 static_threshold -> IDLE
    2. 速度较高且手张开:
       - 有目标接近度: 接近 -> REACH, 远离 -> RETREAT
       - 无目标信息: 运动起始半段 -> REACH, 后半段 -> RETREAT
    3. 手部开合度明显减小（闭合中）-> GRASP
    4. 手部开合度明显增大（张开中）-> RELEASE
    5. 手闭合且速度中等 -> MANIPULATE
    """

    def __init__(
        self,
        static_threshold: float = 0.01,      # 静止判定速度
        grasp_open_delta: float = 0.05,      # 开合度变化阈值（闭合/张开判定）
        delta_window: int = 3,               # 开合度变化计算窗口（帧），提高慢速动作鲁棒性
        min_phase_len: int = 3,              # 最小阶段帧数（后处理合并噪声）
        default_fps: float = 30.0,
    ):
        self.static_threshold = static_threshold
        self.grasp_open_delta = grasp_open_delta
        self.delta_window = max(1, delta_window)
        self.min_phase_len = min_phase_len
        self.default_fps = default_fps

    def recognize(
        self,
        hand_speed: np.ndarray,
        hand_openness: Optional[np.ndarray] = None,
        timestamps: Optional[np.ndarray] = None,
        object_proximity: Optional[np.ndarray] = None,
    ) -> List[PhaseSpan]:
        """逐帧识别动作阶段

        Args:
            hand_speed: (T,) 手部运动速度
            hand_openness: (T,) 可选，手部开合度 [0,1]，1 表示全张开
            timestamps: (T,) 可选时间戳
            object_proximity: (T,) 可选，与目标的接近度 [0,1]，
                             1 表示接触目标，0 表示远离
        """
        speed = np.asarray(hand_speed, dtype=np.float64)
        if speed.ndim != 1:
            raise ValueError(f"hand_speed must be 1-D, got {speed.ndim}D")

        openness = (
            np.asarray(hand_openness, dtype=np.float64)
            if hand_openness is not None else None
        )
        proximity = (
            np.asarray(object_proximity, dtype=np.float64)
            if object_proximity is not None else None
        )
        ts = (
            np.asarray(timestamps, dtype=np.float64)
            if timestamps is not None
            else np.arange(len(speed)) / self.default_fps
        )

        phases = np.empty(len(speed), dtype=object)
        n = len(speed)

        for i in range(n):
            phases[i] = self._classify_frame(
                i, speed, openness, proximity, n
            )

        # 平滑: 过滤孤立噪声帧
        phases = self._smooth(phases)

        return self._to_spans(phases, ts)

    # ------------------------------------------------------------------
    def _classify_frame(
        self,
        i: int,
        speed: np.ndarray,
        openness: Optional[np.ndarray],
        proximity: Optional[np.ndarray],
        n: int,
    ) -> PhaseType:
        if speed[i] < self.static_threshold:
            # 静止: 若手闭合可能是持握暂停，否则视为空闲
            if openness is not None and openness[i] < 0.5:
                return PhaseType.MANIPULATE
            return PhaseType.IDLE

        # 运动中的手部开合变化（窗口累计变化，鲁棒于慢速闭合/张开）
        if openness is not None:
            prev = max(0, i - self.delta_window)
            open_delta = openness[i] - openness[prev]
            # 闭合过程 -> GRASP
            if open_delta < -self.grasp_open_delta:
                return PhaseType.GRASP
            # 张开过程 -> RELEASE
            if open_delta > self.grasp_open_delta:
                return PhaseType.RELEASE
            # 手闭合持握 -> MANIPULATE
            if openness[i] < 0.5:
                return PhaseType.MANIPULATE

        # 手张开（或无限开合度信息）时区分接近/缩回
        if proximity is not None:
            if proximity[i] > proximity[max(0, i - 1)]:
                return PhaseType.REACH
            if proximity[i] < proximity[max(0, i - 1)]:
                return PhaseType.RETREAT

        # 无目标信息: 按运动位置粗略划分前半段接近、后半段缩回
        if i < n * 0.5:
            return PhaseType.REACH
        return PhaseType.RETREAT

    def _smooth(self, phases: np.ndarray) -> np.ndarray:
        """把短于 min_phase_len 的噪声阶段并入前一个阶段"""
        out = phases.copy()
        i = 0
        n = len(out)
        while i < n:
            j = i
            while j < n and out[j] == out[i]:
                j += 1
            length = j - i
            if length < self.min_phase_len and i > 0 and j < n:
                out[i:j] = out[i - 1]
            i = j
        return out

    def _to_spans(self, phases: np.ndarray, ts: np.ndarray) -> List[PhaseSpan]:
        spans: List[PhaseSpan] = []
        start = 0
        for i in range(1, len(phases) + 1):
            if i == len(phases) or phases[i] != phases[start]:
                spans.append(
                    PhaseSpan(
                        phase=PhaseType(phases[start]),
                        start_idx=start,
                        end_idx=i - 1,
                        start_time=float(ts[start]),
                        end_time=float(ts[i - 1]),
                    )
                )
                start = i
        return spans
