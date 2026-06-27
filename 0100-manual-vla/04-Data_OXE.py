"""
04-Data_OXE.py — Open-X-Embodiment 数据加载器
===============================================
从 Open-X-Embodiment 数据集中加载真实的机器人操作数据。

Open-X-Embodiment (OXE) 是 Google DeepMind 联合多家机构发布的
大规模机器人操作数据集，包含 60+ 个机器人数据集，统一为 RLDS 格式。

本文件支持两种加载方式:
  1. tensorflow_datasets (推荐): 自动下载, 无需手动处理
  2. 本地目录: 从预先下载的 RLDS/TFRecord 文件加载

数据格式:
  观测: RGB 图像 + 自然语言指令
  动作: 末端位姿变化 (dx, dy, dz, droll, dpitch, dyaw) + 夹爪开合

使用方法:
  python 04-Data_OXE.py --quick   # 下载并验证数据
  python 04-Data_OXE.py --subset  # 下载指定子集
"""

import os
import sys
import json
import random
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Iterator
from dataclasses import dataclass, field

import numpy as np
import torch
from torch.utils.data import Dataset, DataLoader, IterableDataset
from PIL import Image
from transformers import AutoTokenizer
from torchvision import transforms


# ═══════════════════════════════════════════════════════════════
# 1. 支持的 OXE 数据集子集
# ═══════════════════════════════════════════════════════════════

@dataclass
class OXEDatasetInfo:
    """OXE 数据集子集元信息"""
    name: str
    tfds_name: str
    description: str
    action_dim: int = 7             # 典型: dx,dy,dz,dr,dp,dy,grip
    image_size: Tuple[int, int] = (224, 224)
    sample_count: int = 0


# Open-X-Embodiment 中常用的数据集子集
OXE_SUBSETS = {
    "fractal": OXEDatasetInfo(
        name="fractal",
        tfds_name="fractal20220817_data",
        description="RT-1 数据集: 桌面操作, 13 台机器人, 130k+ episodes",
        action_dim=7,
        image_size=(224, 224),
        sample_count=130000,
    ),
    "bridge": OXEDatasetInfo(
        name="bridge",
        tfds_name="bridge_dataset",
        description="BridgeData V2: WidowX 机器人, 厨房/桌面操作, 60k+ trajectories",
        action_dim=7,
        image_size=(224, 224),
        sample_count=60000,
    ),
    "kuka": OXEDatasetInfo(
        name="kuka",
        tfds_name="kuka",
        description="KUKA 机器人: 拾取放置任务",
        action_dim=7,
        image_size=(224, 224),
        sample_count=500000,
    ),
    "berkeley_autolab": OXEDatasetInfo(
        name="berkeley_autolab",
        tfds_name="berkeley_autolab_ur5",
        description="Berkeley UR5: 拾取放置, 推拉等任务",
        action_dim=7,
        image_size=(224, 224),
        sample_count=90000,
    ),
    "usc_cloth": OXEDatasetInfo(
        name="usc_cloth",
        tfds_name="usc_cloth_sim",
        description="USC Cloth Sim: 布料操作仿真数据",
        action_dim=4,
        image_size=(224, 224),
        sample_count=50000,
    ),
}


# ═══════════════════════════════════════════════════════════════
# 2. 图像预处理
# ═══════════════════════════════════════════════════════════════

IMAGENET_MEAN = [0.485, 0.456, 0.406]
IMAGENET_STD  = [0.229, 0.224, 0.225]

def get_image_transform(image_size: int = 224, is_train: bool = True) -> transforms.Compose:
    t = [
        transforms.Resize((image_size, image_size)),
        transforms.ToTensor(),
        transforms.Normalize(IMAGENET_MEAN, IMAGENET_STD),
    ]
    if is_train:
        t.insert(1, transforms.RandomHorizontalFlip(p=0.5))
        t.insert(2, transforms.ColorJitter(brightness=0.2, contrast=0.2))
    return transforms.Compose(t)


# ═══════════════════════════════════════════════════════════════
# 3. OXE 数据加载 (via tensorflow_datasets)
# ═══════════════════════════════════════════════════════════════

