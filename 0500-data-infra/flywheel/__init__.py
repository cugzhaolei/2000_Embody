"""
具身数据飞轮
============
实现实机失败数据、低成功率任务及新增场景数据的自动回流、筛选和再训练：

- failure_ingest: 失败数据接入（评估日志 / Episode 标注 / 手动上报）
- curation: 回流数据筛选、去重、任务平衡
- loop: 飞轮编排（失败 -> 筛选 -> 回流训练集 -> 重训练 -> 验证关闭）
"""

from .failure_ingest import FailureIngester
from .curation import CuratedPool, FlywheelCurator
from .loop import DataFlywheel, FlywheelReport

__all__ = [
    "FailureIngester",
    "CuratedPool",
    "FlywheelCurator",
    "DataFlywheel",
    "FlywheelReport",
]
