"""
图像质量检查
===========
自动检测图像模糊度、亮度、对比度、遮挡等问题。
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np


@dataclass
class ImageQualityReport:
    """图像质量报告"""
    frame_count: int = 0
    blur_scores: List[float] = field(default_factory=list)
    brightness_scores: List[float] = field(default_factory=list)
    contrast_scores: List[float] = field(default_factory=list)
    resolution_issues: int = 0
    corrupted_frames: int = 0
    overall_score: float = 0.0
    issues: List[str] = field(default_factory=list)


class ImageQualityChecker:
    """图像质量自动检测器

    检测维度:
    - 模糊度 (Laplacian 方差)
    - 亮度 (平均像素值)
    - 对比度 (标准差)
    - 分辨率一致性
    - 数据完整性
    """

    def __init__(
        self,
        blur_threshold: float = 50.0,
        brightness_min: float = 10.0,
        brightness_max: float = 245.0,
        contrast_min: float = 20.0,
    ):
        self.blur_threshold = blur_threshold
        self.brightness_min = brightness_min
        self.brightness_max = brightness_max
        self.contrast_min = contrast_min

    def check_frame(self, frame: np.ndarray) -> Dict[str, float]:
        """检查单帧质量"""
        if frame.ndim == 3:
            gray = frame.mean(axis=-1).astype(np.float64)
        else:
            gray = frame.astype(np.float64)

        return {
            "blur": self._compute_blur(gray),
            "brightness": float(gray.mean()),
            "contrast": float(gray.std()),
        }

    def check_sequence(
        self, frames: np.ndarray, sample_rate: int = 1
    ) -> ImageQualityReport:
        """检查帧序列质量"""
        report = ImageQualityReport()

        if not isinstance(frames, np.ndarray) or frames.ndim < 3:
            report.issues.append("Invalid frame data format")
            return report

        indices = range(0, len(frames), sample_rate)
        report.frame_count = len(frames)

        for i in indices:
            frame = frames[i]
            metrics = self.check_frame(frame)

            report.blur_scores.append(metrics["blur"])
            report.brightness_scores.append(metrics["brightness"])
            report.contrast_scores.append(metrics["contrast"])

            # 检查问题
            if metrics["blur"] < self.blur_threshold:
                report.issues.append(f"Frame {i}: blurry (score={metrics['blur']:.1f})")

            if metrics["brightness"] < self.brightness_min:
                report.issues.append(f"Frame {i}: too dark (brightness={metrics['brightness']:.1f})")
            elif metrics["brightness"] > self.brightness_max:
                report.issues.append(f"Frame {i}: too bright (brightness={metrics['brightness']:.1f})")

            if metrics["contrast"] < self.contrast_min:
                report.issues.append(f"Frame {i}: low contrast (contrast={metrics['contrast']:.1f})")

        # 检查分辨率一致性
        ref_shape = frames[0].shape
        for i in indices:
            if frames[i].shape != ref_shape:
                report.resolution_issues += 1

        # 综合评分
        scores = []
        if report.blur_scores:
            blur_pass_ratio = sum(1 for s in report.blur_scores if s >= self.blur_threshold) / len(report.blur_scores)
            scores.append(blur_pass_ratio)
        if report.brightness_scores:
            bright_pass_ratio = sum(
                1 for s in report.brightness_scores
                if self.brightness_min <= s <= self.brightness_max
            ) / len(report.brightness_scores)
            scores.append(bright_pass_ratio)
        if report.contrast_scores:
            contrast_pass_ratio = sum(1 for s in report.contrast_scores if s >= self.contrast_min) / len(report.contrast_scores)
            scores.append(contrast_pass_ratio)

        report.overall_score = np.mean(scores) if scores else 0.0

        return report

    @staticmethod
    def _compute_blur(gray: np.ndarray) -> float:
        """计算图像模糊度评分"""
        laplacian = np.array([[0, 1, 0], [1, -4, 1], [0, 1, 0]], dtype=np.float64)
        try:
            from scipy.ndimage import convolve
            filtered = convolve(gray, laplacian)
            return float(np.var(filtered))
        except ImportError:
            # 简化版 Laplacian
            h, w = gray.shape
            if h < 3 or w < 3:
                return 100.0
            lap = (
                gray[1:-1, 1:-1] * 4
                - gray[:-2, 1:-1] - gray[2:, 1:-1]
                - gray[1:-1, :-2] - gray[1:-1, 2:]
            )
            return float(np.var(lap))

    @staticmethod
    def detect_camera_occlusion(frame: np.ndarray, threshold: float = 0.8) -> bool:
        """检测相机遮挡"""
        if frame.ndim == 3:
            gray = frame.mean(axis=-1)
        else:
            gray = frame

        dark_ratio = (gray < 10).mean()
        bright_ratio = (gray > 245).mean()
        return dark_ratio > threshold or bright_ratio > threshold
