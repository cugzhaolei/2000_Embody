"""
冒烟测试
========
在零依赖（仅 numpy / Pillow）环境下验证核心链路:
  采集(DummySource) -> 落盘 -> 读取 -> 校验 -> 统计
不依赖仿真/ROS，可离线运行。

跑法:
  python 0500-data-collection/scripts/smoke_test.py
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT.parent))

from cli._bootstrap import register_package  # noqa: E402
register_package()

import numpy as np  # noqa: E402


def main():
    from embodied_data.sources.base import DummySource
    from embodied_data.core.recorder import EpisodeRecorder
    from embodied_data.core.verify import verify_dataset, compute_stats
    from embodied_data.store.lerobot import LeRobotDatasetIterator
    from embodied_data.core.utils import list_episodes

    tmp = tempfile.mkdtemp(prefix="embody_smoke_")
    out_root = str(Path(tmp) / "episodes")

    step = 0

    print("[1/6] 创建 Dummy 数据源...")
    src = DummySource(image_size=(48, 48), state_dim=6, action_dim=7, seed=0)

    print("[2/6] 采集 2 条 episode...")
    rec = EpisodeRecorder(src, out_root=out_root, fps=10, video_backend="none")
    for ep_idx in range(2):
        ep = rec.create_episode(instruction=f"task {ep_idx}")
        for i in range(6):
            a = np.zeros(7, dtype=np.float32)
            a[6] = 1.0 if i % 2 == 0 else 0.0
            rec.record_step(ep, a)
            step += 1
        idx = rec.finish_episode(ep)
        print(f"    episode {idx} saved ({ep.num_steps} steps)")
    src.close()

    print("[3/6] 校验...")
    report = verify_dataset(out_root, action_dim=7)
    assert report.ok, f"校验失败: {report.problems}"
    print(f"    ok ({report.n_episodes} ep, {report.n_steps} steps)")

    print("[4/6] 统计...")
    stats = compute_stats(out_root)
    print(f"    {stats}")

    print("[5/6] LeRobot 迭代器读取...")
    it = LeRobotDatasetIterator(out_root, action_dim=7)
    sample = next(iter(it))
    assert "image" in sample and "action" in sample
    print(f"    sample: image={sample['image'].shape} action={sample['action'].shape}")

    print("[6/6] 导出 legacy traj...")
    from embodied_data.store.local import convert_to_legacy
    n = convert_to_legacy(out_root, str(Path(tmp) / "legacy"))
    print(f"    converted {n} traj")

    print("\n" + "=" * 50)
    print("冒烟测试全部通过")


if __name__ == "__main__":
    main()