"""
轨迹异常检测
===========
检测机器人轨迹中的跳变、越界、卡顿等异常。
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np


@dataclass
class TrajectoryCheckResult:
    """轨迹检查结果"""
    total_frames: int = 0
    jump_count: int = 0
    out_of_bounds: int = 0
    velocity_violations: int = 0
    smoothness_score: float = 1.0
    success: bool = True
    issues: List[str] = field(default_factory=list)
    anomaly_indices: List[int] = field(default_factory=list)


class TrajectoryChecker:
    """轨迹异常检测器

    检测维度:
    - 位置跳变 (帧间位移 > 阈值)
    - 关节越限 (超出机械限位)
    - 速度/加速度超限
    - 轨迹平滑度
    - 静止检测 (长时间无运动)
    """

    def __init__(
        self,
        max_position_jump: float = 0.05,     # 5cm
        max_velocity: float = 2.0,            # 2 rad/s
        max_acceleration: float = 10.0,       # 10 rad/s^2
        joint_limits: Optional[Dict[int, Tuple[float, float]]] = None,
        min_movement_threshold: float = 0.001,  # 1mm
    ):
        self.max_position_jump = max_position_jump
        self.max_velocity = max_velocity
        self.max_acceleration = max_acceleration
        self.joint_limits = joint_limits or {}
        self.min_movement_threshold = min_movement_threshold

    def check(self, trajectory: np.ndarray) -> TrajectoryCheckResult:
        """检查轨迹"""
        result = TrajectoryCheckResult(total_frames=len(trajectory))

        if trajectory.ndim != 2 or len(trajectory) < 2:
            return result

        # 检查位置跳变
        self._check_jumps(trajectory, result)

        # 检查关节限位
        self._check_joint_limits(trajectory, result)

        # 检查速度
        self._check_velocity(trajectory, result)

        # 检查加速度
        self._check_acceleration(trajectory, result)

        # 评估平滑度
        result.smoothness_score = self._compute_smoothness(trajectory)

        result.success = len(result.issues) == 0
        return result

    def _check_jumps(self, trajectory: np.ndarray, result: TrajectoryCheckResult) -> None:
        """检查位置跳变"""
        diffs = np.abs(np.diff(trajectory, axis=0))
        max_diffs = diffs.max(axis=1) if diffs.ndim > 1 else diffs

        jump_mask = max_diffs > self.max_position_jump
        result.jump_count = int(jump_mask.sum())
        result.anomaly_indices.extend(np.where(jump_mask)[0].tolist())

        if result.jump_count > 0:
            max_jump = max_diffs.max()
            result.issues.append(
                f"Position jumps detected: {result.jump_count} "
                f"(max={max_jump*1000:.1f}mm, threshold={self.max_position_jump*1000:.1f}mm)"
            )

    def _check_joint_limits(self, trajectory: np.ndarray, result: TrajectoryCheckResult) -> None:
        """检查关节限位"""
        num_dims = trajectory.shape[1]
        violations = 0

        for dim in range(num_dims):
            if dim in self.joint_limits:
                lo, hi = self.joint_limits[dim]
                out_of_range = (trajectory[:, dim] < lo) | (trajectory[:, dim] > hi)
                violations += int(out_of_range.sum())

        # 默认限位 ±π
        if not self.joint_limits:
            violations = int((np.abs(trajectory) > np.pi).sum())

        result.out_of_bounds = violations
        if violations > 0:
            result.issues.append(f"Joint limit violations: {violations}")

    def _check_velocity(self, trajectory: np.ndarray, result: TrajectoryCheckResult) -> None:
        """检查速度超限"""
        velocities = np.diff(trajectory, axis=0)
        max_vels = np.abs(velocities).max(axis=1) if velocities.ndim > 1 else np.abs(velocities)

        violations = int((max_vels > self.max_velocity).sum())
        result.velocity_violations = violations

        if violations > 0:
            result.issues.append(f"Velocity violations: {violations} (max_vel={self.max_velocity})")

    def _check_acceleration(self, trajectory: np.ndarray, result: TrajectoryCheckResult) -> None:
        """检查加速度超限"""
        if len(trajectory) < 3:
            return

        velocities = np.diff(trajectory, axis=0)
        accelerations = np.diff(velocities, axis=0)
        max_accels = np.abs(accelerations).max(axis=1) if accelerations.ndim > 1 else np.abs(accelerations)

        violations = int((max_accels > self.max_acceleration).sum())
        if violations > 0:
            result.issues.append(f"Acceleration violations: {violations}")
            result.anomaly_indices.extend(np.where(max_accels > self.max_acceleration)[0].tolist())

    @staticmethod
    def _compute_smoothness(trajectory: np.ndarray) -> float:
        """计算轨迹平滑度评分 (0~1)"""
        if len(trajectory) < 3:
            return 1.0

        velocities = np.diff(trajectory, axis=0)
        accelerations = np.diff(velocities, axis=0)

        jerk = np.abs(accelerations).mean()
        # 归一化到 0~1
        smoothness = max(0.0, 1.0 - jerk / 5.0)
        return float(smoothness)

    def detect_stuck(
        self, trajectory: np.ndarray, window: int = 10, threshold: float = 0.0001
    ) -> List[int]:
        """检测卡顿 (长时间无运动)"""
        stuck_indices = []
        for i in range(len(trajectory) - window):
            segment = trajectory[i:i + window]
            movement = np.abs(np.diff(segment, axis=0)).max()
            if movement < threshold:
                stuck_indices.extend(range(i, i + window))
        return sorted(list(set(stuck_indices)))

    def detect_phantom_motion(
        self, trajectory: np.ndarray, expected_static: Optional[List[int]] = None
    ) -> List[int]:
        """检测静止段的异常运动"""
        if expected_static is None:
            return []

        phantom_indices = []
        for idx in expected_static:
            if 0 < idx < len(trajectory):
                window = 3
                start = max(0, idx - window)
                end = min(len(trajectory), idx + window + 1)
                segment = trajectory[start:end]
                movement = np.abs(np.diff(segment, axis=0)).max()
                if movement > self.min_movement_threshold:
                    phantom_indices.append(idx)
        return phantom_indices
