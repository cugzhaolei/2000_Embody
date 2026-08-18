"""
规则化自动标注器
================
无需人工/模型即可自动产出基础标签：

- 操作成败: 轨迹异常 + 动作合法性 + 深度有效性 联合判定
- 质量标签: 模糊 / 遮挡 / 静止无操作 / 轨迹跳变
- 阶段标签: 由 ego.action_phase 提供（可选）

设计为后处理流水线的一环：批量标注 Episode 并回写到元数据。
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

import numpy as np

from ..quality.image_quality import ImageQualityChecker
from ..quality.trajectory_check import TrajectoryChecker


class LabelType(str, Enum):
    SUCCESS = "success"                 # 操作成功
    FAILURE = "failure"                 # 操作失败
    QUALITY_BLUR = "quality_blur"       # 图像模糊
    QUALITY_OCCLUSION = "quality_occlusion"  # 遮挡/异常亮暗
    QUALITY_STATIC = "quality_static"   # 静止无操作
    TRAJECTORY_JUMP = "trajectory_jump" # 轨迹跳变


@dataclass
class AnnotationResult:
    """单个 Episode 的标注结果"""
    episode_id: str
    labels: Dict[str, Any] = field(default_factory=dict)   # 标签名 -> 值
    confidence: float = 1.0
    reasons: List[str] = field(default_factory=list)
    extra: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "episode_id": self.episode_id,
            "labels": self.labels,
            "confidence": self.confidence,
            "reasons": self.reasons,
            "extra": self.extra,
        }


class AutoLabeler:
    """规则化自动标注器"""

    def __init__(
        self,
        jump_threshold: float = 0.05,     # 轨迹跳变阈值（米/rad）
        blur_threshold: float = 50.0,
        static_active_ratio: float = 0.4, # 活跃帧占比低于该值 -> 静止
        occlusion_threshold: float = 0.8,
    ):
        self.jump_threshold = jump_threshold
        self.blur_threshold = blur_threshold
        self.static_active_ratio = static_active_ratio
        self.occlusion_threshold = occlusion_threshold
        self._img_checker = ImageQualityChecker(blur_threshold=blur_threshold)
        self._traj_checker = TrajectoryChecker(max_position_jump=jump_threshold)

    # ------------------------------------------------------------------
    def label_episode(
        self,
        episode_data: Dict[str, Any],
        episode_id: str = "ep",
        sample_frames: int = 10,
    ) -> AnnotationResult:
        """标注单个 Episode

        episode_data 支持字段:
        - eef_pose / joint_state: (T, D) 轨迹
        - action: (T, D) 动作
        - rgb / images: (T, H, W[, C]) 或帧列表
        - depth: (T, H, W) 深度图（检测无效值）
        - success: 外部给定成败（优先使用）
        """
        result = AnnotationResult(episode_id=episode_id)
        labels: Dict[str, Any] = {}
        reasons: List[str] = []
        confidence_scores: List[float] = []

        # ---- 轨迹检查 ----
        trajectory = episode_data.get("eef_pose", episode_data.get("joint_state"))
        if trajectory is not None:
            traj = np.asarray(trajectory)
            if traj.ndim == 2 and len(traj) >= 2:
                check = self._traj_checker.check(traj)
                labels["trajectory_ok"] = check.success
                if check.jump_count > 0:
                    labels["jump_count"] = check.jump_count
                    labels["label_trajectory_jump"] = True
                    reasons.append(f"trajectory jump x{check.jump_count}")
                else:
                    labels["label_trajectory_jump"] = False
                labels["smoothness"] = round(check.smoothness_score, 4)
                confidence_scores.append(1.0)

        # ---- 图像质量 ----
        frames = episode_data.get("rgb", episode_data.get("images"))
        if frames is not None and len(frames) > 0:
            arr = np.asarray(frames)
            if arr.ndim >= 3:
                sample_idx = np.linspace(0, len(arr) - 1, min(sample_frames, len(arr))).astype(int)
                blur_bad = 0
                occ_bad = 0
                for i in sample_idx:
                    metrics = self._img_checker.check_frame(arr[i])
                    if metrics["blur"] < self.blur_threshold:
                        blur_bad += 1
                    if self._img_checker.detect_camera_occlusion(arr[i]):
                        occ_bad += 1
                n = len(sample_idx)
                labels["blur_ratio"] = round(blur_bad / n, 3)
                labels["occlusion_ratio"] = round(occ_bad / n, 3)
                labels["label_quality_blur"] = blur_bad / n > 0.5
                labels["label_quality_occlusion"] = occ_bad / n > self.occlusion_threshold
                if labels["label_quality_blur"]:
                    reasons.append(f"blur ratio {labels['blur_ratio']:.2f}")
                if labels["label_quality_occlusion"]:
                    reasons.append(f"occlusion ratio {labels['occlusion_ratio']:.2f}")
                confidence_scores.append(0.9)

        # ---- 静止检测 ----
        if trajectory is not None:
            traj = np.asarray(trajectory)
            if traj.ndim == 2 and len(traj) >= 5:
                motion = np.linalg.norm(np.diff(traj, axis=0), axis=-1)
                active_ratio = float((motion > self.jump_threshold * 0.2).mean())
                labels["active_ratio"] = round(active_ratio, 3)
                labels["label_quality_static"] = active_ratio < self.static_active_ratio
                if labels["label_quality_static"]:
                    reasons.append(f"static/no-op (active {active_ratio:.2f})")
                confidence_scores.append(0.95)

        # ---- 成败判定 ----
        external = episode_data.get("success")
        if external is not None:
            labels["success"] = bool(external)
        else:
            # 规则判定: 无质量/轨迹异常即认为成功
            failed_flags = [
                labels.get(k, False) for k in (
                    "label_quality_blur", "label_quality_occlusion",
                    "label_quality_static", "label_trajectory_jump",
                )
            ]
            is_failure = any(failed_flags)
            labels["success"] = not is_failure
            if is_failure:
                reasons.append("rule-based failure: abnormal labels present")
        labels["label_success"] = labels["success"]
        labels["label_failure"] = not labels["success"]

        result.labels = labels
        result.reasons = reasons
        result.confidence = float(np.mean(confidence_scores)) if confidence_scores else 1.0
        return result

    # ------------------------------------------------------------------
    def label_batch(
        self,
        episodes: Dict[str, Dict[str, Any]],
    ) -> List[AnnotationResult]:
        """批量标注 {episode_id: episode_data}"""
        return [
            self.label_episode(data, episode_id=ep_id)
            for ep_id, data in episodes.items()
        ]

    def apply_to_metadata(self, episode_meta: Any, result: AnnotationResult) -> Any:
        """将标注结果回写 EpisodeMetadata（schemas.dataset.EpisodeMetadata）"""
        episode_meta.success = result.labels.get("success")
        if hasattr(episode_meta, "extra"):
            episode_meta.extra["auto_labels"] = result.labels
            episode_meta.extra["auto_label_reasons"] = result.reasons
            episode_meta.extra["auto_label_confidence"] = result.confidence
        return episode_meta
