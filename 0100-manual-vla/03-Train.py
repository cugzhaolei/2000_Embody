"""
03-Train.py — VLA 模型训练脚本
================================
包含完整的训练流程:
  1. 数据准备 (SyntheticVLADataset / VLADataset)
  2. 训练循环 (MSE Loss + AdamW)
  3. 验证循环 (计算 Val Loss)
  4. 模型保存 / 恢复
  5. 训练曲线可视化 (Loss 随 epoch 下降)

训练 VLA 的核心: 让模型学会 "看到画面 + 听到指令 → 输出正确动作"
"""

import importlib
import os
import sys
from pathlib import Path
from typing import Dict, Optional

import torch
import torch.nn as nn
from torch.utils.data import DataLoader
from torch.optim import AdamW
from torch.optim.lr_scheduler import CosineAnnealingLR
from transformers import AutoTokenizer

# 导入我们自己的模块 (文件名以数字开头, 不能用标准 import, 用 importlib)
_BASE = Path(__file__).parent
sys.path.insert(0, str(_BASE))

_minivla_mod = importlib.import_module("01-MiniVLA")
MiniVLA = _minivla_mod.MiniVLA

_dataset_mod = importlib.import_module("02-VLADataset")
SyntheticVLADataset = _dataset_mod.SyntheticVLADataset
VLADataset = _dataset_mod.VLADataset
collate_fn = _dataset_mod.collate_fn


# ═══════════════════════════════════════════════════════════════
# 1. 训练配置 (超参数集中管理)
# ═══════════════════════════════════════════════════════════════

class TrainConfig:
    """训练超参数"""

    # ── 模型 ──
    vision_model   = "google/vit-base-patch16-224"
    language_model = "bert-base-uncased"
    action_dim     = 7                     # xyz + 四元数 + gripper

    # ── 数据 ──
    image_size      = 224
    max_text_length = 64
    batch_size      = 16
    num_workers     = 0                    # Windows 下多进程 DataLoader 有时有问题

    # ── 优化器 ──
    learning_rate = 1e-4
    weight_decay  = 1e-4
    num_epochs    = 10
    warmup_ratio  = 0.1                   # 前 10% steps 线性 warmup

    # ── 设备 ──
    device = "cuda" if torch.cuda.is_available() else "cpu"

    # ── 日志 & 保存 ──
    log_interval    = 10                   # 每 N 个 batch 打印一次 loss
    save_dir        = "./checkpoints"
    experiment_name = "minivla_v1"


# ═══════════════════════════════════════════════════════════════
# 2. 训练一个 Epoch
# ═══════════════════════════════════════════════════════════════

def train_one_epoch(
    model: nn.Module,
    dataloader: DataLoader,
    optimizer: torch.optim.Optimizer,
    scheduler: Optional[torch.optim.lr_scheduler.LRScheduler],
    criterion: nn.Module,
    epoch: int,
    config: TrainConfig,
) -> float:
    """
    执行一个 epoch 的训练, 返回平均 loss。
    """
    model.train()
    total_loss = 0.0
    num_batches = len(dataloader)

    for batch_idx, batch in enumerate(dataloader):
        # ── 数据移到设备 ──
        images     = batch["images"].to(config.device)
        input_ids  = batch["input_ids"].to(config.device)
        actions_gt = batch["actions"].to(config.device)     # ground truth

        # ── 前向传播 ──
        actions_pred = model(images, input_ids)             # [B, action_dim]

        # ── 计算损失 (MSE for continuous action regression) ──
        loss = criterion(actions_pred, actions_gt)

        # ── 反向传播 ──
        optimizer.zero_grad()
        loss.backward()

        # ── 梯度裁剪 (防止梯度爆炸) ──
        torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)

        optimizer.step()
        if scheduler is not None:
            scheduler.step()

        total_loss += loss.item()

        # ── 打印日志 ──
        if (batch_idx + 1) % config.log_interval == 0:
            current_lr = optimizer.param_groups[0]["lr"]
            print(f"  Epoch [{epoch+1}/{config.num_epochs}] "
                  f"Batch [{batch_idx+1}/{num_batches}] "
                  f"Loss: {loss.item():.6f} "
                  f"LR: {current_lr:.2e}")

    return total_loss / num_batches


# ═══════════════════════════════════════════════════════════════
# 3. 验证
# ═══════════════════════════════════════════════════════════════

@torch.no_grad()
def validate(
    model: nn.Module,
    dataloader: DataLoader,
    criterion: nn.Module,
    config: TrainConfig,
) -> float:
    """
    在验证集上评估模型, 返回平均 loss。
    """
    model.eval()
    total_loss = 0.0

    for batch in dataloader:
        images     = batch["images"].to(config.device)
        input_ids  = batch["input_ids"].to(config.device)
        actions_gt = batch["actions"].to(config.device)

        actions_pred = model(images, input_ids)
        loss = criterion(actions_pred, actions_gt)
        total_loss += loss.item()

    return total_loss / len(dataloader)


