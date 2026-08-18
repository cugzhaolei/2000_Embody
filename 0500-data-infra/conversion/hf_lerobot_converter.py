"""
HuggingFace LeRobot v3 数据集转换器
==================================
将 HuggingFace 下载的 LeRobot v3.0 结构（data/*.parquet + videos/*.mp4）
转换为 VLA 训练可用的 JSON 标注 + 帧图像格式。

输入结构（snapshot_download 产物）:
  data/chunk-xxx/file-xxx.parquet    逐帧数据（action / observation.state / next.success ...）
  videos/observation.image/chunk-xxx/file-xxx.mp4  所有 episode 拼接的视频
  meta/info.json                    数据集元信息
  meta/episodes/.../parquet         episode 索引

输出结构:
  {out_dir}/
    images/episode_{ep:06d}/frame_{i:06d}.jpg
    train.json    [{image, instruction, action}, ...]   action 已归一化到 [-1, 1]
    val.json      同上（按 episode 8:2 划分）
    meta.json     统计与归一化参数

用法:
  python 0500-data-infra/conversion/hf_lerobot_converter.py \
      --input data/pusht --output data/pusht_converted \
      [--val_ratio 0.2] [--max_frames 25650] [--image_size 96]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd


def find_data_files(root: Path) -> list[Path]:
    return sorted((root / "data").rglob("*.parquet"))


def find_video_files(root: Path) -> list[Path]:
    return sorted((root / "videos").rglob("*.mp4"))


def find_episodes_parquet(root: Path) -> list[Path]:
    return sorted((root / "meta" / "episodes").rglob("*.parquet"))


def extract_frames(video_path: Path, image_dir: Path, max_frames: int) -> int:
    """用 PyAV 将视频逐帧抽出为 JPEG。返回抽出的帧数。"""
    import av

    image_dir.mkdir(parents=True, exist_ok=True)
    container = av.open(str(video_path))
    n = 0
    for frame in container.decode(video=0):
        if max_frames and n >= max_frames:
            break
        img = frame.to_image()  # PIL Image, RGB
        img.save(image_dir / f"frame_{n:06d}.jpg", quality=88)
        n += 1
    container.close()
    return n


def main():
    parser = argparse.ArgumentParser(description="HuggingFace LeRobot v3 -> JSON + frames")
    parser.add_argument("--input", required=True, help="snapshot_download 下载目录")
    parser.add_argument("--output", required=True, help="输出目录")
    parser.add_argument("--val_ratio", type=float, default=0.2)
    parser.add_argument("--max_frames", type=int, default=0, help="0=全部")
    parser.add_argument("--image_size", type=int, default=96, help="抽帧后保存尺寸（保持原始）")
    args = parser.parse_args()

    root = Path(args.input)
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)

    print(f"[1/5] 读取元信息 {root / 'meta' / 'info.json'}")
    with open(root / "meta" / "info.json", "r", encoding="utf-8") as f:
        info = json.load(f)
    print(f"      episodes={info['total_episodes']} frames={info['total_frames']} fps={info['fps']}")

    print("[2/5] 读取数据 parquet")
    data_files = find_data_files(root)
    if not data_files:
        sys.exit("未找到 data/*.parquet")
    df = pd.concat([pd.read_parquet(str(p)) for p in data_files], ignore_index=True)
    print(f"      rows={len(df)}")

    print("[3/5] 读取任务指令")
    task_file = root / "meta" / "tasks.parquet"
    tasks = {}
    if task_file.exists():
        tdf = pd.read_parquet(str(task_file))
        for col in tdf.columns:
            if col != "task_index":
                tasks = {int(i): str(t) for i, t in tdf[col].items()}
    if not tasks:
        tasks = {0: "Push the T-shaped block onto the T-shaped target."}
    print(f"      tasks={tasks}")

    print("[4/5] 抽取视频帧")
    videos = find_video_files(root)
    frames_flat = []  # (episode_index, frame_index)
    n_frames = 0
    for v in videos:
        n_frames = extract_frames(v, out / "images" / "_raw", args.max_frames)
    print(f"      抽帧完成: {n_frames} 帧")

    # 按 episode 归组：episodes parquet 提供每 episode 在视频中的起止帧
    print("[5/5] 构建 JSON 标注")
    ep_file = find_episodes_parquet(root)[0]
    epdf = pd.read_parquet(str(ep_file))

    # 归一化参数（像素坐标 -> [-1,1]）
    center = 255.5
    scale = 255.5

    def norm(a: np.ndarray) -> list:
        return ((np.asarray(a, dtype=np.float32) - center) / scale).round(6).tolist()

    train_samples, val_samples = [], []
    val_episodes = set()
    rng = np.random.default_rng(42)
    ep_indices = sorted(epdf["episode_index"].unique().tolist())
    n_val = max(1, int(len(ep_indices) * args.val_ratio))
    val_episodes = set(rng.choice(ep_indices, size=n_val, replace=False).tolist())

    raw_img = out / "images" / "_raw"
    for _, row in epdf.iterrows():
        ep = int(row["episode_index"])
        from_i = int(row["dataset_from_index"])
        to_i = int(row["dataset_to_index"])
        if to_i >= n_frames:
            continue
        instruction = tasks.get(int(row.get("task_index", 0)), next(iter(tasks.values())))
        ep_rows = df.iloc[from_i : to_i + 1]
        ep_dir = out / "images" / f"episode_{ep:06d}"
        ep_dir.mkdir(parents=True, exist_ok=True)
        samples = []
        for _, r in ep_rows.iterrows():
            frm = int(r["index"])
            # 视频帧序号 = data parquet 全局 index（与视频逐帧一一对应）
            img_name = f"episode_{ep:06d}/frame_{frm:06d}.jpg"
            src = raw_img / f"frame_{frm:06d}.jpg"
            if not src.exists():
                continue
            dst = ep_dir / f"frame_{frm:06d}.jpg"
            if not dst.exists():
                dst.write_bytes(src.read_bytes())
            samples.append({
                "image": img_name,
                "instruction": instruction,
                "action": norm(r["action"]),
            })
        if ep in val_episodes:
            val_samples.extend(samples)
        else:
            train_samples.extend(samples)

    for name, samples in (("train", train_samples), ("val", val_samples)):
        with open(out / f"{name}.json", "w", encoding="utf-8") as f:
            json.dump(samples, f, ensure_ascii=False)

    meta = {
        "source": "lerobot/pusht",
        "fps": info["fps"],
        "n_episodes": len(ep_indices),
        "n_train_frames": len(train_samples),
        "n_val_frames": len(val_samples),
        "action_dim": 2,
        "action_norm": {"center": center, "scale": scale},
        "image_size": args.image_size,
        "instruction": next(iter(tasks.values())),
    }
    with open(out / "meta.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)

    # 清理临时平铺目录
    import shutil
    shutil.rmtree(raw_img, ignore_errors=True)

    print("=" * 56)
    print(f"转换完成 -> {out}")
    print(f"  train samples: {len(train_samples)} | val: {len(val_samples)}")
    print(f"  action_dim: {meta['action_dim']}  norm: {norm([255.5])} 示例 action: {train_samples[0]['action'] if train_samples else 'n/a'}")


if __name__ == "__main__":
    main()
