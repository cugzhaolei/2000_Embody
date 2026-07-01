"""
PyBullet 机械臂仿真环境
======================
使用 PyBullet 物理引擎搭建桌面机械臂抓取环境。
支持专家轨迹录制（keyboard/scripted），用于模仿学习数据采集。

动作空间 (7维): [dx, dy, dz, droll, dpitch, dyaw, gripper]
观测空间:
  - image: RGB 图像 (H, W, 3)
  - joint_positions: 关节角度 (6,)
  - end_effector_pos: 末端位姿 (7,) [xyz + quat + grip]

使用方法:
  env = PyBulletArmEnv(render=True)
  obs = env.reset()
  for action in action_sequence:
      obs, reward, done, info = env.step(action)
  env.close()
"""

import os
import math
import time
from typing import Dict, Optional, Tuple

import numpy as np


class PyBulletArmEnv:
    """
    PyBullet 6-DOF 桌面机械臂环境。

    特点:
      - 纯 CPU 运行，无需 GPU
      - 内置桌面、目标物体、简单抓取场景
      - 支持关键点/脚本化专家轨迹录制
      - 返回 RGB 图像观测
    """

    # 默认机器人 URDF 路径 (PyBullet 内置)
    ROBOT_URDF = "panda/panda.urdf"

    def __init__(
        self,
        render: bool = False,
        image_size: Tuple[int, int] = (224, 224),
        action_dim: int = 7,
        max_steps: int = 200,
        reward_type: str = "sparse",  # "sparse" | "dense"
    ):
        self.render = render
        self.image_size = image_size
        self.action_dim = action_dim
        self.max_steps = max_steps
        self.reward_type = reward_type

        self._p = None
        self._robot_id = None
        self._target_id = None
        self._step_count = 0

    def _connect(self):
        """连接 PyBullet 物理引擎"""
        try:
            import pybullet as p
            import pybullet_data
        except ImportError:
            raise ImportError("请安装 PyBullet: pip install pybullet")

        if self.render:
            self._p = p.connect(p.GUI)
        else:
            self._p = p.connect(p.DIRECT)

        p = self._p
        p.setAdditionalSearchPath(pybullet_data.getDataPath())
        p.setGravity(0, 0, -9.81)
        p.setTimeStep(1.0 / 240.0)

        # 加载地面
        p.loadURDF("plane.urdf")

        # 加载桌面
        table_col = p.createCollisionShape(p.GEOM_BOX, halfExtents=[0.3, 0.4, 0.02])
        table_vis = p.createVisualShape(p.GEOM_BOX, halfExtents=[0.3, 0.4, 0.02], rgbaColor=[0.5, 0.35, 0.2, 1])
        p.createMultiBody(baseMass=0, baseCollisionShapeIndex=table_col,
                          baseVisualShapeIndex=table_vis, basePosition=[0.5, 0, 0.0])

        # 加载机器人
        self._robot_id = p.loadURDF(
            self.ROBOT_URDF,
            basePosition=[0, 0, 0],
            useFixedBase=True,
        )

        # 加载目标物体 (红色方块)
        col = p.createCollisionShape(p.GEOM_BOX, halfExtents=[0.02, 0.02, 0.02])
        vis = p.createVisualShape(p.GEOM_BOX, halfExtents=[0.02, 0.02, 0.02], rgbaColor=[1, 0.2, 0.2, 1])
        self._target_id = p.createMultiBody(baseMass=0.05, baseCollisionShapeIndex=col,
                                             baseVisualShapeIndex=vis, basePosition=[0.5, 0.1, 0.04])

        # 末端执行器约束
        self._num_joints = p.getNumJoints(self._robot_id)

    def reset(self, target_pos: Optional[np.ndarray] = None) -> Dict[str, np.ndarray]:
        """重置环境，返回初始观测"""
        if self._p is None:
            self._connect()

        p = self._p
        p.resetSimulation()
        p.setGravity(0, 0, -9.81)
        p.setTimeStep(1.0 / 240.0)

        # 重新加载场景
        p.loadURDF("plane.urdf")
        table_col = p.createCollisionShape(p.GEOM_BOX, halfExtents=[0.3, 0.4, 0.02])
        table_vis = p.createVisualShape(p.GEOM_BOX, halfExtents=[0.3, 0.4, 0.02], rgbaColor=[0.5, 0.35, 0.2, 1])
        p.createMultiBody(baseMass=0, baseCollisionShapeIndex=table_col,
                          baseVisualShapeIndex=table_vis, basePosition=[0.5, 0, 0.0])

        self._robot_id = p.loadURDF(self.ROBOT_URDF, basePosition=[0, 0, 0], useFixedBase=True)
        self._num_joints = p.getNumJoints(self._robot_id)

        # 随机或指定目标位置
        if target_pos is None:
            target_pos = np.array([0.5 + np.random.uniform(-0.1, 0.1),
                                   np.random.uniform(-0.15, 0.15),
                                   0.04])
        col = p.createCollisionShape(p.GEOM_BOX, halfExtents=[0.02, 0.02, 0.02])
        vis = p.createVisualShape(p.GEOM_BOX, halfExtents=[0.02, 0.02, 0.02], rgbaColor=[1, 0.2, 0.2, 1])
        self._target_id = p.createMultiBody(baseMass=0.05, baseCollisionShapeIndex=col,
                                             baseVisualShapeIndex=vis, basePosition=target_pos.tolist())

        self._target_pos = target_pos
        self._step_count = 0

        # 等待物理稳定
        for _ in range(100):
            p.stepSimulation()

        return self._get_obs()

    def step(self, action: np.ndarray) -> Tuple[Dict[str, np.ndarray], float, bool, Dict]:
        """
        执行一个动作步。

        Args:
            action: [7] 动作向量 [dx, dy, dz, droll, dpitch, dyaw, gripper]

        Returns:
            obs, reward, done, info
        """
        p = self._p
        action = np.clip(action, -1.0, 1.0)

        # 获取当前末端位姿
        ee_pos, ee_orn = self._get_end_effector_pose()

        # 增量位姿控制
        dx, dy, dz = action[0] * 0.02, action[1] * 0.02, action[2] * 0.02
        new_pos = [ee_pos[0] + dx, ee_pos[1] + dy, ee_pos[2] + dz]

        # 夹爪控制
        grip = action[6] if len(action) > 6 else 0.0
        finger_target = max(0, min(0.04, grip * 0.04))

        # 使用 IK 计算关节目标
        joint_positions = p.calculateInverseKinematics(
            self._robot_id,
            endEffectorLinkIndex=self._num_joints - 1,
            targetPosition=new_pos,
            targetOrientation=ee_orn,
            maxNumIterations=50,
            residualThreshold=1e-3,
        )

        # 设置关节位置
        for i in range(min(self._num_joints, len(joint_positions))):
            p.setJointMotorControl2(
                self._robot_id, i,
                controlMode=p.POSITION_CONTROL,
                targetPosition=joint_positions[i],
                force=100,
            )

        # 夹爪控制
        if self._num_joints >= 9:
            for finger_idx in [7, 8]:
                p.setJointMotorControl2(
                    self._robot_id, finger_idx,
                    controlMode=p.POSITION_CONTROL,
                    targetPosition=finger_target,
                    force=20,
                )

        # 步进仿真
        for _ in range(10):
            p.stepSimulation()

        self._step_count += 1

        # 计算奖励
        obs = self._get_obs()
        reward = self._compute_reward(obs)
        done = self._step_count >= self.max_steps or reward > 0.9

        info = {"step": self._step_count, "reward": reward}
        return obs, reward, done, info

    def _get_obs(self) -> Dict[str, np.ndarray]:
        """获取当前观测"""
        p = self._p

        # 渲染图像
        image = self._render_image()

        # 关节角度
        joint_positions = np.zeros(6)
        for i in range(min(6, self._num_joints)):
            joint_positions[i] = p.getJointState(self._robot_id, i)[0]

        # 末端位姿
        ee_pos, ee_orn = self._get_end_effector_pose()
        ee_quat = np.array(ee_orn) if ee_orn is not None else np.array([0, 0, 0, 1])

        return {
            "image": image,
            "joint_positions": joint_positions,
            "end_effector_pos": np.concatenate([ee_pos, ee_quat]),
        }

    def _render_image(self) -> np.ndarray:
        """渲染 RGB 图像"""
        p = self._p
        view_matrix = p.computeViewMatrix(
            cameraEyePosition=[0.5, -0.5, 0.5],
            cameraTargetPosition=[0.5, 0, 0.1],
            cameraUpVector=[0, 0, 1],
        )
        proj_matrix = p.computeProjectionMatrixFOV(
            fov=60, aspect=1.0, nearVal=0.01, farVal=10.0,
        )
        _, _, rgba, _, _ = p.getCameraImage(
            width=self.image_size[1],
            height=self.image_size[0],
            viewMatrix=view_matrix,
            projectionMatrix=proj_matrix,
        )
        image = np.array(rgba, dtype=np.uint8).reshape(self.image_size[0], self.image_size[1], 4)[:, :, :3]
        return image

    def _get_end_effector_pose(self):
        """获取末端执行器位姿"""
        p = self._p
        ee_state = p.getLinkState(self._robot_id, self._num_joints - 1)
        return list(ee_state[0]), list(ee_state[1])

    def _compute_reward(self, obs: Dict[str, np.ndarray]) -> float:
        """计算奖励"""
        ee_pos = obs["end_effector_pos"][:3]
        dist = np.linalg.norm(ee_pos - self._target_pos)

        if self.reward_type == "sparse":
            return 1.0 if dist < 0.03 else 0.0
        else:
            return max(0, 1.0 - dist / 0.5)

    def close(self):
        """断开连接"""
        if self._p is not None:
            import pybullet as p
            p.disconnect(self._p)
            self._p = None


