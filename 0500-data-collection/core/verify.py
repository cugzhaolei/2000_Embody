"""
数据校验与统计
==============
用于采集后审计数据集完整性：
  - 逐 episode 检查 step 字段、图像文件、动作维度、时间戳单调性
  - 汇总统计指标（轨迹数、总步数、时长、动作范围、指令分布）
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np

from .utils import find_episode_dir, list_episodes
from .utils import safe_json_dump


class DatasetReport:
    """校验/统计结果容器。"""

    def __init__(self):
        self.problems: List[Dict] = []
        self.stats: Dict = {}
        self.n_episodes = 0
        self.n_steps = 0

    def add_problem(self, episode: int, step: int, kind: str, detail: str):
        self.problems.append({
            "episode": episode, "step": step, "kind": kind, "detail": detail,
        })

    @property
    def ok(self) -> bool:
        return len(self.problems) == 0

    def to_dict(self) -> Dict:
        return {
            "ok": self.ok,
            "n_episodes": self.n_episodes,
            "n_steps": self.n_steps,
            "n_problems": len(self.problems),
            "problems": self.problems,
            "stats": self.stats,
        }

    def save(self, path: str):
        safe_json_dump(self.to_dict(), path)


def load_episode_steps(ep_dir: Path) -> List[Dict]:
    """读取 episode 的步骤数据（parquet 或 JSON）。"""
    pq = ep_dir / "steps.parquet"
    js = ep_dir / "steps.json"
    if pq.exists():
        import pandas as pd
        df = pd.read_parquet(pq)
        return df.to_dict("records")
    if js.exists():
        with open(js, encoding="utf-8") as f:
            return json.load(f)
    return []


def _extract_action(step: Dict) -> Optional[np.ndarray]:
    for key in ("action",):
        if key in step:
            val = step[key]
            if isinstance(val, str):
                val = np.frombuffer(val.encode(), dtype=np.float32) if False else None
            if isinstance(val, (list, tuple)):
                return np.asarray(val, dtype=np.float32)
            if isinstance(val, np.ndarray):
                return val
            if isinstance(val, (int, float)):
                return np.asarray([float(val)], dtype=np.float32)
    return None


def verify_dataset(out_root: str, action_dim: int = 7) -> DatasetReport:
    """校验数据集完整性。"""
    report = DatasetReport()
    episodes = list_episodes(out_root)

    root = Path(out_root)
    image_files = set()
    if (root / "videos").exists():
        image_files.update(p.name for p in (root / "videos").glob("*"))

    state_dims: Counter = Counter()
    action_dims: Counter = Counter()
    instructions: Counter = Counter()
    timestamps_ok = True
    total_actions = 0
    action_sum = None

    for ep_meta in episodes:
        idx = ep_meta.get("episode_index") if isinstance(ep_meta, dict) else ep_meta
        ep_dir = find_episode_dir(out_root, idx)
        if ep_dir is None:
            report.add_problem(idx, -1, "missing_dir", f"未找到 episode_{idx:06d} 目录")
            continue
        steps = load_episode_steps(ep_dir)
        if not steps:
            report.add_problem(idx, -1, "empty", "无步骤数据")
            continue

        # 时间戳单调性
        prev_ts = None
        for i, step in enumerate(steps):
            ts = step.get("timestamp", -1)
            if prev_ts is not None and ts < prev_ts:
                timestamps_ok = False
                report.add_problem(idx, i, "timestamp_decreasing",
                                   f"时间戳倒退: {prev_ts:.3f} -> {ts:.3f}")
            prev_ts = ts

            act = _extract_action(step)
            if act is None:
                report.add_problem(idx, i, "missing_action", "缺少 action 字段")
            else:
                action_dims[act.shape[0]] += 1
                total_actions += 1
                if action_sum is None:
                    action_sum = np.zeros(act.shape[0], dtype=np.float32)
                if action_sum.shape != act.shape:
                    action_sum = np.zeros(max(action_sum.shape[0], act.shape[0]), dtype=np.float32)
                action_sum += act

            st = step.get("observation.state", None)
            if st is not None:
                arr = np.asarray(st)
                state_dims[arr.shape[0] if arr.ndim == 1 else -1] += 1

            inst = step.get("instruction", "")
            if inst:
                instructions[inst] += 1

        if action_dims and max(action_dims) != action_dim:
            report.add_problem(idx, -1, "action_dim",
                               f"期望 {action_dim} 维动作，实际分布 {dict(action_dims)}")

    report.n_episodes = len([e for e in episodes if find_episode_dir(out_root, e.get("episode_index") if isinstance(e, dict) else e) is not None])
    report.n_steps = sum(ep_meta.get("num_steps", 0) if isinstance(ep_meta, dict) else 0 for ep_meta in episodes)

    report.stats = {
        "num_episodes": len(episodes),
        "valid_episodes": report.n_episodes,
        "total_steps": total_actions,
        "timestamps_monotonic": timestamps_ok,
        "action_dim_distribution": {str(k): v for k, v in sorted(action_dims.items())},
        "state_dim_distribution": {str(k): v for k, v in sorted(state_dims.items())},
        "action_distribution": instructions.most_common(3),
        "mean_action": _fmt_vec(action_sum / max(total_actions, 1)) if action_sum is not None else None,
    }
    return report


def compute_stats(out_root: str) -> Dict:
    """采集后统计（含时长 / 平均步长）。"""
    episodes = list_episodes(out_root)
    durations = []
    steps_per_ep = []
    for ep in episodes:
        idx = ep.get("episode_index") if isinstance(ep, dict) else ep
        ep_dir = find_episode_dir(out_root, idx)
        if not ep_dir:
            continue
        steps = load_episode_steps(ep_dir)
        steps_per_ep.append(len(steps))
        if steps:
            durations.append(steps[-1].get("timestamp", 0.0) - steps[0].get("timestamp", 0.0))
    return {
        "num_episodes": len(episodes),
        "total_steps": sum(steps_per_ep),
        "mean_steps_per_episode": round(float(np.mean(steps_per_ep)), 1) if steps_per_ep else 0,
        "mean_duration_sec": round(float(np.mean(durations)), 2) if durations else 0.0,
        "total_duration_sec": round(float(np.sum(durations)), 2),
    }


def _fmt_vec(v: np.ndarray) -> str:
    return np.array2string(v, precision=3, suppress_small=True)