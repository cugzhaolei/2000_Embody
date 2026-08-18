"""
数据清洗模块
===========
数据质量检查、异常值过滤、缺失值处理、数据规范化。
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np


class CleaningAction(str, Enum):
    """清洗操作类型"""
    REMOVE = "remove"           # 删除异常帧
    INTERPOLATE = "interpolate" # 插值填充
    CLIP = "clip"               # 裁剪到合法范围
    SMOOTH = "smooth"           # 平滑处理
    FLAG = "flag"               # 仅标记不修改


@dataclass
class CleaningRule:
    """单条清洗规则"""
    name: str
    modality: str               # 适用的数据模态
    action: CleaningAction
    check_fn: Callable[[Any], bool] = None  # 异常检测函数
    params: Dict[str, Any] = field(default_factory=dict)
    description: str = ""

    def apply(self, data: Any) -> Tuple[Any, bool]:
        """应用规则，返回 (处理后数据, 是否异常)"""
        if self.check_fn is None:
            return data, False

        is_anomaly = self.check_fn(data)
        if not is_anomaly:
            return data, False

        if self.action == CleaningAction.REMOVE:
            return None, True
        elif self.action == CleaningAction.CLIP:
            lo = self.params.get("min", -np.inf)
            hi = self.params.get("max", np.inf)
            return np.clip(data, lo, hi), True
        elif self.action == CleaningAction.INTERPOLATE:
            return data, True  # 需要外部处理插值
        elif self.action == CleaningAction.SMOOTH:
            window = self.params.get("window", 5)
            return self._smooth(data, window), True
        elif self.action == CleaningAction.FLAG:
            return data, True

        return data, False

    @staticmethod
    def _smooth(data: np.ndarray, window: int) -> np.ndarray:
        if data.ndim == 1:
            kernel = np.ones(window) / window
            return np.convolve(data, kernel, mode="same")
        smoothed = np.copy(data)
        for i in range(data.shape[1]):
            kernel = np.ones(window) / window
            smoothed[:, i] = np.convolve(data[:, i], kernel, mode="same")
        return smoothed


class DataCleaner:
    """数据清洗流水线

    管理一组清洗规则，按序执行，输出清洗后的数据和清洗报告。
    """

    def __init__(self):
        self._rules: List[CleaningRule] = []

    def add_rule(self, rule: CleaningRule) -> None:
        self._rules.append(rule)

    def remove_rule(self, name: str) -> bool:
        for i, r in enumerate(self._rules):
            if r.name == name:
                self._rules.pop(i)
                return True
        return False

    def clean_episode(self, episode_data: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """清洗一个 Episode 的数据

        Args:
            episode_data: {modality_name: data_array, ...}

        Returns:
            (cleaned_data, report)
        """
        report = {
            "total_rules_applied": 0,
            "anomalies_found": {},
            "frames_removed": 0,
            "frames_modified": 0,
        }

        cleaned = dict(episode_data)

        for rule in self._rules:
            if rule.modality not in cleaned:
                continue

            data = cleaned[rule.modality]
            if data is None:
                continue

            report["total_rules_applied"] += 1

            if isinstance(data, np.ndarray) and data.ndim >= 2:
                # 逐帧检查
                anomaly_mask = np.zeros(len(data), dtype=bool)
                for i in range(len(data)):
                    _, is_anomaly = rule.apply(data[i])
                    anomaly_mask[i] = is_anomaly

                num_anomalies = anomaly_mask.sum()
                if num_anomalies > 0:
                    report["anomalies_found"][rule.name] = int(num_anomalies)

                    if rule.action == CleaningAction.REMOVE:
                        cleaned[rule.modality] = data[~anomaly_mask]
                        report["frames_removed"] += num_anomalies
                    elif rule.action in (CleaningAction.CLIP, CleaningAction.SMOOTH):
                        for i in np.where(anomaly_mask)[0]:
                            cleaned[rule.modality][i], _ = rule.apply(data[i])
                        report["frames_modified"] += num_anomalies
            else:
                _, is_anomaly = rule.apply(data)
                if is_anomaly:
                    report["anomalies_found"][rule.name] = 1
                    if rule.action == CleaningAction.REMOVE:
                        cleaned[rule.modality] = None
                    else:
                        cleaned[rule.modality], _ = rule.apply(data)
                        report["frames_modified"] += 1

        return cleaned, report

    @staticmethod
    def create_default_rules() -> List[CleaningRule]:
        """创建默认清洗规则集"""
        return [
            CleaningRule(
                name="rgb_blur_check",
                modality="rgb",
                action=CleaningAction.FLAG,
                check_fn=lambda frame: (
                    _compute_blur_score(frame) < 50.0 if isinstance(frame, np.ndarray) else False
                ),
                description="检测模糊帧",
            ),
            CleaningRule(
                name="rgb_brightness_check",
                modality="rgb",
                action=CleaningAction.FLAG,
                check_fn=lambda frame: (
                    isinstance(frame, np.ndarray) and (frame.mean() < 10 or frame.mean() > 245)
                ),
                description="检测过暗/过亮帧",
            ),
            CleaningRule(
                name="depth_validity_check",
                modality="depth",
                action=CleaningAction.FLAG,
                check_fn=lambda d: (
                    isinstance(d, np.ndarray) and (d <= 0).mean() > 0.3
                ),
                description="深度图无效区域超过 30%",
            ),
            CleaningRule(
                name="trajectory_jump_check",
                modality="eef_pose",
                action=CleaningAction.SMOOTH,
                check_fn=lambda pose: (
                    isinstance(pose, np.ndarray) and pose.ndim == 2 and
                    any(np.abs(np.diff(pose, axis=0)).max(axis=0) > 0.5)
                ),
                params={"window": 3},
                description="检测轨迹跳变",
            ),
            CleaningRule(
                name="action_range_check",
                modality="action",
                action=CleaningAction.CLIP,
                check_fn=lambda action: (
                    isinstance(action, np.ndarray) and np.any(np.abs(action) > 10.0)
                ),
                params={"min": -10.0, "max": 10.0},
                description="动作值超出合理范围",
            ),
        ]


def _compute_blur_score(frame: np.ndarray) -> float:
    """计算图像模糊度评分 (Laplacian 方差)"""
    if frame.ndim == 3:
        gray = frame.mean(axis=-1)
    else:
        gray = frame

    laplacian = np.array([[0, 1, 0], [1, -4, 1], [0, 1, 0]], dtype=np.float64)
    from scipy.ndimage import convolve
    try:
        filtered = convolve(gray.astype(np.float64), laplacian)
        return float(np.var(filtered))
    except ImportError:
        return 100.0  # 默认不认为模糊
