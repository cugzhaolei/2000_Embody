"""
流水线质量检查
=============
对处理后的数据进行完整性、一致性、质量检查。
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np


@dataclass
class QualityCheckResult:
    """质量检查结果"""
    check_name: str
    passed: bool
    score: float  # 0~1
    details: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class QualityReport:
    """质量检查报告"""
    episode_id: str
    total_checks: int = 0
    passed_checks: int = 0
    failed_checks: int = 0
    overall_score: float = 0.0
    results: List[QualityCheckResult] = field(default_factory=list)
    summary: str = ""

    def add_result(self, result: QualityCheckResult) -> None:
        self.results.append(result)
        self.total_checks += 1
        if result.passed:
            self.passed_checks += 1
        else:
            self.failed_checks += 1
        self._update_score()

    def _update_score(self) -> None:
        if self.results:
            self.overall_score = np.mean([r.score for r in self.results])
        if self.overall_score >= 0.8:
            self.summary = "GOOD"
        elif self.overall_score >= 0.5:
            self.summary = "FAIR"
        else:
            self.summary = "POOR"


class PipelineQualityChecker:
    """流水线质量检查器

    检查维度:
    1. 时间同步误差
    2. 数据完整性
    3. 轨迹连续性
    4. 图像质量
    5. 动作合理性
    6. 数据一致性
    """

    def __init__(self, sync_tolerance_ms: float = 10.0):
        self.sync_tolerance_ms = sync_tolerance_ms

    def check_episode(
        self,
        episode_data: Dict[str, Any],
        episode_id: str = "unknown",
    ) -> QualityReport:
        """对一个 Episode 执行全面质量检查"""
        report = QualityReport(episode_id=episode_id)

        # 1. 数据完整性检查
        report.add_result(self._check_completeness(episode_data))

        # 2. 时间同步检查
        if "timestamps" in episode_data:
            report.add_result(self._check_time_sync(episode_data["timestamps"]))

        # 3. 轨迹连续性检查
        if "eef_pose" in episode_data:
            report.add_result(self._check_trajectory_continuity(episode_data["eef_pose"]))

        # 4. 图像质量检查
        if "rgb" in episode_data:
            report.add_result(self._check_image_quality(episode_data["rgb"]))

        # 5. 深度数据检查
        if "depth" in episode_data:
            report.add_result(self._check_depth_quality(episode_data["depth"]))

        # 6. 动作合理性检查
        if "action" in episode_data:
            report.add_result(self._check_action_validity(episode_data["action"]))

        # 7. 关节限位检查
        if "joint_state" in episode_data:
            report.add_result(self._check_joint_limits(episode_data["joint_state"]))

        # 8. 数据维度一致性
        report.add_result(self._check_dimension_consistency(episode_data))

        return report

    def _check_completeness(self, data: Dict[str, Any]) -> QualityCheckResult:
        """数据完整性检查"""
        required_keys = ["rgb", "eef_pose", "action"]
        present = [k for k in required_keys if k in data and data[k] is not None]
        missing = [k for k in required_keys if k not in present]

        score = len(present) / len(required_keys) if required_keys else 1.0
        return QualityCheckResult(
            check_name="completeness",
            passed=len(missing) == 0,
            score=score,
            details=f"Missing: {missing}" if missing else "All required modalities present",
        )

    def _check_time_sync(self, timestamps: np.ndarray) -> QualityCheckResult:
        """时间同步检查"""
        if len(timestamps) < 2:
            return QualityCheckResult("time_sync", True, 1.0, "Single timestamp")

        dt = np.diff(timestamps)
        median_dt = np.median(dt)
        max_deviation_ms = np.abs(dt - median_dt).max() * 1000

        passed = max_deviation_ms < self.sync_tolerance_ms
        score = max(0.0, 1.0 - max_deviation_ms / (self.sync_tolerance_ms * 2))

        return QualityCheckResult(
            check_name="time_sync",
            passed=passed,
            score=score,
            details=f"Max deviation: {max_deviation_ms:.2f}ms (tolerance: {self.sync_tolerance_ms}ms)",
            metadata={"max_deviation_ms": float(max_deviation_ms), "median_dt": float(median_dt)},
        )

    def _check_trajectory_continuity(self, eef_pose: np.ndarray) -> QualityCheckResult:
        """轨迹连续性检查"""
        if eef_pose.ndim != 2 or len(eef_pose) < 2:
            return QualityCheckResult("trajectory_continuity", True, 1.0)

        diffs = np.abs(np.diff(eef_pose[:, :3], axis=0))
        max_jump = diffs.max()
        mean_jump = diffs.mean()

        # 跳变阈值 (5cm)
        jump_threshold = 0.05
        num_jumps = (diffs > jump_threshold).any(axis=1).sum()

        score = max(0.0, 1.0 - num_jumps / max(len(diffs), 1))
        passed = num_jumps == 0

        return QualityCheckResult(
            check_name="trajectory_continuity",
            passed=passed,
            score=score,
            details=f"Max jump: {max_jump*1000:.1f}mm, jumps: {num_jumps}/{len(diffs)}",
            metadata={"max_jump_m": float(max_jump), "num_jumps": int(num_jumps)},
        )

    def _check_image_quality(self, images: np.ndarray) -> QualityCheckResult:
        """图像质量检查"""
        if not isinstance(images, np.ndarray) or images.ndim < 3:
            return QualityCheckResult("image_quality", True, 0.5, "Non-array image data")

        num_frames = len(images)
        blur_scores = []
        brightness_scores = []

        # 采样检查 (避免太慢)
        sample_indices = np.linspace(0, num_frames - 1, min(20, num_frames)).astype(int)

        for i in sample_indices:
            frame = images[i]
            gray = frame.mean(axis=-1) if frame.ndim == 3 else frame
            brightness_scores.append(float(gray.mean()))

            # 简单 Laplacian 方差作为模糊度
            laplacian = np.array([[0, 1, 0], [1, -4, 1], [0, 1, 0]])
            try:
                from scipy.ndimage import convolve
                filtered = convolve(gray.astype(np.float64), laplacian)
                blur_scores.append(float(np.var(filtered)))
            except ImportError:
                blur_scores.append(100.0)

        avg_blur = np.mean(blur_scores)
        avg_brightness = np.mean(brightness_scores)

        blur_ok = avg_blur > 50
        brightness_ok = 10 < avg_brightness < 245

        score = (blur_ok + brightness_ok) / 2
        return QualityCheckResult(
            check_name="image_quality",
            passed=blur_ok and brightness_ok,
            score=score,
            details=f"Avg blur: {avg_blur:.1f}, avg brightness: {avg_brightness:.1f}",
            metadata={"avg_blur": avg_blur, "avg_brightness": avg_brightness},
        )

    def _check_depth_quality(self, depth: np.ndarray) -> QualityCheckResult:
        """深度数据质量检查"""
        if not isinstance(depth, np.ndarray):
            return QualityCheckResult("depth_quality", True, 0.5)

        total_pixels = depth.size
        invalid_pixels = (depth <= 0).sum()
        invalid_ratio = invalid_pixels / total_pixels

        passed = invalid_ratio < 0.3
        score = max(0.0, 1.0 - invalid_ratio)

        return QualityCheckResult(
            check_name="depth_quality",
            passed=passed,
            score=score,
            details=f"Invalid depth ratio: {invalid_ratio*100:.1f}%",
            metadata={"invalid_ratio": float(invalid_ratio)},
        )

    def _check_action_validity(self, actions: np.ndarray) -> QualityCheckResult:
        """动作合理性检查"""
        if not isinstance(actions, np.ndarray) or actions.ndim != 2:
            return QualityCheckResult("action_validity", True, 0.5)

        # 检查 NaN/Inf
        has_nan = np.isnan(actions).any()
        has_inf = np.isinf(actions).any()

        # 检查动作范围
        max_val = np.abs(actions).max()
        range_ok = max_val < 10.0

        # 检查动作突变
        diffs = np.abs(np.diff(actions, axis=0))
        max_diff = diffs.max() if len(diffs) > 0 else 0
        smoothness_ok = max_diff < 2.0

        score = (not has_nan) * 0.4 + (not has_inf) * 0.2 + range_ok * 0.2 + smoothness_ok * 0.2
        passed = not has_nan and not has_inf and range_ok

        return QualityCheckResult(
            check_name="action_validity",
            passed=passed,
            score=score,
            details=f"NaN: {has_nan}, Inf: {has_inf}, max_val: {max_val:.3f}, max_diff: {max_diff:.3f}",
        )

    def _check_joint_limits(self, joint_states: np.ndarray) -> QualityCheckResult:
        """关节限位检查"""
        if not isinstance(joint_states, np.ndarray):
            return QualityCheckResult("joint_limits", True, 0.5)

        # 通用关节限位 (弧度)
        limit = np.pi
        violations = (np.abs(joint_states) > limit).sum()
        total = joint_states.size
        violation_ratio = violations / total if total > 0 else 0

        passed = violation_ratio < 0.01
        score = max(0.0, 1.0 - violation_ratio * 10)

        return QualityCheckResult(
            check_name="joint_limits",
            passed=passed,
            score=score,
            details=f"Joint limit violations: {violations}/{total} ({violation_ratio*100:.2f}%)",
        )

    def _check_dimension_consistency(self, data: Dict[str, Any]) -> QualityCheckResult:
        """数据维度一致性检查"""
        lengths = {}
        for key, val in data.items():
            if isinstance(val, np.ndarray) and val.ndim >= 1:
                lengths[key] = len(val)

        if len(lengths) < 2:
            return QualityCheckResult("dimension_consistency", True, 1.0)

        unique_lengths = set(lengths.values())
        consistent = len(unique_lengths) <= 1

        if not consistent:
            # 找出不一致的模态
            most_common = max(set(lengths.values()), key=list(lengths.values()).count)
            mismatched = {k: v for k, v in lengths.items() if v != most_common}
            details = f"Inconsistent lengths: {mismatched} (most common: {most_common})"
        else:
            details = f"All modalities have consistent length: {list(lengths.values())[0]}"

        return QualityCheckResult(
            check_name="dimension_consistency",
            passed=consistent,
            score=1.0 if consistent else 0.5,
            details=details,
        )

    def batch_check(
        self, episodes: List[Dict[str, Any]], episode_ids: Optional[List[str]] = None
    ) -> List[QualityReport]:
        """批量质量检查"""
        if episode_ids is None:
            episode_ids = [f"ep_{i:04d}" for i in range(len(episodes))]

        return [
            self.check_episode(ep, eid)
            for ep, eid in zip(episodes, episode_ids)
        ]
