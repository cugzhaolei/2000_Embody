"""
训练与评估平台关联管理
======================
实现 Dataset、训练任务、模型版本、Benchmark、实机结果及失败 Case
之间的关联管理与全链路血缘追溯。
"""

from .models import (
    JobStatus,
    FailureStatus,
    TrainingJob,
    ModelVersion,
    BenchmarkResult,
    RealWorldEval,
    FailureCase,
)
from .registry import TrainingRegistry

__all__ = [
    "JobStatus",
    "FailureStatus",
    "TrainingJob",
    "ModelVersion",
    "BenchmarkResult",
    "RealWorldEval",
    "FailureCase",
    "TrainingRegistry",
]