class OXEDataset(Dataset):
    """
    从 tensorflow_datasets 加载 Open-X-Embodiment 数据,
    转换为 PyTorch Dataset 格式。

    每个样本包含:
      - image:        RGB 观测图像 [3, H, W]
      - instruction:  tokenized 文本指令 [L]
      - action:       动作标签 [A]
    """

    def __init__(
        self,
        dataset_name: str = "fractal20220817_data",
        tokenizer: AutoTokenizer = None,
        image_size: int = 224,
        max_text_length: int = 64,
        max_samples: Optional[int] = None,
        is_train: bool = True,
        split: str = "train",
        data_dir: Optional[str] = None,
    ):
        """
        Args:
            dataset_name:    tfds 数据集名 (如 "fractal20220817_data")
            tokenizer:       HuggingFace tokenizer (None 则自动加载 bert-base-uncased)
            image_size:      图像 resize 目标尺寸
            max_text_length: 文本最大 token 数
            max_samples:     最多加载多少条 (None = 全部, 用于快速测试)
            is_train:        是否训练模式 (影响数据增强)
            split:           tfds split ("train", "val", "train[:10%]")
            data_dir:        tfds 数据存储目录 (None = 默认 ~/tensorflow_datasets)
        """
        self.max_samples = max_samples
        self.is_train = is_train
        self.image_size = image_size
        self.max_text_length = max_text_length

        # Tokenizer
        if tokenizer is None:
            self.tokenizer = AutoTokenizer.from_pretrained("bert-base-uncased")
        else:
            self.tokenizer = tokenizer

        # 图像变换
        self.transform = get_image_transform(image_size, is_train)

        # ── 加载 tfds 数据 ──
        print(f"Loading OXE dataset: {dataset_name}  (split={split})")
        try:
            import tensorflow_datasets as tfds
        except ImportError:
            raise ImportError(
                "请先安装 tensorflow_datasets:\n"
                "  pip install tensorflow tensorflow_datasets\n"
                "或使用 SyntheticVLADataset 做假数据训练。"
            )

        builder_kwargs = {}
        if data_dir is not None:
            builder_kwargs["data_dir"] = data_dir

        self.ds = tfds.load(
            dataset_name,
            split=split,
            shuffle_files=is_train,
            **builder_kwargs,
        )

        # 转换为 list (小数据集) 或保持 iterator
        print(f"  Converting to memory... (this may take a while)")
        self.samples = list(self._iter_dataset(self.ds))
        print(f"  Loaded {len(self.samples)} samples")

        # 推断 action_dim
        if len(self.samples) > 0:
            self.action_dim = len(self.samples[0]["action"])
        else:
            self.action_dim = 7

    def _iter_dataset(self, ds) -> Iterator[dict]:
        """迭代 tfds dataset, 提取 image / instruction / action"""
        count = 0
        for episode in ds:
            # OXE 数据按 episode 组织, 每个 episode 包含多个 step
            steps = list(episode["steps"])
            instruction = self._extract_instruction(episode)

            for step in steps:
                if self.max_samples and count >= self.max_samples:
                    return

                try:
                    image = self._extract_image(step)
                    action = self._extract_action(step)
                except (KeyError, IndexError, TypeError):
                    continue

                if image is None or action is None:
                    continue

                count += 1
                yield {
                    "image": image,
                    "instruction": instruction,
                    "action": np.array(action, dtype=np.float32),
                }

    def _extract_instruction(self, episode) -> str:
        """从 episode 中提取自然语言指令"""
        # 尝试多种可能的字段名
        ep = episode
        if isinstance(ep, dict):
            for key in ["description", "language_instruction", "instruction", "text"]:
                if key in ep:
                    val = ep[key]
                    if isinstance(val, bytes):
                        val = val.decode("utf-8")
                    if isinstance(val, np.ndarray):
                        val = val.item()
                        if isinstance(val, bytes):
                            val = val.decode("utf-8")
                    return str(val)
        return "do something"

    def _extract_image(self, step) -> Optional[np.ndarray]:
        """从 step 中提取 RGB 图像"""
        obs = step.get("observation", step)
        if isinstance(obs, dict):
            for key in ["image", "rgb", "image_0", "cam_0", "front_rgb"]:
                if key in obs:
                    img = obs[key]
                    if isinstance(img, np.ndarray):
                        return self._preprocess_image(img)
                    if isinstance(img, dict):
                        # 有些数据集 image 是 dict {"encoded": ..., "shape": ...}
                        if "encoded" in img:
                            return self._preprocess_image(img["encoded"])
        return None

    def _preprocess_image(self, img: np.ndarray) -> np.ndarray:
        """标准化图像格式 → [H, W, 3] uint8"""
        img = np.asarray(img)
        if img.dtype == np.uint8:
            pass
        elif img.max() <= 1.0:
            img = (img * 255).astype(np.uint8)

        # 处理不同形状
        if img.ndim == 2:
            img = np.stack([img] * 3, axis=-1)  # 灰度 → RGB
        elif img.shape[-1] not in (3, 4):
            img = img.transpose(1, 2, 0)  # [C, H, W] → [H, W, C]

        if img.shape[-1] == 4:
            img = img[..., :3]  # RGBA → RGB

        return img

    def _extract_action(self, step) -> Optional[np.ndarray]:
        """从 step 中提取动作"""
        if "action" in step:
            act = step["action"]
            if isinstance(act, dict):
                # 有些数据集 action 是嵌套字典
                parts = []
                for k in sorted(act.keys()):
                    parts.append(np.asarray(act[k]).flatten())
                return np.concatenate(parts) if parts else None
            return np.asarray(act).flatten()
        return None

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, idx: int) -> Dict[str, torch.Tensor]:
        sample = self.samples[idx]

        # ── 图像 ──
        image_np = sample["image"]
        image_pil = Image.fromarray(image_np)
        image_tensor = self.transform(image_pil)  # [3, H, W]

        # ── 文本 ──
        instruction = sample["instruction"]
        encoded = self.tokenizer(
            instruction,
            max_length=self.max_text_length,
            padding="max_length",
            truncation=True,
            return_tensors="pt",
        )

        # ── 动作 ──
        action = torch.from_numpy(sample["action"])

        return {
            "images": image_tensor,
            "input_ids": encoded.input_ids.squeeze(0),
            "attention_mask": encoded.attention_mask.squeeze(0),
            "actions": action,
        }


