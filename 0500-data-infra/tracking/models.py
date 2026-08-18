"""
训练评估关联实体
================
定义 Dataset、训练任务、模型版本、Benchmark、实机结果、失败 Case
等实体及其关联字段，全部支持 to_dict/from_dict 持久化。
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class JobStatus(str, Enum):
    """训练任务状态"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class FailureStatus(str, Enum):
    """失败 Case 生命周期"""
    OPEN = "open"                       # 刚上报/回流
    IN_CURATION = "in_curation"         # 进入筛选整理
    ADDED_TO_TRAINING = "added_to_training"  # 已加入训练集
    VERIFIED = "verified"               # 新模型验证通过
    CLOSED = "closed"                   # 已关闭


@dataclass
class TrainingJob:
    """训练任务"""
    job_id: str
    dataset_version: str                 # 使用的 Dataset 版本
    model_id: str = ""                   # 产出模型 ID（成功后填充）
    config: Dict[str, Any] = field(default_factory=dict)   # 训练配置快照
    status: JobStatus = JobStatus.PENDING
    metrics: Dict[str, Any] = field(default_factory=dict)  # loss/epoch 等
    success_rate: Optional[float] = None # 训练集/验证集成功率
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    tags: List[str] = field(default_factory=list)
    extra: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "job_id": self.job_id,
            "dataset_version": self.dataset_version,
            "model_id": self.model_id,
            "config": self.config,
            "status": self.status.value,
            "metrics": self.metrics,
            "success_rate": self.success_rate,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "tags": self.tags,
            "extra": self.extra,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "TrainingJob":
        return cls(
            job_id=d["job_id"],
            dataset_version=d["dataset_version"],
            model_id=d.get("model_id", ""),
            config=d.get("config", {}),
            status=JobStatus(d.get("status", "pending")),
            metrics=d.get("metrics", {}),
            success_rate=d.get("success_rate"),
            started_at=_parse_dt(d.get("started_at")),
            finished_at=_parse_dt(d.get("finished_at")),
            tags=d.get("tags", []),
            extra=d.get("extra", {}),
        )


@dataclass
class ModelVersion:
    """模型版本"""
    model_id: str
    version: str = "v1"
    artifact_path: str = ""
    training_job_id: str = ""            # 由哪个训练任务产出
    metrics: Dict[str, Any] = field(default_factory=dict)
    created_at: Optional[datetime] = None
    tags: List[str] = field(default_factory=list)
    extra: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "model_id": self.model_id,
            "version": self.version,
            "artifact_path": self.artifact_path,
            "training_job_id": self.training_job_id,
            "metrics": self.metrics,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "tags": self.tags,
            "extra": self.extra,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "ModelVersion":
        return cls(
            model_id=d["model_id"],
            version=d.get("version", "v1"),
            artifact_path=d.get("artifact_path", ""),
            training_job_id=d.get("training_job_id", ""),
            metrics=d.get("metrics", {}),
            created_at=_parse_dt(d.get("created_at")),
            tags=d.get("tags", []),
            extra=d.get("extra", {}),
        )


@dataclass
class BenchmarkResult:
    """Benchmark 评测结果"""
    benchmark_id: str
    name: str                              # benchmark 名称
    model_id: str = ""
    dataset_version: str = ""              # 使用的评测集版本
    metrics: Dict[str, Any] = field(default_factory=dict)
    overall_score: float = 0.0
    created_at: Optional[datetime] = None
    extra: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "benchmark_id": self.benchmark_id,
            "name": self.name,
            "model_id": self.model_id,
            "dataset_version": self.dataset_version,
            "metrics": self.metrics,
            "overall_score": self.overall_score,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "extra": self.extra,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "BenchmarkResult":
        return cls(
            benchmark_id=d["benchmark_id"],
            name=d["name"],
            model_id=d.get("model_id", ""),
            dataset_version=d.get("dataset_version", ""),
            metrics=d.get("metrics", {}),
            overall_score=d.get("overall_score", 0.0),
            created_at=_parse_dt(d.get("created_at")),
            extra=d.get("extra", {}),
        )


@dataclass
class RealWorldEval:
    """实机（真机）评估结果"""
    eval_id: str
    model_id: str
    robot_id: str = ""
    task_name: str = ""
    num_trials: int = 0
    success_count: int = 0
    success_rate: float = 0.0
    environment: str = ""                  # 场景/环境描述
    notes: str = ""
    created_at: Optional[datetime] = None
    extra: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "eval_id": self.eval_id,
            "model_id": self.model_id,
            "robot_id": self.robot_id,
            "task_name": self.task_name,
            "num_trials": self.num_trials,
            "success_count": self.success_count,
            "success_rate": self.success_rate,
            "environment": self.environment,
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "extra": self.extra,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "RealWorldEval":
        return cls(
            eval_id=d["eval_id"],
            model_id=d["model_id"],
            robot_id=d.get("robot_id", ""),
            task_name=d.get("task_name", ""),
            num_trials=d.get("num_trials", 0),
            success_count=d.get("success_count", 0),
            success_rate=d.get("success_rate", 0.0),
            environment=d.get("environment", ""),
            notes=d.get("notes", ""),
            created_at=_parse_dt(d.get("created_at")),
            extra=d.get("extra", {}),
        )


@dataclass
class FailureCase:
    """失败 Case（实机失败 / 低成功率任务 / 新增场景数据）"""
    case_id: str
    task_name: str
    model_id: str = ""
    episode_id: str = ""                   # 对应数据 Episode（如适用）
    robot_id: str = ""
    failure_type: str = "unknown"          # grasp_loss / collision / timeout / ...
    description: str = ""
    video_ref: str = ""                    # 视频/数据引用
    created_at: Optional[datetime] = None
    priority: int = 1                      # 1(低)~5(高)
    status: FailureStatus = FailureStatus.OPEN
    retrain_version: str = ""              # 加入的训练集版本
    extra: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "case_id": self.case_id,
            "task_name": self.task_name,
            "model_id": self.model_id,
            "episode_id": self.episode_id,
            "robot_id": self.robot_id,
            "failure_type": self.failure_type,
            "description": self.description,
            "video_ref": self.video_ref,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "priority": self.priority,
            "status": self.status.value,
            "retrain_version": self.retrain_version,
            "extra": self.extra,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "FailureCase":
        return cls(
            case_id=d["case_id"],
            task_name=d["task_name"],
            model_id=d.get("model_id", ""),
            episode_id=d.get("episode_id", ""),
            robot_id=d.get("robot_id", ""),
            failure_type=d.get("failure_type", "unknown"),
            description=d.get("description", ""),
            video_ref=d.get("video_ref", ""),
            created_at=_parse_dt(d.get("created_at")),
            priority=d.get("priority", 1),
            status=FailureStatus(d.get("status", "open")),
            retrain_version=d.get("retrain_version", ""),
            extra=d.get("extra", {}),
        )


def _parse_dt(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None
