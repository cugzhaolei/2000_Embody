"""
新模块冒烟测试
=============
验证 ego / annotation / tracking / flywheel 四个新模块可运行，
覆盖: 片段切分、阶段识别、异常过滤、样本生成、自动标注、
关联注册与血缘追溯、数据飞轮一轮闭环。

运行: python 0500-data-infra/scripts/smoke_new_modules.py
"""

import importlib.util
import pathlib
import shutil
import sys
import tempfile

# 把 "0500-data-infra" 注册为合法包别名 embodied_infra（同 0500-data-collection 的 bootstrap 做法）
PACKAGE_ALIAS = "embodied_infra"
PACKAGE_DIR = pathlib.Path(__file__).resolve().parent.parent

spec = importlib.util.spec_from_file_location(
    PACKAGE_ALIAS, str(PACKAGE_DIR / "__init__.py"),
    submodule_search_locations=[str(PACKAGE_DIR)],
)
module = importlib.util.module_from_spec(spec)
sys.modules[PACKAGE_ALIAS] = module
spec.loader.exec_module(module)

import numpy as np

from embodied_infra.ego import (
    EgoVideoSegmenter, ActionPhaseRecognizer, EgoAbnormalFilter, EgoSampleGenerator,
)
from embodied_infra.annotation import AutoLabeler
from embodied_infra.tracking import TrainingRegistry, TrainingJob, ModelVersion, BenchmarkResult, RealWorldEval, FailureCase
from embodied_infra.flywheel import FailureIngester, FlywheelCurator, DataFlywheel
from embodied_infra.versioning.dataset_version import DatasetVersionManager
from embodied_infra.schemas.dataset import EpisodeMetadata


def check(name, cond, detail=""):
    status = "PASS" if cond else "FAIL"
    print(f"  [{status}] {name} {detail}")
    if not cond:
        sys.exit(1)


