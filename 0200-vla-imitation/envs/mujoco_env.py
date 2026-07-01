"""
MuJoCo 机械臂仿真环境
=====================
使用 MuJoCo 物理引擎搭建桌面机械臂抓取环境。
MuJoCo 是机器人控制的标准环境，仿真精度高于 PyBullet。

动作空间 (7维): [dx, dy, dz, droll, dpitch, dyaw, gripper]
观测空间:
  - image: RGB 图像 (H, W, 3)
  - joint_positions: 关节角度 (6,)
  - end_effector_pos: 末端位姿

使用方法:
  env = MuJoCoArmEnv(render=True)
  obs = env.reset()
  for action in action_sequence:
      obs, reward, done, info = env.step(action)
  env.close()
"""

import os
import math
import tempfile
from typing import Dict, Optional, Tuple

import numpy as np


# 7-DOF 桌面机械臂 MuJoCo XML 模型
ROBOT_ARM_XML = """<?xml version="1.0" encoding="utf-8"?>
<mujoco model="robot_arm">
  <compiler angle="radian"/>

  <visual>
    <global offwidth="224" offheight="224"/>
  </visual>

  <option timestep="0.002" gravity="0 0 -9.81">
    <flag contact="enable"/>
  </option>

  <asset>
    <texture type="skybox" builtin="gradient" rgb1="0.3 0.5 0.7" rgb2="0.1 0.2 0.3" width="512" height="512"/>
    <texture name="tex_plane" type="2d" builtin="checker" width="512" height="512"
             rgb1="0.2 0.3 0.4" rgb2="0.3 0.4 0.5"/>
    <material name="mat_plane" texture="tex_plane" texrepeat="5 5" reflectance="0.1"/>
    <material name="mat_base" rgba="0.3 0.3 0.3 1"/>
    <material name="mat_link1" rgba="0.2 0.6 0.8 1"/>
    <material name="mat_link2" rgba="0.8 0.3 0.2 1"/>
    <material name="mat_link3" rgba="0.2 0.8 0.3 1"/>
    <material name="mat_link4" rgba="0.8 0.7 0.1 1"/>
    <material name="mat_gripper" rgba="0.6 0.6 0.6 1"/>
    <material name="mat_target" rgba="1.0 0.2 0.2 0.8"/>
  </asset>

  <worldbody>
    <geom name="floor" type="plane" size="1.5 1.5 0.1" material="mat_plane"/>
    <light directional="true" pos="1 1 1.5" dir="-1 -1 -1.5" diffuse="0.8 0.8 0.8"/>

    <!-- 底座 -->
    <body name="base" pos="0 0 0.0">
      <geom type="cylinder" size="0.08 0.05" material="mat_base" pos="0 0 0.025"/>
      <joint name="base_yaw" type="hinge" axis="0 0 1" range="-3.14 3.14" damping="0.5"/>

      <body name="shoulder" pos="0 0 0.05">
        <geom type="capsule" size="0.04" fromto="0 0 0 0 0 0.15" material="mat_link1"/>
        <joint name="shoulder_pitch" type="hinge" axis="0 1 0" range="-2.5 1.5" damping="0.5"/>

        <body name="upper_arm" pos="0 0 0.15">
          <geom type="capsule" size="0.035" fromto="0 0 0 0.15 0 0" material="mat_link2"/>
          <joint name="elbow_pitch" type="hinge" axis="0 1 0" range="-2.5 0.5" damping="0.3"/>

          <body name="forearm" pos="0.15 0 0">
            <geom type="capsule" size="0.03" fromto="0 0 0 0.12 0 0" material="mat_link3"/>
            <joint name="wrist_pitch" type="hinge" axis="0 1 0" range="-2.0 2.0" damping="0.2"/>

            <body name="wrist_roll_body" pos="0.12 0 0">
              <joint name="wrist_roll" type="hinge" axis="1 0 0" range="-3.14 3.14" damping="0.1"/>
              <geom type="capsule" size="0.02" fromto="0 0 0 0.05 0 0" material="mat_link4"/>

              <body name="gripper_left" pos="0.05 0.02 0">
                <joint name="gripper_left" type="slide" axis="0 1 0" range="-0.03 0.03" damping="0.5"/>
                <geom type="box" size="0.015 0.005 0.02" material="mat_gripper"/>
              </body>

              <body name="gripper_right" pos="0.05 -0.02 0">
                <joint name="gripper_right" type="slide" axis="0 -1 0" range="-0.03 0.03" damping="0.5"/>
                <geom type="box" size="0.015 0.005 0.02" material="mat_gripper"/>
              </body>

              <site name="end_effector" type="sphere" size="0.01" rgba="1 0 0 1" pos="0.05 0 0"/>
            </body>
          </body>
        </body>
      </body>
    </body>

    <!-- 目标物体 -->
    <body name="target_object" pos="0.3 0.15 0.02">
      <joint name="target_x" type="slide" axis="1 0 0" range="-0.2 0.2" damping="0.1"/>
      <joint name="target_y" type="slide" axis="0 1 0" range="-0.2 0.2" damping="0.1"/>
      <joint name="target_z" type="slide" axis="0 0 1" range="0 0.3" damping="0.1"/>
      <geom name="target_geom" type="box" size="0.02 0.02 0.02" material="mat_target" mass="0.05"/>
    </body>

    <!-- 工作台 -->
    <body name="table" pos="0.25 0 -0.05">
      <geom type="box" size="0.2 0.3 0.02" material="mat_base" rgba="0.5 0.35 0.2 1"/>
    </body>
  </worldbody>

  <actuator>
    <position name="act_base_yaw"       joint="base_yaw"       kp="100" kv="10"/>
    <position name="act_shoulder_pitch" joint="shoulder_pitch" kp="100" kv="10"/>
    <position name="act_elbow_pitch"    joint="elbow_pitch"    kp="100" kv="10"/>
    <position name="act_wrist_pitch"    joint="wrist_pitch"    kp="100" kv="10"/>
    <position name="act_wrist_roll"     joint="wrist_roll"     kp="100" kv="10"/>
    <position name="act_gripper_left"   joint="gripper_left"   kp="50" kv="5"/>
    <position name="act_gripper_right"  joint="gripper_right"  kp="50" kv="5"/>
  </actuator>
</mujoco>
"""


