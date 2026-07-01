"""
统一配置管理
============
使用 dataclass 管理所有模块的超参数，支持 YAML 文件加载和命令行覆盖。
"""

from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional, List, Tuple
import json


@dataclass
class BaseConfig:
    """所有配置的基类，提供序列化/反序列化能力"""

    def to_dict(self) -> dict:
        return asdict(self)

    def save(self, path: str):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)

    @classmethod
    def from_dict(cls, d: dict):
        # 过滤掉不属于该 dataclass 的字段
        valid_fields = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in d.items() if k in valid_fields}
        return cls(**filtered)

    @classmethod
    def load(cls, path: str):
        with open(path, "r", encoding="utf-8") as f:
            return cls.from_dict(json.load(f))


@dataclass
class DeviceConfig(BaseConfig):
    """设备配置"""
    device: str = "auto"  # "auto" | "cuda" | "cpu"
    seed: int = 42
    num_workers: int = 0
    pin_memory: bool = False

    def resolve_device(self) -> str:
        if self.device == "auto":
            import torch
            return "cuda" if torch.cuda.is_available() else "cpu"
        return self.device


@dataclass
class VLAConfig(BaseConfig):
    """VLA 模仿学习配置"""
    # 模型
    vision_model: str = "google/vit-base-patch16-224"
    language_model: str = "bert-base-uncased"
    action_dim: int = 7  # dx, dy, dz, droll, dpitch, dyaw, gripper
    image_size: int = 224
    max_text_length: int = 64

    # 训练
    batch_size: int = 16
    learning_rate: float = 1e-4
    weight_decay: float = 1e-4
    num_epochs: int = 20
    warmup_ratio: float = 0.1
    max_grad_norm: float = 1.0

    # 数据
    dataset_type: str = "inmemory"  # "inmemory" | "pybullet" | "mujoco" | "oxe"
    max_samples: int = 2048

    # 日志
    log_interval: int = 10
    save_dir: str = "./checkpoints"
    experiment_name: str = "vla_v1"
    visualize_epochs: int = 5


@dataclass
class RLConfig(BaseConfig):
    """机器人强化学习配置"""
    # 环境
    env_name: str = "HalfCheetah-v4"  # Gymnasium 环境名
    num_envs: int = 1

    # PPO
    algorithm: str = "ppo"  # "ppo" | "sac"
    learning_rate: float = 3e-4
    gamma: float = 0.99
    gae_lambda: float = 0.95
    clip_epsilon: float = 0.2
    value_coef: float = 0.5
    entropy_coef: float = 0.01
    max_grad_norm: float = 0.5

    # 训练
    total_timesteps: int = 1_000_000
    rollout_steps: int = 2048
    mini_batch_size: int = 64
    ppo_epochs: int = 10

    # 日志
    save_dir: str = "./checkpoints"
    experiment_name: str = "rl_ppo_v1"
    log_interval: int = 10


@dataclass
class WorldModelConfig(BaseConfig):
    """世界模型配置"""
    # 模型架构
    rssm_hidden: int = 512
    rssm_deterministic: int = 512
    rssm_stochastic: int = 32
    rssm_discrete: int = 32
    hidden_dim: int = 512

    # 训练
    learning_rate: float = 1e-4
    batch_size: int = 50
    sequence_length: int = 50
    imagination_horizon: int = 15
    gamma: float = 0.99
    lambda_: float = 0.95

    # 训练轮数
    total_steps: int = 1_000_000
    log_interval: int = 1000

    # 日志
    save_dir: str = "./checkpoints"
    experiment_name: str = "dreamer_v1"


@dataclass
class ProjectConfig(BaseConfig):
    """项目全局配置"""
    project_root: str = str(Path(__file__).parent.parent)
    device: DeviceConfig = field(default_factory=DeviceConfig)
    vla: VLAConfig = field(default_factory=VLAConfig)
    rl: RLConfig = field(default_factory=RLConfig)
    world_model: WorldModelConfig = field(default_factory=WorldModelConfig)
