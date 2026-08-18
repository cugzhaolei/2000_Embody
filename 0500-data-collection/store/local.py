"""
本地存储后端
============
读取/导出采集目录、以及将 le-robot 兼容目录转换为 0200-vla-imitation
预期的 traj_*.json + frame_*.png 旧格式（兼容 VLADataset._load_samples）。
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np

from ..core.utils import find_episode_dir, list_episodes


def convert_to_legacy(
    out_root: str,
    legacy_root: str,
    episode_indices: Optional[List[int]] = None,
    max_frames_per_episode: Optional[int] = None,
):
    """把 LeRobot 采集目录转换为 legacy traj 格式。

    输出:
      legacy_root/
        traj_0000.json            # {observations, actions, metadata}
        traj_0000/frame_0000.png  # 抽帧图像
        metadata.json
    """
    legacy_root = Path(legacy_root)
    legacy_root.mkdir(parents=True, exist_ok=True)

    episodes = list_episodes(out_root)
    if episode_indices:
        episodes = [e for e in episodes
                    if (e.get("episode_index") if isinstance(e, dict) else e) in episode_indices]

    converted = 0
    for ep_meta in episodes:
        idx = ep_meta.get("episode_index") if isinstance(ep_meta, dict) else ep_meta
        ep_dir = find_episode_dir(out_root, idx)
        if ep_dir is None:
            continue

        steps = _load_steps(ep_dir)
        if not steps:
            continue

        observations = []
        actions = []
        instruction = ""
        for i, st in enumerate(steps):
            instruction = instruction or st.get("instruction", "")
            obs = {"instruction": instruction}
            state = st.get("observation.state")
            if state is not None:
                obs["joint_positions"] = np.asarray(state).tolist()
            observations.append(obs)
            act = np.asarray(st.get("action", []), dtype=np.float32)
            actions.append(act.tolist())
        if not actions:
            continue

        traj = {
            "observations": observations,
            "actions": actions,
            "metadata": {"instruction": instruction, "num_steps": len(actions),
                         "source_episode": int(idx)},
        }
        traj_path = legacy_root / f"traj_{converted:04d}.json"
        with open(traj_path, "w", encoding="utf-8") as f:
            json.dump(traj, f, ensure_ascii=False, indent=2)

        # 图像：优先逐帧解码内嵌 JPEG，其次用视频抽帧
        img_dir = legacy_root / f"traj_{converted:04d}"
        img_dir.mkdir(exist_ok=True)
        png_count = 0
        frames = _extract_frames_from_steps(steps)
        if not frames:
            video = ep_dir.parent / f"episode_{idx:06d}.gif"
            if video.exists():
                from ..core.video import read_frames
                frames = read_frames(str(video))
        from PIL import Image
        for j, f in enumerate(frames):
            if max_frames_per_episode and j >= max_frames_per_episode:
                break
            Image.fromarray(f).save(img_dir / f"frame_{png_count:04d}.png")
            png_count += 1
        converted += 1

    # metadata.json
    meta = {
        "num_trajectories": converted,
        "total_steps": sum(
            len(_load_steps(find_episode_dir(out_root, e.get("episode_index") if isinstance(e, dict) else e)))
            for e in episodes if find_episode_dir(out_root, e.get("episode_index") if isinstance(e, dict) else e) is not None
        ),
        "instructions": list({e.get("task", "") for e in episodes}),
    }
    with open(legacy_root / "metadata.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    return converted


def _load_steps(ep_dir: Path) -> List[Dict]:
    pq = ep_dir / "steps.parquet"
    js = ep_dir / "steps.json"
    if pq.exists():
        try:
            import pandas as pd
            return pd.read_parquet(pq).to_dict("records")
        except ImportError:
            pass
    if js.exists():
        with open(js, encoding="utf-8") as f:
            return json.load(f)
    return []


def _extract_frames_from_steps(steps: List[Dict]) -> List[np.ndarray]:
    """从 steps 中逐帧解码内嵌图像（observation.images.* 的 JPEG bytes）。"""
    from ..core.schema import decode_image_bytes
    from ..core.utils import ensure_rgb
    frames: List[np.ndarray] = []
    img_keys = sorted({
        k for s in steps for k in s if k.startswith("observation.images.")
    })
    if not img_keys:
        return frames
    cam = img_keys[0]
    for st in steps:
        val = st.get(cam)
        if isinstance(val, np.ndarray):
            frames.append(ensure_rgb(val))
        elif isinstance(val, (bytes, bytearray, str)):
            img = decode_image_bytes(val)
            if img is not None:
                frames.append(ensure_rgb(img))
        if len(frames) >= len(steps):
            break
    return frames