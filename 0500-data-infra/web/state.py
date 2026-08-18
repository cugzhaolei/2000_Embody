"""
应用共享状态
============
持有 registry / version_manager / flywheel 等全局实例，
并提供演示数据种子与 Episode 汇总查询。
"""

import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..tracking.registry import TrainingRegistry
from ..versioning.dataset_version import DatasetVersionManager
from ..flywheel.failure_ingest import FailureIngester
from ..flywheel.curation import FlywheelCurator
from ..flywheel.loop import DataFlywheel

# 说明: 本文件通过包别名 embodied_infra.web.state 加载，上面的相对导入
# 解析到 embodied_infra.tracking / .versioning / .flywheel。


class AppState:
    """Web 平台共享状态"""

    def __init__(self, base_dir: Optional[str] = None):
        base = Path(base_dir) if base_dir else Path(__file__).resolve().parent
        self.base_dir = base

        self.registry = TrainingRegistry(str(base / "data" / "registry"))
        self.version_manager = DatasetVersionManager(str(base / "data" / "versions"))
        self.ingester = FailureIngester(self.registry)
        self.curator = FlywheelCurator(self.registry, max_per_task=20)
        self.flywheel = DataFlywheel(
            self.registry, self.version_manager, self.ingester, self.curator
        )
        # 保证重启后 job/model 编号继续递增，避免与已持久化的实体冲突
        self.flywheel._iteration = max(0, len(self.registry.list_jobs()))

    # ------------------------------------------------------------------
    def load_all_episodes(self) -> Dict[str, Any]:
        """从所有数据集版本加载 Episode，返回 episode_id -> EpisodeMetadata"""
        from ..schemas.dataset import EpisodeMetadata

        lookup: Dict[str, Any] = {}
        for version in self.version_manager.list_versions():
            ep_file = self.version_manager.store_dir / f"v{version.version}" / "episodes.json"
            if not ep_file.exists():
                continue
            import json
            with open(ep_file, "r", encoding="utf-8") as f:
                for item in json.load(f):
                    ep = EpisodeMetadata.from_dict(item)
                    lookup[ep.episode_id] = ep
        return lookup

    # ------------------------------------------------------------------
    def latest_model_id(self) -> str:
        models = self.registry.list_models()
        return models[0].model_id if models else ""

    def snapshot(self) -> Dict[str, Any]:
        """聚合当前全部状态（供总览页使用）"""
        jobs = self.registry.list_jobs()
        models = self.registry.list_models()
        evals = self.registry.list_evals()
        failures = self.registry.list_failures()

        status_counts: Dict[str, int] = {}
        for c in failures:
            status_counts[c.status.value] = status_counts.get(c.status.value, 0) + 1

        task_success: Dict[str, Dict[str, float]] = {}
        for ev in evals:
            entry = task_success.setdefault(ev.task_name, {"trials": 0, "success": 0, "evals": 0})
            entry["trials"] += ev.num_trials
            entry["success"] += ev.success_count
            entry["evals"] += 1
        for t, e in task_success.items():
            e["success_rate"] = round(e["success"] / e["trials"], 3) if e["trials"] else 0.0

        return {
            "stats": {
                "versions": len(self.version_manager.list_versions()),
                "models": len(models),
                "jobs": len(jobs),
                "benchmarks": len(self.registry.list_benchmarks()),
                "evals": len(evals),
                "failures_open": status_counts.get("open", 0),
                "failures_total": len(failures),
                "flywheel_runs": len(self.flywheel.history()),
            },
            "task_success": task_success,
            "failure_status": status_counts,
            "versions": self.version_manager.get_version_lineage(),
            "recent_jobs": [j.to_dict() for j in jobs[:10]],
            "models": [m.to_dict() for m in models[:10]],
            "flywheel_history": [r.to_dict() for r in self.flywheel.history()],
        }
