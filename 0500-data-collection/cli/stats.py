"""
统计命令（CLI 入口）
====================
python 0500-data-collection/cli/stats.py -d ./data/episodes/demo
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
from embodied_data.core.verify import compute_stats  # noqa: E402
from embodied_data.core.utils import list_episodes  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="数据统计")
    parser.add_argument("-d", "--data", default="./data/episodes", help="数据根目录")
    return parser


def main():
    args = build_parser().parse_args()

    stats = compute_stats(args.data)
    episodes = list_episodes(args.data)

    print("=" * 60)
    print(f"数据统计 | {args.data}")
    print("=" * 60)
    print(f"  轨迹数:      {stats['num_episodes']}")
    print(f"  总步数:      {stats['total_steps']}")
    print(f"  平均每轨迹:  {stats['mean_steps_per_episode']} 步")
    print(f"  平均时长:    {stats['mean_duration_sec']}s")
    print(f"  累计时长:    {stats['total_duration_sec']}s")
    print("\n  轨迹索引:")
    for e in episodes[:20]:
        t = e.get("task", "") if isinstance(e, dict) else ""
        print(f"    ep{e['episode_index'] if isinstance(e, dict) else e}: {t}")


if __name__ == "__main__":
    main()