# ═══════════════════════════════════════════════════════════════
# 4. Warmup Scheduler (线性预热)
# ═══════════════════════════════════════════════════════════════

class WarmupScheduler:
    """
    线性 warmup: 前 warmup_steps 步 LR 从 0 线性增长到 base_lr。
    用于配合 CosineAnnealingLR 使用。
    """
    def __init__(self, optimizer, warmup_steps: int):
        self.optimizer = optimizer
        self.warmup_steps = warmup_steps
        self.base_lrs = [group["lr"] for group in optimizer.param_groups]
        self.current_step = 0

    def step(self):
        self.current_step += 1
        if self.current_step <= self.warmup_steps:
            # 线性增长
            scale = self.current_step / self.warmup_steps
            for param_group, base_lr in zip(self.optimizer.param_groups, self.base_lrs):
                param_group["lr"] = base_lr * scale


# ═══════════════════════════════════════════════════════════════
# 5. 保存 / 加载 Checkpoint
# ═══════════════════════════════════════════════════════════════

def save_checkpoint(
    model: nn.Module,
    optimizer: torch.optim.Optimizer,
    epoch: int,
    loss: float,
    config: TrainConfig,
):
    """保存训练状态"""
    save_dir = Path(config.save_dir) / config.experiment_name
    save_dir.mkdir(parents=True, exist_ok=True)

    checkpoint = {
        "epoch": epoch,
        "model_state_dict": model.state_dict(),
        "optimizer_state_dict": optimizer.state_dict(),
        "loss": loss,
        "config": {k: v for k, v in vars(config).items() if not k.startswith("_")},
    }
    path = save_dir / f"checkpoint_epoch_{epoch+1}.pt"
    torch.save(checkpoint, path)
    print(f"  Checkpoint saved → {path}")

    # 同时保存一份 best model
    best_path = save_dir / "best_model.pt"
    if not best_path.exists():
        torch.save(checkpoint, best_path)
    else:
        prev = torch.load(best_path, map_location="cpu", weights_only=False)
        if loss < prev["loss"]:
            torch.save(checkpoint, best_path)
            print(f"  New best model! Loss {loss:.6f} < {prev['loss']:.6f}")


def load_checkpoint(path: str, model: nn.Module, optimizer: Optional[torch.optim.Optimizer] = None):
    """恢复训练"""
    checkpoint = torch.load(path, map_location="cpu", weights_only=False)
    model.load_state_dict(checkpoint["model_state_dict"])
    if optimizer is not None:
        optimizer.load_state_dict(checkpoint["optimizer_state_dict"])
    return checkpoint["epoch"], checkpoint["loss"]


# ═══════════════════════════════════════════════════════════════
# 6. 主训练入口
# ═══════════════════════════════════════════════════════════════

