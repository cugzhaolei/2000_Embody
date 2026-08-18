"""
通用工具函数
============
提供 seed 设置、图像标准化、路径管理、动作归一化等公共能力，
与 common/utils.py 保持一致的风格。
"""

from __future__ import annotations

import json
import os
import random
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np


def set_seed(seed: int = 42):
    """设置随机种子（numpy 级即可，无需 torch）。"""
    random.seed(seed)
    np.random.seed(seed)


def ensure_rgb(arr: np.ndarray) -> np.ndarray:
    """把任意图像数组归一化为 uint8 [H, W, 3]。"""
    a = np.asarray(arr)
    if a.dtype == np.float32 or a.dtype == np.float64:
        if a.max() <= 1.0:
            a = (a * 255).astype(np.uint8)
        else:
            a = a.astype(np.uint8)
    elif a.dtype != np.uint8:
        a = a.astype(np.uint8)
    if a.ndim == 2:
        a = np.stack([a] * 3, axis=-1)
    if a.shape[-1] == 4:
        a = a[:, :, :3]
    if a.shape[-1] != 3:
        raise ValueError(f"无法将 shape={a.shape} 转为 RGB")
    return a


def normalize_action(action: np.ndarray, low: float = -1.0, high: float = 1.0) -> np.ndarray:
    """动作归一化到 [low, high]。"""
    a = np.asarray(action, dtype=np.float32)
    if a.size == 0:
        return a
    lo, hi = a.min(), a.max()
    if hi - lo < 1e-8:
        return np.full_like(a, (low + high) / 2)
    return ((a - lo) / (hi - lo)) * (high - low) + low


def denormalize_action(action: np.ndarray, low: float = -1.0, high: float = 1.0) -> np.ndarray:
    """逆归一化。"""
    a = np.asarray(action, dtype=np.float32)
    return (a - low) / (high - low)


def safe_json_dump(obj: Any, path: str):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False, default=_json_default)


def _json_default(o: Any):
    if isinstance(o, np.ndarray):
        return o.tolist()
    if isinstance(o, np.generic):
        return o.item()
    if isinstance(o, (Path,)):
        return str(o)
    return str(o)


def list_episodes(out_root: str) -> List[Dict]:
    """枚举数据集中的全部 episode 索引。"""
    root = Path(out_root)
    episodes = []
    info_path = root / "meta" / "info.json"
    if info_path.exists():
        with open(info_path, encoding="utf-8") as f:
            info = json.load(f)
        episodes = info.get("episodes", [])
    else:
        for d in sorted((root / "data").glob("episode_*")):
            if d.is_dir():
                episodes.append({"episode_index": int(d.name.split("_")[1])})
    return episodes


def find_episode_dir(out_root: str, idx: int) -> Optional[Path]:
    root = Path(out_root)
    data = root / "data"
    exe = data / f"episode_{idx:06d}"
    exj = data / f"episode_{idx}"
    for cand in (exe, exj):
        if cand.is_dir():
            return cand
    return None