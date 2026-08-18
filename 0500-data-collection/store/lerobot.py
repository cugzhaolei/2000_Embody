"""
LeRobot 兼容数据集读取
======================
把采集目录 (meta/info.json + data/episode_*.parquet) 包装为
PyTorch Dataset / generator，输出与 0200-vla-imitation/data/dataset.py
的 VLADataset 相同字段：(images, input_ids, attention_mask, actions)。

若未安装 torch/transformers，返回纯 numpy dict 走可迭代接口。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Iterator, List, Optional, Tuple

import numpy as np

from ..core.utils import find_episode_dir, list_episodes


class LeRobotDatasetIterator:
    """轻量可迭代数据集：逐 sample 产出 numpy 字典。

    sample 字段:
      "image": np.ndarray [H, W, 3] uint8
      "state": np.ndarray [S] float32
      "instruction": str
      "action": np.ndarray [A] float32
      "frame_index": int
    """

    def __init__(self, out_root: str, action_dim: int = 7, only_images: bool = False):
        self.out_root = Path(out_root)
        self.action_dim = action_dim
        self.only_images = only_images
        self.episodes = list_episodes(out_root)
        self._samples: List[Tuple[int, int, Dict]] = self._index()

    def _index(self) -> List[Tuple[int, int, Dict]]:
        samples = []
        for ep in self.episodes:
            idx = ep.get("episode_index") if isinstance(ep, dict) else ep
            ep_dir = find_episode_dir(self.out_root, idx)
            if ep_dir is None:
                continue
            steps = self._load_steps(ep_dir)
            for i, st in enumerate(steps):
                samples.append((idx, i, st))
        return samples

    def _load_steps(self, ep_dir: Path) -> List[Dict]:
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

    def __len__(self) -> int:
        return len(self._samples)

    def __iter__(self) -> Iterator[Dict[str, np.ndarray]]:
        for ep_idx, frame_idx, st in self._samples:
            yield self._convert(st)

    def __getitem__(self, i: int) -> Dict[str, np.ndarray]:
        ep_idx, frame_idx, st = self._samples[i]
        return self._convert(st)

    def _convert(self, st: Dict) -> Dict[str, np.ndarray]:
        from ..core.schema import decode_image_bytes
        out: Dict[str, np.ndarray] = {
            "instruction": str(st.get("instruction", "")),
            "state": np.asarray(st.get("observation.state", np.zeros(6)), dtype=np.float32),
            "action": np.asarray(st.get("action", np.zeros(self.action_dim)), dtype=np.float32),
            "frame_index": int(st.get("frame_index", 0)),
        }
        # 提取第一张相机图（bytes 解码 / 路径 / 原生数组）
        img_keys = sorted(k for k in st if k.startswith("observation.images."))
        if img_keys:
            val = st[img_keys[0]]
            img = None
            if isinstance(val, np.ndarray):
                img = val
            elif isinstance(val, (bytes, bytearray, str)):
                img = decode_image_bytes(val)
            if img is None:
                h = st.get("_img_h", 160); w = st.get("_img_w", 160)
                img = np.zeros((h, w, 3), dtype=np.uint8)
            out["image"] = img
        return out


# ── PyTorch 桥接（可选）────────────────────────────────────────────
def _torch_dataset(out_root: str, tokenizer, image_size=224, max_text_length=64,
                   action_dim=7, is_train=True):
    """构建与 VLADataset 输出完全一致的 torch Dataset。

    依赖: torch, torchvision, transformers。若缺失则抛 ImportError。
    """
    import torch
    from torch.utils.data import Dataset
    from torchvision import transforms
    from PIL import Image
    from ..core.utils import ensure_rgb

    MEAN = [0.485, 0.456, 0.406]
    STD = [0.229, 0.224, 0.225]

    transform = transforms.Compose([
        transforms.Resize((image_size, image_size)),
        transforms.ToTensor(),
        transforms.Normalize(MEAN, STD),
    ])

    base = LeRobotDatasetIterator(out_root, action_dim=action_dim)

    class _DS(Dataset):
        def __len__(self):
            return len(base)

        def __getitem__(self, i):
            sample = base[i]
            img = sample.get("image")
            if img is None:
                img = np.zeros((image_size, image_size, 3), np.uint8)
            img_t = transform(Image.fromarray(ensure_rgb(img)))
            enc = tokenizer(
                sample["instruction"],
                max_length=max_text_length,
                padding="max_length",
                truncation=True,
                return_tensors="pt",
            )
            action = torch.tensor(sample["action"], dtype=torch.float32)
            if len(action) < action_dim:
                action = torch.cat([action, torch.zeros(action_dim - len(action))])
            return {
                "images": img_t,
                "input_ids": enc.input_ids.squeeze(0),
                "attention_mask": enc.attention_mask.squeeze(0),
                "actions": action[:action_dim],
            }

    return _DS()


def create_lerobot_dataloader(
    out_root: str,
    tokenizer,
    batch_size=16,
    image_size=224,
    max_text_length=64,
    action_dim=7,
    is_train=True,
    num_workers=0,
):
    """创建可直接训练的数据加载器（保持与 0200-vla-imitation 接口一致）。"""
    import torch
    from torch.utils.data import DataLoader

    ds = _torch_dataset(out_root, tokenizer, image_size, max_text_length,
                        action_dim, is_train)

    def collate(batch):
        return {k: torch.stack([b[k] for b in batch]) for k in batch[0]}

    return DataLoader(ds, batch_size=batch_size, shuffle=is_train,
                      num_workers=num_workers, collate_fn=collate)