class MuJoCoArmEnv:
    """MuJoCo 6-DOF 桌面机械臂环境"""

    def __init__(
        self,
        render: bool = False,
        image_size: Tuple[int, int] = (224, 224),
        action_dim: int = 7,
        max_steps: int = 200,
        reward_type: str = "dense",
    ):
        self.render_mode = render
        self.image_size = image_size
        self.action_dim = action_dim
        self.max_steps = max_steps
        self.reward_type = reward_type

        self._mj = None
        self._model = None
        self._data = None
        self._renderer = None
        self._tmp_dir = None
        self._step_count = 0

    def _init_mujoco(self):
        """初始化 MuJoCo 模型"""
        try:
            import mujoco
            self._mj = mujoco
        except ImportError:
            raise ImportError("请安装 MuJoCo: pip install mujoco")

        # 写入临时 XML
        self._tmp_dir = tempfile.mkdtemp(prefix="mujoco_vla_")
        xml_path = os.path.join(self._tmp_dir, "robot.xml")
        with open(xml_path, "w") as f:
            f.write(ROBOT_ARM_XML)

        self._model = self._mj.MjModel.from_xml_path(xml_path)
        self._data = self._mj.MjData(self._model)
        self._renderer = self._mj.Renderer(self._model, height=self.image_size[0], width=self.image_size[1])

        # 记录默认关节位置
        self._default_qpos = self._data.qpos.copy()

    def reset(self, target_pos: Optional[np.ndarray] = None) -> Dict[str, np.ndarray]:
        """重置环境"""
        if self._model is None:
            self._init_mujoco()

        self._data.qpos[:] = self._default_qpos
        self._data.qvel[:] = 0

        # 随机目标位置
        if target_pos is not None:
            # 设置目标物体位置
            for i, val in enumerate(target_pos[:3]):
                if i + 8 < self._model.nq:  # 目标物体关节偏移
                    self._data.qpos[8 + i] = val

        self._target_pos = target_pos if target_pos is not None else np.array([0.3, 0.15, 0.02])
        self._mj.mj_forward(self._model, self._data)
        self._step_count = 0

        return self._get_obs()

    def step(self, action: np.ndarray) -> Tuple[Dict[str, np.ndarray], float, bool, Dict]:
        """执行动作"""
        action = np.clip(action, -1.0, 1.0)

        # 简化映射: 增量动作 → 关节增量
        joint_delta = np.zeros(7)
        joint_delta[0] = action[1] * 0.1  # dy → base_yaw
        joint_delta[1] = -action[2] * 0.15  # dz → shoulder_pitch
        joint_delta[2] = -action[2] * 0.1  # dz → elbow_pitch
        joint_delta[3] = action[4] * 0.1   # dpitch → wrist_pitch
        joint_delta[4] = action[3] * 0.1   # droll → wrist_roll
        joint_delta[5] = action[6] * 0.03 - 0.015  # grip → gripper_left
        joint_delta[6] = (1 - action[6]) * 0.03 - 0.015  # grip → gripper_right

        # 更新关节目标
        new_qpos = self._data.qpos[:7].copy() + joint_delta

        # 限制关节范围
        for i in range(min(7, self._model.njnt)):
            if self._model.jnt_limited[i]:
                lo, hi = self._model.jnt_range[i]
                idx = self._model.jnt_qposadr[i]
                if idx < len(new_qpos):
                    new_qpos[idx] = np.clip(new_qpos[idx], lo, hi)

        self._data.ctrl[:7] = new_qpos[:7]

        # 仿真步进
        for _ in range(10):
            self._mj.mj_step(self._model, self._data)

        self._step_count += 1

        obs = self._get_obs()
        reward = self._compute_reward(obs)
        done = self._step_count >= self.max_steps or reward > 0.9

        return obs, reward, done, {"step": self._step_count}

    def _get_obs(self) -> Dict[str, np.ndarray]:
        """获取观测"""
        image = self._render_image()
        joint_positions = self._data.qpos[:6].copy()

        # 末端执行器位置
        site_id = self._mj.mj_name2id(self._model, self._mj.mjtObj.mjOBJ_SITE, "end_effector")
        ee_pos = self._data.site_xpos[site_id].copy()

        return {
            "image": image,
            "joint_positions": joint_positions,
            "end_effector_pos": ee_pos,
        }

    def _render_image(self) -> np.ndarray:
        """渲染 RGB 图像"""
        self._renderer.update_scene(self._data, camera=-1)
        return self._renderer.render()

    def _compute_reward(self, obs: Dict[str, np.ndarray]) -> float:
        """计算奖励"""
        ee_pos = obs["end_effector_pos"][:3]
        dist = np.linalg.norm(ee_pos - self._target_pos)

        if self.reward_type == "sparse":
            return 1.0 if dist < 0.03 else 0.0
        else:
            return max(0, 1.0 - dist / 0.5)

    def close(self):
        """清理资源"""
        if self._renderer is not None:
            self._renderer.close()
        if self._tmp_dir is not None:
            import shutil
            shutil.rmtree(self._tmp_dir, ignore_errors=True)
