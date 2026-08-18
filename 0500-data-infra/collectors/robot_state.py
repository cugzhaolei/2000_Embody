"""
机器人状态采集器
===============
采集机器人关节状态、末端位姿、夹爪状态等运动学数据。
"""

import time
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np

from .base import BaseCollector


class RobotStateCollector(BaseCollector):
    """机器人状态数据采集器

    采集数据包括:
    - 关节位置 (joint positions)
    - 关节速度 (joint velocities)
    - 关节力矩 (joint efforts/torques)
    - 末端执行器位姿 (EEF pose: 6DoF)
    - 夹爪状态 (gripper state)
    - 碰撞/力传感器数据
    """

    def __init__(
        self,
        sensor_id: str,
        num_joints: int = 6,
        has_gripper: bool = True,
        has_eef_force: bool = False,
        publish_frequency: float = 125.0,  # 控制频率
        buffer_size: int = 5000,
        callback: Optional[Callable] = None,
        source_type: str = "simulated",  # "ros" | "sdk" | "simulated"
        robot_model: str = "",
    ):
        super().__init__(sensor_id, buffer_size, callback)
        self.num_joints = num_joints
        self.has_gripper = has_gripper
        self.has_eef_force = has_eef_force
        self.publish_frequency = publish_frequency
        self.source_type = source_type
        self.robot_model = robot_model
        self._step_count = 0

    def _setup(self) -> None:
        print(
            f"[{self.sensor_id}] Robot state collector initialized: "
            f"{self.num_joints} joints, gripper={self.has_gripper}, "
            f"source={self.source_type}"
        )

    def _collect_once(self) -> Optional[Tuple[Any, float]]:
        timestamp = time.time()
        self._step_count += 1

        state = {
            "joint_positions": np.random.uniform(-np.pi, np.pi, (self.num_joints,)).astype(np.float64),
            "joint_velocities": np.random.uniform(-1.0, 1.0, (self.num_joints,)).astype(np.float64),
            "joint_efforts": np.random.uniform(-5.0, 5.0, (self.num_joints,)).astype(np.float64),
            "eef_pose": np.array(
                [0.4, 0.0, 0.3, 0.0, np.pi, 0.0], dtype=np.float64
            ),  # x,y,z,rx,ry,rz
            "eef_velocity": np.zeros(6, dtype=np.float64),
        }

        if self.has_gripper:
            state["gripper_position"] = np.array([0.5], dtype=np.float32)  # 0=开, 1=合
            state["gripper_effort"] = np.array([0.0], dtype=np.float32)

        if self.has_eef_force:
            state["eef_force"] = np.random.uniform(-10.0, 10.0, (6,)).astype(np.float64)

        time.sleep(1.0 / self.publish_frequency)
        return state, timestamp

    def _cleanup(self) -> None:
        self._step_count = 0

    def forward_kinematics(self, joint_positions: np.ndarray) -> np.ndarray:
        """简单的正运动学 (示例: 仅做位置映射)"""
        # 实际项目中应使用机器人 URDF 进行 FK 计算
        eef = np.zeros(6, dtype=np.float64)
        eef[:3] = joint_positions[:3] * 0.1  # 简化映射
        return eef