# ═══════════════════════════════════════════════════════════════
# 4. OXE 数据下载器 (无需 tfds, 从 HuggingFace 下载预处理子集)
# ═══════════════════════════════════════════════════════════════

class OXEHuggingFaceDataset(Dataset):
    """
    从 HuggingFace datasets 加载预处理的 OXE 子集。
    比 tfds 方案更轻量, 不需要 tensorflow。

    支持的 HuggingFace 数据集:
      - "jaeheejung/fractal20220817_data_processed"  (预处理后的 RT-1)
      - "embodied-generalist/oxe_fractal20220817_data_converted"
    """

    def __init__(
        self,
        hf_dataset_name: str = "jaeheejung/fractal20220817_data_processed",
        tokenizer: AutoTokenizer = None,
        image_size: int = 224,
        max_text_length: int = 64,
        max_samples: Optional[int] = None,
        is_train: bool = True,
        split: str = "train",
    ):
        self.max_samples = max_samples
        self.is_train = is_train
        self.image_size = image_size
        self.max_text_length = max_text_length

        if tokenizer is None:
            self.tokenizer = AutoTokenizer.from_pretrained("bert-base-uncased")
        else:
            self.tokenizer = tokenizer

        self.transform = get_image_transform(image_size, is_train)

        print(f"Loading from HuggingFace: {hf_dataset_name}  (split={split})")
        try:
            from datasets import load_dataset
        except ImportError:
            raise ImportError("请安装 datasets: pip install datasets")

        # 尝试加载, 如果指定 split 不存在则用默认
        try:
            self.ds = load_dataset(hf_dataset_name, split=split)
        except Exception:
            self.ds = load_dataset(hf_dataset_name)
            if isinstance(self.ds, dict):
                self.ds = self.ds[split]

        self.action_dim = self._infer_action_dim()

        print(f"  Loaded {len(self.ds)} samples, action_dim={self.action_dim}")

    def _infer_action_dim(self) -> int:
        if len(self.ds) > 0:
            sample = self.ds[0]
            if "action" in sample:
                return len(np.asarray(sample["action"]).flatten())
        return 7

    def __len__(self) -> int:
        if self.max_samples:
            return min(self.max_samples, len(self.ds))
        return len(self.ds)

    def __getitem__(self, idx: int) -> Dict[str, torch.Tensor]:
        sample = self.ds[idx]

        # ── 图像 ──
        image = sample.get("image") or sample.get("observation_image")
        if isinstance(image, dict) and "bytes" in image:
            from io import BytesIO
            image = Image.open(BytesIO(image["bytes"]))
        elif isinstance(image, Image.Image):
            pass
        elif isinstance(image, np.ndarray):
            image = Image.fromarray(image.astype(np.uint8))
        else:
            image = Image.new("RGB", (self.image_size, self.image_size), (128, 128, 128))

        image_tensor = self.transform(image.convert("RGB"))

        # ── 文本 ──
        instruction = sample.get("language_instruction") or sample.get("instruction") or sample.get("text") or "do something"
        if isinstance(instruction, (list, np.ndarray)):
            instruction = str(instruction[0]) if len(instruction) > 0 else "do something"
        encoded = self.tokenizer(
            str(instruction),
            max_length=self.max_text_length,
            padding="max_length",
            truncation=True,
            return_tensors="pt",
        )

        # ── 动作 ──
        action = np.asarray(sample["action"], dtype=np.float32).flatten()

        return {
            "images": image_tensor,
            "input_ids": encoded.input_ids.squeeze(0),
            "attention_mask": encoded.attention_mask.squeeze(0),
            "actions": torch.from_numpy(action),
        }


