"""
Dataset 版本管理器
=================
实现 Dataset 的版本控制、快照管理和实验关联。
"""

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from ..schemas.dataset import DatasetMetadata, DatasetVersion, EpisodeMetadata, EpisodeStatus


class DatasetVersionManager:
    """Dataset 版本管理器

    功能:
    - 版本创建和切换
    - 数据快照 (包含 Episode 列表)
    - 训练实验关联
    - 版本间 Diff 对比
    - 前向/后向兼容性管理
    """

    def __init__(self, store_dir: str):
        self.store_dir = Path(store_dir)
        self.store_dir.mkdir(parents=True, exist_ok=True)
        self._versions_file = self.store_dir / "versions.json"
        self._versions: List[DatasetVersion] = []
        self._current_version: Optional[str] = None
        self._load_versions()

    def _load_versions(self) -> None:
        if self._versions_file.exists():
            with open(self._versions_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                self._versions = [DatasetVersion.from_dict(v) for v in data.get("versions", [])]
                self._current_version = data.get("current_version")

    def _save_versions(self) -> None:
        data = {
            "versions": [v.to_dict() for v in self._versions],
            "current_version": self._current_version,
        }
        with open(self._versions_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)

    def create_version(
        self,
        version: str,
        episodes: List[EpisodeMetadata],
        description: str = "",
        changelog: str = "",
        commit_hash: str = "",
    ) -> DatasetVersion:
        """创建新版本"""
        # 检查版本号是否已存在
        for v in self._versions:
            if v.version == version:
                raise ValueError(f"Version '{version}' already exists")

        included_ids = [ep.episode_id for ep in episodes]
        total_steps = sum(ep.num_steps for ep in episodes)

        new_version = DatasetVersion(
            version=version,
            created_at=datetime.now(),
            commit_hash=commit_hash,
            description=description,
            changelog=changelog,
            num_episodes=len(episodes),
            num_steps=total_steps,
            included_episodes=included_ids,
        )

        self._versions.append(new_version)
        self._current_version = version
        self._save_versions()

        # 创建版本快照目录
        version_dir = self.store_dir / f"v{version}"
        version_dir.mkdir(exist_ok=True)

        # 保存 Episode 列表
        ep_data = [ep.to_dict() for ep in episodes]
        with open(version_dir / "episodes.json", "w", encoding="utf-8") as f:
            json.dump(ep_data, f, indent=2, ensure_ascii=False, default=str)

        print(f"Created version {version}: {len(episodes)} episodes, {total_steps} steps")
        return new_version

    def get_current_version(self) -> Optional[DatasetVersion]:
        """获取当前版本"""
        for v in self._versions:
            if v.version == self._current_version:
                return v
        return None

    def get_version(self, version: str) -> Optional[DatasetVersion]:
        """获取指定版本"""
        for v in self._versions:
            if v.version == version:
                return v
        return None

    def list_versions(self) -> List[DatasetVersion]:
        """列出所有版本"""
        return list(self._versions)

    def switch_version(self, version: str) -> bool:
        """切换到指定版本"""
        for v in self._versions:
            if v.version == version:
                self._current_version = version
                self._save_versions()
                return True
        return False

    def delete_version(self, version: str) -> bool:
        """删除版本"""
        for i, v in enumerate(self._versions):
            if v.version == version:
                self._versions.pop(i)
                if self._current_version == version:
                    self._current_version = self._versions[-1].version if self._versions else None
                self._save_versions()

                # 删除版本目录
                version_dir = self.store_dir / f"v{version}"
                if version_dir.exists():
                    import shutil
                    shutil.rmtree(version_dir)
                return True
        return False

    def compare_versions(self, v1: str, v2: str) -> Dict[str, Any]:
        """对比两个版本"""
        ver1 = self.get_version(v1)
        ver2 = self.get_version(v2)

        if ver1 is None or ver2 is None:
            return {"error": "Version not found"}

        eps1 = set(ver1.included_episodes)
        eps2 = set(ver2.included_episodes)

        return {
            "version_1": v1,
            "version_2": v2,
            "episodes_added": sorted(list(eps2 - eps1)),
            "episodes_removed": sorted(list(eps1 - eps2)),
            "episodes_common": sorted(list(eps1 & eps2)),
            "episode_count_diff": ver2.num_episodes - ver1.num_episodes,
            "step_count_diff": ver2.num_steps - ver1.num_steps,
        }

    def link_training_run(self, version: str, run_id: str) -> bool:
        """关联训练实验"""
        for v in self._versions:
            if v.version == version:
                if run_id not in v.training_runs:
                    v.training_runs.append(run_id)
                    self._save_versions()
                return True
        return False

    def get_version_lineage(self) -> List[Dict[str, Any]]:
        """获取版本演进时间线"""
        return [
            {
                "version": v.version,
                "created_at": v.created_at.isoformat() if v.created_at else None,
                "num_episodes": v.num_episodes,
                "description": v.description,
                "training_runs": v.training_runs,
            }
            for v in sorted(self._versions, key=lambda x: x.created_at or datetime.min)
        ]

    def compute_data_hash(self, episodes: List[EpisodeMetadata]) -> str:
        """计算数据指纹"""
        content = json.dumps(
            [ep.to_dict() for ep in episodes],
            sort_keys=True,
            default=str,
        )
        return hashlib.sha256(content.encode()).hexdigest()[:16]
