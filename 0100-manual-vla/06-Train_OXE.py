"""
06-Train_OXE.py — 端到端 VLA 训练 (使用 Open-X-Embodiment 数据 + MuJoCo 可视化)
==================================================================================
完整训练流程:
  1. 加载 OXE 数据 (真实数据 / 模拟数据)
  2. 训练 MiniVLA 模型
  3. 每个 epoch 后可视化模型预测动作
  4. 保存模型和渲染结果

使用方法:
  # 使用模拟 OXE 数据快速验证
  python 06-Train_OXE.py --quick

  # 使用 tensorflow_datasets 加载真实 OXE 数据
  python 06-Train_OXE.py --tfds

  # 使用 HuggingFace datasets 加载
  python 06-Train_OXE.py --hf

  # 训练 + 可视化
  python 06-Train_OXE.py --visualize --save_dir ./output

  # 从 checkpoint 恢复
  python 06-Train_OXE.py --resume ./checkpoints/oxe_v1/checkpoint_epoch_5.pt
"""

import importlib
import os
import sys
import time
import json
from pathlib import Path
from typing import Optional, Dict, List
from dataclasses import dataclass

import torch
import torch.nn as nn
from torch.utils.data import DataLoader
from torch.optim import AdamW
from torch.optim.lr_scheduler import CosineAnnealingLR
from transformers import AutoTokenizer
import numpy as np

# 导入本地模块 (文件名以数字开头, 用 importlib)
_BASE = Path(__file__).parent
sys.path.insert(0, str(_BASE))

_minivla_mod = importlib.import_module("01-MiniVLA")
MiniVLA = _minivla_mod.MiniVLA

_oxe_data_mod = importlib.import_module("04-Data_OXE")
create_oxe_dataloader = _oxe_data_mod.create_oxe_dataloader
OXEInMemoryDataset = _oxe_data_mod.OXEInMemoryDataset
OXEDataset = _oxe_data_mod.OXEDataset
OXEHuggingFaceDataset = _oxe_data_mod.OXEHuggingFaceDataset

# 可视化模块 (可选)
try:
    _renderer_mod = importlib.import_module("05-MuJoCoRenderer")
    create_renderer = _renderer_mod.create_renderer
    visualize_vla_predictions = _renderer_mod.visualize_vla_predictions
    HAS_RENDERER = True
except ImportError:
    HAS_RENDERER = False


# ═══════════════════════════════════════════════════════════════
# 1. 训练配置
# ═══════════════════════════════════════════════════════════════

@dataclass
class TrainConfig:
    # ── 模型 ──
    vision_model: str   = "google/vit-base-patch16-224"
    language_model: str = "bert-base-uncased"
    action_dim: int     = 7

    # ── 数据 ──
    dataset_type: str   = "inmemory"          # "inmemory" | "tfds" | "huggingface"
    dataset_name: str   = "fractal20220817_data"
    max_samples: int    = 2048                 # 最多加载多少样本
    image_size: int     = 224
    max_text_length: int = 64
    batch_size: int     = 16
    num_workers: int    = 0

    # ── 优化器 ──
    learning_rate: float = 1e-4
    weight_decay: float  = 1e-4
    num_epochs: int      = 20
    warmup_ratio: float  = 0.1

    # ── 设备 ──
    device: str = "cuda" if torch.cuda.is_available() else "cpu"

    # ── 日志 & 保存 ──
    log_interval: int     = 10
    save_dir: str         = "./checkpoints"
    experiment_name: str  = "oxe_v1"
    visualize_epochs: int = 5   # 每 N 个 epoch 可视化一次

    # ── 混合精度 (可选) ──
    use_amp: bool = False  # 需要 torch.cuda.amp


# ═══════════════════════════════════════════════════════════════
# 2. 训练指标追踪
# ═══════════════════════════════════════════════════════════════

