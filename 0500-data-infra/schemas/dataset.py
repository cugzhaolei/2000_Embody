"""
Dataset Schema 定义
==================
定义 Episode 和 Dataset 的元数据结构，支持版本管理和全链路追溯。
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
from enum import Enum


class EpisodeStatus(str, Enum):
    """Episode 状态"""
    RECORDED = "recorded"        # 已录制
    PROCESSING = "processing"    # 处理中
    VALIDATED = "validated"      # 已验证
    FAILED = "failed"            # 处理失败
    ARCHIVED = "archived"        # 已归档
    DISCARDED = "discarded"      # 已丢弃


@dataclass
class EpisodeMetadata:
    """单个 Episode 的元数据"""
    episode_id: str                        # 唯一标识
    task_name: str                         # 任务名称
    robot_id: str = ""                     # 机器人 ID
    operator_id: str = ""                  # 操作者 ID
    scene_id: str = ""                     # 场景 ID

    # 时间信息
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    duration_sec: float = 0.0

    # 数据信息
    num_steps: int = 0
    modalities: List[str] = field(default_factory=list)
    frame_counts: Dict[str, int] = field(default_factory=dict)  # modality -> frame count

    # 状态
    status: EpisodeStatus = EpisodeStatus.RECORDED
    success: Optional[bool] = None         # 操作是否成功

    # 标定和环境
    calibration_version: str = ""
    camera_positions: Dict[str, Any] = field(default_factory=dict)
    environment_tags: List[str] = field(default_factory=list)

    # 来源
    source_device: str = ""                # 采集设备标识
    recording_config: Dict[str, Any] = field(default_factory=dict)

    # 自定义字段
    extra: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "episode_id": self.episode_id,
            "task_name": self.task_name,
            "robot_id": self.robot_id,
            "operator_id": self.operator_id,
            "scene_id": self.scene_id,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_sec": self.duration_sec,
            "num_steps": self.num_steps,
            "modalities": self.modalities,
            "frame_counts": self.frame_counts,
            "status": self.status.value,
            "success": self.success,
            "calibration_version": self.calibration_version,
            "camera_positions": self.camera_positions,
            "environment_tags": self.environment_tags,
            "source_device": self.source_device,
            "recording_config": self.recording_config,
            "extra": self.extra,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "EpisodeMetadata":
        start_time = None
        end_time = None
        if d.get("start_time"):
            start_time = datetime.fromisoformat(d["start_time"])
        if d.get("end_time"):
            end_time = datetime.fromisoformat(d["end_time"])
        return cls(
            episode_id=d["episode_id"],
            task_name=d["task_name"],
            robot_id=d.get("robot_id", ""),
            operator_id=d.get("operator_id", ""),
            scene_id=d.get("scene_id", ""),
            start_time=start_time,
            end_time=end_time,
            duration_sec=d.get("duration_sec", 0.0),
            num_steps=d.get("num_steps", 0),
            modalities=d.get("modalities", []),
            frame_counts=d.get("frame_counts", {}),
            status=EpisodeStatus(d.get("status", "recorded")),
            success=d.get("success"),
            calibration_version=d.get("calibration_version", ""),
            camera_positions=d.get("camera_positions", {}),
            environment_tags=d.get("environment_tags", []),
            source_device=d.get("source_device", ""),
            recording_config=d.get("recording_config", {}),
            extra=d.get("extra", {}),
        )


@dataclass
class DatasetMetadata:
    """Dataset 级别元数据"""
    name: str
    description: str = ""
    version: str = "0.1.0"
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    # 数据统计
    total_episodes: int = 0
    total_steps: int = 0
    modalities: List[str] = field(default_factory=list)

    # 来源追溯
    schema_name: str = ""                  # 使用的 SensorSchema
    robot_type: str = ""
    task_categories: List[str] = field(default_factory=list)
    scene_categories: List[str] = field(default_factory=list)

    # 质量信息
    quality_score: float = 0.0             # 0~1 综合质量分
    validated_episodes: int = 0
    failed_episodes: int = 0

    # 自定义
    tags: List[str] = field(default_factory=list)
    extra: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "total_episodes": self.total_episodes,
            "total_steps": self.total_steps,
            "modalities": self.modalities,
            "schema_name": self.schema_name,
            "robot_type": self.robot_type,
            "task_categories": self.task_categories,
            "scene_categories": self.scene_categories,
            "quality_score": self.quality_score,
            "validated_episodes": self.validated_episodes,
            "failed_episodes": self.failed_episodes,
            "tags": self.tags,
            "extra": self.extra,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "DatasetMetadata":
        created_at = datetime.fromisoformat(d["created_at"]) if d.get("created_at") else None
        updated_at = datetime.fromisoformat(d["updated_at"]) if d.get("updated_at") else None
        return cls(
            name=d["name"],
            description=d.get("description", ""),
            version=d.get("version", "0.1.0"),
            created_at=created_at,
            updated_at=updated_at,
            total_episodes=d.get("total_episodes", 0),
            total_steps=d.get("total_steps", 0),
            modalities=d.get("modalities", []),
            schema_name=d.get("schema_name", ""),
            robot_type=d.get("robot_type", ""),
            task_categories=d.get("task_categories", []),
            scene_categories=d.get("scene_categories", []),
            quality_score=d.get("quality_score", 0.0),
            validated_episodes=d.get("validated_episodes", 0),
            failed_episodes=d.get("failed_episodes", 0),
            tags=d.get("tags", []),
            extra=d.get("extra", {}),
        )


@dataclass
class DatasetVersion:
    """Dataset 版本信息，支持版本间对比和回溯"""
    version: str
    created_at: Optional[datetime] = None
    commit_hash: str = ""
    description: str = ""
    changelog: str = ""

    # 快照统计
    num_episodes: int = 0
    num_steps: int = 0
    quality_score: float = 0.0

    # 关联的训练实验
    training_runs: List[str] = field(default_factory=list)

    # 数据子集
    included_episodes: List[str] = field(default_factory=list)
    excluded_episodes: List[str] = field(default_factory=list)

    extra: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "version": self.version,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "commit_hash": self.commit_hash,
            "description": self.description,
            "changelog": self.changelog,
            "num_episodes": self.num_episodes,
            "num_steps": self.num_steps,
            "quality_score": self.quality_score,
            "training_runs": self.training_runs,
            "included_episodes": self.included_episodes,
            "excluded_episodes": self.excluded_episodes,
            "extra": self.extra,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "DatasetVersion":
        created_at = datetime.fromisoformat(d["created_at"]) if d.get("created_at") else None
        return cls(
            version=d["version"],
            created_at=created_at,
            commit_hash=d.get("commit_hash", ""),
            description=d.get("description", ""),
            changelog=d.get("changelog", ""),
            num_episodes=d.get("num_episodes", 0),
            num_steps=d.get("num_steps", 0),
            quality_score=d.get("quality_score", 0.0),
            training_runs=d.get("training_runs", []),
            included_episodes=d.get("included_episodes", []),
            excluded_episodes=d.get("excluded_episodes", []),
            extra=d.get("extra", {}),
        )


@dataclass
class DatasetSchema:
    """完整的 Dataset Schema，整合 DatasetMetadata + EpisodeSchema"""
    metadata: DatasetMetadata
    episodes: List[EpisodeMetadata] = field(default_factory=list)
    versions: List[DatasetVersion] = field(default_factory=list)

    def add_episode(self, episode: EpisodeMetadata) -> None:
        self.episodes.append(episode)
        self._update_stats()

    def remove_episode(self, episode_id: str) -> bool:
        for i, ep in enumerate(self.episodes):
            if ep.episode_id == episode_id:
                self.episodes.pop(i)
                self._update_stats()
                return True
        return False

    def get_episode(self, episode_id: str) -> Optional[EpisodeMetadata]:
        for ep in self.episodes:
            if ep.episode_id == episode_id:
                return ep
        return None

    def get_episodes_by_status(self, status: EpisodeStatus) -> List[EpisodeMetadata]:
        return [ep for ep in self.episodes if ep.status == status]

    def get_episodes_by_task(self, task_name: str) -> List[EpisodeMetadata]:
        return [ep for ep in self.episodes if ep.task_name == task_name]

    def get_successful_episodes(self) -> List[EpisodeMetadata]:
        return [ep for ep in self.episodes if ep.success is True]

    def _update_stats(self) -> None:
        self.metadata.total_episodes = len(self.episodes)
        self.metadata.total_steps = sum(ep.num_steps for ep in self.episodes)
        all_modalities = set()
        for ep in self.episodes:
            all_modalities.update(ep.modalities)
        self.metadata.modalities = sorted(list(all_modalities))
        self.metadata.validated_episodes = len(
            [ep for ep in self.episodes if ep.status == EpisodeStatus.VALIDATED]
        )
        self.metadata.failed_episodes = len(
            [ep for ep in self.episodes if ep.status == EpisodeStatus.FAILED]
        )

    def to_dict(self) -> dict:
        return {
            "metadata": self.metadata.to_dict(),
            "episodes": [ep.to_dict() for ep in self.episodes],
            "versions": [v.to_dict() for v in self.versions],
        }

    @classmethod
    def from_dict(cls, d: dict) -> "DatasetSchema":
        metadata = DatasetMetadata.from_dict(d["metadata"])
        episodes = [EpisodeMetadata.from_dict(ep) for ep in d.get("episodes", [])]
        versions = [DatasetVersion.from_dict(v) for v in d.get("versions", [])]
        return cls(metadata=metadata, episodes=episodes, versions=versions)
