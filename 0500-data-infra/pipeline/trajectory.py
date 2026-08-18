"""
轨迹转换模块
===========
机器人轨迹数据格式转换、动作序列处理、轨迹插值和重采样。
"""

from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np


class TrajectoryConverter:
    """机器人轨迹格式转换器

    支持:
    - 不同动作空间之间的转换
    - 轨迹插值和重采样
    - 相对/绝对动作转换
    - Delta 动作计算
    """

    def __init__(self, action_dim: int = 7):
        """
        Args:
            action_dim: 动作维度 (default: 7 = xyz + rpy + gripper)
        """
        self.action_dim = action_dim

    def interpolate_trajectory(
        self,
        positions: np.ndarray,
        timestamps: np.ndarray,
        target_freq: float,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """线性插值轨迹到目标频率

        Args:
            positions: (T, D) 位置序列
            timestamps: (T,) 时间戳序列 (秒)
            target_freq: 目标频率 (Hz)

        Returns:
            (interpolated_positions, interpolated_timestamps)
        """
        duration = timestamps[-1] - timestamps[0]
        num_steps = int(duration * target_freq)
        if num_steps <= 0:
            return positions, timestamps

        new_timestamps = np.linspace(timestamps[0], timestamps[-1], num_steps)
        interpolated = np.zeros((num_steps, positions.shape[1]))

        for dim in range(positions.shape[1]):
            interpolated[:, dim] = np.interp(new_timestamps, timestamps, positions[:, dim])

        return interpolated, new_timestamps

    def resample_trajectory(
        self,
        actions: np.ndarray,
        source_freq: float,
        target_freq: float,
    ) -> np.ndarray:
        """重采样动作序列"""
        if source_freq == target_freq:
            return actions

        ratio = target_freq / source_freq
        new_length = int(len(actions) * ratio)
        indices = np.linspace(0, len(actions) - 1, new_length).astype(int)
        return actions[indices]

    def absolute_to_relative(
        self,
        eef_poses: np.ndarray,
    ) -> np.ndarray:
        """绝对位姿转相对增量 (delta)

        Args:
            eef_poses: (T, 6) 末端位姿序列 [x,y,z,rx,ry,rz]

        Returns:
            (T, 6) 相对增量序列，第一帧为零
        """
        deltas = np.zeros_like(eef_poses)
        deltas[1:] = eef_poses[1:] - eef_poses[:-1]
        return deltas

    def relative_to_absolute(
        self,
        deltas: np.ndarray,
        initial_pose: np.ndarray,
    ) -> np.ndarray:
        """相对增量转绝对位姿"""
        poses = np.zeros_like(deltas)
        poses[0] = initial_pose
        for i in range(1, len(deltas)):
            poses[i] = poses[i - 1] + deltas[i]
        return poses

    def smooth_trajectory(
        self,
        trajectory: np.ndarray,
        window_size: int = 5,
    ) -> np.ndarray:
        """滑动平均平滑"""
        if window_size <= 1:
            return trajectory

        smoothed = np.copy(trajectory)
        for i in range(len(trajectory)):
            start = max(0, i - window_size // 2)
            end = min(len(trajectory), i + window_size // 2 + 1)
            smoothed[i] = trajectory[start:end].mean(axis=0)
        return smoothed

    def detect_velocities(
        self,
        positions: np.ndarray,
        dt: float,
    ) -> np.ndarray:
        """从位置序列计算速度"""
        velocities = np.zeros_like(positions)
        velocities[1:] = (positions[1:] - positions[:-1]) / dt
        return velocities

    def compute_actions(
        self,
        eef_poses: np.ndarray,
        joint_states: Optional[np.ndarray] = None,
        gripper_states: Optional[np.ndarray] = None,
    ) -> np.ndarray:
        """组装完整的动作向量

        Returns:
            (T, D) 动作矩阵，D = 6(eef_delta) + N_joints + N_gripper
        """
        deltas = self.absolute_to_relative(eef_poses)
        action_parts = [deltas]

        if joint_states is not None:
            action_parts.append(joint_states)

        if gripper_states is not None:
            action_parts.append(gripper_states)

        return np.concatenate(action_parts, axis=-1)


class ActionTransformer:
    """动作空间变换器

    支持:
    - 不同机器人动作空间之间的映射
    - 动作归一化/反归一化
    - 动作裁剪
    """

    def __init__(self):
        self._normalization_stats: Dict[str, Dict[str, np.ndarray]] = {}

    def compute_normalization(
        self, actions: np.ndarray, method: str = "minmax"
    ) -> Dict[str, np.ndarray]:
        """计算归一化参数"""
        stats = {}
        if method == "minmax":
            stats["min"] = actions.min(axis=0)
            stats["max"] = actions.max(axis=0)
        elif method == "zscore":
            stats["mean"] = actions.mean(axis=0)
            stats["std"] = actions.std(axis=0) + 1e-8
        self._normalization_stats[method] = stats
        return stats

    def normalize(
        self, actions: np.ndarray, method: str = "minmax"
    ) -> np.ndarray:
        """归一化动作"""
        stats = self._normalization_stats.get(method)
        if stats is None:
            stats = self.compute_normalization(actions, method)

        if method == "minmax":
            range_val = stats["max"] - stats["min"]
            range_val[range_val == 0] = 1.0
            return (actions - stats["min"]) / range_val
        elif method == "zscore":
            return (actions - stats["mean"]) / stats["std"]
        return actions

    def denormalize(
        self, actions: np.ndarray, method: str = "minmax"
    ) -> np.ndarray:
        """反归一化动作"""
        stats = self._normalization_stats.get(method)
        if stats is None:
            raise ValueError(f"No normalization stats for method '{method}'")

        if method == "minmax":
            range_val = stats["max"] - stats["min"]
            return actions * range_val + stats["min"]
        elif method == "zscore":
            return actions * stats["std"] + stats["mean"]
        return actions

    def clip_actions(
        self,
        actions: np.ndarray,
        limits: Optional[Dict[int, Tuple[float, float]]] = None,
    ) -> np.ndarray:
        """裁剪动作到合法范围"""
        clipped = actions.copy()
        if limits:
            for dim, (lo, hi) in limits.items():
                if dim < clipped.shape[1]:
                    clipped[:, dim] = np.clip(clipped[:, dim], lo, hi)
        return clipped

    def rescale_action_space(
        self,
        actions: np.ndarray,
        source_range: Tuple[float, float],
        target_range: Tuple[float, float],
    ) -> np.ndarray:
        """动作空间缩放 [-1,1] <-> [min,max]"""
        src_lo, src_hi = source_range
        tgt_lo, tgt_hi = target_range
        normalized = (actions - src_lo) / (src_hi - src_lo) * 2 - 1
        return normalized * (tgt_hi - tgt_lo) / 2 + (tgt_hi + tgt_lo) / 2