class MetricTracker:
    """追踪训练过程中的各项指标"""

    def __init__(self):
        self.train_losses: List[float] = []
        self.val_losses: List[float] = []
        self.action_errors: List[float] = []  # 每个 epoch 的平均动作误差
        self.start_time = time.time()

    def update(self, train_loss: float, val_loss: float, action_error: float = 0.0):
        self.train_losses.append(train_loss)
        self.val_losses.append(val_loss)
        self.action_errors.append(action_error)

    def summary(self) -> str:
        elapsed = time.time() - self.start_time
        lines = [
            f"Elapsed: {elapsed:.0f}s ({elapsed/60:.1f}min)",
            f"Train Loss: {self.train_losses[-1]:.6f} → {self.train_losses[0]:.6f}",
            f"Val Loss:   {self.val_losses[-1]:.6f} → {self.val_losses[0]:.6f}",
        ]
        if len(self.train_losses) > 1:
            lines.append(f"Train Δ:    {self.train_losses[-1] - self.train_losses[0]:.6f}")
            lines.append(f"Val Δ:      {self.val_losses[-1] - self.val_losses[0]:.6f}")
        return "\n".join(lines)

    def save(self, path: str):
        with open(path, "w") as f:
            json.dump({
                "train_losses": self.train_losses,
                "val_losses": self.val_losses,
                "action_errors": self.action_errors,
            }, f, indent=2)


# ═══════════════════════════════════════════════════════════════
# 3. 训练一个 Epoch
# ═══════════════════════════════════════════════════════════════

def train_one_epoch(
    model: nn.Module,
    dataloader: DataLoader,
    optimizer: torch.optim.Optimizer,
    scheduler,
    criterion: nn.Module,
    epoch: int,
    config: TrainConfig,
    scaler=None,
) -> float:
    """训练一个 epoch, 返回平均 loss"""
    model.train()
    total_loss = 0.0
    num_batches = len(dataloader)

    for batch_idx, batch in enumerate(dataloader):
        images = batch["images"].to(config.device)
        input_ids = batch["input_ids"].to(config.device)
        actions_gt = batch["actions"].to(config.device)

        # 前向传播 (可选混合精度)
        if config.use_amp and scaler is not None:
            with torch.cuda.amp.autocast():
                actions_pred = model(images, input_ids)
                loss = criterion(actions_pred, actions_gt)
        else:
            actions_pred = model(images, input_ids)
            loss = criterion(actions_pred, actions_gt)

        # 反向传播
        optimizer.zero_grad()
        if config.use_amp and scaler is not None:
            scaler.scale(loss).backward()
            scaler.unscale_(optimizer)
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            scaler.step(optimizer)
            scaler.update()
        else:
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            optimizer.step()

        if scheduler is not None:
            scheduler.step()

        total_loss += loss.item()

        if (batch_idx + 1) % config.log_interval == 0:
            lr = optimizer.param_groups[0]["lr"]
            print(f"  Epoch [{epoch+1:3d}/{config.num_epochs}] "
                  f"Batch [{batch_idx+1:4d}/{num_batches}] "
                  f"Loss: {loss.item():.6f}  LR: {lr:.2e}")

    return total_loss / num_batches


# ═══════════════════════════════════════════════════════════════
# 4. 验证
# ═══════════════════════════════════════════════════════════════

@torch.no_grad()
def validate(
    model: nn.Module,
    dataloader: DataLoader,
    criterion: nn.Module,
    config: TrainConfig,
) -> tuple:
    """验证, 返回 (平均 loss, 平均动作误差)"""
    model.eval()
    total_loss = 0.0
    total_error = 0.0

    for batch in dataloader:
        images = batch["images"].to(config.device)
        input_ids = batch["input_ids"].to(config.device)
        actions_gt = batch["actions"].to(config.device)

        actions_pred = model(images, input_ids)
        loss = criterion(actions_pred, actions_gt)

        total_loss += loss.item()
        total_error += torch.mean(torch.abs(actions_pred - actions_gt)).item()

    n = len(dataloader)
    return total_loss / n, total_error / n


# ═══════════════════════════════════════════════════════════════
# 5. Checkpoint 管理
# ═══════════════════════════════════════════════════════════════

