"""
VLA 训练脚本
============
支持 VLABaseModel / ACTModel / DiffusionPolicyModel 的训练。

使用方法:
  # 合成数据快速验证
  python train_vla.py --model vla --quick

  # VLA 基础模型训练
  python train_vla.py --model vla --epochs 20 --batch_size 16

  # ACT 模型训练
  python train_vla.py --model act --epochs 30 --chunk_size 10

  # Diffusion Policy 训练
  python train_vla.py --model diffusion --epochs 30 --chunk_size 16

  # 从采集的轨迹数据训练
  python train_vla.py --model vla --dataset trajectory --data_dir ./data/trajectories
"""

import os
import sys
import time
import argparse
from pathlib import Path

# 添加项目根目录到 path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import torch
import torch.nn as nn
from torch.optim import AdamW
from transformers import AutoTokenizer

from common.config import VLAConfig, DeviceConfig
from common.utils import set_seed, count_parameters, save_checkpoint, load_checkpoint, save_metrics
from common.logger import setup_logger, MetricLogger

# 模型导入
from models.vlafactory import VLABaseModel
from models.act import ACTModel
from models.diffusion_policy import DiffusionPolicyModel

# 数据导入
from data.dataset import create_dataloader, SyntheticVLADataset, collate_fn


def build_model(model_type: str, config: VLAConfig) -> nn.Module:
    """构建模型"""
    if model_type == "vla":
        return VLABaseModel(
            vision_model_name=config.vision_model,
            language_model_name=config.language_model,
            action_dim=config.action_dim,
            use_state=False,
        )
    elif model_type == "act":
        return ACTModel(
            vision_model_name=config.vision_model,
            language_model_name=config.language_model,
            action_dim=config.action_dim,
            chunk_size=10,
            latent_dim=32,
            num_decoder_layers=4,
        )
    elif model_type == "diffusion":
        return DiffusionPolicyModel(
            vision_model_name=config.vision_model,
            language_model_name=config.language_model,
            action_dim=config.action_dim,
            chunk_size=16,
            num_diffusion_steps=100,
        )
    else:
        raise ValueError(f"Unknown model type: {model_type}")


def train_one_epoch(model, dataloader, optimizer, scheduler, epoch, config, device, model_type):
    """训练一个 epoch"""
    model.train()
    total_loss = 0.0

    for batch_idx, batch in enumerate(dataloader):
        images = batch["images"].to(device)
        input_ids = batch["input_ids"].to(device)
        attention_mask = batch["attention_mask"].to(device)
        actions_gt = batch["actions"].to(device)

        optimizer.zero_grad()

        if model_type == "vla":
            pred = model(images, input_ids, attention_mask)
            loss = nn.MSELoss()(pred, actions_gt)
        elif model_type == "act":
            # ACT 需要 chunk 格式的 actions
            chunk_size = model.chunk_size
            if actions_gt.dim() == 2:
                # 简化: 复制单步动作为 chunk
                actions_chunk = actions_gt.unsqueeze(1).expand(-1, chunk_size, -1)
            else:
                actions_chunk = actions_gt
            result = model(images, input_ids, attention_mask, actions_gt=actions_chunk)
            mse_loss = nn.MSELoss()(result["actions_pred"][:, 0, :], actions_gt)
            loss = mse_loss + result["kl_loss"] * 0.01  # KL 权重
        elif model_type == "diffusion":
            chunk_size = model.chunk_size
            if actions_gt.dim() == 2:
                actions_chunk = actions_gt.unsqueeze(1).expand(-1, chunk_size, -1)
            else:
                actions_chunk = actions_gt
            result = model(images, input_ids, attention_mask, actions_gt=actions_chunk)
            loss = result["loss"]
        else:
            raise ValueError(f"Unknown model type: {model_type}")

        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), config.max_grad_norm)
        optimizer.step()

        if scheduler is not None:
            scheduler.step()

        total_loss += loss.item()

        if (batch_idx + 1) % config.log_interval == 0:
            lr = optimizer.param_groups[0]["lr"]
            print(f"  Epoch [{epoch+1}/{config.num_epochs}] "
                  f"Batch [{batch_idx+1}/{len(dataloader)}] "
                  f"Loss: {loss.item():.6f}  LR: {lr:.2e}")

    return total_loss / len(dataloader)


