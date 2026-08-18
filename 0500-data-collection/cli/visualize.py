"""
可视化命令（CLI 入口）
======================
把采集数据转成训练友好的汇总图（动作曲线 / 状态曲线 / 指令分布）。

python 0500-data-collection/cli/visualize.py -d ./data/episodes/demo -o ./plots
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
PKG = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(PKG))
from cli._bootstrap import register_package  # noqa: E402

register_package()
from embodied_data.core.utils import list_episodes, find_episode_dir  # noqa: E402
from embodied_data.core.verify import load_episode_steps  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="数据集可视化")
    parser.add_argument("-d", "--data", default="./data/episodes", help="数据根目录")
    parser.add_argument("-o", "--out", default="./plots", help="输出目录")
    return parser


def main():
    args = build_parser().parse_args()

    import numpy as np
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlib 未安装，跳过可视化。pip install matplotlib")
        return

    episodes = list_episodes(args.data)
    all_actions = []
    all_states = []

    # 动作曲线（单 episode 示例）
    if episodes:
        e0 = episodes[0]
        idx = e0.get("episode_index") if isinstance(e0, dict) else e0
        ep_dir = find_episode_dir(args.data, idx)
        if ep_dir:
            steps = load_episode_steps(ep_dir)
            actions = [np.asarray(s["action"], dtype=np.float32)
                       for s in steps if "action" in s]
            if actions:
                A = np.stack(actions)
                fig, ax = plt.subplots(figsize=(10, 3))
                ax.plot(A, linewidth=1.2)
                ax.set_title(f"Action trajectory - episode {idx}")
                ax.grid(True, alpha=0.3)
                fig.tight_layout()
                fig.savefig(out / "action_trajectory.png", dpi=120)
                plt.close(fig)

    # 指令分布
    from collections import Counter
    tasks = Counter()
    for e in episodes:
        t = e.get("task", "") if isinstance(e, dict) else ""
        if t:
            tasks[t] += 1
    if tasks:
        fig, ax = plt.subplots(figsize=(6, 4))
        ax.barh(list(tasks.keys()), list(tasks.values()))
        ax.set_title("Task distribution")
        fig.tight_layout()
        fig.savefig(out / "task_distribution.png", dpi=120)
        plt.close(fig)

    # 每轨迹步数分布
    step_counts = []
    for e in episodes:
        idx = e.get("episode_index") if isinstance(e, dict) else e
        ep_dir = find_episode_dir(args.data, idx)
        if ep_dir:
            step_counts.append(len(load_episode_steps(ep_dir)))
    if step_counts:
        fig, ax = plt.subplots(figsize=(6, 4))
        ax.hist(step_counts, bins=min(20, max(step_counts, default=1)))
        ax.set_title("Steps per episode")
        ax.set_xlabel("steps")
        fig.tight_layout()
        fig.savefig(out / "steps_hist.png", dpi=120)
        plt.close(fig)

    print(f"可视化完成 → {out}")


if __name__ == "__main__":
    main()