def save_checkpoint(
    model, optimizer, epoch: int, val_loss: float, config: TrainConfig, tracker: MetricTracker
):
    save_dir = Path(config.save_dir) / config.experiment_name
    save_dir.mkdir(parents=True, exist_ok=True)

    ckpt = {
        "epoch": epoch,
        "model_state_dict": model.state_dict(),
        "optimizer_state_dict": optimizer.state_dict(),
        "val_loss": val_loss,
        "config": {k: v for k, v in vars(config).items() if not k.startswith("_")},
    }
    path = save_dir / f"checkpoint_epoch_{epoch+1:03d}.pt"
    torch.save(ckpt, path)

    # 保存 best model
    best_path = save_dir / "best_model.pt"
    if not best_path.exists():
        torch.save(ckpt, best_path)
    else:
        prev = torch.load(best_path, map_location="cpu", weights_only=False)
        if val_loss < prev["val_loss"]:
            torch.save(ckpt, best_path)
            print(f"  ★ New best model! Val Loss: {val_loss:.6f}")

    # 保存指标
    tracker.save(str(save_dir / "metrics.json"))


def load_checkpoint(path: str, model, optimizer=None):
    ckpt = torch.load(path, map_location="cpu", weights_only=False)
    model.load_state_dict(ckpt["model_state_dict"])
    if optimizer is not None:
        optimizer.load_state_dict(ckpt["optimizer_state_dict"])
    return ckpt.get("epoch", -1) + 1, ckpt.get("val_loss", float("inf"))


# ═══════════════════════════════════════════════════════════════
# 6. 可视化预测
# ═══════════════════════════════════════════════════════════════

def visualize_predictions(model, dataloader, config: TrainConfig, epoch: int):
    """使用 MuJoCo/Matplotlib 可视化模型预测"""
    if not HAS_RENDERER:
        print("  (Renderer not available, skip visualization)")
        return

    print(f"  Visualizing predictions for epoch {epoch+1}...")
    save_dir = Path(config.save_dir) / config.experiment_name / f"vis_epoch_{epoch+1:03d}"
    save_dir.mkdir(parents=True, exist_ok=True)

    try:
        renderer = create_renderer(backend="auto")
        frames = visualize_vla_predictions(
            model=model,
            dataloader=dataloader,
            renderer=renderer,
            num_steps=50,
            save_dir=str(save_dir),
            device=config.device,
        )
        print(f"  Saved {len(frames)} frames → {save_dir}")
    except Exception as e:
        print(f"  Visualization failed: {e}")


# ═══════════════════════════════════════════════════════════════
# 7. 主训练入口
# ═══════════════════════════════════════════════════════════════