# ═══════════════════════════════════════════════════════════════
# 5. 轻量模拟 OXE 数据 (无需网络, 纯本地)
# ═══════════════════════════════════════════════════════════════

class OXEInMemoryDataset(Dataset):
    """
    纯内存 OXE 风格数据集: 模拟 OXE 数据格式, 但不需要下载。
    用于在没有网络的环境下快速验证 VLA 训练流程。

    OXE 数据特征:
      - 图像: 机器人视角的桌面操作场景 (这里用随机噪声模拟)
      - 指令: 多样化的操作任务描述
      - 动作: 7维连续动作 (dx,dy,dz,dr,dp,dy,grip)
    """

    # 真实 OXE 数据集中的典型指令示例
    OXE_INSTRUCTIONS = [
        # RT-1 风格 (桌面操作)
        "pick up the red block",
        "place the block in the bowl",
        "move the banana to the plate",
        "pick up the green can and place it on the table",
        "push the blue cube to the left",
        "stack the red block on the blue block",
        "open the drawer",
        "close the drawer",
        "pick up the spoon",
        "put the apple in the basket",
        "slide the object to the right",
        "grasp the yellow block",
        "lift the cup",
        "move the eraser near the marker",
        "pick up the orange and place it near the purple object",
        # BridgeData V2 风格 (厨房/桌面)
        "put the spoon in the pot",
        "take the lid off the pot",
        "fold the cloth",
        "wipe the table",
        "pick up the knife from the rack",
        "open the microwave",
        "put the carrot on the cutting board",
        "push the button",
        "flip the pancake",
        "stir the pot",
        # KUKA 风格
        "pick the object from the bin",
        "place the peg in the hole",
        "insert the plug into the socket",
        "push the button on the panel",
        "grasp the tool from the rack",
    ]

    def __init__(
        self,
        num_samples: int = 1024,
        tokenizer: AutoTokenizer = None,
        action_dim: int = 7,
        image_size: int = 224,
        max_text_length: int = 64,
        is_train: bool = True,
        seed: int = 42,
    ):
        self.num_samples = num_samples
        self.action_dim = action_dim
        self.max_text_length = max_text_length
        self.is_train = is_train
        self.image_size = image_size

        if tokenizer is None:
            self.tokenizer = AutoTokenizer.from_pretrained("bert-base-uncased")
        else:
            self.tokenizer = tokenizer

        self.transform = get_image_transform(image_size, is_train)

        rng = random.Random(seed)

        # 预生成数据
        self.images = torch.randn(num_samples, 3, image_size, image_size)
        self.actions = torch.randn(num_samples, action_dim) * 0.1  # 小范围动作

        # 随机选择指令
        self.instructions = [rng.choice(self.OXE_INSTRUCTIONS) for _ in range(num_samples)]
        encoded = self.tokenizer(
            self.instructions,
            max_length=max_text_length,
            padding="max_length",
            truncation=True,
            return_tensors="pt",
        )
        self.input_ids = encoded.input_ids
        self.attention_mask = encoded.attention_mask

    def __len__(self):
        return self.num_samples

    def __getitem__(self, idx):
        return {
            "images": self.images[idx],
            "input_ids": self.input_ids[idx],
            "attention_mask": self.attention_mask[idx],
            "actions": self.actions[idx],
        }


# ═══════════════════════════════════════════════════════════════
# 6. 数据加载器工厂函数
# ═══════════════════════════════════════════════════════════════

