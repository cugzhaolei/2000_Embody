"""
Episode 切分模块
===============
将连续录制的数据流切分为独立的 Episode，支持按时间、动作、事件切分。
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np


class SplitMethod(str, Enum):
    """Episode 切分方法"""
    TIME = "time"           # 按固定时长切分
    ACTION = "action"       # 按动作变化切分
    GAP = "gap"             # 按数据间隔切分
    EVENT = "event"         # 按事件标记切分
    CUSTOM = "custom"       # 自定义切分函数


@dataclass
class EpisodeSplitConfig:
    """Episode 切分配置"""
    method: SplitMethod = SplitMethod.TIME
    min_episode_length: int = 10           # 最小 Episode 长度 (帧)
    max_episode_length: int = 10000        # 最大 Episode 长度
    gap_threshold_sec: float = 0.5         # 间隔切分阈值 (秒)
    time_window_sec: float = 10.0          # 固定时长窗口 (秒)
    action_threshold: float = 0.1          # 动作变化阈值
    overlap_ratio: float = 0.0            # 切分重叠比例


@dataclass
class EpisodeSegment:
    """切分后的 Episode 片段"""
    episode_id: str
    start_idx: int
    end_idx: int
    start_time: float
    end_time: float
    duration: float
    num_steps: int
    success: Optional[bool] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class EpisodeSegmenter:
    """Episode 语义切分器

    将长序列数据切分为有意义的操作片段:
    - 按操作阶段切分 (approach -> grasp -> lift -> place)
    - 按操作成功/失败标记
    - 按动作模式变化检测
    """

    def __init__(self, config: Optional[EpisodeSplitConfig] = None):
        self.config = config or EpisodeSplitConfig()

    def segment_by_time(
        self,
        timestamps: np.ndarray,
        window_sec: float = 10.0,
    ) -> List[EpisodeSegment]:
        """按时间窗口切分"""
        segments = []
        start = timestamps[0]
        idx = 0

        while idx < len(timestamps):
            window_start = timestamps[idx]
            window_end = window_start + window_sec

            # 找到窗口结束位置
            end_idx = idx
            while end_idx < len(timestamps) and timestamps[end_idx] < window_end:
                end_idx += 1
            end_idx = min(end_idx, len(timestamps) - 1)

            if end_idx - idx >= self.config.min_episode_length:
                seg = EpisodeSegment(
                    episode_id=f"ep_time_{len(segments):04d}",
                    start_idx=idx,
                    end_idx=end_idx,
                    start_time=float(timestamps[idx]),
                    end_time=float(timestamps[end_idx]),
                    duration=float(timestamps[end_idx] - timestamps[idx]),
                    num_steps=end_idx - idx,
                )
                segments.append(seg)

            idx = end_idx + 1

        return segments

    def segment_by_gap(
        self,
        timestamps: np.ndarray,
        gap_threshold_sec: float = 0.5,
    ) -> List[EpisodeSegment]:
        """按数据间隔切分（连续录制中断）"""
        if len(timestamps) < 2:
            return []

        gaps = np.diff(timestamps)
        split_indices = np.where(gaps > gap_threshold_sec)[0] + 1

        boundaries = [0] + list(split_indices) + [len(timestamps)]
        segments = []

        for i in range(len(boundaries) - 1):
            start = boundaries[i]
            end = boundaries[i + 1]

            if end - start >= self.config.min_episode_length:
                seg = EpisodeSegment(
                    episode_id=f"ep_gap_{i:04d}",
                    start_idx=start,
                    end_idx=end,
                    start_time=float(timestamps[start]),
                    end_time=float(timestamps[end]),
                    duration=float(timestamps[end] - timestamps[start]),
                    num_steps=end - start,
                )
                segments.append(seg)

        return segments

    def segment_by_action_change(
        self,
        actions: np.ndarray,
        timestamps: np.ndarray,
        threshold: float = 0.1,
    ) -> List[EpisodeSegment]:
        """按动作模式变化切分"""
        if len(actions) < 2:
            return []

        # 计算动作变化幅度
        action_diff = np.abs(np.diff(actions, axis=0)).sum(axis=-1)
        # 平滑
        window = min(10, len(action_diff) // 3)
        if window > 1:
            kernel = np.ones(window) / window
            action_diff = np.convolve(action_diff, kernel, mode="same")

        # 检测静止段 (动作变化低于阈值)
        is_static = action_diff < threshold

        # 找到从运动到静止的转换点
        split_points = []
        for i in range(1, len(is_static)):
            if is_static[i - 1] and not is_static[i]:
                split_points.append(i)
            elif not is_static[i - 1] and is_static[i]:
                split_points.append(i)

        if not split_points:
            return [EpisodeSegment(
                episode_id="ep_action_0000",
                start_idx=0,
                end_idx=len(actions) - 1,
                start_time=float(timestamps[0]),
                end_time=float(timestamps[-1]),
                duration=float(timestamps[-1] - timestamps[0]),
                num_steps=len(actions),
            )]

        boundaries = [0] + split_points + [len(actions)]
        segments = []

        for i in range(len(boundaries) - 1):
            start = boundaries[i]
            end = boundaries[i + 1]
            if end - start >= self.config.min_episode_length:
                seg = EpisodeSegment(
                    episode_id=f"ep_action_{i:04d}",
                    start_idx=start,
                    end_idx=end,
                    start_time=float(timestamps[start]),
                    end_time=float(timestamps[end]),
                    duration=float(timestamps[end] - timestamps[start]),
                    num_steps=end - start,
                )
                segments.append(seg)

        return segments

    def segment_by_custom_function(
        self,
        data: Dict[str, Any],
        split_fn: Callable[[Dict[str, Any], int], bool],
    ) -> List[EpisodeSegment]:
        """使用自定义函数切分"""
        timestamps = data.get("timestamps", np.arange(len(next(iter(data.values())))))
        total_len = len(timestamps)

        split_points = [0]
        for i in range(1, total_len):
            frame_data = {k: v[i] if hasattr(v, '__getitem__') else v for k, v in data.items()}
            if split_fn(frame_data, i):
                split_points.append(i)
        split_points.append(total_len)

        segments = []
        for i in range(len(split_points) - 1):
            start, end = split_points[i], split_points[i + 1]
            if end - start >= self.config.min_episode_length:
                seg = EpisodeSegment(
                    episode_id=f"ep_custom_{i:04d}",
                    start_idx=start,
                    end_idx=end,
                    start_time=float(timestamps[start]),
                    end_time=float(timestamps[end - 1]),
                    duration=float(timestamps[end - 1] - timestamps[start]),
                    num_steps=end - start,
                )
                segments.append(seg)

        return segments


class EpisodeSplitter:
    """Episode 拆分工具

    将切分后的 Episode 片段提取为独立的数据块。
    """

    @staticmethod
    def extract_episode(
        episode_data: Dict[str, np.ndarray],
        segment: EpisodeSegment,
    ) -> Dict[str, np.ndarray]:
        """提取单个 Episode 的数据"""
        extracted = {}
        for key, data in episode_data.items():
            if isinstance(data, np.ndarray):
                extracted[key] = data[segment.start_idx:segment.end_idx]
            else:
                extracted[key] = data
        return extracted

    @staticmethod
    def split_dataset(
        episode_data: Dict[str, np.ndarray],
        segments: List[EpisodeSegment],
    ) -> List[Dict[str, np.ndarray]]:
        """将完整数据集拆分为多个 Episode"""
        return [
            EpisodeSplitter.extract_episode(episode_data, seg)
            for seg in segments
        ]

    @staticmethod
    def merge_episodes(
        episodes: List[Dict[str, np.ndarray]],
    ) -> Dict[str, np.ndarray]:
        """合并多个 Episode 为连续数据"""
        merged = {}
        for key in episodes[0]:
            arrays = [ep[key] for ep in episodes if key in ep]
            if arrays and isinstance(arrays[0], np.ndarray):
                merged[key] = np.concatenate(arrays, axis=0)
            else:
                merged[key] = arrays[-1] if arrays else None
        return merged
