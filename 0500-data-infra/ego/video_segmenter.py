"""
Ego 长视频有效操作片段切分
=========================
从 Ego 视角长视频（或手部关键点运动序列）中自动定位有效操作片段：

- 基于运动活性的滞回阈值检测（区分操作段与空闲段）
- 基于手部存在性的片段定位（可选）
- 片段合并、填充与最小长度过滤
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import numpy as np


@dataclass
class EgoSegment:
    """切分后的有效操作片段"""
    segment_id: str
    start_idx: int                 # 起始帧索引（含）
    end_idx: int                   # 结束帧索引（含）
    start_time: float              # 起始时间 (s)
    end_time: float                # 结束时间 (s)
    duration: float                # 时长 (s)
    active_ratio: float = 0.0      # 片段内运动活跃帧占比
    peak_motion: float = 0.0       # 片段内峰值运动量
    motion_stats: Dict[str, float] = field(default_factory=dict)  # mean/std/max
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def num_steps(self) -> int:
        return self.end_idx - self.start_idx + 1

    def to_dict(self) -> dict:
        return {
            "segment_id": self.segment_id,
            "start_idx": self.start_idx,
            "end_idx": self.end_idx,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration": self.duration,
            "active_ratio": self.active_ratio,
            "peak_motion": self.peak_motion,
            "motion_stats": self.motion_stats,
            "metadata": self.metadata,
        }


class EgoVideoSegmenter:
    """Ego 长视频有效片段切分器

    输入:
    - motion: (T,) 逐帧运动量序列（如手部中心位移、帧差幅度）
    - timestamps: (T,) 可选时间戳（秒），缺省按帧索引/30fps 估算
    - hand_presence: (T,) 可选手部可见性（概率或 0/1）

    策略:
    - 滞回阈值（high/low）避免临界抖动导致碎片化
    - 空闲段超过 min_idle_sec 才切分
    - 片段两侧 pad_sec 缓冲，保留接近动作的过渡帧
    """

    def __init__(
        self,
        motion_threshold: float = 0.02,      # 活跃判定阈值
        low_motion_ratio: float = 0.5,       # 滞回低阈值 = threshold * ratio
        min_active_sec: float = 2.0,         # 有效片段最小时长
        min_idle_sec: float = 1.0,           # 空闲多久才认为一段结束
        pad_sec: float = 0.3,                # 片段前后缓冲
        default_fps: float = 30.0,
        min_segment_len: int = 5,            # 最小片段帧数
    ):
        self.motion_threshold = motion_threshold
        self.low_motion_threshold = motion_threshold * low_motion_ratio
        self.min_active_sec = min_active_sec
        self.min_idle_sec = min_idle_sec
        self.pad_sec = pad_sec
        self.default_fps = default_fps
        self.min_segment_len = min_segment_len

    # ------------------------------------------------------------------
    # 运动量计算
    # ------------------------------------------------------------------
    @staticmethod
    def compute_motion_from_poses(hand_landmarks: np.ndarray) -> np.ndarray:
        """从手部关键点序列 (T, N, 2|3) 计算逐帧运动量

        使用手部中心点（全部关键点均值）的帧间位移作为运动量，
        对抖动更鲁棒；若关键点存在置信度列 (T, N, 3)，自动忽略。
        """
        pts = np.asarray(hand_landmarks, dtype=np.float64)
        if pts.ndim == 2:
            pts = pts[:, None, :]
        if pts.ndim != 3:
            raise ValueError(f"hand_landmarks must be (T, N, 2|3), got {pts.shape}")

        center = pts[:, :, :2].mean(axis=1)          # (T, 2)
        displacement = np.linalg.norm(np.diff(center, axis=0), axis=-1)
        return np.concatenate([[0.0], displacement])  # 与输入对齐 (T,)

    @staticmethod
    def compute_motion_from_frames(frames: np.ndarray, sample_step: int = 1) -> np.ndarray:
        """从灰度/彩色帧序列 (T, H, W[, C]) 计算帧差运动量"""
        arr = np.asarray(frames, dtype=np.float64)
        if arr.ndim == 4:
            gray = arr.mean(axis=-1)
        elif arr.ndim == 3:
            gray = arr
        else:
            raise ValueError(f"frames must be (T, H, W[, C]), got {arr.shape}")

        gray = gray[::sample_step]
        diff = np.abs(np.diff(gray, axis=0)).mean(axis=(1, 2))
        motion = np.zeros(len(arr))
        motion[::sample_step][1:] = diff
        return motion

    # ------------------------------------------------------------------
    # 主切分逻辑
    # ------------------------------------------------------------------
    def segment_by_motion(
        self,
        motion: np.ndarray,
        timestamps: Optional[np.ndarray] = None,
        hand_presence: Optional[np.ndarray] = None,
    ) -> List[EgoSegment]:
        """基于运动活性的片段切分"""
        motion = np.asarray(motion, dtype=np.float64)
        if motion.ndim != 1:
            raise ValueError(f"motion must be 1-D, got {motion.ndim}D")

        ts = self._resolve_timestamps(timestamps, len(motion))
        fps = 1.0 / (ts[1] - ts[0]) if len(ts) > 1 and ts[1] > ts[0] else self.default_fps

        # 1. 滞回阈值得到活跃掩码
        active = self._hysteresis_mask(motion)

        # 2. 可选: 手部不存在帧强制置为非活跃
        if hand_presence is not None:
            presence = np.asarray(hand_presence, dtype=np.float64)
            if len(presence) != len(motion):
                raise ValueError("hand_presence length must match motion")
            active = active & (presence > 0.5)

        # 3. 连续活跃段
        raw_segments = self._contiguous_active(active, ts)

        # 4. 过滤最小时长、合并过近片段
        segments = self._filter_and_merge(raw_segments, motion, ts, fps)

        # 5. 填充缓冲
        segments = self._apply_padding(segments, ts, fps)

        return segments

    def segment_by_hand_presence(
        self,
        hand_presence: np.ndarray,
        timestamps: Optional[np.ndarray] = None,
        min_sec: float = 2.0,
    ) -> List[EgoSegment]:
        """仅基于手部可见性切分（无需运动量）"""
        presence = np.asarray(hand_presence, dtype=np.float64)
        ts = self._resolve_timestamps(timestamps, len(presence))
        fps = 1.0 / (ts[1] - ts[0]) if len(ts) > 1 and ts[1] > ts[0] else self.default_fps

        active = presence > 0.5
        raw = self._contiguous_active(active, ts)
        motion = np.zeros(len(presence))
        return self._filter_and_merge(raw, motion, ts, fps)

    # ------------------------------------------------------------------
    # 内部工具
    # ------------------------------------------------------------------
    def _resolve_timestamps(self, timestamps: Optional[np.ndarray], n: int) -> np.ndarray:
        if timestamps is None:
            return np.arange(n) / self.default_fps
        ts = np.asarray(timestamps, dtype=np.float64)
        if len(ts) != n:
            raise ValueError(f"timestamps length {len(ts)} != frames {n}")
        return ts

    def _hysteresis_mask(self, motion: np.ndarray) -> np.ndarray:
        """滞回阈值状态机: 高于高阈值进入活跃，低于低阈值退出活跃"""
        high = self.motion_threshold
        low = self.low_motion_threshold
        active = np.zeros(len(motion), dtype=bool)
        state = False
        for i, m in enumerate(motion):
            if state:
                if m < low:
                    state = False
            else:
                if m > high:
                    state = True
            active[i] = state
        return active

    def _contiguous_active(
        self, active: np.ndarray, ts: np.ndarray
    ) -> List[EgoSegment]:
        """把连续活跃帧转为初步片段"""
        segments: List[EgoSegment] = []
        start = None
        for i, a in enumerate(active):
            if a and start is None:
                start = i
            elif not a and start is not None:
                segments.append(self._make_segment(start, i - 1, ts))
                start = None
        if start is not None:
            segments.append(self._make_segment(start, len(active) - 1, ts))
        return segments

    def _make_segment(self, start: int, end: int, ts: np.ndarray) -> EgoSegment:
        return EgoSegment(
            segment_id=f"ego_seg_{start:06d}_{end:06d}",
            start_idx=start,
            end_idx=end,
            start_time=float(ts[start]),
            end_time=float(ts[end]),
            duration=float(ts[end] - ts[start]),
        )

    def _filter_and_merge(
        self,
        segments: List[EgoSegment],
        motion: np.ndarray,
        ts: np.ndarray,
        fps: float,
    ) -> List[EgoSegment]:
        """过滤过短片段；两个片段之间空闲不足 min_idle_sec 则合并"""
        if not segments:
            return []

        min_len = max(self.min_segment_len, int(self.min_active_sec * fps))
        merged: List[EgoSegment] = []
        cur = segments[0]

        for nxt in segments[1:]:
            gap_sec = nxt.start_time - cur.end_time
            if gap_sec <= self.min_idle_sec:
                # 合并两段（连同间隙）
                cur = EgoSegment(
                    segment_id=f"{cur.segment_id}_{nxt.segment_id}",
                    start_idx=cur.start_idx,
                    end_idx=nxt.end_idx,
                    start_time=cur.start_time,
                    end_time=nxt.end_time,
                    duration=nxt.end_time - cur.start_time,
                )
            else:
                merged.append(cur)
                cur = nxt
        merged.append(cur)

        # 计算统计信息并过滤
        out: List[EgoSegment] = []
        for seg in merged:
            seg_motion = motion[seg.start_idx:seg.end_idx + 1]
            if len(seg_motion) == 0:
                continue
            seg.active_ratio = float((seg_motion > self.motion_threshold).mean())
            seg.peak_motion = float(seg_motion.max())
            seg.motion_stats = {
                "mean": float(seg_motion.mean()),
                "std": float(seg_motion.std()),
                "max": seg.peak_motion,
            }
            if seg.num_steps >= min_len:
                out.append(seg)
        return out

    def _apply_padding(
        self, segments: List[EgoSegment], ts: np.ndarray, fps: float
    ) -> List[EgoSegment]:
        """向片段两侧扩展 pad_sec，夹紧到 [0, len-1] 且不与相邻片段重叠"""
        pad_frames = int(self.pad_sec * fps)
        if pad_frames <= 0 or not segments:
            return segments

        n = len(ts)
        padded: List[EgoSegment] = []
        for i, seg in enumerate(segments):
            start = max(0, seg.start_idx - pad_frames)
            end = min(n - 1, seg.end_idx + pad_frames)
            # 不与前一片段重叠
            if padded:
                start = max(start, padded[-1].end_idx + 1)
            if end < start:
                continue
            padded.append(
                EgoSegment(
                    segment_id=seg.segment_id,
                    start_idx=start,
                    end_idx=end,
                    start_time=float(ts[start]),
                    end_time=float(ts[end]),
                    duration=float(ts[end] - ts[start]),
                    active_ratio=seg.active_ratio,
                    peak_motion=seg.peak_motion,
                    motion_stats=seg.motion_stats,
                    metadata=seg.metadata,
                )
            )
        return padded
