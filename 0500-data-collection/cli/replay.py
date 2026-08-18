"""
回放命令（CLI 入口）
====================
把一条 episode 抽帧为 GIF / 逐帧 PNG，或直接打印动作统计。

python 0500-data-collection/cli/replay.py -d ./data/episodes/demo -e 0 -o ./replay_out
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
from embodied_data.core.utils import find_episode_dir  # noqa: E402
from embodied_data.core.video import save_video, read_frames  # noqa: E402
from embodied_data.core.verify import load_episode_steps  # noqa: E402
from embodied_data.core.utils import ensure_rgb  # noqa: E402
from embodied_data.core.schema import decode_image_bytes  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="回放 episode")
    parser.add_argument("-d", "--data", default="./data/episodes", help="数据根目录")
    parser.add_argument("-e", "--episode", type=int, default=0, help="episode 索引")
    parser.add_argument("-o", "--out", default=None, help="输出文件（GIF）或目录（PNG）")
    parser.add_argument("--backend", default="gif", choices=["gif", "mp4", "png"])
    return parser


def main():
    args = build_parser().parse_args()

    ep_dir = find_episode_dir(args.data, args.episode)
    if ep_dir is None:
        print(f"未找到 episode_{args.episode:06d}")
        sys.exit(1)

    steps = load_episode_steps(ep_dir)
    print(f"episode {args.episode}: {len(steps)} steps")

    # 提取图像：优先 steps 内嵌 numpy 图，其次读视频帧
    frames = _extract_frames(steps, ep_dir)

    if args.out:
        out = Path(args.out)
        if args.backend == "png":
            out.mkdir(parents=True, exist_ok=True)
            from PIL import Image
            for i, f in enumerate(frames):
                Image.fromarray(ensure_rgb(f)).save(out / f"frame_{i:04d}.png")
            print(f"→ 已导出 {len(frames)} 帧到 {out}")
        else:
            suffix = ".gif" if args.backend == "gif" else ".mp4"
            save_video(frames, str(out.with_suffix(suffix)), fps=10, backend=args.backend)
            print(f"→ 已保存视频: {out.with_suffix(suffix)}")

    # 动作摘要
    import numpy as np
    acts = []
    for st in steps:
        a = st.get("action")
        if isinstance(a, (list, np.ndarray)):
            acts.append(np.asarray(a, dtype=np.float32))
    if acts:
        A = np.stack(acts)
        print(f"  动作范围: min={A.min(0).round(3)} max={A.max(0).round(3)}")


def _extract_frames(steps, ep_dir: Path):
    """从 steps 或视频文件恢复帧序列。"""
    import numpy as np
    frames = []
    img_keys = None
    if steps:
        img_keys = sorted(k for k in steps[0] if k.startswith("observation.images."))
        if img_keys:
            for st in steps:
                v = st.get(img_keys[0])
                img = None
                if isinstance(v, np.ndarray):
                    img = v
                elif isinstance(v, (bytes, bytearray, str)):
                    img = decode_image_bytes(v)
                elif isinstance(v, (list, tuple)):
                    try:
                        img = np.asarray(v, dtype=np.uint8)
                    except Exception:
                        img = None
                if img is not None:
                    try:
                        frames.append(ensure_rgb(img))
                    except Exception:
                        pass
    if frames:
        return frames
    # 回退：读视频
    idx_str = ep_dir.name.split("_")[1]
    for vid in sorted(ep_dir.parent.glob(f"episode_{idx_str}.gif")) + \
               sorted(ep_dir.parent.glob(f"episode_{idx_str}.mp4")):
        return read_frames(str(vid))
    return []