"""
可视化工具
==========
支持训练曲线绘制、动作轨迹可视化、渲染帧保存。
"""

import os
from pathlib import Path
from typing import List, Dict, Optional, Tuple

import numpy as np


def plot_training_curves(
    metrics: Dict[str, List[float]],
    save_path: Optional[str] = None,
    title: str = "Training Curves",
):
    """绘制训练曲线（Loss、LR 等）"""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlib 未安装，跳过可视化")
        return

    fig, axes = plt.subplots(1, len(metrics), figsize=(6 * len(metrics), 4))
    if len(metrics) == 1:
        axes = [axes]

    for ax, (name, values) in zip(axes, metrics.items()):
        ax.plot(values, linewidth=1.5)
        ax.set_title(name)
        ax.set_xlabel("Epoch")
        ax.set_ylabel(name)
        ax.grid(True, alpha=0.3)

    fig.suptitle(title)
    fig.tight_layout()

    if save_path:
        Path(save_path).parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(save_path, dpi=150, bbox_inches="tight")
        print(f"Training curves saved → {save_path}")
    plt.close(fig)


def save_frames_as_gif(
    frames: List[np.ndarray],
    save_path: str,
    duration: float = 50,  # ms per frame
):
    """将帧序列保存为 GIF"""
    try:
        from PIL import Image
        Path(save_path).parent.mkdir(parents=True, exist_ok=True)
        pil_frames = [Image.fromarray(f) for f in frames]
        pil_frames[0].save(
            save_path,
            save_all=True,
            append_images=pil_frames[1:],
            duration=duration,
            loop=0,
        )
        print(f"GIF saved → {save_path}")
    except ImportError:
        print("Pillow 未安装，跳过 GIF 保存")


def plot_action_trajectory(
    actions: np.ndarray,
    action_labels: Optional[List[str]] = None,
    save_path: Optional[str] = None,
):
    """绘制动作轨迹"""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlib 未安装，跳过可视化")
        return

    if actions.ndim == 1:
        actions = actions.reshape(-1, 1)

    num_dims = actions.shape[1]
    if action_labels is None:
        action_labels = [f"dim_{i}" for i in range(num_dims)]

    fig, axes = plt.subplots(num_dims, 1, figsize=(10, 2.5 * num_dims), squeeze=False)
    for i, (ax, label) in enumerate(zip(axes.flatten(), action_labels)):
        ax.plot(actions[:, i], linewidth=1.2)
        ax.set_ylabel(label)
        ax.grid(True, alpha=0.3)
    axes[-1][0].set_xlabel("Step")
    fig.suptitle("Action Trajectory")
    fig.tight_layout()

    if save_path:
        Path(save_path).parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