@torch.no_grad()
def validate(model, dataloader, config, device, model_type):
    """验证"""
    model.eval()
    total_loss = 0.0

    for batch in dataloader:
        images = batch["images"].to(device)
        input_ids = batch["input_ids"].to(device)
        attention_mask = batch["attention_mask"].to(device)
        actions_gt = batch["actions"].to(device)

        if model_type == "vla":
            pred = model(images, input_ids, attention_mask)
            loss = nn.MSELoss()(pred, actions_gt)
        elif model_type == "act":
            chunk_size = model.chunk_size
            actions_chunk = actions_gt.unsqueeze(1).expand(-1, chunk_size, -1)
            result = model(images, input_ids, attention_mask, actions_gt=actions_chunk)
            loss = nn.MSELoss()(result["actions_pred"][:, 0, :], actions_gt)
        elif model_type == "diffusion":
            chunk_size = model.chunk_size
            actions_chunk = actions_gt.unsqueeze(1).expand(-1, chunk_size, -1)
            result = model(images, input_ids, attention_mask, actions_gt=actions_chunk)
            loss = result["loss"]
        else:
            loss = torch.tensor(0.0)

        total_loss += loss.item()

    return total_loss / len(dataloader)


def main():
    parser = argparse.ArgumentParser(description="Train VLA Model")
    parser.add_argument("--model", type=str, default="vla", choices=["vla", "act", "diffusion"])
    parser.add_argument("--quick", action="store_true", help="Quick test (3 epochs)")
    parser.add_argument("--epochs", type=int, default=None)
    parser.add_argument("--batch_size", type=int, default=None)
    parser.add_argument("--lr", type=float, default=None)
    parser.add_argument("--dataset", type=str, default="synthetic")
    parser.add_argument("--data_dir", type=str, default=None)
    parser.add_argument("--save_dir", type=str, default="./checkpoints")
    parser.add_argument("--resume", type=str, default=None)
    args = parser.parse_args()

    # 配置
    config = VLAConfig()
    if args.epochs:
        config.num_epochs = args.epochs
    if args.batch_size:
        config.batch_size = args.batch_size
    if args.lr:
        config.learning_rate = args.lr
    if args.quick:
        config.num_epochs = 3
        config.max_samples = 128
        config.batch_size = 8
    config.dataset_type = args.dataset
    config.save_dir = args.save_dir
    config.experiment_name = f"{args.model}_vla"

    device_config = DeviceConfig()
    device = device_config.resolve_device()
    set_seed(device_config.seed)

    print("=" * 60)
    print(f"VLA Training — {config.experiment_name}")
    print(f"Model: {args.model} | Device: {device}")
    print("=" * 60)

    # 初始化模型
    print("\n[1/5] 初始化模型...")
    model = build_model(args.model, config).to(device)
    params = count_parameters(model)
    print(f"  Total: {params['total_M']}M | Trainable: {params['trainable_M']}M")

    # 准备数据
    print("\n[2/5] 准备数据...")
    tokenizer = AutoTokenizer.from_pretrained(config.language_model)
    train_loader = create_dataloader(
        dataset_type=config.dataset_type, data_dir=args.data_dir,
        tokenizer=tokenizer, batch_size=config.batch_size,
        num_samples=config.max_samples, is_train=True,
    )
    val_loader = create_dataloader(
        dataset_type=config.dataset_type, data_dir=args.data_dir,
        tokenizer=tokenizer, batch_size=config.batch_size,
        num_samples=max(64, config.max_samples // 5), is_train=False,
    )
    print(f"  Train: {len(train_loader.dataset)} | Val: {len(val_loader.dataset)}")

    # 优化器
    print("\n[3/5] 配置优化器...")
    criterion = nn.MSELoss()
    optimizer = AdamW(model.parameters(), lr=config.learning_rate, weight_decay=config.weight_decay)
    total_steps = len(train_loader) * config.num_epochs
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=total_steps)
    print(f"  Optimizer: AdamW | LR: {config.learning_rate} | Steps: {total_steps}")

    # 恢复训练
    start_epoch = 0
    if args.resume:
        ckpt = load_checkpoint(args.resume, model, optimizer, device)
        start_epoch = ckpt["epoch"] + 1
        print(f"  Resumed from epoch {start_epoch}")

    # 训练循环
    print(f"\n[4/5] 开始训练 ({config.num_epochs} epochs)...")
    train_losses = []
    val_losses = []
    best_val_loss = float("inf")

    for epoch in range(start_epoch, config.num_epochs):
        train_loss = train_one_epoch(model, train_loader, optimizer, scheduler, epoch, config, device, args.model)
        val_loss = validate(model, val_loader, config, device, args.model)

        train_losses.append(train_loss)
        val_losses.append(val_loss)

        is_best = val_loss < best_val_loss
        if is_best:
            best_val_loss = val_loss

        save_checkpoint(model, optimizer, epoch, {"train_loss": train_loss, "val_loss": val_loss},
                        config.save_dir, config.experiment_name, is_best=is_best)

        print(f"  Epoch {epoch+1}: Train={train_loss:.6f} | Val={val_loss:.6f} {'*' if is_best else ''}")

    # 结果
    print(f"\n[5/5] 训练完成!")
    print(f"  Best Val Loss: {best_val_loss:.6f}")
    print(f"  模型保存: {Path(config.save_dir) / config.experiment_name}")


if __name__ == "__main__":
    main()
