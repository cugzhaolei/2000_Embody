"""
统一配置管理
============
提供数据采集相关的 dataclass 配置，风格与 common/config.py 对齐。
支持 jso/save/load。
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional


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
        valid_fields = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in d.items() if k in valid_fields}
        return cls(**filtered)

    @classmethod
    def load(cls, path: str):
        with open(path, "r", encoding="utf-8") as f:
            return cls.from_dict(json.load(f))


@dataclass
class CollectionConfig(BaseConfig):
    """数据采集配置"""
    # 采集
    source: str = "dummy"          # dummy | scripted | pybullet | mujoco | keyboard | ros2
    fps: int = 10
    action_dim: int = 7            # dx,dy,dz,droll,dpitch,dyaw,gripper
    episodes: int = 3
    steps_per_episode: int = 30
    seed: int = 42

    # 输出
    out_root: str = "./data/episodes"
    video_backend: str = "gif"     # gif | mp4 | png | none
    min_episode_len: int = 4

    # 任务
    instruction: str = "pick up the red block"

    # 数据源参数
    render: bool = False
    use_gui: bool = False          # keyboard 遥操作是否用 GUI 窗口


@dataclass
class DatasetConfig(BaseConfig):
    """数据集管理配置（verify / stats / convert）"""
    data_root: str = "./data/episodes"
    action_dim: int = 7
    report_path: Optional[str] = None      # verify 报告输出路径
    legacy_out: Optional[str] = None       # convert_to_legacy 目标目录