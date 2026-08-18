"""
采集命令（CLI 入口）
====================
python 0500-data-collection/cli/collect.py -s scripted -n 20 -o ./data/episodes/demo
python 0500-data-collection/cli/collect.py -s keyboard -t "pick up the red block"
python 0500-data-collection/cli/collect.py -s dummy -n 3 --video none   # 冒烟
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import numpy as np

# 项目根目录 + 包引导（数字目录名不可直接用 -m/相对导入）
ROOT = Path(__file__).resolve().parent.parent.parent
PKG = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(PKG))
from cli._bootstrap import register_package  # noqa: E402

register_package()
from embodied_data import core as dc_core  # noqa: E402
from embodied_data.sources.factory import create_source  # noqa: E402

EpisodeRecorder = dc_core.recorder.EpisodeRecorder
set_seed = dc_core.utils.set_seed


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="具身数据采集")
    parser.add_argument("-s", "--source", default="dummy",
                        choices=["dummy", "scripted", "pybullet", "mujoco", "keyboard", "ros2"])
    parser.add_argument("-n", "--episodes", type=int, default=3, help="采集轨迹数")
    parser.add_argument("-T", "--steps", type=int, default=30, help="每条轨迹步数上限")
    parser.add_argument("-o", "--out", default="./data/episodes", help="输出根目录")
    parser.add_argument("-t", "--task", default="pick up the red block", help="语言指令")
    parser.add_argument("-f", "--fps", type=int, default=10)
    parser.add_argument("--video", default="gif", choices=["gif", "mp4", "png", "none"])
    parser.add_argument("-g", "--gui", action="store_true", help="键盘遥操作使用 GUI 窗口")
    parser.add_argument("--seed", type=int, default=42)
    return parser


def main():
    args = build_parser().parse_args()

    set_seed(args.seed)

    print("=" * 60)
    print(f"具身数据采集 | source={args.source} | episodes={args.episodes} | fps={args.fps}")
    print("=" * 60)

    source = create_source(
        source=args.source,
        instruction=args.task,
        render=args.gui,
        use_gui=args.gui,
    )

    recorder = EpisodeRecorder(
        source=source,
        out_root=args.out,
        fps=args.fps,
        action_dim=7,
        video_backend=args.video,
    )

    try:
        for ep_idx in range(args.episodes):
            ep = recorder.create_episode(instruction=args.task)
            print(f"\n[episode {ep_idx+1}/{args.episodes}] 开始录制: {args.task}")

            if args.source == "keyboard":
                _run_keyboard(recorder, ep, source, args.steps)
            else:
                _run_auto(recorder, ep, source, args.steps)

            idx = recorder.finish_episode(ep)
            if idx is not None:
                print(f"  -> episode {idx} 已保存 ({ep.num_steps} steps)")
    finally:
        source.close()

    summary = recorder.export_summary()
    print("\n" + "=" * 60)
    print("采集完成!")
    print(f"  轨迹数: {summary['num_episodes']}")
    print(f"  总步数: {summary['total_steps']}")
    print(f"  输出目录: {args.out}")


def _run_keyboard(recorder, ep, source, max_steps: int):
    """人工示教: 每步读键盘指令 -> 执行 -> 录制。"""
    for step in range(max_steps):
        action = source.read_command()
        source.step(action)
        recorder.record_step(ep, action)
        print(f"  step {step+1:3d} | action={np.round(action, 3)}")
        time.sleep(1.0 / max(getattr(recorder, "fps", 10), 1))


def _run_auto(recorder, ep, source, max_steps: int):
    """自动源: 逐动作执行并录制。"""
    for step in range(max_steps):
        action = _next_action(source, step)
        recorder.record_step(ep, action)
        if step % 10 == 0:
            print(f"  step {step+1:4d}/{max_steps}")


def _next_action(source, step: int) -> np.ndarray:
    """从源获取当前步动作并执行。

    对实现了内部轨迹的源（ScriptedExpertSource）返回其生成的动作；
    普通源返回随机增量。
    """
    if hasattr(source, "_actions") and isinstance(getattr(source, "_actions"), list):
        acts = list(getattr(source, "_actions"))
        if acts:
            a = acts[step % len(acts)]
            source.step(a)
            return np.asarray(a, dtype=np.float32)
    rng = np.random.default_rng(step * 7 + 42)
    a = rng.uniform(-0.05, 0.05, size=7).astype(np.float32)
    a[6] = 1.0 if step % 6 < 3 else 0.0
    source.step(a)
    return a


if __name__ == "__main__":
    main()