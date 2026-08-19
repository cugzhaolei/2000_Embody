"""tracking + flywheel + ego 模块单元测试：训练评估关联管理与数据飞轮闭环。"""

import numpy as np
import pytest

from embodied_infra.tracking import (
    TrainingJob, ModelVersion, BenchmarkResult, RealWorldEval, FailureCase, TrainingRegistry,
)
from embodied_infra.flywheel import FailureIngester, FlywheelCurator, DataFlywheel
from embodied_infra.versioning.dataset_version import DatasetVersionManager
from embodied_infra.schemas.dataset import EpisodeMetadata
from embodied_infra.ego import (
    EgoVideoSegmenter, ActionPhaseRecognizer, EgoAbnormalFilter, EgoSampleGenerator,
)


# ---------- tracking ----------

def test_tracking_registry_lineage(tmp_path):
    """训练评估关联：血缘追溯完整覆盖 job/dataset/benchmark/eval/failure。"""
    registry = TrainingRegistry(str(tmp_path / "registry"))

    registry.register_job(TrainingJob(job_id="job_1", dataset_version="v2"))
    registry.register_model(ModelVersion(model_id="m1", training_job_id="job_1", artifact_path="/ckpt/m1.pt"))
    registry.update_job("job_1", model_id="m1", success_rate=0.6, finished=True)
    registry.register_benchmark(BenchmarkResult(benchmark_id="b1", name="sim", model_id="m1", overall_score=0.7))
    registry.register_eval(RealWorldEval(eval_id="e1", model_id="m1", task_name="pick_cup", num_trials=10, success_count=4))
    registry.register_failure(FailureCase(case_id="c1", task_name="pick_cup", model_id="m1", episode_id="ep1", failure_type="grasp_loss", priority=3))

    lineage = registry.trace_lineage("m1")
    assert lineage["training_job"]["job_id"] == "job_1"
    assert lineage["dataset_version"] == "v2"
    assert len(lineage["failure_cases"]) == 1

    low = registry.low_success_tasks("m1", threshold=0.5)
    assert "pick_cup" in low


def test_tracking_registry_persistence(tmp_path):
    """注册表持久化：重新打开后数据仍在。"""
    d = tmp_path / "reg2"
    r1 = TrainingRegistry(str(d))
    r1.register_job(TrainingJob(job_id="j1", dataset_version="v1"))
    r2 = TrainingRegistry(str(d))
    assert r2.get_job("j1") is not None


# ---------- flywheel ----------

def _make_curated_failure(registry, tmp_path):
    """准备一个可被飞轮策展的失败 Case 池。"""
    registry.register_job(TrainingJob(job_id="job_0", dataset_version="v1"))
    registry.register_model(ModelVersion(model_id="model_v1", training_job_id="job_0", artifact_path="/ckpt/v1.pt"))
    registry.register_eval(RealWorldEval(eval_id="eval_0", model_id="model_v1", task_name="pick_cup", num_trials=10, success_count=3))
    registry.register_failure(FailureCase(
        case_id="case_0", task_name="pick_cup", model_id="model_v1",
        episode_id="ep_1", failure_type="grasp_loss", priority=5,
    ))


def test_flywheel_full_cycle(tmp_path):
    """数据飞轮一轮闭环：失败回流 -> 新版本 -> 训练 -> 验证。"""
    reg_dir = tmp_path / "registry"
    ver_dir = tmp_path / "versions"
    registry = TrainingRegistry(str(reg_dir))
    vm = DatasetVersionManager(str(ver_dir))

    ep1 = EpisodeMetadata(episode_id="ep_1", task_name="pick_cup", num_steps=100, success=False)
    ep2 = EpisodeMetadata(episode_id="ep_2", task_name="pick_cup", num_steps=120, success=False)
    vm.create_version("v1", [ep1, ep2], description="initial")
    _make_curated_failure(registry, tmp_path)

    flywheel = DataFlywheel(registry, vm, FailureIngester(registry), FlywheelCurator(registry, max_per_task=10))
    episode_lookup = {"ep_1": ep1, "ep_2": ep2}

    def train_fn(dataset_version, job_id):
        return "model_v2"

    def eval_fn(model_id, task_filter):
        return {"pick_cup": {"trials": 10, "success": 8, "success_rate": 0.8}}

    report = flywheel.run_once(model_id="model_v1", episode_lookup=episode_lookup, train_fn=train_fn, eval_fn=eval_fn)
    assert report.new_version != ""
    assert report.training_job_id != ""


def test_flywheel_failure_ingest_from_episodes(tmp_path):
    """失败数据回流：从失败 Episode 批量生成 Case。"""
    registry = TrainingRegistry(str(tmp_path / "registry"))
    ingester = FailureIngester(registry)
    eps = [
        EpisodeMetadata(episode_id="e1", task_name="insert_peg", num_steps=50, success=False),
        EpisodeMetadata(episode_id="e2", task_name="insert_peg", num_steps=60, success=False),
    ]
    ingester.ingest_from_episodes(
        eps, model_id="m1",
    )
    cases = registry.list_failures(task_name="insert_peg")
    assert len(cases) >= 2


# ---------- ego ----------

def test_ego_segmenter_hysteresis():
    """Ego 片段切分：两个操作段被正确分离。"""
    fps = 30.0
    total = int(120 * fps)
    ts = np.arange(total) / fps
    motion = np.zeros(total)
    motion[int(40*fps):int(75*fps)] = 0.08  # 操作段 1
    motion[int(85*fps):int(120*fps)] = 0.06  # 操作段 2
    seg = EgoVideoSegmenter(min_active_sec=2.0, min_idle_sec=1.0, pad_sec=0.3)
    segments = seg.segment_by_motion(motion, ts)
    assert len(segments) == 2
    assert segments[0].start_time < segments[1].start_time


def test_ego_phase_recognizer():
    """动作阶段识别：grasp/manipulate/release 均被识别。"""
    fps = 30.0
    total = int(60 * fps)
    ts = np.arange(total) / fps
    motion = np.zeros(total)
    motion[int(5*fps):int(50*fps)] = 0.05
    hand = np.ones(total) * 0.9
    hand[int(10*fps):int(11*fps)] = np.linspace(0.9, 0.1, int(1*fps))
    hand[int(11*fps):int(40*fps)] = 0.1
    hand[int(40*fps):int(41*fps)] = np.linspace(0.1, 0.9, int(1*fps))
    rec = ActionPhaseRecognizer()
    spans = rec.recognize(motion, hand, ts)
    phases = {s.phase.value for s in spans if s.num_steps > 5}
    assert "grasp" in phases
    assert "manipulate" in phases
    assert "release" in phases


def test_ego_sample_generator(tmp_path):
    """训练样本生成：窗口滑窗产出样本并可导出 JSON。"""
    fps = 30.0
    total = int(30 * fps)
    ts = np.arange(total) / fps
    motion = np.ones(total) * 0.05
    seg = EgoVideoSegmenter(min_active_sec=1.0, min_idle_sec=1.0)
    segments = seg.segment_by_motion(motion, ts)
    gen = EgoSampleGenerator(window_size=10, stride=5)
    samples = gen.generate(
        segments, source_video="ego.mp4",
        instructions={s.segment_id: "pick cup" for s in segments},
        success_labels={s.segment_id: True for s in segments},
        phase_spans=[],
    )
    assert len(samples) > 0
    out = tmp_path / "samples.json"
    gen.export_json(samples, str(out))
    assert out.exists()
