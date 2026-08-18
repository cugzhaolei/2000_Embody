"""
导出脚本: 采集数据 → 0200-vla-imitation 可训练的 VLADataset 格式
================================================================
把 0500-data-collection 采集的 LeRobot 兼容目录，转为
0200-vla-imitation/data/dataset.py 中 VLADataset 期望的 legacy 格式:
  <legacy_root>/
    traj_0000.json          # {observations, actions, metadata}
    traj_0000/frame_0000.png
    metadata.json
```

用法:
  python 0500-data-collection/scripts/export_for_vla.py \
      -d ./demo_data -o ./0200-vla-imitation/data/trajectories

随后在 0200-vla-imitation 目录内跑训练:
  python -m scripts.train_vla --model vla --dataset trajectory \
      --data_dir ./data/trajectories --epochs 20 --batch_size 16
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT.parent))

from cli._bootstrap import register_package  # noqa: E402
register_package()

from embodied_data.store.local import convert_to_legacy  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="采集数据导出为 VLA 训练格式")
    parser.add_argument("-d", "--data", required=True, help="采集数据集根目录")
    parser.add_argument("-o", "--out", required=True, help="导出目标目录 (traj_*.json)")
    parser.add_argument("-e", "--episodes", nargs="*", type=int, default=None,
                        help="仅导出指定 episode 索引（默认全部）")
    parser.add_argument("--frames", type=int, default=0,
                        help="每轨迹最大抽帧数（0=全部，大轨迹可限制）")
    return parser


def main():
    args = build_parser().parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    print(f"导出 {args.data} → {out}")
    n = convert_to_legacy(
        out_root=args.data,
        legacy_root=str(out),
        episode_indices=args.episodes,
        max_frames_per_episode=args.frames or None,
    )
    print(f"完成: 导出 {n} 条轨迹到 {out}")
    print("\n下一步（在 0200-vla-imitation 目录下）:")
    print(f'  $env:HF_ENDPOINT="https://hf-mirror.com"')
    print("  python -m scripts.train_vla --model vla --dataset trajectory \\")
    print(f'      --data_dir {out} --epochs 20 --batch_size 16')


if __name__ == "__main__":
    main()