"""
飞轮数据筛选与整理
==================
对回流失败数据做质量控制、去重和任务平衡，产出可加入训练集的
精选数据池 (CuratedPool)，并生成训练集 Episode 列表。
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..tracking.models import FailureCase, FailureStatus
from ..tracking.registry import TrainingRegistry


@dataclass
class CuratedPool:
    """一轮飞轮筛选出的训练数据池"""
    pool_id: str
    created_at: Optional[datetime] = None
    cases: List[FailureCase] = field(default_factory=list)
    stats: Dict[str, Any] = field(default_factory=dict)

    @property
    def task_counts(self) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for c in self.cases:
            counts[c.task_name] = counts.get(c.task_name, 0) + 1
        return counts

    @property
    def total_cases(self) -> int:
        return len(self.cases)

    def to_dict(self) -> dict:
        return {
            "pool_id": self.pool_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "cases": [c.to_dict() for c in self.cases],
            "stats": self.stats,
        }


class FlywheelCurator:
    """飞轮数据筛选器

    筛选维度:
    - 去重: 按 (task_name, episode_id) 或视频引用去重
    - 优先级: 过滤低优先级 Case
    - 任务平衡: 每任务最多 max_per_task 条，避免类别失衡
    - 数据可用性: 必须有 episode_id 或 video_ref（可回溯到数据）
    """

    def __init__(
        self,
        registry: TrainingRegistry,
        max_per_task: int = 20,
        min_priority: int = 2,
        require_data_ref: bool = True,
    ):
        self.registry = registry
        self.max_per_task = max_per_task
        self.min_priority = min_priority
        self.require_data_ref = require_data_ref

    def curate(
        self,
        cases: Optional[List[FailureCase]] = None,
        tasks: Optional[List[str]] = None,
        max_per_task: Optional[int] = None,
    ) -> CuratedPool:
        """筛选出一轮可回流的训练数据池"""
        if cases is None:
            cases = self.registry.list_failures(status=FailureStatus.OPEN)
        if tasks:
            cases = [c for c in cases if c.task_name in tasks]

        max_per = max_per_task or self.max_per_task

        # 1. 优先级过滤
        cases = [c for c in cases if c.priority >= self.min_priority]

        # 2. 数据可用性过滤
        if self.require_data_ref:
            cases = [c for c in cases if c.episode_id or c.video_ref]

        # 3. 去重（保留优先级高的）
        dedup: Dict[str, FailureCase] = {}
        for c in sorted(cases, key=lambda x: x.priority, reverse=True):
            key = c.episode_id or c.video_ref or c.case_id
            dedup.setdefault(f"{c.task_name}|{key}", c)

        # 4. 任务平衡
        balanced: Dict[str, List[FailureCase]] = {}
        for c in dedup.values():
            balanced.setdefault(c.task_name, []).append(c)
        selected: List[FailureCase] = []
        for task, task_cases in balanced.items():
            task_cases = sorted(task_cases, key=lambda x: x.priority, reverse=True)
            selected.extend(task_cases[:max_per])

        pool = CuratedPool(
            pool_id=f"pool_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            created_at=datetime.now(),
            cases=selected,
        )
        pool.stats = {
            "input_count": len(cases),
            "after_dedup": len(dedup),
            "selected": len(selected),
            "task_counts": pool.task_counts,
            "discarded_reasons": self._summarize_discards(cases, selected),
        }
        return pool

    def to_episodes(self, pool: CuratedPool, episode_lookup: Dict[str, Any]) -> List[Any]:
        """将精选 Case 映射为 EpisodeMetadata 列表（用于创建新数据集版本）

        Args:
            pool: 精选数据池
            episode_lookup: episode_id -> EpisodeMetadata（失败数据的原始 Episode）
        """
        episodes = []
        for case in pool.cases:
            ep = episode_lookup.get(case.episode_id)
            if ep is not None:
                # 标注为失败样本（供困难样本挖掘）
                if hasattr(ep, "success"):
                    ep.success = False
                if hasattr(ep, "extra"):
                    ep.extra["failure_type"] = case.failure_type
                    ep.extra["failure_priority"] = case.priority
                episodes.append(ep)
        return episodes

    def _summarize_discards(
        self, all_cases: List[FailureCase], selected: List[FailureCase]
    ) -> Dict[str, int]:
        selected_ids = {c.case_id for c in selected}
        discard_reasons = {"low_priority": 0, "no_data_ref": 0, "duplicate": 0, "task_overflow": 0}
        for c in all_cases:
            if c.case_id in selected_ids:
                continue
            if c.priority < self.min_priority:
                discard_reasons["low_priority"] += 1
            elif not (c.episode_id or c.video_ref):
                discard_reasons["no_data_ref"] += 1
            else:
                discard_reasons["duplicate"] += 1  # 近似统计（含任务溢出）
        return discard_reasons