def main(config: TrainConfig):
    print("=" * 60)
    print(f"MiniVLA + Open-X-Embodiment 训练")
    print(f"Experiment: {config.experiment_name}")
    print(f"Device:     {config.device}")
    print(f"Dataset:    {config.dataset_type}/{config.dataset_name}")
    print("=" * 60)

    # ── Step 1: 初始化模型 ──
    print("\n[1/6] 初始化模型...")
    model = MiniVLA(
        vision_model_name=config.vision_model,
        language_model_name=config.language_model,
        action_dim=config.action_dim,
    ).to(config.device)

    total = sum(p.numel() for p in model.parameters()) / 1e6
    trainable = sum(p.numel() for p in model.parameters() if p.requires_grad) / 1e6
    print(f"  Params: {total:.2f}M total, {trainable:.2f}M trainable")

    # ── Step 2: 准备数据 ──
    print("\n[2/6] 准备数据...")
    tokenizer = AutoTokenizer.from_pretrained(config.language_model)

    # 训练集
    train_loader = create_oxe_dataloader(
        dataset_type=config.dataset_type,
        dataset_name=config.dataset_name,
        tokenizer=tokenizer,
        batch_size=config.batch_size,
        image_size=config.image_size,
        max_text_length=config.max_text_length,
        max_samples=config.max_samples,
        is_train=True,
        split="train",
        num_workers=config.num_workers,
    )

    # 验证集 (取 20% 样本)
    val_max_samples = max(64, config.max_samples // 5) if config.max_samples else 256
    val_loader = create_oxe_dataloader(
        dataset_type=config.dataset_type,
        dataset_name=config.dataset_name,
        tokenizer=tokenizer,
        batch_size=config.batch_size,
        image_size=config.image_size,
        max_text_length=config.max_text_length,
        max_samples=val_max_samples,
        is_train=False,
        split="train",
        num_workers=config.num_workers,
    )

    print(f"  Train: {len(train_loader.dataset)} samples, {len(train_loader)} batches")
    print(f"  Val:   {len(val_loader.dataset)} samples, {len(val_loader)} batches")

    # ── Step 3: 优化器 & 损失函数 ──
    print("\n[3/6] 配置优化器...")
    criterion = nn.MSELoss()
    optimizer = AdamW(model.parameters(), lr=config.learning_rate, weight_decay=config.weight_decay)

    # 学习率调度
    total_steps = len(train_loader) * config.num_epochs
    warmup_steps = int(total_steps * config.warmup_ratio)

    class WarmupThenCosine:
        def __init__(self, optimizer, warmup_steps, total_steps):
            self.optimizer = optimizer
            self.warmup_steps = warmup_steps
            self.total_steps = total_steps
            self.base_lrs = [g["lr"] for g in optimizer.param_groups]
            self.step_count = 0

        def step(self):
            self.step_count += 1
            if self.step_count <= self.warmup_steps:
                scale = self.step_count / max(1, self.warmup_steps)
                for g, blr in zip(self.optimizer.param_groups, self.base_lrs):
                    g["lr"] = blr * scale
            else:
                progress = (self.step_count - self.warmup_steps) / max(1, self.total_steps - self.warmup_steps)
                cosine = 0.5 * (1 + np.cos(np.pi * progress))
                for g, blr in zip(self.optimizer.param_groups, self.base_lrs):
                    g["lr"] = blr * cosine

    scheduler = WarmupThenCosine(optimizer, warmup_steps, total_steps)

    print(f"  Loss:      MSELoss")
    print(f"  Optimizer: AdamW(lr={config.learning_rate}, wd={config.weight_decay})")
    print(f"  Scheduler: Warmup({warmup_steps}) + Cosine → {total_steps} total steps")

    # ── Step 4: 混合精度 ──
    scaler = None
    if config.use_amp and config.device == "cuda":
        scaler = torch.cuda.amp.GradScaler()
        print("  AMP: enabled (mixed precision)")

    # ── Step 5: 训练循环 ──
    print(f"\n[4/6] 开始训练 ({config.num_epochs} epochs)...")
    print("-" * 50)

    tracker = MetricTracker()
    start_epoch = 0

    for epoch in range(start_epoch, config.num_epochs):
        epoch_start = time.time()

        train_loss = train_one_epoch(
            model, train_loader, optimizer, scheduler,
            criterion, epoch, config, scaler,
        )

        val_loss, action_error = validate(model, val_loader, criterion, config)
        tracker.update(train_loss, val_loss, action_error)

        epoch_time = time.time() - epoch_start
        print(f"  ── Epoch {epoch+1:3d}/{config.num_epochs} "
              f"| Train: {train_loss:.6f} | Val: {val_loss:.6f} "
              f"| Time: {epoch_time:.1f}s")

        # 保存 checkpoint
        save_checkpoint(model, optimizer, epoch, val_loss, config, tracker)

        # 可视化 (每 N 个 epoch)
        if config.visualize_epochs > 0 and (epoch + 1) % config.visualize_epochs == 0:
            visualize_predictions(model, val_loader, config, epoch)

    # ── Step 6: 结果汇总 ──
    print(f"\n[5/6] 训练完成!")
    print("=" * 60)
    print(tracker.summary())

    # 打印训练历史
    print(f"\n{'Epoch':>6} {'Train Loss':>12} {'Val Loss':>12} {'Act Error':>10}")
    print("-" * 45)
    for i, (tl, vl, ae) in enumerate(zip(tracker.train_losses, tracker.val_losses, tracker.action_errors)):
        print(f"{i+1:>6} {tl:>12.6f} {vl:>12.6f} {ae:>10.6f}")
    print("=" * 60)

    # ── 最终可视化 ──
    print(f"\n[6/6] 最终可视化...")
    if config.visualize_epochs >= 0:
        visualize_predictions(model, val_loader, config, config.num_epochs - 1)

    # 保存最终模型
    final_path = Path(config.save_dir) / config.experiment_name / "final_model.pt"
    torch.save({
        "model_state_dict": model.state_dict(),
        "config": {k: v for k, v in vars(config).items() if not k.startswith("_")},
    }, final_path)
    print(f"Final model saved → {final_path}")


# ═══════════════════════════════════════════════════════════════
# 8. 快速验证入口
# ═══════════════════════════════════════════════════════════════

def quick_test():
    """极速验证: 3 epochs, 小数据集"""
    config = TrainConfig()
    config.dataset_type = "inmemory"
    config.num_epochs = 3
    config.max_samples = 128
    config.batch_size = 8
    config.log_interval = 5
    config.visualize_epochs = 1
    config.experiment_name = "quick_test"
    main(config)


# ═══════════════════════════════════════════════════════════════
# 9. CLI
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Train MiniVLA on Open-X-Embodiment data")

    # 预设模式
    parser.add_argument("--quick", action="store_true", help="快速验证 (3 epochs)")
    parser.add_argument("--tfds", action="store_true", help="使用 tensorflow_datasets 加载真实数据")
    parser.add_argument("--hf", action="store_true", help="使用 HuggingFace datasets 加载")

    # 数据
    parser.add_argument("--dataset", type=str, default="fractal20220817_data", help="OXE 数据集名")
    parser.add_argument("--max_samples", type=int, default=2048, help="最多加载样本数")
    parser.add_argument("--batch_size", type=int, default=16, help="batch size")
    parser.add_argument("--epochs", type=int, default=20, help="训练轮数")
    parser.add_argument("--lr", type=float, default=1e-4, help="学习率")

    # 可视化
    parser.add_argument("--visualize", action="store_true", default=True, help="启用可视化")
    parser.add_argument("--no_visualize", action="store_true", help="禁用可视化")
    parser.add_argument("--vis_epochs", type=int, default=5, help="每 N 个 epoch 可视化一次")

    # 保存
    parser.add_argument("--save_dir", type=str, default="./checkpoints", help="模型保存目录")
    parser.add_argument("--exp_name", type=str, default="oxe_v1", help="实验名称")
    parser.add_argument("--resume", type=str, default=None, help="从 checkpoint 恢复")

    # 设备
    parser.add_argument("--device", type=str, default="auto", help="设备 (auto/cuda/cpu)")
    parser.add_argument("--amp", action="store_true", help="启用混合精度训练")

    args = parser.parse_args()

    if args.quick:
        quick_test()
    else:
        config = TrainConfig()

        # 数据集类型
        if args.tfds:
            config.dataset_type = "tfds"
        elif args.hf:
            config.dataset_type = "huggingface"
        else:
            config.dataset_type = "inmemory"

        config.dataset_name = args.dataset
        config.max_samples = args.max_samples
        config.batch_size = args.batch_size
        config.num_epochs = args.epochs
        config.learning_rate = args.lr
        config.save_dir = args.save_dir
        config.experiment_name = args.exp_name
        config.use_amp = args.amp

        if args.no_visualize:
            config.visualize_epochs = 0
        else:
            config.visualize_epochs = args.vis_epochs

        if args.device != "auto":
            config.device = args.device

        if args.resume:
            print(f"Resuming from {args.resume}")
            model = MiniVLA(config.vision_model, config.language_model, config.action_dim)
            model.to(config.device)
            _, _ = load_checkpoint(args.resume, model)
            # 简化恢复: 直接继续训练
            main(config)

        main(config)