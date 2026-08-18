"""
异常片段过滤
============
对切分出的 Ego 片段做自动异常检测，过滤不适合训练的数据：

- 静止/无操作 (no-op): 片段内有效运动占比过低
- 画面模糊: 帧模糊度低于阈值（采样帧方差-Laplacian）
- 相机遮挡/极端亮暗: 复用 ImageQualityChecker 的遮挡检测
- 运动异常抖动: 峰值运动超出合理范围
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

import numpy as np

from ..quality.image_quality import ImageQualityChecker
from .video_segmenter import EgoSegment


class FilterVerdict(str, Enum):
    KEEP = "keep"
    DISCARD = "discard"


@dataclass
class AbnormalFilterResult:
    """单个片段的过滤结果"""
    segment_id: str
    verdict: FilterVerdict
    reasons: List[str] = field(default_factory=list)
    scores: Dict[str, float] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "segment_id": self.segment_id,
            "verdict": self.verdict.value,
            "reasons": self.reasons,
            "scores": self.scores,
            "metadata": self.metadata,
        }


class EgoAbnormalFilter:
    """Ego 片段异常过滤器"""

    def __init__(
        self,
        blur_threshold: float = 50.0,        # 模糊度阈值（与 ImageQualityChecker 一致）
        static_ratio_max: float = 0.4,       # 片段内活跃帧占比下限
        peak_motion_max: Optional[float] = None,  # 峰值运动上限（防抖动/异常）
        occlusion_threshold: float = 0.8,    # 遮挡帧占比阈值
        frame_sample: int = 10,              # 每片段采样的帧数
    ):
        self.blur_threshold = blur_threshold
        self.static_ratio_max = static_ratio_max
        self.peak_motion_max = peak_motion_max
        self.occlusion_threshold = occlusion_threshold
        self.frame_sample = frame_sample
        self._img_checker = ImageQualityChecker(blur_threshold=blur_threshold)

    def check_segment(
        self,
        segment: EgoSegment,
        motion: Optional[np.ndarray] = None,
        frames: Optional[np.ndarray] = None,
    ) -> AbnormalFilterResult:
        """检查单个片段

        Args:
            segment: 待检查片段
            motion: (T,) 可选，全序列运动量（用于活跃占比）
            frames: (T, H, W[, C]) 可选，全序列帧（用于模糊/遮挡检测）
        """
        scores: Dict[str, float] = {}
        reasons: List[str] = []

        # 1. 静止/无操作检测
        active_ratio = None
        if motion is not None:
            seg_motion = motion[segment.start_idx:segment.end_idx + 1]
            active_ratio = float((seg_motion > 0.02).mean())
            scores["active_ratio"] = active_ratio
            if active_ratio < self.static_ratio_max:
                reasons.append(
                    f"no-op: active_ratio={active_ratio:.2f} < {self.static_ratio_max:.2f}"
                )

            if self.peak_motion_max is not None and segment.peak_motion > self.peak_motion_max:
                reasons.append(
                    f"abnormal motion peak: {segment.peak_motion:.3f} > {self.peak_motion_max:.3f}"
                )

        # 2. 模糊度检测（采样帧）
        if frames is not None and frames.ndim >= 3:
            idx = np.linspace(
                segment.start_idx, segment.end_idx, self.frame_sample
            ).astype(int)
            idx = np.clip(idx, 0, len(frames) - 1)
            blur_scores = [self._img_checker.check_frame(frames[i])["blur"] for i in idx]
            blur_ratio_bad = float(np.mean([b < self.blur_threshold for b in blur_scores]))
            scores["blur_ratio_bad"] = blur_ratio_bad
            if blur_ratio_bad > 0.5:
                reasons.append(
                    f"blurry frames: {blur_ratio_bad:.0%} below threshold {self.blur_threshold}"
                )

        # 3. 遮挡/极端亮暗检测
        if frames is not None and frames.ndim >= 3:
            occlusion_ratio = float(np.mean([
                self._img_checker.detect_camera_occlusion(frames[i])
                for i in idx
            ]))
            scores["occlusion_ratio"] = occlusion_ratio
            if occlusion_ratio > self.occlusion_threshold:
                reasons.append(
                    f"occlusion: {occlusion_ratio:.0%} frames occluded"
                )

        verdict = FilterVerdict.DISCARD if reasons else FilterVerdict.KEEP
        return AbnormalFilterResult(
            segment_id=segment.segment_id,
            verdict=verdict,
            reasons=reasons,
            scores=scores,
        )

    def filter_segments(
        self,
        segments: List[EgoSegment],
        motion: Optional[np.ndarray] = None,
        frames: Optional[np.ndarray] = None,
    ) -> (List[EgoSegment], List[AbnormalFilterResult]):
        """批量过滤，返回 (保留片段, 全部检查结果)"""
        kept: List[EgoSegment] = []
        results: List[AbnormalFilterResult] = []
        for seg in segments:
            result = self.check_segment(seg, motion=motion, frames=frames)
            results.append(result)
            if result.verdict == FilterVerdict.KEEP:
                kept.append(seg)
        return kept, results
