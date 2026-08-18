"""
演示数据生成
============
- Ego 长视频合成场景（运动量 + 手部开合度 + 时间戳）
- 训练评估平台种子数据（版本 / 任务 / 模型 / 评测 / 失败 Case）
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

import numpy as np

from ..tracking.models import (
    BenchmarkResult,
    FailureCase,
    FailureStatus,
    ModelVersion,
    RealWorldEval,
    TrainingJob,
)
from ..schemas.dataset import EpisodeMetadata


# ======================================================================
# Ego 合成场景
# ======================================================================
def generate_ego_scenario(
    duration_sec: float = 120.0,
    fps: float = 30.0,
    operation_windows: Optional[List[Dict[str, float]]] = None,
    motion_amplitude: float = 0.08,
    motion_noise: float = 0.01,
    idle_noise: float = 0.002,
    seed: int = 42,
) -> Dict[str, Any]:
    """合成一段 Ego 长视频的运动量 / 手部开合 / 时间戳

    operation_windows: [{"start": 40, "end": 75, "amplitude": 0.08}, ...]
    手部开合: 每个操作窗口内 闭合(15%) -> 持握 -> 张开(10%)
    """
    rng = np.random.default_rng(seed)
    n = int(duration_sec * fps)
    ts = np.arange(n) / fps

    if operation_windows is None:
        operation_windows = [
            {"start": 40, "end": 75, "amplitude": motion_amplitude},
            {"start": 85, "end": 120, "amplitude": motion_amplitude * 0.8},
        ]

    motion = np.full(n, idle_noise)
    motion += rng.normal(0, idle_noise * 0.5, n)

    for w in operation_windows:
        s = int(w["start"] * fps)
        e = int(w["end"] * fps)
        amp = w.get("amplitude", motion_amplitude)
        base = amp + rng.normal(0, motion_noise, e - s)
        motion[s:e] = np.abs(base)
        # 操作中短暂停顿，考验滞回阈值
        dip_len = max(1, int(1.5 * fps))
        if (e - s) > dip_len * 3:
            motion[s + int(fps * 1): s + int(fps * 1) + dip_len] = idle_noise

    # 手部开合度
    openness = np.full(n, 0.9)
    for w in operation_windows:
        s = int(w["start"] * fps)
        e = int(w["end"] * fps)
        length = e - s
        close_end = s + max(1, int(length * 0.15))
        open_start = e - max(1, int(length * 0.10))
        if close_end < open_start:
            openness[s:close_end] = np.linspace(0.9, 0.1, close_end - s)
            openness[close_end:open_start] = 0.1
            openness[open_start:e] = np.linspace(0.1, 0.9, e - open_start)

    return {
        "motion": motion.tolist(),
        "timestamps": ts.tolist(),
        "hand_openness": openness.tolist(),
        "fps": fps,
        "duration_sec": duration_sec,
        "operation_windows": operation_windows,
    }


# ======================================================================
# 训练评估平台种子数据
# ======================================================================
SEED_TASKS = {
    "pick_cup": {"trials": 20, "success": 8},
    "insert_peg": {"trials": 20, "success": 6},
    "stack_blocks": {"trials": 15, "success": 12},
    "pour_water": {"trials": 12, "success": 7},
}


def _seed_episodes() -> List[EpisodeMetadata]:
    episodes = []
    for i in range(8):
        task = ["pick_cup", "pick_cup", "insert_peg", "insert_peg",
                "stack_blocks", "stack_blocks", "pour_water", "pour_water"][i]
        failed = i in (1, 3, 7)   # 部分失败样本
        episodes.append(
            EpisodeMetadata(
                episode_id=f"ep_{i+1:03d}",
                task_name=task,
                robot_id="so101",
                operator_id="demo_operator",
                scene_id="demo_scene",
                num_steps=100 + i * 20,
                modalities=["rgb", "depth", "joint_state", "action"],
                success=not failed,
                source_device="demo",
            )
        )
    return episodes


def seed(app_state) -> None:
    """首次启动时写入演示数据（已存在则跳过）"""
    if app_state.registry.list_jobs():
        return

    registry = app_state.registry
    vm = app_state.version_manager

    # 1. 初始数据集版本
    episodes = _seed_episodes()
    vm.create_version("v1", episodes, description="seed demo dataset")

    # 2. 基线训练任务 -> 模型 v1
    registry.register_job(TrainingJob(
        job_id="job_001", dataset_version="v1",
    ))
    registry.update_job(
        "job_001", model_id="model_act_v1", success_rate=0.55, finished=True,
    )
    registry.register_model(ModelVersion(
        model_id="model_act_v1", version="v1",
        artifact_path="checkpoints/model_act_v1.pt", training_job_id="job_001",
        metrics={"success_rate": 0.55},
    ))
    registry.register_benchmark(BenchmarkResult(
        benchmark_id="bench_001", name="sim_bench_v1",
        model_id="model_act_v1", dataset_version="v1",
        overall_score=0.58,
    ))

    # 3. 实机评估（低成功率任务 -> 失败 Case）
    for task, info in SEED_TASKS.items():
        registry.register_eval(RealWorldEval(
            eval_id=f"eval_{task}",
            model_id="model_act_v1", task_name=task, robot_id="so101",
            num_trials=info["trials"], success_count=info["success"],
            environment="demo_table",
        ))
        failed = info["trials"] - info["success"]
        if failed >= 2 and task in ("pick_cup", "insert_peg", "pour_water"):
            for k in range(min(failed, 2)):
                registry.register_failure(FailureCase(
                    case_id=f"case_{task}_{k}",
                    task_name=task, model_id="model_act_v1",
                    episode_id=f"ep_{3 + k * 4:03d}" if task != "pour_water" else f"ep_{8:03d}",
                    failure_type={"pick_cup": "grasp_loss", "insert_peg": "collision",
                                  "pour_water": "spill"}[task],
                    priority=3 + k, status=FailureStatus.OPEN,
                ))

    # 4. 预置一轮飞轮（v1.1 回流 + 重训练 -> model_act_v2 提升）
    #    run_once 内部已注册 job / model / eval / failure case，无需重复注册
    flywheel = app_state.flywheel
    episode_lookup = app_state.load_all_episodes()

    def train_fn(ds_version: str, job_id: str) -> str:
        return "model_act_v2"

    def eval_fn(model_id: str, task_filter=None) -> Dict[str, Any]:
        result = {}
        for task, info in SEED_TASKS.items():
            result[task] = {
                "trials": info["trials"],
                "success": min(info["trials"], int(info["success"] * 1.6)),
                "success_rate": min(0.95, (info["success"] / info["trials"]) * 1.6),
            }
        return result

    try:
        flywheel.run_once(
            model_id="model_act_v1",
            episode_lookup=episode_lookup,
            train_fn=train_fn,
            eval_fn=eval_fn,
            new_model_id="model_act_v2",
            new_version_desc="seed flywheel round",
        )
    except Exception as e:  # pragma: no cover - 种子失败不阻塞启动
        print(f"[demo] flywheel seed skipped: {e}")

    print("[demo] seeded demo data: 1 version, 2 models, 1 benchmark, "
          f"{len(SEED_TASKS)} evals, {len(registry.list_failures())} failure cases")