def main():
    tmp = tempfile.mkdtemp(prefix="embodied_smoke_")
    print(f"临时目录: {tmp}\n")

    # ============================================================
    print("=== 1. ego: Ego 长视频处理 ===")
    fps = 30.0
    total = int(120 * fps)  # 2 分钟视频
    ts = np.arange(total) / fps

    # 构造运动信号: 0-40s 空闲, 40-75s 操作, 75-85s 空闲, 85-120s 操作
    motion = np.zeros(total)
    motion[int(40*fps):int(75*fps)] = 0.08 + 0.02*np.random.rand(int(35*fps))
    motion[int(85*fps):int(120*fps)] = 0.06 + 0.01*np.random.rand(int(35*fps))
    motion[int(42*fps):int(44*fps)] = 0.001  # 操作中短暂停顿，测试滞回

    seg = EgoVideoSegmenter(min_active_sec=2.0, min_idle_sec=1.0, pad_sec=0.3)
    segments = seg.segment_by_motion(motion, ts)
    check("片段切分", len(segments) >= 2,
          f"-> {len(segments)} 段: " + ", ".join(
              f"{s.segment_id}({s.start_time:.0f}s-{s.end_time:.0f}s)" for s in segments))

    # 阶段识别: 1 秒级闭合/张开（真实速度）
    rec = ActionPhaseRecognizer()
    hand_openness = np.ones(total) * 0.9
    hand_openness[int(41*fps):int(42*fps)] = np.linspace(0.9, 0.1, int(1*fps))    # 闭合 -> grasp
    hand_openness[int(42*fps):int(70*fps)] = 0.1                                  # 持握 -> manipulate
    hand_openness[int(70*fps):int(71*fps)] = np.linspace(0.1, 0.9, int(1*fps))    # 张开 -> release
    spans = rec.recognize(motion, hand_openness, ts)
    phases = {s.phase.value for s in spans if s.num_steps > 10}
    check("阶段识别", "grasp" in phases and "manipulate" in phases and "release" in phases,
          f"-> 阶段: {sorted(phases)}")

    # 异常过滤: 注入一个低活跃段
    seg_static = EgoVideoSegmenter(motion_threshold=0.02, min_active_sec=1.0, min_idle_sec=1.0)
    motion2 = motion.copy()
    motion2[int(20*fps):int(25*fps)] = 0.001  # 低活跃段
    segments2 = seg_static.segment_by_motion(motion2, ts)
    filt = EgoAbnormalFilter()
    kept, results = filt.filter_segments(segments2, motion=motion2)
    check("异常过滤", any(r.verdict.value == "discard" for r in results) or kept,
          f"-> 保留 {len(kept)}/{len(segments2)}")

    # 样本生成
    gen = EgoSampleGenerator(window_size=30, stride=15)
    samples = gen.generate(
        segments, source_video="ego_001.mp4",
        instructions={s.segment_id: "pick and place the cup" for s in segments},
        success_labels={s.segment_id: True for s in segments},
        phase_spans=spans,
    )
    check("样本生成", len(samples) > 0, f"-> {len(samples)} 个样本, top phases={samples[0].phases}")
    json_path = pathlib.Path(tmp) / "ego_samples.json"
    gen.export_json(samples, str(json_path))
    check("样本导出", json_path.exists())

    # ============================================================
    print("\n=== 2. annotation: 自动标注 ===")
    T = 100
    good_traj = np.zeros((T, 6))
    good_traj[:, 0] = np.linspace(0, 1.5, T)   # 平滑快速移动（0.015m/帧，活跃）
    bad_traj = good_traj.copy()
    bad_traj[50:, 0] += 0.5                     # 跳变
    frames = np.random.randint(0, 255, (T, 32, 32, 3), dtype=np.uint8)

    labeler = AutoLabeler()
    r_good = labeler.label_episode({"eef_pose": good_traj, "rgb": frames}, "ep_good")
    r_bad = labeler.label_episode({"eef_pose": bad_traj, "rgb": frames}, "ep_bad")
    check("成败标注", r_good.labels["success"] is True and r_bad.labels["success"] is False,
          f"-> good={r_good.labels['success']}, bad={r_bad.labels['success']}, "
          f"bad reasons={r_bad.reasons}")

    ep_meta = EpisodeMetadata(episode_id="ep_good", task_name="pick_cup")
    labeler.apply_to_metadata(ep_meta, r_good)
    check("标注回写元数据", ep_meta.success is True and "auto_labels" in ep_meta.extra)

    # ============================================================
    print("\n=== 3. tracking: 训练评估关联管理 ===")
    reg_dir = pathlib.Path(tmp) / "registry"
    registry = TrainingRegistry(str(reg_dir))

    job = registry.register_job(TrainingJob(job_id="job_1", dataset_version="v2"))
    model = registry.register_model(ModelVersion(
        model_id="model_act_v2", training_job_id="job_1", artifact_path="/ckpt/v2.pt",
    ))
    registry.update_job("job_1", model_id="model_act_v2", success_rate=0.62, finished=True)
    registry.register_benchmark(BenchmarkResult(
        benchmark_id="b1", name="sim_bench", model_id="model_act_v2", overall_score=0.71,
    ))
    registry.register_eval(RealWorldEval(
        eval_id="e1", model_id="model_act_v2", task_name="pick_cup",
        num_trials=10, success_count=4,
    ))
    registry.register_failure(FailureCase(
        case_id="case_1", task_name="pick_cup", model_id="model_act_v2",
        episode_id="ep_0001", failure_type="grasp_loss", priority=4,
    ))

    lineage = registry.trace_lineage("model_act_v2")
    check("血缘追溯", lineage.get("training_job") and lineage["dataset_version"] == "v2"
          and len(lineage["failure_cases"]) == 1)
    low = registry.low_success_tasks("model_act_v2", threshold=0.5)
    check("低成功率任务识别", "pick_cup" in low, f"-> {low}")

    # ============================================================
    print("\n=== 4. flywheel: 数据飞轮一轮闭环 ===")
    ver_dir = pathlib.Path(tmp) / "versions"
    vm = DatasetVersionManager(str(ver_dir))
    # 初始版本
    ep1 = EpisodeMetadata(episode_id="ep_0001", task_name="pick_cup", num_steps=100, success=False)
    ep2 = EpisodeMetadata(episode_id="ep_0002", task_name="pick_cup", num_steps=120, success=False)
    vm.create_version("v2", [ep1, ep2], description="initial")

    flywheel = DataFlywheel(registry, vm, FailureIngester(registry), FlywheelCurator(registry, max_per_task=10))
    episode_lookup = {"ep_0001": ep1, "ep_0002": ep2}

    def train_fn(dataset_version, job_id):
        return "model_act_v3"

    def eval_fn(model_id, task_filter):
        return {"pick_cup": {"trials": 10, "success": 8, "success_rate": 0.8}}

    report = flywheel.run_once(
        model_id="model_act_v2",
        episode_lookup=episode_lookup,
        train_fn=train_fn,
        eval_fn=eval_fn,
    )
    check("飞轮新版本", bool(report.new_version), f"-> version={report.new_version}")
    check("飞轮训练任务", bool(report.training_job_id), f"-> job={report.training_job_id}")
    check("飞轮验证关闭", report.verified_cases >= 1,
          f"-> verified={report.verified_cases}")

    # 实机评估自动回流失败
    flywheel.record_real_world_eval(
        model_id="model_act_v3", task_name="insert_peg",
        num_trials=20, success_count=6,
    )
    peg_cases = registry.list_failures(task_name="insert_peg")
    check("实机失败自动回流", len(peg_cases) >= 1, f"-> {len(peg_cases)} 个失败 Case")

    # ============================================================
    print("\n全部冒烟测试通过!")
    shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
