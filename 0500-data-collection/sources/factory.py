"""
数据源工厂
==========
根据配置字符串创建对应数据源，供 CLI 使用。
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Dict

import numpy as np

from .base import DataSource, DummySource, ScriptedExpertSource
from .mujoco_arm import MuJoCoArmSource
from .pybullet_arm import PyBulletArmSource
from .teleop_keyboard import KeyboardTeleopSource


def _import_env_envs():
    """导入 0200-vla-imitation 的 envs，失败返回 None。"""
    try:
        here = Path(__file__).resolve().parent.parent.parent  # 2000_Embody
        import importlib.util

        for base in (here, here / "0200-vla-imitation"):
            env_file = base / "envs" / "pybullet_env.py"
            if not env_file.exists():
                continue
            spec = importlib.util.spec_from_file_location(
                "dc_env_pybullet_factory", str(env_file))
            module = importlib.util.module_from_spec(spec)
            sys.modules["dc_env_pybullet_factory"] = module
            if spec.loader:
                spec.loader.exec_module(module)
            return {
                "PyBulletArmEnv": module.PyBulletArmEnv,
                "ScriptedExpert": module.ScriptedExpert,
            }
        return None
    except Exception:
        return None


def create_source(
    source: str = "dummy",
    instruction: str = "pick up the red block",
    render: bool = False,
    action_dim: int = 7,
    **kwargs,
) -> DataSource:
    """创建数据源。

    Args:
        source: "dummy" | "scripted" | "pybullet" | "mujoco" | "keyboard" | "ros2"
    """
    s = source.lower()

    if s == "dummy":
        return DummySource(state_dim=6, action_dim=action_dim)

    if s == "scripted":
        envs = _import_env_envs()
        if envs is None:
            print("[factory] 0200-vla-imitation/envs 不可用，scripted 回退为 dummy")
            return DummySource(state_dim=6, action_dim=action_dim)
        env = envs["PyBulletArmEnv"](render=render, image_size=(160, 160), max_steps=400)
        expert = envs["ScriptedExpert"](env)

        def gen():
            return expert.generate_trajectory()

        def reset():
            env.reset()

        def frame():
            try:
                return env._get_obs()
            except AttributeError:
                return env.reset()

        def step(a):
            env.step(a)

        return PyBulletScriptedAdapter(
            gen=gen, reset_fn=reset, frame_fn=frame, step_fn=step,
            close_fn=env.close, action_dim=action_dim,
        )

    if s == "pybullet":
        return PyBulletArmSource(render=False, image_size=(160, 160))

    if s == "mujoco":
        return MuJoCoArmSource(render=False, image_size=(160, 160))

    if s == "keyboard":
        # 键盘遥操作需要一个底层环境源
        base = create_source(source="pybullet", action_dim=action_dim)
        return KeyboardTeleopSource(base, use_gui=kwargs.get("use_gui", False))

    if s == "ros2":
        from .ros2_robot import ROS2RobotSource
        return ROS2RobotSource(action_dim=action_dim)

    raise ValueError(f"未知数据源: {source}，可选: dummy/scripted/pybullet/mujoco/keyboard/ros2")


class PyBulletScriptedAdapter(ScriptedExpertSource):
    """针对 pybullet ScriptedExpert 的适配（把回调命名对齐）。"""

    def __init__(self, gen, reset_fn, frame_fn, step_fn, close_fn, action_dim=7):
        super().__init__(
            expert_actions_fn=gen,
            frame_fn=frame_fn,
            step_fn=step_fn,
            reset_fn=reset_fn,
            close_fn=close_fn,
            action_dim=action_dim,
        )