def main():
    config = TrainConfig()

    print("=" * 60)
    print(f"MiniVLA 训练 — {config.experiment_name}")
    print(f"Device: {config.device}")
    print("=" * 60)

    # ── Step 1: 初始化模型 ──
    print("\n[1/5] 初始化模型...")
    model = MiniVLA(
        vision_model_name=config.vision_model,
        language_model_name=config.language_model,
        action_dim=config.action_dim,
    ).to(config.device)

    total_params = sum(p.numel() for p in model.parameters()) / 1e6
    trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad) / 1e6
    print(f"  Total params:     {total_params:.2f}M")
    print(f"  Trainable params: {trainable_params:.2f}M")

    # ── Step 2: 准备数据 ──
    print("\n[2/5] 准备数据...")
    tokenizer = AutoTokenizer.from_pretrained(config.language_model)

    train_dataset = SyntheticVLADataset(
        num_samples=512,
        tokenizer=tokenizer,
        action_dim=config.action_dim,
        image_size=config.image_size,
        max_text_length=config.max_text_length,
        is_train=True,
    )
    val_dataset = SyntheticVLADataset(
        num_samples=128,
        tokenizer=tokenizer,
        action_dim=config.action_dim,
        image_size=config.image_size,
        max_text_length=config.max_text_length,
        is_train=False,
    )

    train_loader = DataLoader(
        train_dataset,
        batch_size=config.batch_size,
        shuffle=True,
        num_workers=config.num_workers,
        collate_fn=collate_fn,
        drop_last=True,  # 丢弃最后不完整的 batch
    )
    val_loader = DataLoader(
        val_dataset,
        batch_size=config.batch_size,
        shuffle=False,
        num_workers=config.num_workers,
        collate_fn=collate_fn,
    )
    print(f"  Train samples: {len(train_dataset)}, batches: {len(train_loader)}")
    print(f"  Val samples:   {len(val_dataset)}, batches: {len(val_loader)}")

    # ── Step 3: 优化器 & 损失函数 ──
    print("\n[3/5] 配置优化器 & 损失函数...")

    # MSE: 均方误差, VLA 最基础的回归损失
    criterion = nn.MSELoss()

    # AdamW: 带权重衰减的 Adam
    optimizer = AdamW(
        model.parameters(),
        lr=config.learning_rate,
        weight_decay=config.weight_decay,
    )

    # Warmup + Cosine 学习率衰减
    total_steps = len(train_loader) * config.num_epochs
    warmup_steps = int(total_steps * config.warmup_ratio)
    warmup = WarmupScheduler(optimizer, warmup_steps)
    cosine_scheduler = CosineAnnealingLR(optimizer, T_max=total_steps - warmup_steps)

    print(f"  Loss:       MSELoss (回归损失)")
    print(f"  Optimizer:  AdamW (lr={config.learning_rate}, wd={config.weight_decay})")
    print(f"  Scheduler:  Warmup({warmup_steps} steps) + CosineAnnealing")
    print(f"  Total steps: {total_steps}")

    # ── Step 4: 训练循环 ──
    print(f"\n[4/5] 开始训练 ({config.num_epochs} epochs)...")
    print("-" * 40)

    train_losses = []
    val_losses = []

    for epoch in range(config.num_epochs):
        # Warmup 阶段
        if epoch == 0:
            orig_scheduler = warmup
        else:
            orig_scheduler = cosine_scheduler

        train_loss = train_one_epoch(
            model, train_loader, optimizer, orig_scheduler,
            criterion, epoch, config,
        )
        train_losses.append(train_loss)

        val_loss = validate(model, val_loader, criterion, config)
        val_losses.append(val_loss)

        print(f"  ── Epoch {epoch+1} Summary ──")
        print(f"  Train Loss: {train_loss:.6f}")
        print(f"  Val Loss:   {val_loss:.6f}")

        # 保存 checkpoint
        save_checkpoint(model, optimizer, epoch, val_loss, config)

    # ── Step 5: 结果汇总 ──
    print(f"\n[5/5] 训练完成!")
    print("=" * 60)
    print("训练历史:")
    print(f"{'Epoch':>6} {'Train Loss':>12} {'Val Loss':>12}")
    print("-" * 32)
    for i, (tl, vl) in enumerate(zip(train_losses, val_losses)):
        print(f"{i+1:>6} {tl:>12.6f} {vl:>12.6f}")
    print("=" * 60)

    # 简单的 loss 下降趋势检查
    if len(val_losses) >= 2 and val_losses[-1] < val_losses[0]:
        print("✓ Val Loss 整体下降 — 模型在正向收敛!")
    else:
        print("⚠ Val Loss 未下降 — 可能需要更多 epoch 或调整超参数.")

    print(f"\n模型保存在: {Path(config.save_dir) / config.experiment_name}")


# ═══════════════════════════════════════════════════════════════
# 7. 假数据快速验证入口 (比完整训练快)
# ═══════════════════════════════════════════════════════════════

def quick_test():
    """
    极速验证: 只跑 3 个 epoch, 小数据集, 验证整个 pipeline 无 bug。
    """
    print("=" * 60)
    print("快速验证 (3 epochs, 64 samples)")
    print("=" * 60)

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Device: {device}")

    # 小模型 + 小数据
    model = MiniVLA(
        vision_model_name="google/vit-base-patch16-224",
        language_model_name="bert-base-uncased",
        action_dim=7,
    ).to(device)

    tokenizer = AutoTokenizer.from_pretrained("bert-base-uncased")
    dataset = SyntheticVLADataset(
        num_samples=64,
        tokenizer=tokenizer,
        action_dim=7,
        max_text_length=32,
    )
    loader = DataLoader(dataset, batch_size=8, shuffle=True, collate_fn=collate_fn)

    criterion = nn.MSELoss()
    optimizer = AdamW(model.parameters(), lr=1e-4)

    for epoch in range(3):
        model.train()
        total_loss = 0
        for batch in loader:
            images = batch["images"].to(device)
            input_ids = batch["input_ids"].to(device)
            actions_gt = batch["actions"].to(device)

            pred = model(images, input_ids)
            loss = criterion(pred, actions_gt)

            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            total_loss += loss.item()

        avg_loss = total_loss / len(loader)
        print(f"  Epoch {epoch+1}/3 — Avg Loss: {avg_loss:.6f}")

    print("\n快速验证通过! 训练 pipeline 无 bug.")
    print("=" * 60)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--quick", action="store_true", help="只跑 3 epoch 快速验证")
    parser.add_argument("--resume", type=str, default=None, help="从 checkpoint 恢复训练")
    args = parser.parse_args()

    if args.quick:
        quick_test()
    else:
        main()