def create_oxe_dataloader(
    dataset_type: str = "inmemory",   # "inmemory" | "tfds" | "huggingface"
    dataset_name: str = "fractal20220817_data",
    tokenizer: AutoTokenizer = None,
    batch_size: int = 16,
    image_size: int = 224,
    max_text_length: int = 64,
    max_samples: Optional[int] = None,
    is_train: bool = True,
    split: str = "train",
    num_workers: int = 0,
) -> DataLoader:
    """
    工厂函数: 根据 dataset_type 创建对应的 DataLoader。

    Args:
        dataset_type: "inmemory" | "tfds" | "huggingface"
        dataset_name: 数据集名称
        max_samples:  最多加载多少样本 (用于快速测试)
    """
    if tokenizer is None:
        tokenizer = AutoTokenizer.from_pretrained("bert-base-uncased")

    if dataset_type == "inmemory":
        dataset = OXEInMemoryDataset(
            num_samples=max_samples or 1024,
            tokenizer=tokenizer,
            action_dim=7,
            image_size=image_size,
            max_text_length=max_text_length,
            is_train=is_train,
        )
    elif dataset_type == "tfds":
        dataset = OXEDataset(
            dataset_name=dataset_name,
            tokenizer=tokenizer,
            image_size=image_size,
            max_text_length=max_text_length,
            max_samples=max_samples,
            is_train=is_train,
            split=split,
        )
    elif dataset_type == "huggingface":
        dataset = OXEHuggingFaceDataset(
            hf_dataset_name=dataset_name,
            tokenizer=tokenizer,
            image_size=image_size,
            max_text_length=max_text_length,
            max_samples=max_samples,
            is_train=is_train,
            split=split,
        )
    else:
        raise ValueError(f"Unknown dataset_type: {dataset_type}")

    # collate_fn
    def collate_fn(batch):
        return {
            "images": torch.stack([b["images"] for b in batch]),
            "input_ids": torch.stack([b["input_ids"] for b in batch]),
            "attention_mask": torch.stack([b["attention_mask"] for b in batch]),
            "actions": torch.stack([b["actions"] for b in batch]),
        }

    return DataLoader(
        dataset,
        batch_size=batch_size,
        shuffle=is_train,
        num_workers=num_workers,
        collate_fn=collate_fn,
        drop_last=is_train,
    )


# ═══════════════════════════════════════════════════════════════
# 7. 快速验证
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="OXE Data Loader")
    parser.add_argument("--quick", action="store_true", help="快速验证 (inmemory)")
    parser.add_argument("--tfds", action="store_true", help="使用 tensorflow_datasets 加载")
    parser.add_argument("--hf", action="store_true", help="使用 HuggingFace datasets 加载")
    parser.add_argument("--dataset", type=str, default="fractal20220817_data", help="数据集名")
    parser.add_argument("--max_samples", type=int, default=256, help="最大样本数")
    parser.add_argument("--batch_size", type=int, default=8, help="batch size")
    args = parser.parse_args()

    print("=" * 60)
    print("Open-X-Embodiment 数据加载验证")
    print("=" * 60)

    tokenizer = AutoTokenizer.from_pretrained("bert-base-uncased")

    if args.tfds:
        print("\n[TFDS 模式] 加载真实 OXE 数据...")
        loader = create_oxe_dataloader(
            dataset_type="tfds",
            dataset_name=args.dataset,
            tokenizer=tokenizer,
            batch_size=args.batch_size,
            max_samples=args.max_samples,
            is_train=True,
        )
    elif args.hf:
        print("\n[HuggingFace 模式] 加载预处理 OXE 数据...")
        loader = create_oxe_dataloader(
            dataset_type="huggingface",
            dataset_name=args.dataset,
            tokenizer=tokenizer,
            batch_size=args.batch_size,
            max_samples=args.max_samples,
            is_train=True,
        )
    else:
        print("\n[InMemory 模式] 使用模拟 OXE 数据...")
        loader = create_oxe_dataloader(
            dataset_type="inmemory",
            tokenizer=tokenizer,
            batch_size=args.batch_size,
            max_samples=args.max_samples,
            is_train=True,
        )

    batch = next(iter(loader))
    print(f"\nBatch shapes:")
    print(f"  images:         {batch['images'].shape}")
    print(f"  input_ids:      {batch['input_ids'].shape}")
    print(f"  attention_mask: {batch['attention_mask'].shape}")
    print(f"  actions:        {batch['actions'].shape}")
    print(f"  action range:   [{batch['actions'].min():.4f}, {batch['actions'].max():.4f}]")

    print(f"\n{'=' * 60}")
    print("数据加载验证通过!")
    print(f"{'=' * 60}")