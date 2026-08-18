"""
数据飞轮编排器
==============
串联「失败数据回流 -> 筛选整理 -> 加入训练集(新版本) -> 触发重训练 ->
实机/评测验证 -> 关闭 Case」的完整闭环，输出每轮飞轮报告。
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from ..tracking.models import (
    BenchmarkResult,
    FailureStatus,
    ModelVersion,
    RealWorldEval,
    TrainingJob,
)
from ..tracking.registry import TrainingRegistry
from ..versioning.dataset_version import DatasetVersionManager
from .curation import CuratedPool, FlywheelCurator
from .failure_ingest import FailureIngester


@dataclass
class FlywheelReport:
    """一轮飞轮的执行报告"""
    iteration: int = 0
    run_at: Optional[datetime] = None
    ingested: int = 0
    curated: int = 0
    new_version: str = ""
    training_job_id: str = ""
    model_id: str = ""
    verified_cases: int = 0
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "iteration": self.iteration,
            "run_at": self.run_at.isoformat() if self.run_at else None,
            "ingested": self.ingested,
            "curated": self.curated,
            "new_version": self.new_version,
            "training_job_id": self.training_job_id,
            "model_id": self.model_id,
            "verified_cases": self.verified_cases,
            "details": self.details,
        }


class DataFlywheel:
    """具身数据飞轮

    依赖:
    - TrainingRegistry: 失败 Case / 训练任务 / 模型 / 评测 关联管理
    - DatasetVersionManager: 创建回流后的新数据集版本
    - FailureIngester / FlywheelCurator: 接入与筛选

    训练/评估通过回调注入（train_fn / eval_fn），本模块不绑定具体训练框架。
    """

    def __init__(
        self,
        registry: TrainingRegistry,
        version_manager: DatasetVersionManager,
        ingester: Optional[FailureIngester] = None,
        curator: Optional[FlywheelCurator] = None,
    ):
        self.registry = registry
        self.version_manager = version_manager
        self.ingester = ingester or FailureIngester(registry)
        self.curator = curator or FlywheelCurator(registry)
        self._iteration = 0
        self._history: List[FlywheelReport] = []

    # ------------------------------------------------------------------
    def run_once(
        self,
        model_id: str,
        episode_lookup: Optional[Dict[str, Any]] = None,
        task_filter: Optional[List[str]] = None,
        train_fn: Optional[Callable[[str, str], str]] = None,
        eval_fn: Optional[Callable[[str, str], Dict[str, Any]]] = None,
        new_model_id: str = "",
        new_version_desc: str = "",
    ) -> FlywheelReport:
        """执行一轮飞轮

        Args:
            model_id: 当前要改进的模型
            episode_lookup: episode_id -> EpisodeMetadata（失败数据的原始数据）
            task_filter: 仅回流指定任务
            train_fn: (dataset_version, job_id) -> 产出模型 id（外部训练）
            eval_fn: (model_id, task_filter) -> 返回 {task: {trials, success}} 等
            new_model_id: 新模型 id（train_fn 未提供时使用）
        """
        self._iteration += 1
        report = FlywheelReport(iteration=self._iteration, run_at=datetime.now())

        # 1. 接入失败数据（低成功率任务自动纳入）
        low_tasks = self.registry.low_success_tasks(model_id, threshold=0.5)
        report.details["low_success_tasks"] = low_tasks
        if low_tasks:
            cases = self.registry.list_failures(status=FailureStatus.OPEN)
            missing = [t for t in low_tasks
                       if t not in {c.task_name for c in cases}]
            for task in missing:
                self.ingester.ingest_manual(
                    task_name=task, model_id=model_id,
                    failure_type="low_success", priority=4,
                )
        report.ingested = len(self.registry.list_failures(status=FailureStatus.OPEN))

        # 2. 筛选
        pool = self.curator.curate(tasks=task_filter)
        report.curated = pool.total_cases
        report.details["pool_stats"] = pool.stats
        if pool.total_cases == 0:
            report.details["note"] = "no curated cases this round"
            self._history.append(report)
            return report

        # 3. 加入训练集 -> 创建新数据集版本
        episodes = self.curator.to_episodes(pool, episode_lookup or {})
        if episodes:
            version = f"{self.version_manager._current_version or 'v1'}.{self._iteration}"
            # 幂等版本号
            if self.version_manager.get_version(version):
                version = f"fw{datetime.now().strftime('%Y%m%d%H%M%S')}"
            self.version_manager.create_version(
                version=version,
                episodes=episodes,
                description=new_version_desc or f"flywheel iteration {self._iteration}",
                changelog=f"flywheel: {len(episodes)} failure episodes",
            )
            report.new_version = version
            for case in pool.cases:
                self.registry.update_failure_status(
                    case.case_id, FailureStatus.ADDED_TO_TRAINING, retrain_version=version
                )

        # 4. 触发重训练
        job = TrainingJob(
            job_id=f"job_fw_{self._iteration}",
            dataset_version=report.new_version or "",
        )
        self.registry.register_job(job)
        report.training_job_id = job.job_id

        produced_model = new_model_id or f"model_fw_{self._iteration}"
        if train_fn is not None:
            try:
                produced_model = train_fn(report.new_version, job.job_id)
            except Exception as e:  # 训练失败不阻塞飞轮
                report.details["train_error"] = str(e)
        self.registry.update_job(
            job.job_id, model_id=produced_model, finished=True
        )
        self.registry.register_model(
            ModelVersion(
                model_id=produced_model,
                version="v1",
                training_job_id=job.job_id,
                metrics={"dataset_version": report.new_version},
            )
        )
        report.model_id = produced_model

        # 5. 验证（可选）并关闭已验证 Case
        if eval_fn is not None:
            try:
                eval_result = eval_fn(produced_model, task_filter)
                self._record_eval_result(produced_model, eval_result)
                report.verified_cases = self._close_verified_cases(
                    produced_model, eval_result
                )
                report.details["eval_result"] = eval_result
            except Exception as e:
                report.details["eval_error"] = str(e)

        self._history.append(report)
        return report

    # ------------------------------------------------------------------
    def record_real_world_eval(
        self,
        model_id: str,
        task_name: str,
        num_trials: int,
        success_count: int,
        robot_id: str = "",
        environment: str = "",
        notes: str = "",
    ) -> RealWorldEval:
        """登记一次实机评估，自动生成失败 Case 并触发回流"""
        ev = RealWorldEval(
            eval_id=f"eval_{datetime.now().strftime('%Y%m%d%H%M%S')}_{len(self.registry.list_evals()):04d}",
            model_id=model_id,
            task_name=task_name,
            robot_id=robot_id,
            num_trials=num_trials,
            success_count=success_count,
            environment=environment,
            notes=notes,
        )
        self.registry.register_eval(ev)

        # 失败 -> 按「模型+任务」聚合为一个失败 Case（避免同一评估产生大量重复 Case）
        failed = num_trials - success_count
        if failed > 0:
            self.ingester.ingest_manual(
                task_name=task_name,
                model_id=model_id,
                robot_id=robot_id,
                failure_type="real_world",
                description=(
                    f"real-world eval {task_name}: {success_count}/{num_trials} "
                    f"({failed} failures)"
                ),
                priority=min(5, 2 + failed // 5),
                case_id=f"case_eval_{ev.eval_id}",
            )
        return ev

    def benchmark(self, bench: BenchmarkResult) -> BenchmarkResult:
        """登记 Benchmark 评测结果"""
        return self.registry.register_benchmark(bench)

    def history(self) -> List[FlywheelReport]:
        return list(self._history)

    # ------------------------------------------------------------------
    def _record_eval_result(self, model_id: str, eval_result: Dict[str, Any]) -> None:
        """把 eval_fn 的返回结构登记为 RealWorldEval 并回流失败"""
        for task, info in eval_result.items():
            if isinstance(info, dict):
                trials = int(info.get("trials", 0))
                success = int(info.get("success", 0))
                if trials > 0:
                    self.record_real_world_eval(
                        model_id=model_id, task_name=task,
                        num_trials=trials, success_count=success,
                        environment=info.get("environment", ""),
                        notes=info.get("notes", ""),
                    )

    def _close_verified_cases(self, model_id: str, eval_result: Dict[str, Any]) -> int:
        """新模型在相关任务成功率达标后，关闭对应失败 Case"""
        verified = 0
        for task, info in eval_result.items():
            if not isinstance(info, dict):
                continue
            rate = info.get("success_rate")
            if rate is None and info.get("trials"):
                rate = info.get("success", 0) / info["trials"]
            if rate is None or rate < 0.7:
                continue
            for case in self.registry.list_failures(
                task_name=task, status=FailureStatus.ADDED_TO_TRAINING
            ):
                self.registry.update_failure_status(case.case_id, FailureStatus.VERIFIED)
                verified += 1
        return verified
