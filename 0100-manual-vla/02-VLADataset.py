"""
02-VLADataset.py — VLA 数据加载组件
=====================================
VLA 训练需要三种模态的数据：
  - 图像 (Image):  机器人观测到的 RGB 画面
  - 文本 (Text):   任务指令，如 "pick up the red block"
  - 动作 (Action): 监督标签，如末端位姿 (x,y,z,qx,qy,qz,qw) + 夹爪开合

本文件包含:
  1. VLADataset         — 从 JSON 标注文件加载真实数据
  2. SyntheticVLADataset — 纯内存假数据，用于快速验证模型/训练流程
  3. collate_fn         — DataLoader 的 batch 拼接函数
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Tuple, Optional

import torch
from torch.utils.data import Dataset, DataLoader
from torchvision import transforms
from PIL import Image
from transformers import AutoTokenizer


# ═══════════════════════════════════════════════════════════════
# 1. 图像预处理: resize + 归一化
# ═══════════════════════════════════════════════════════════════

# ImageNet 标准均值/标准差 (ViT/BERT 预训练时用的)
IMAGENET_MEAN = [0.485, 0.456, 0.406]
IMAGENET_STD  = [0.229, 0.224, 0.225]

def get_image_transform(image_size: int = 224, is_train: bool = True) -> transforms.Compose:
    """构建图像预处理 pipeline"""
    transform_list = [
        transforms.Resize((image_size, image_size)),
        transforms.ToTensor(),                          # [0,255] → [0,1] float
        transforms.Normalize(IMAGENET_MEAN, IMAGENET_STD),  # ImageNet 标准化
    ]
    if is_train:
        # 训练时加入数据增强，提升泛化能力
        transform_list.insert(1, transforms.RandomHorizontalFlip(p=0.5))
        transform_list.insert(2, transforms.ColorJitter(brightness=0.2, contrast=0.2, saturation=0.2))

    return transforms.Compose(transform_list)


# ═══════════════════════════════════════════════════════════════
# 2. VLADataset — 从磁盘加载真实数据
# ═══════════════════════════════════════════════════════════════

class VLADataset(Dataset):
    """
    标准 VLA 数据集，从 JSON 标注文件读取样本。

    JSON 格式示例:
    [
      {
        "image": "episode_0/frame_000.jpg",
        "instruction": "pick up the red block",
        "action": [0.12, -0.34, 0.56, 0.0, 0.0, 0.0, 1.0, 0.0]
      },
      ...
    ]

    action 维度说明 (8维示例):
      [x, y, z, qx, qy, qz, qw, gripper]
    """

    def __init__(
        self,
        json_path: str,
        image_root: str,
        tokenizer: AutoTokenizer,
        image_size: int = 224,
        max_text_length: int = 64,
        is_train: bool = True,
    ):
        """
        Args:
            json_path:       标注 JSON 文件路径
            image_root:      图像文件的根目录
            tokenizer:       HuggingFace tokenizer 实例
            image_size:      图像 resize 尺寸
            max_text_length: 文本最大 token 数 (截断/填充)
            is_train:        是否为训练模式 (决定是否做增强)
        """
        with open(json_path, "r", encoding="utf-8") as f:
            self.samples = json.load(f)

        self.image_root = Path(image_root)
        self.tokenizer = tokenizer
        self.max_text_length = max_text_length
        self.transform = get_image_transform(image_size, is_train)

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, idx: int) -> Dict[str, torch.Tensor]:
        sample = self.samples[idx]

        # ── 图像加载 & 预处理 ──
        img_path = self.image_root / sample["image"]
        image = Image.open(img_path).convert("RGB")
        image_tensor = self.transform(image)  # [3, H, W]

        # ── 文本 token 化 ──
        instruction = sample["instruction"]
        tokens = self.tokenizer(
            instruction,
            max_length=self.max_text_length,
            padding="max_length",
            truncation=True,
            return_tensors="pt",
        )
        input_ids = tokens.input_ids.squeeze(0)        # [L]
        attention_mask = tokens.attention_mask.squeeze(0)  # [L]

        # ── 动作标签 ──
        action = torch.tensor(sample["action"], dtype=torch.float32)  # [A]

        return {
            "images": image_tensor,
            "input_ids": input_ids,
            "attention_mask": attention_mask,
            "actions": action,
        }

    @property
    def action_dim(self) -> int:
        """从第一条样本推断动作维度"""
        return len(self.samples[0]["action"])


# ═══════════════════════════════════════════════════════════════
# 3. SyntheticVLADataset — 纯内存假数据 (快速验证用)
# ═══════════════════════════════════════════════════════════════

class SyntheticVLADataset(Dataset):
    """
    合成数据集: 不需要磁盘文件，全在内存中生成随机数据。
    用于快速验证模型架构和训练流程是否能跑通。

    生成的数据包括:
      - 随机噪声图像 [3, H, W]
      - 随机文本 token [L]
      - 随机动作标签 [A]
    """

    # 模拟的机器人操作指令
    DUMMY_INSTRUCTIONS = [
        "pick up the red block",
        "place the block on the table",
        "push the object forward",
        "grasp the cup",
        "move to the left",
        "open the drawer",
        "close the gripper",
        "rotate clockwise",
        "reach the blue sphere",
        "stack the green cube on top",
    ]

    def __init__(
        self,
        num_samples: int,
        tokenizer: AutoTokenizer,
        action_dim: int = 7,
        image_size: int = 224,
        max_text_length: int = 64,
        is_train: bool = True,
    ):
        """
        Args:
            num_samples:     生成多少条假样本
            tokenizer:       HuggingFace tokenizer
            action_dim:      动作维度
            image_size:      图像尺寸
            max_text_length: 文本最大长度
            is_train:        是否训练模式
        """
        self.num_samples = num_samples
        self.tokenizer = tokenizer
        self.action_dim = action_dim
        self.max_text_length = max_text_length
        self.transform = get_image_transform(image_size, is_train)

        # 预先生成随机图像和动作 (避免每次 __getitem__ 重新生成)
        self.dummy_images = torch.randn(num_samples, 3, image_size, image_size)
        self.dummy_actions = torch.randn(num_samples, action_dim)

        # 预生成 tokenized 文本
        import random
        rng = random.Random(42)
        chosen_texts = [rng.choice(self.DUMMY_INSTRUCTIONS) for _ in range(num_samples)]
        encoded = tokenizer(
            chosen_texts,
            max_length=max_text_length,
            padding="max_length",
            truncation=True,
            return_tensors="pt",
        )
        self.input_ids = encoded.input_ids       # [N, L]
        self.attention_mask = encoded.attention_mask  # [N, L]

    def __len__(self) -> int:
        return self.num_samples

    def __getitem__(self, idx: int) -> Dict[str, torch.Tensor]:
        return {
            "images": self.dummy_images[idx],
            "input_ids": self.input_ids[idx],
            "attention_mask": self.attention_mask[idx],
            "actions": self.dummy_actions[idx],
        }


# ═══════════════════════════════════════════════════════════════
# 4. collate_fn — DataLoader 的 batch 拼装函数
# ═══════════════════════════════════════════════════════════════

def collate_fn(batch: List[Dict[str, torch.Tensor]]) -> Dict[str, torch.Tensor]:
    """
    将 list of dict 转换为 dict of batched tensors。
    DataLoader 默认行为是 stack list of tensors，但 dict 需要自定义。
    """
    return {
        "images":          torch.stack([item["images"]          for item in batch], dim=0),
        "input_ids":       torch.stack([item["input_ids"]       for item in batch], dim=0),
        "attention_mask":  torch.stack([item["attention_mask"]  for item in batch], dim=0),
        "actions":         torch.stack([item["actions"]         for item in batch], dim=0),
    }


# ═══════════════════════════════════════════════════════════════
# 5. 快速验证
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 60)
    print("VLADataset 数据加载验证")
    print("=" * 60)

    # 加载 tokenizer
    tokenizer = AutoTokenizer.from_pretrained("bert-base-uncased")

    # ── 测试 SyntheticVLADataset ──
    print("\n[1] SyntheticVLADataset 测试")
    dataset = SyntheticVLADataset(
        num_samples=128,
        tokenizer=tokenizer,
        action_dim=7,
        image_size=224,
        max_text_length=32,
    )
    print(f"  数据集大小: {len(dataset)}")

    sample = dataset[0]
    print(f"  images shape:         {sample['images'].shape}")          # [3, 224, 224]
    print(f"  input_ids shape:      {sample['input_ids'].shape}")       # [32]
    print(f"  attention_mask shape: {sample['attention_mask'].shape}")  # [32]
    print(f"  actions shape:        {sample['actions'].shape}")         # [7]

    # ── 测试 DataLoader ──
    print("\n[2] DataLoader 测试")
    dataloader = DataLoader(dataset, batch_size=16, shuffle=True, collate_fn=collate_fn)
    batch = next(iter(dataloader))
    print(f"  batch['images'] shape:         {batch['images'].shape}")          # [16, 3, 224, 224]
    print(f"  batch['input_ids'] shape:      {batch['input_ids'].shape}")       # [16, 32]
    print(f"  batch['attention_mask'] shape: {batch['attention_mask'].shape}")  # [16, 32]
    print(f"  batch['actions'] shape:        {batch['actions'].shape}")         # [16, 7]

    # ── 测试真实 VLADataset (如果有 JSON 文件) ──
    print("\n[3] VLADataset 测试 (需要真实 JSON 文件)")
    print("  提示: 创建示例数据文件...")
    dummy_json_path = Path(__file__).parent / "_dummy_data.json"
    dummy_image_dir = Path(__file__).parent / "_dummy_images"
    dummy_image_dir.mkdir(exist_ok=True)

    # 造几条假标注
    dummy_samples = []
    for i in range(8):
        # 生成一张假图片
        img = Image.new("RGB", (224, 224), color=(i * 30, 100, 200 - i * 20))
        img_name = f"frame_{i:03d}.jpg"
        img.save(dummy_image_dir / img_name)

        dummy_samples.append({
            "image": img_name,
            "instruction": f"task instruction {i}",
            "action": [0.1 * i, -0.2, 0.5, 0.0, 0.0, 0.0, 1.0],
        })

    with open(dummy_json_path, "w") as f:
        json.dump(dummy_samples, f, indent=2)

    try:
        real_dataset = VLADataset(
            json_path=str(dummy_json_path),
            image_root=str(dummy_image_dir),
            tokenizer=tokenizer,
        )
        sample = real_dataset[0]
        print(f"  VLADataset 加载成功! 共 {len(real_dataset)} 条, action_dim={real_dataset.action_dim}")
        print(f"  images shape: {sample['images'].shape}")
        print(f"  actions:      {sample['actions'].tolist()}")
    finally:
        # 清理测试文件
        import shutil
        dummy_json_path.unlink(missing_ok=True)
        shutil.rmtree(dummy_image_dir, ignore_errors=True)

    print(f"\n{'=' * 60}")
    print("数据加载组件验证通过!")
    print(f"{'=' * 60}")