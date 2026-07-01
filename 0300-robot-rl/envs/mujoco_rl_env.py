"""
MuJoCo RL 环境
=============
将 MuJoCo 机械臂环境封装为 Gymnasium 接口，供 RL 算法使用。

支持:
  - 标准 Gymnasium API (reset, step, render)
  - 域随机化 (domain randomization)
  - 密集/稀疏奖励
  - 多种任务: reach, push, pick

使用方法:
  env = MuJoCoRLEnv(task="reach")
  obs, info = env.reset()
  for _ in range(1000):
      action = env.action_space.sample()
      obs, reward, terminated, truncated, info = env.step(action)
"""

import os
import math
import tempfile
import shutil
from typing import Dict, Optional, Tuple

import numpy as np

try:
    import gymnasium as gym
    from gymnasium import spaces
except ImportError:
    import gym
    from gym import spaces


# 机械臂 XML (复用 VLA 模块的模型)
_ROBOT_XML = """<?xml version="1.0" encoding="utf-8"?>
<mujoco model="robot_arm_rl">
  <compiler angle="radian"/>
  <option timestep="0.005" gravity="0 0 -9.81"/>
  <asset>
    <texture type="skybox" builtin="gradient" rgb1="0.3 0.5 0.7" rgb2="0.1 0.2 0.3" width="256" height="256"/>
    <texture name="tex_plane" type="2d" builtin="checker" width="256" height="256" rgb1="0.2 0.3 0.4" rgb2="0.3 0.4 0.5"/>
    <material name="mat_plane" texture="tex_plane" texrepeat="3 3" reflectance="0.1"/>
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
    <body name="base" pos="0 0 0">
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
    <body name="target_object" pos="0.3 0.15 0.02">
      <joint name="target_x" type="slide" axis="1 0 0" range="-0.3 0.3" damping="0.1"/>
      <joint name="target_y" type="slide" axis="0 1 0" range="-0.3 0.3" damping="0.1"/>
      <joint name="target_z" type="slide" axis="0 0 1" range="0 0.3" damping="0.1"/>
      <geom name="target_geom" type="box" size="0.02 0.02 0.02" material="mat_target" mass="0.05"/>
    </body>
  </worldbody>
  <actuator>
    <position name="act_base_yaw" joint="base_yaw" kp="100" kv="10"/>
    <position name="act_shoulder_pitch" joint="shoulder_pitch" kp="100" kv="10"/>
    <position name="act_elbow_pitch" joint="elbow_pitch" kp="100" kv="10"/>
    <position name="act_wrist_pitch" joint="wrist_pitch" kp="100" kv="10"/>
    <position name="act_wrist_roll" joint="wrist_roll" kp="100" kv="10"/>
    <position name="act_gripper_left" joint="gripper_left" kp="50" kv="5"/>
    <position name="act_gripper_right" joint="gripper_right" kp="50" kv="5"/>
  </actuator>
</mujoco>
"""


class MuJoCoRLEnv(gym.Env):
    """MuJoCo 机械臂 RL 环境"""

    metadata = {"render_modes": ["human", "rgb_array"]}

    def __init__(
        self,
        task: str = "reach",
        reward_type: str = "dense",
        max_steps: int = 200,
        domain_rand: bool = False,
        render_mode: Optional[str] = None,
    ):
        super().__init__()

        self.task = task  # "reach" | "push" | "pick"
        self.reward_type = reward_type
        self.max_steps = max_steps
        self.domain_rand = domain_rand
        self.render_mode = render_mode

        # 动作空间: 5 个关节 + 夹爪
        self.action_space = spaces.Box(
            low=-1.0, high=1.0, shape=(5,), dtype=np.float32,
        )

        # 观测空间: 关节角度(5) + 末端位姿(3) + 目标位置(3) + 夹爪状态(1)
        obs_dim = 12
        self.observation_space = spaces.Box(
            low=-np.inf, high=np.inf, shape=(obs_dim,), dtype=np.float32,
        )

        self._mj = None
        self._model = None
        self._data = None
        self._renderer = None
        self._tmp_dir = None
        self._step_count = 0

    def _init_mujoco(self):
        try:
            import mujoco
            self._mj = mujoco
        except ImportError:
            raise ImportError("pip install mujoco")

        self._tmp_dir = tempfile.mkdtemp(prefix="mujoco_rl_")
        xml_path = os.path.join(self._tmp_dir, "robot.xml")
        with open(xml_path, "w") as f:
            f.write(_ROBOT_XML)

        self._model = self._mj.MjModel.from_xml_path(xml_path)
        self._data = self._mj.MjData(self._model)
        self._renderer = self._mj.Renderer(self._model, height=224, width=224)
        self._default_qpos = self._data.qpos.copy()

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)

        if self._model is None:
            self._init_mujoco()

        self._data.qpos[:] = self._default_qpos
        self._data.qvel[:] = 0

        # 域随机化
        if self.domain_rand:
            for i in range(min(5, self._model.nq)):
                if self._model.jnt_limited[i]:
                    lo, hi = self._model.jnt_range[i]
                    self._data.qpos[i] = self.np_random.uniform(lo, hi)

        # 随机目标
        self._target_pos = np.array([
            0.2 + self.np_random.uniform(-0.1, 0.2),
            self.np_random.uniform(-0.15, 0.15),
            0.04,
        ])

        self._mj.mj_forward(self._model, self._data)
        self._step_count = 0

        obs = self._get_obs()
        info = {"target_pos": self._target_pos}
        return obs, info

    def step(self, action):
        # 映射动作到关节增量
        joint_delta = action * 0.1
        new_qpos = self._data.qpos[:5].copy() + joint_delta

        for i in range(min(5, self._model.njnt)):
            if self._model.jnt_limited[i]:
                idx = self._model.jnt_qposadr[i]
                if idx < len(new_qpos):
                    lo, hi = self._model.jnt_range[i]
                    new_qpos[idx] = np.clip(new_qpos[idx], lo, hi)

        self._data.ctrl[:5] = new_qpos[:5]

        for _ in range(10):
            self._mj.mj_step(self._model, self._data)

        self._step_count += 1

        obs = self._get_obs()
        reward = self._compute_reward(obs)
        terminated = reward > 0.95
        truncated = self._step_count >= self.max_steps

        return obs, reward, terminated, truncated, {"step": self._step_count}

    def _get_obs(self):
        joint_pos = self._data.qpos[:5].copy()
        site_id = self._mj.mj_name2id(self._model, self._mj.mjtObj.mjOBJ_SITE, "end_effector")
        ee_pos = self._data.site_xpos[site_id].copy()
        grip_state = np.array([self._data.qpos[6]])  # gripper left

        return np.concatenate([joint_pos, ee_pos, self._target_pos, grip_state]).astype(np.float32)

    def _compute_reward(self, obs):
        ee_pos = obs[5:8]
        target = obs[8:11]
        dist = np.linalg.norm(ee_pos - target)

        if self.reward_type == "sparse":
            return 1.0 if dist < 0.03 else 0.0
        else:
            return max(0, 1.0 - dist / 0.5)

    def render(self):
        if self.render_mode == "rgb_array" and self._renderer is not None:
            self._renderer.update_scene(self._data)
            return self._renderer.render()
        return None

    def close(self):
        if self._renderer is not None:
            self._renderer.close()
        if self._tmp_dir is not None:
            shutil.rmtree(self._tmp_dir, ignore_errors=True)
