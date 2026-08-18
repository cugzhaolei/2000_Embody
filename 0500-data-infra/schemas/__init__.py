"""
数据 Schema 定义
===============
统一管理多模态数据的标准 Schema，包括数据模态类型、传感器配置、Episode 和 Dataset 结构。
"""

from .multimodal import (
    ModalityType,
    SensorConfig,
    SensorSchema,
    TimeSyncConfig,
    create_schema,
    validate_modality,
    MODALITY_REGISTRY,
)
from .dataset import (
    EpisodeMetadata,
    DatasetMetadata,
    DatasetSchema,
    DatasetVersion,
)

__all__ = [
    "ModalityType",
    "SensorConfig",
    "SensorSchema",
    "TimeSyncConfig",
    "create_schema",
    "validate_modality",
    "MODALITY_REGISTRY",
    "EpisodeMetadata",
    "DatasetMetadata",
    "DatasetSchema",
    "DatasetVersion",
]
