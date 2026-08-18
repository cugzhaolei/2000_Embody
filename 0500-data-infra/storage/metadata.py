"""
元数据管理
=========
统一管理数据资产的 Metadata，支持数据血缘追溯和标签系统。
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set


class DataAsset:
    """数据资产描述"""

    def __init__(
        self,
        asset_id: str,
        name: str,
        asset_type: str = "dataset",  # "dataset" | "episode" | "model" | "experiment"
        description: str = "",
    ):
        self.asset_id = asset_id
        self.name = name
        self.asset_type = asset_type
        self.description = description
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
        self.tags: Set[str] = set()
        self.properties: Dict[str, Any] = {}
        self.lineage: Dict[str, List[str]] = {
            "parents": [],   # 来源资产
            "children": [],  # 衍生资产
        }

    def add_tag(self, tag: str) -> None:
        self.tags.add(tag)
        self.updated_at = datetime.now()

    def remove_tag(self, tag: str) -> None:
        self.tags.discard(tag)
        self.updated_at = datetime.now()

    def set_property(self, key: str, value: Any) -> None:
        self.properties[key] = value
        self.updated_at = datetime.now()

    def add_parent(self, parent_id: str) -> None:
        if parent_id not in self.lineage["parents"]:
            self.lineage["parents"].append(parent_id)

    def add_child(self, child_id: str) -> None:
        if child_id not in self.lineage["children"]:
            self.lineage["children"].append(child_id)

    def to_dict(self) -> dict:
        return {
            "asset_id": self.asset_id,
            "name": self.name,
            "asset_type": self.asset_type,
            "description": self.description,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "tags": sorted(list(self.tags)),
            "properties": self.properties,
            "lineage": self.lineage,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "DataAsset":
        asset = cls(
            asset_id=d["asset_id"],
            name=d["name"],
            asset_type=d.get("asset_type", "dataset"),
            description=d.get("description", ""),
        )
        asset.created_at = datetime.fromisoformat(d["created_at"])
        asset.updated_at = datetime.fromisoformat(d["updated_at"])
        asset.tags = set(d.get("tags", []))
        asset.properties = d.get("properties", {})
        asset.lineage = d.get("lineage", {"parents": [], "children": []})
        return asset


class MetadataManager:
    """元数据管理器

    功能:
    - 数据资产注册和查询
    - 标签系统 (按任务、场景、操作者、机器人等分类)
    - 数据血缘追溯 (从采集到训练的全链路)
    - Metadata 持久化
    """

    def __init__(self, store_dir: str):
        self.store_dir = Path(store_dir)
        self.store_dir.mkdir(parents=True, exist_ok=True)
        self._assets: Dict[str, DataAsset] = {}
        self._index_file = self.store_dir / "asset_index.json"
        self._load_index()

    def _load_index(self) -> None:
        if self._index_file.exists():
            with open(self._index_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                for d in data.get("assets", []):
                    asset = DataAsset.from_dict(d)
                    self._assets[asset.asset_id] = asset

    def _save_index(self) -> None:
        data = {
            "assets": [a.to_dict() for a in self._assets.values()],
            "updated_at": datetime.now().isoformat(),
        }
        with open(self._index_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)

    def register(self, asset: DataAsset) -> None:
        """注册数据资产"""
        self._assets[asset.asset_id] = asset
        self._save_index()

    def unregister(self, asset_id: str) -> bool:
        if asset_id in self._assets:
            del self._assets[asset_id]
            self._save_index()
            return True
        return False

    def get(self, asset_id: str) -> Optional[DataAsset]:
        return self._assets.get(asset_id)

    def update(self, asset_id: str, **kwargs) -> bool:
        asset = self._assets.get(asset_id)
        if asset is None:
            return False
        for k, v in kwargs.items():
            if hasattr(asset, k):
                setattr(asset, k, v)
        asset.updated_at = datetime.now()
        self._save_index()
        return True

    def search(
        self,
        asset_type: Optional[str] = None,
        tags: Optional[Set[str]] = None,
        name_contains: Optional[str] = None,
    ) -> List[DataAsset]:
        """搜索数据资产"""
        results = []
        for asset in self._assets.values():
            if asset_type and asset.asset_type != asset_type:
                continue
            if tags and not tags.issubset(asset.tags):
                continue
            if name_contains and name_contains.lower() not in asset.name.lower():
                continue
            results.append(asset)
        return results

    def get_all_tags(self) -> Set[str]:
        """获取所有标签"""
        all_tags = set()
        for asset in self._assets.values():
            all_tags.update(asset.tags)
        return all_tags

    def get_lineage(self, asset_id: str, depth: int = -1) -> Dict[str, Any]:
        """获取数据血缘关系"""
        asset = self._assets.get(asset_id)
        if asset is None:
            return {}

        lineage = {
            "asset": asset.to_dict(),
            "parents": [],
            "children": [],
        }

        for pid in asset.lineage["parents"]:
            parent = self._assets.get(pid)
            if parent:
                lineage["parents"].append(parent.to_dict())

        for cid in asset.lineage["children"]:
            child = self._assets.get(cid)
            if child:
                lineage["children"].append(child.to_dict())

        return lineage

    def create_derived_asset(
        self,
        parent_id: str,
        child_id: str,
        child_name: str,
        child_type: str = "dataset",
        description: str = "",
        tags: Optional[Set[str]] = None,
    ) -> DataAsset:
        """创建衍生资产（自动建立血缘关系）"""
        child = DataAsset(
            asset_id=child_id,
            name=child_name,
            asset_type=child_type,
            description=description,
        )
        if tags:
            child.tags = tags

        child.add_parent(parent_id)
        self.register(child)

        parent = self._assets.get(parent_id)
        if parent:
            parent.add_child(child_id)
            self._save_index()

        return child

    def export_report(self) -> Dict[str, Any]:
        """导出资产报告"""
        type_counts = {}
        for asset in self._assets.values():
            t = asset.asset_type
            type_counts[t] = type_counts.get(t, 0) + 1

        return {
            "total_assets": len(self._assets),
            "type_counts": type_counts,
            "all_tags": sorted(list(self.get_all_tags())),
            "assets": [a.to_dict() for a in self._assets.values()],
        }
