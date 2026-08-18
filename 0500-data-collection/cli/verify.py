"""
校验命令（CLI 入口）
====================
python 0500-data-collection/cli/verify.py -d ./data/episodes/demo
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
from embodied_data.core.verify import verify_dataset  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="校验采集数据集")
    parser.add_argument("-d", "--data", default="./data/episodes", help="数据根目录")
    parser.add_argument("-a", "--action_dim", type=int, default=7)
    parser.add_argument("-o", "--out", default=None, help="报告输出路径（可选）")
    return parser


def main():
    args = build_parser().parse_args()

    print("=" * 60)
    print(f"数据校验 | {args.data}")
    print("=" * 60)

    report = verify_dataset(args.data, action_dim=args.action_dim)

    if report.ok:
        print("校验通过：所有字段合法")
    else:
        print(f"发现 {report.n_problems} 个问题:")
        for p in report.problems:
            print(f"  - ep{p['episode']} step{p['step']} [{p['kind']}]: {p['detail']}")

    import json
    print("\n统计摘要:")
    print(json.dumps(report.stats, ensure_ascii=False, indent=2, default=str))

    if args.out:
        report.save(args.out)
        print(f"报告已保存 → {args.out}")

    return 0 if report.ok else 1


if __name__ == "__main__":
    sys.exit(main())