class ScriptedExpert:
    """
    脚本化专家策略：生成简单的抓取轨迹，用于模仿学习数据采集。

    生成策略:
      1. 移动到目标上方
      2. 下降到目标
      3. 闭合夹爪
      4. 提升
      5. 移动到放置位置
    """

    def __init__(self, env: PyBulletArmEnv):
        self.env = env

    def generate_trajectory(self, target_pos: Optional[np.ndarray] = None) -> list:
        """生成一条完整的抓取轨迹"""
        obs = self.env.reset(target_pos=target_pos)
        trajectory = []
        target = self.env._target_pos.copy()
        place_pos = target + np.array([0.0, -0.15, 0.0])

        # 阶段1: 移动到目标上方
        above_pos = target + np.array([0.0, 0.0, 0.15])
        trajectory.extend(self._move_to(obs, above_pos, grip=1.0, steps=30))

        # 阶段2: 下降到目标
        trajectory.extend(self._move_to(obs, target + np.array([0.0, 0.0, 0.02]), grip=1.0, steps=20))

        # 阶段3: 闭合夹爪
        trajectory.extend(self._move_to(obs, target + np.array([0.0, 0.0, 0.02]), grip=0.0, steps=10))

        # 阶段4: 提升
        trajectory.extend(self._move_to(obs, above_pos, grip=0.0, steps=20))

        # 阶段5: 移动到放置位置
        above_place = place_pos + np.array([0.0, 0.0, 0.15])
        trajectory.extend(self._move_to(obs, above_place, grip=0.0, steps=30))
        trajectory.extend(self._move_to(obs, place_pos + np.array([0.0, 0.0, 0.02]), grip=0.0, steps=20))

        # 阶段6: 松开夹爪
        trajectory.extend(self._move_to(obs, place_pos + np.array([0.0, 0.0, 0.02]), grip=1.0, steps=10))

        return trajectory

    def _move_to(self, current_obs, target_pos, grip: float = 1.0, steps: int = 20) -> list:
        """生成从当前位置到目标位置的线性插值动作序列"""
        ee_pos = current_obs["end_effector_pos"][:3]
        actions = []

        for i in range(steps):
            alpha = (i + 1) / steps
            next_pos = ee_pos + alpha * (target_pos - ee_pos)
            dx = (next_pos[0] - ee_pos[0]) / 0.02
            dy = (next_pos[1] - ee_pos[1]) / 0.02
            dz = (next_pos[2] - ee_pos[2]) / 0.02
            action = np.array([dx, dy, dz, 0, 0, 0, grip])
            actions.append(action)
            ee_pos = next_pos

        return actions
