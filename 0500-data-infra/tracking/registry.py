"""
训练评估关联注册中心
====================
集中管理训练任务、模型版本、Benchmark、实机评估、失败 Case，
提供实体注册、查询、血缘追溯与聚合统计。JSON 文件持久化。

血缘链路示例:
    Dataset 版本 -> TrainingJob -> ModelVersion
        -> BenchmarkResult / RealWorldEval -> FailureCase -> 新 Dataset 版本
"""

import json
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from .models import (
    BenchmarkResult,
    FailureCase,
    FailureStatus,
    ModelVersion,
    RealWorldEval,
    TrainingJob,
)


class TrainingRegistry:
    """训练评估关联注册中心（JSON 存储）"""

    def __init__(self, store_dir: str):
        self.store_dir = Path(store_dir)
        self.store_dir.mkdir(parents=True, exist_ok=True)

        self._lock = threading.Lock()
        self._jobs: Dict[str, TrainingJob] = {}
        self._models: Dict[str, ModelVersion] = {}
        self._benchmarks: Dict[str, BenchmarkResult] = {}
        self._evals: Dict[str, RealWorldEval] = {}
        self._failures: Dict[str, FailureCase] = {}

        self._load()

    # ------------------------------------------------------------------
    # 持久化
    # ------------------------------------------------------------------
    def _load(self) -> None:
        for key, cls, loader in [
            ("jobs", TrainingJob, self._load_jobs),
            ("models", ModelVersion, self._load_models),
            ("benchmarks", BenchmarkResult, self._load_benchmarks),
            ("evals", RealWorldEval, self._load_evals),
            ("failures", FailureCase, self._load_failures),
        ]:
            loader()

    def _read_json(self, name: str) -> dict:
        path = self.store_dir / f"{name}.json"
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def _write_json(self, name: str, data: dict) -> None:
        path = self.store_dir / f"{name}.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)

    def _load_jobs(self) -> None:
        for k, v in self._read_json("jobs").items():
            self._jobs[k] = TrainingJob.from_dict(v)

    def _load_models(self) -> None:
        for k, v in self._read_json("models").items():
            self._models[k] = ModelVersion.from_dict(v)

    def _load_benchmarks(self) -> None:
        for k, v in self._read_json("benchmarks").items():
            self._benchmarks[k] = BenchmarkResult.from_dict(v)

    def _load_evals(self) -> None:
        for k, v in self._read_json("evals").items():
            self._evals[k] = RealWorldEval.from_dict(v)

    def _load_failures(self) -> None:
        for k, v in self._read_json("failures").items():
            self._failures[k] = FailureCase.from_dict(v)

    def _save_all(self) -> None:
        with self._lock:
            self._write_json("jobs", {k: v.to_dict() for k, v in self._jobs.items()})
            self._write_json("models", {k: v.to_dict() for k, v in self._models.items()})
            self._write_json("benchmarks", {k: v.to_dict() for k, v in self._benchmarks.items()})
            self._write_json("evals", {k: v.to_dict() for k, v in self._evals.items()})
            self._write_json("failures", {k: v.to_dict() for k, v in self._failures.items()})

    # ------------------------------------------------------------------
    # 注册 / 更新
    # ------------------------------------------------------------------
    def register_job(self, job: TrainingJob) -> TrainingJob:
        if job.job_id in self._jobs:
            raise ValueError(f"TrainingJob '{job.job_id}' already exists")
        if job.started_at is None:
            job.started_at = datetime.now()
        self._jobs[job.job_id] = job
        self._save_all()
        return job

    def update_job(
        self, job_id: str, status=None, metrics=None, success_rate=None,
        model_id=None, finished=None,
    ) -> Optional[TrainingJob]:
        job = self._jobs.get(job_id)
        if job is None:
            return None
        if status is not None:
            job.status = status
        if metrics is not None:
            job.metrics.update(metrics)
        if success_rate is not None:
            job.success_rate = success_rate
        if model_id is not None:
            job.model_id = model_id
        if finished:
            job.finished_at = datetime.now()
        self._save_all()
        return job

    def register_model(self, model: ModelVersion) -> ModelVersion:
        key = f"{model.model_id}@{model.version}"
        if key in self._models:
            raise ValueError(f"ModelVersion '{key}' already exists")
        if model.created_at is None:
            model.created_at = datetime.now()
        self._models[key] = model
        self._save_all()
        return model

    def register_benchmark(self, bench: BenchmarkResult) -> BenchmarkResult:
        if bench.benchmark_id in self._benchmarks:
            raise ValueError(f"BenchmarkResult '{bench.benchmark_id}' already exists")
        if bench.created_at is None:
            bench.created_at = datetime.now()
        self._benchmarks[bench.benchmark_id] = bench
        self._save_all()
        return bench

    def register_eval(self, ev: RealWorldEval) -> RealWorldEval:
        if ev.eval_id in self._evals:
            raise ValueError(f"RealWorldEval '{ev.eval_id}' already exists")
        if ev.created_at is None:
            ev.created_at = datetime.now()
        if ev.num_trials > 0:
            ev.success_rate = ev.success_count / ev.num_trials
        self._evals[ev.eval_id] = ev
        self._save_all()
        return ev

    def register_failure(self, case: FailureCase) -> FailureCase:
        if case.case_id in self._failures:
            raise ValueError(f"FailureCase '{case.case_id}' already exists")
        if case.created_at is None:
            case.created_at = datetime.now()
        self._failures[case.case_id] = case
        self._save_all()
        return case

    def update_failure_status(
        self, case_id: str, status: FailureStatus, retrain_version: str = "",
    ) -> Optional[FailureCase]:
        case = self._failures.get(case_id)
        if case is None:
            return None
        case.status = status
        if retrain_version:
            case.retrain_version = retrain_version
        self._save_all()
        return case

    # ------------------------------------------------------------------
    # 查询
    # ------------------------------------------------------------------
    def get_job(self, job_id: str) -> Optional[TrainingJob]:
        return self._jobs.get(job_id)

    def get_model(self, model_id: str, version: str = "v1") -> Optional[ModelVersion]:
        return self._models.get(f"{model_id}@{version}")

    def get_failure(self, case_id: str) -> Optional[FailureCase]:
        return self._failures.get(case_id)

    def list_jobs(self, dataset_version: Optional[str] = None) -> List[TrainingJob]:
        jobs = list(self._jobs.values())
        if dataset_version:
            jobs = [j for j in jobs if j.dataset_version == dataset_version]
        return sorted(jobs, key=lambda j: j.started_at or datetime.min, reverse=True)

    def list_models(self, training_job_id: Optional[str] = None) -> List[ModelVersion]:
        models = list(self._models.values())
        if training_job_id:
            models = [m for m in models if m.training_job_id == training_job_id]
        return sorted(models, key=lambda m: m.created_at or datetime.min, reverse=True)

    def list_benchmarks(self, model_id: Optional[str] = None) -> List[BenchmarkResult]:
        benches = list(self._benchmarks.values())
        if model_id:
            benches = [b for b in benches if b.model_id == model_id]
        return sorted(benches, key=lambda b: b.created_at or datetime.min, reverse=True)

    def list_evals(
        self,
        model_id: Optional[str] = None,
        task_name: Optional[str] = None,
    ) -> List[RealWorldEval]:
        evals = list(self._evals.values())
        if model_id:
            evals = [e for e in evals if e.model_id == model_id]
        if task_name:
            evals = [e for e in evals if e.task_name == task_name]
        return sorted(evals, key=lambda e: e.created_at or datetime.min, reverse=True)

    def list_failures(
        self,
        model_id: Optional[str] = None,
        task_name: Optional[str] = None,
        status: Optional[FailureStatus] = None,
        min_priority: int = 0,
    ) -> List[FailureCase]:
        cases = list(self._failures.values())
        if model_id:
            cases = [c for c in cases if c.model_id == model_id]
        if task_name:
            cases = [c for c in cases if c.task_name == task_name]
        if status:
            cases = [c for c in cases if c.status == status]
        if min_priority > 0:
            cases = [c for c in cases if c.priority >= min_priority]
        return sorted(cases, key=lambda c: c.priority, reverse=True)

    # ------------------------------------------------------------------
    # 血缘追溯 / 聚合
    # ------------------------------------------------------------------
    def trace_lineage(self, model_id: str) -> Dict[str, Any]:
        """追溯模型完整血缘: 数据集 -> 训练任务 -> 模型 -> 评测/失败"""
        model = self.get_model(model_id)
        if model is None:
            return {"error": f"Model '{model_id}' not found"}

        job = self._jobs.get(model.training_job_id)
        lineage: Dict[str, Any] = {
            "model": model.to_dict(),
            "training_job": job.to_dict() if job else None,
            "dataset_version": job.dataset_version if job else "",
            "benchmarks": [b.to_dict() for b in self.list_benchmarks(model_id)],
            "real_world_evals": [e.to_dict() for e in self.list_evals(model_id)],
            "failure_cases": [
                c.to_dict() for c in self.list_failures(model_id=model_id)
            ],
        }
        return lineage

    def trace_dataset(self, dataset_version: str) -> Dict[str, Any]:
        """从 Dataset 版本出发向下追溯"""
        jobs = self.list_jobs(dataset_version=dataset_version)
        return {
            "dataset_version": dataset_version,
            "jobs": [j.to_dict() for j in jobs],
            "models": [
                m.to_dict() for m in self.list_models()
                if any(m.training_job_id == j.job_id for j in jobs)
            ],
        }

    def aggregate_success_rate_by_task(self, model_id: str) -> Dict[str, Dict[str, Any]]:
        """按任务聚合实机成功率（用于识别低成功率任务）"""
        agg: Dict[str, Dict[str, Any]] = {}
        for ev in self.list_evals(model_id=model_id):
            entry = agg.setdefault(ev.task_name, {"trials": 0, "success": 0, "evals": 0})
            entry["trials"] += ev.num_trials
            entry["success"] += ev.success_count
            entry["evals"] += 1
        for task, entry in agg.items():
            entry["success_rate"] = (
                entry["success"] / entry["trials"] if entry["trials"] > 0 else 0.0
            )
        return agg

    def low_success_tasks(self, model_id: str, threshold: float = 0.5) -> List[str]:
        """返回成功率低于阈值的任务列表（数据飞轮输入）"""
        agg = self.aggregate_success_rate_by_task(model_id)
        return sorted(
            [t for t, e in agg.items() if e["success_rate"] < threshold],
            key=lambda t: agg[t]["success_rate"],
        )
