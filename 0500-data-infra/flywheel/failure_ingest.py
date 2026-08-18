"""
失败数据接入
============
将实机失败数据回流到系统，支持多种来源：

- 评估日志（JSON/CSV）批量接入
- Episode 元数据自动标注失败
- 手动上报单个失败 Case
"""

import csv
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..tracking.models import FailureCase, FailureStatus
from ..tracking.registry import TrainingRegistry


class FailureIngester:
    """失败数据接入器"""

    def __init__(self, registry: TrainingRegistry):
        self.registry = registry

    # ------------------------------------------------------------------
    def ingest_from_eval_log(
        self,
        path: str,
        model_id: str,
        robot_id: str = "",
        source_format: str = "json",   # json | csv
        failure_field: str = "success",  # 失败标记字段（值为 false 视为失败）
    ) -> List[FailureCase]:
        """从评估日志接入失败 Case

        日志每条记录应包含: task_name, episode_id(可选), success(bool),
        failure_type(可选), description(可选), priority(可选)
        """
        path = Path(path)
        if source_format == "json":
            with open(path, "r", encoding="utf-8") as f:
                records = json.load(f)
                if isinstance(records, dict):
                    records = records.get("records", [])
        elif source_format == "csv":
            with open(path, "r", encoding="utf-8", newline="") as f:
                records = list(csv.DictReader(f))
        else:
            raise ValueError(f"Unsupported format: {source_format}")

        cases: List[FailureCase] = []
        for rec in records:
            success = rec.get(failure_field)
            if isinstance(success, str):
                success = success.strip().lower() in ("true", "1", "yes", "success")
            if success is not False and success != "false":
                continue
            cases.append(self._from_record(rec, model_id, robot_id))
        return self._register_all(cases)

    def ingest_from_episodes(
        self,
        episodes: List[Any],
        model_id: str,
        robot_id: str = "",
        failed_only: bool = True,
    ) -> List[FailureCase]:
        """从 Episode 元数据接入失败（复用 schemas.EpisodeMetadata）"""
        cases: List[FailureCase] = []
        for ep in episodes:
            # 兼容 dict 与 EpisodeMetadata
            episode_id = getattr(ep, "episode_id", None) or (ep.get("episode_id") if isinstance(ep, dict) else None)
            task_name = getattr(ep, "task_name", "") or (ep.get("task_name", "") if isinstance(ep, dict) else "")
            success = getattr(ep, "success", None)
            if isinstance(ep, dict):
                success = ep.get("success")
            if failed_only and success is not False:
                continue
            cases.append(
                FailureCase(
                    case_id=f"case_{episode_id or task_name}",
                    task_name=task_name or "unknown",
                    model_id=model_id,
                    episode_id=episode_id or "",
                    robot_id=robot_id,
                    failure_type="task_failure",
                    description="episode marked as failed",
                    status=FailureStatus.OPEN,
                    priority=3,
                )
            )
        return self._register_all(cases)

    def ingest_manual(
        self,
        task_name: str,
        model_id: str,
        episode_id: str = "",
        robot_id: str = "",
        failure_type: str = "unknown",
        description: str = "",
        priority: int = 3,
        case_id: Optional[str] = None,
    ) -> FailureCase:
        """手动上报单个失败 Case"""
        case_id = case_id or f"case_manual_{len(self.registry.list_failures()) + 1:04d}"
        return self._register_all([
            FailureCase(
                case_id=case_id,
                task_name=task_name,
                model_id=model_id,
                episode_id=episode_id,
                robot_id=robot_id,
                failure_type=failure_type,
                description=description,
                priority=priority,
                status=FailureStatus.OPEN,
            )
        ])[0]

    # ------------------------------------------------------------------
    def _from_record(
        self, rec: Dict[str, Any], model_id: str, robot_id: str
    ) -> FailureCase:
        task_name = rec.get("task_name", "unknown")
        episode_id = rec.get("episode_id", "")
        case_id = rec.get("case_id") or f"case_{task_name}_{episode_id or len(self.registry.list_failures()):04d}"
        return FailureCase(
            case_id=case_id,
            task_name=task_name,
            model_id=model_id,
            episode_id=episode_id,
            robot_id=rec.get("robot_id", robot_id),
            failure_type=rec.get("failure_type", "unknown"),
            description=rec.get("description", ""),
            video_ref=rec.get("video_ref", ""),
            priority=int(rec.get("priority", 3)),
            status=FailureStatus(rec.get("status", "open")),
            extra={k: v for k, v in rec.items()
                   if k not in ("case_id", "task_name", "episode_id", "robot_id",
                                "failure_type", "description", "video_ref", "priority", "status")},
        )

    def _register_all(self, cases: List[FailureCase]) -> List[FailureCase]:
        registered: List[FailureCase] = []
        for case in cases:
            # 幂等: 已存在（同 case_id / 同 episode_id 同任务）则跳过
            existing = self.registry.get_failure(case.case_id)
            if existing is None and case.episode_id:
                dup = [
                    c for c in self.registry.list_failures(task_name=case.task_name)
                    if c.episode_id == case.episode_id and c.episode_id
                ]
                if dup:
                    continue
            if existing is None:
                registered.append(self.registry.register_failure(case))
        return registered
