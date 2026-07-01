"""
通用工具函数
============
提供种子设置、模型参数统计、checkpoint 管理等公共功能。
"""

import os
import json
import random
import shutil
from pathlib import Path
from typing import Optional, Dict, Any

import numpy as np
import torch


def set_seed(seed: int = 42):
    """统一设置随机种子，确保可复现性"""
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
        torch.backends.cudnn.deterministic = True
        torch.backends.cudnn.benchmark = False


def count_parameters(model: torch.nn.Module) -> Dict[str, float]:
    """统计模型参数量（单位：M）"""
    total = sum(p.numel() for p in model.parameters()) / 1e6
    trainable = sum(p.numel() for p in model.parameters() if p.requires_grad) / 1e6
    frozen = total - trainable
    return {"total_M": round(total, 2), "trainable_M": round(trainable, 2), "frozen_M": round(frozen, 2)}


def save_checkpoint(
    model: torch.nn.Module,
    optimizer: torch.optim.Optimizer,
    epoch: int,
    metrics: Dict[str, float],
    save_dir: str,
    experiment_name: str,
    is_best: bool = False,
    extra: Optional[Dict[str, Any]] = None,
):
    """保存训练 checkpoint"""
    save_path = Path(save_dir) / experiment_name
    save_path.mkdir(parents=True, exist_ok=True)

    checkpoint = {
        "epoch": epoch,
        "model_state_dict": model.state_dict(),
        "optimizer_state_dict": optimizer.state_dict(),
        "metrics": metrics,
    }
    if extra:
        checkpoint["extra"] = extra

    # 保存当前 epoch 的 checkpoint
    ckpt_path = save_path / f"checkpoint_epoch_{epoch+1:03d}.pt"
    torch.save(checkpoint, ckpt_path)

    # 如果是最佳模型，额外保存一份
    if is_best:
        best_path = save_path / "best_model.pt"
        shutil.copy2(ckpt_path, best_path)

    # 只保留最近 5 个 checkpoint
    _cleanup_old_checkpoints(save_path, keep=5)

    return ckpt_path


def load_checkpoint(
    path: str,
    model: torch.nn.Module,
    optimizer: Optional[torch.optim.Optimizer] = None,
    device: str = "cpu",
) -> Dict[str, Any]:
    """加载 checkpoint"""
    checkpoint = torch.load(path, map_location=device, weights_only=False)
    model.load_state_dict(checkpoint["model_state_dict"])
    if optimizer is not None and "optimizer_state_dict" in checkpoint:
        optimizer.load_state_dict(checkpoint["optimizer_state_dict"])
    return checkpoint


def _cleanup_old_checkpoints(save_path: Path, keep: int = 5):
    """只保留最近 N 个 checkpoint"""
    ckpts = sorted(save_path.glob("checkpoint_epoch_*.pt"))
    if len(ckpts) > keep:
        for old_ckpt in ckpts[:-keep]:
            old_ckpt.unlink(missing_ok=True)


def save_metrics(metrics: Dict[str, Any], path: str):
    """保存训练指标到 JSON"""
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2, ensure_ascii=False)


def load_metrics(path: str) -> Dict[str, Any]:
    """从 JSON 加载训练指标"""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)
