"""
多模态数据 Schema
================
定义所有具身数据模态的类型、结构和校验规则。
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, Union
import numpy as np


class ModalityType(str, Enum):
    """支持的多模态数据类型"""
    RGB = "rgb"                    # RGB 图像/视频
    DEPTH = "depth"                # 深度图
    TACTILE = "tactile"            # 触觉传感器数据
    ROBOT_STATE = "robot_state"    # 机器人整体状态
    EEF_POSE = "eef_pose"          # 末端执行器位姿 (6DoF: x,y,z,rx,ry,rz)
    JOINT_STATE = "joint_state"    # 关节状态 (pos, vel, effort)
    ACTION = "action"              # 机器人动作
    IMU = "imu"                    # IMU 惯性数据 (acc + gyro)
    HAND_STATE = "hand_state"      # 灵巧手状态
    LANGUAGE = "language"          # 语言指令
    GRIPPER = "gripper"            # 夹爪状态
    FORCE_TORQUE = "force_torque"  # 力/力矩传感器


@dataclass
class SensorConfig:
    """单个传感器的配置"""
    name: str
    modality: ModalityType
    sensor_id: str                      # 唯一标识符
    topic: str = ""                     # ROS topic / 数据来源
    frame_id: str = ""                  # TF 坐标系
    frequency_hz: float = 30.0          # 采集频率
    resolution: Optional[Tuple[int, int]] = None  # (W, H) for cameras
    dtype: str = "float32"              # 数据类型
    description: str = ""

    # 时间同步相关
    hardware_sync: bool = False         # 是否硬件同步
    sync_delay_ms: float = 0.0          # 同步延迟补偿

    def validate(self) -> bool:
        """校验传感器配置"""
        if not self.sensor_id:
            raise ValueError(f"Sensor '{self.name}' must have a sensor_id")
        if self.frequency_hz <= 0:
            raise ValueError(f"Sensor '{self.name}' frequency must be > 0")
        return True


@dataclass
class TimeSyncConfig:
    """多设备时间同步配置"""
    method: str = "hardware"            # "hardware" | "software" | "ntp" | "ptp"
    tolerance_ms: float = 5.0           # 允许的最大时间偏差
    master_clock: str = ""              # 主时钟设备 sensor_id
    drift_correction: bool = True       # 是否进行时钟漂移校正

    def get_sync_threshold_sec(self) -> float:
        return self.tolerance_ms / 1000.0


@dataclass
class SensorSchema:
    """完整的传感器 Schema，包含所有传感器配置和同步参数"""
    name: str
    sensors: List[SensorConfig] = field(default_factory=list)
    time_sync: TimeSyncConfig = field(default_factory=TimeSyncConfig)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_sensor(self, sensor: SensorConfig) -> None:
        """添加传感器"""
        sensor.validate()
        self.sensors.append(sensor)

    def get_sensors_by_modality(self, modality: ModalityType) -> List[SensorConfig]:
        """按模态类型筛选传感器"""
        return [s for s in self.sensors if s.modality == modality]

    def get_sensor_by_id(self, sensor_id: str) -> Optional[SensorConfig]:
        """按 ID 查找传感器"""
        for s in self.sensors:
            if s.sensor_id == sensor_id:
                return s
        return None

    def get_modalities(self) -> List[ModalityType]:
        """获取所有包含的模态类型"""
        return list(set(s.modality for s in self.sensors))

    def to_dict(self) -> dict:
        """序列化为字典"""
        return {
            "name": self.name,
            "sensors": [
                {
                    "name": s.name,
                    "modality": s.modality.value,
                    "sensor_id": s.sensor_id,
                    "topic": s.topic,
                    "frame_id": s.frame_id,
                    "frequency_hz": s.frequency_hz,
                    "resolution": s.resolution,
                    "dtype": s.dtype,
                    "description": s.description,
                    "hardware_sync": s.hardware_sync,
                    "sync_delay_ms": s.sync_delay_ms,
                }
                for s in self.sensors
            ],
            "time_sync": {
                "method": self.time_sync.method,
                "tolerance_ms": self.time_sync.tolerance_ms,
                "master_clock": self.time_sync.master_clock,
                "drift_correction": self.time_sync.drift_correction,
            },
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "SensorSchema":
        """从字典反序列化"""
        sensors = [
            SensorConfig(
                name=s["name"],
                modality=ModalityType(s["modality"]),
                sensor_id=s["sensor_id"],
                topic=s.get("topic", ""),
                frame_id=s.get("frame_id", ""),
                frequency_hz=s.get("frequency_hz", 30.0),
                resolution=tuple(s["resolution"]) if s.get("resolution") else None,
                dtype=s.get("dtype", "float32"),
                description=s.get("description", ""),
                hardware_sync=s.get("hardware_sync", False),
                sync_delay_ms=s.get("sync_delay_ms", 0.0),
            )
            for s in d.get("sensors", [])
        ]
        time_sync_cfg = d.get("time_sync", {})
        time_sync = TimeSyncConfig(
            method=time_sync_cfg.get("method", "hardware"),
            tolerance_ms=time_sync_cfg.get("tolerance_ms", 5.0),
            master_clock=time_sync_cfg.get("master_clock", ""),
            drift_correction=time_sync_cfg.get("drift_correction", True),
        )
        return cls(
            name=d["name"],
            sensors=sensors,
            time_sync=time_sync,
            metadata=d.get("metadata", {}),
        )


# 模态注册表：每种模态对应的默认数据描述
MODALITY_REGISTRY: Dict[ModalityType, Dict[str, Any]] = {
    ModalityType.RGB: {
        "dtype": "uint8",
        "shape_desc": "(H, W, 3)",
        "value_range": (0, 255),
        "unit": "pixel",
    },
    ModalityType.DEPTH: {
        "dtype": "float32",
        "shape_desc": "(H, W)",
        "value_range": (0.0, 10.0),
        "unit": "meter",
    },
    ModalityType.TACTILE: {
        "dtype": "float32",
        "shape_desc": "(N_taxels,)",
        "value_range": (0.0, 1.0),
        "unit": "normalized",
    },
    ModalityType.ROBOT_STATE: {
        "dtype": "float32",
        "shape_desc": "(D_state,)",
        "value_range": None,
        "unit": "various",
    },
    ModalityType.EEF_POSE: {
        "dtype": "float64",
        "shape_desc": "(6,)",   # x, y, z, rx, ry, rz
        "value_range": None,
        "unit": "m/rad",
    },
    ModalityType.JOINT_STATE: {
        "dtype": "float64",
        "shape_desc": "(N_joints * 3,)",  # pos, vel, effort
        "value_range": None,
        "unit": "rad/rad_s/N_m",
    },
    ModalityType.ACTION: {
        "dtype": "float64",
        "shape_desc": "(D_action,)",
        "value_range": None,
        "unit": "varies",
    },
    ModalityType.IMU: {
        "dtype": "float64",
        "shape_desc": "(6,)",  # ax,ay,az,gx,gy,gz
        "value_range": None,
        "unit": "m/s^2/rad/s",
    },
    ModalityType.HAND_STATE: {
        "dtype": "float32",
        "shape_desc": "(D_hand,)",
        "value_range": None,
        "unit": "varies",
    },
    ModalityType.LANGUAGE: {
        "dtype": "string",
        "shape_desc": "(1,)",
        "value_range": None,
        "unit": "text",
    },
    ModalityType.GRIPPER: {
        "dtype": "float32",
        "shape_desc": "(2,)",  # position, effort
        "value_range": (0.0, 1.0),
        "unit": "normalized",
    },
    ModalityType.FORCE_TORQUE: {
        "dtype": "float64",
        "shape_desc": "(6,)",  # fx,fy,fz,tx,ty,tz
        "value_range": None,
        "unit": "N/N_m",
    },
}


def create_schema(
    name: str,
    sensor_configs: List[Dict[str, Any]],
    sync_method: str = "hardware",
    sync_tolerance_ms: float = 5.0,
    **kwargs,
) -> SensorSchema:
    """
    工厂函数：快速创建 SensorSchema

    Args:
        name: Schema 名称
        sensor_configs: 传感器配置列表，每个 dict 对应一个 SensorConfig
        sync_method: 时间同步方法
        sync_tolerance_ms: 同步容差

    Returns:
        SensorSchema 实例
    """
    time_sync = TimeSyncConfig(
        method=sync_method,
        tolerance_ms=sync_tolerance_ms,
        master_clock=kwargs.get("master_clock", ""),
        drift_correction=kwargs.get("drift_correction", True),
    )

    schema = SensorSchema(name=name, time_sync=time_sync, metadata=kwargs.get("metadata", {}))

    for cfg in sensor_configs:
        sensor = SensorConfig(
            name=cfg["name"],
            modality=ModalityType(cfg["modality"]),
            sensor_id=cfg["sensor_id"],
            topic=cfg.get("topic", ""),
            frame_id=cfg.get("frame_id", ""),
            frequency_hz=cfg.get("frequency_hz", 30.0),
            resolution=tuple(cfg["resolution"]) if cfg.get("resolution") else None,
            dtype=cfg.get("dtype", MODALITY_REGISTRY[ModalityType(cfg["modality"])]["dtype"]),
            description=cfg.get("description", ""),
            hardware_sync=cfg.get("hardware_sync", False),
            sync_delay_ms=cfg.get("sync_delay_ms", 0.0),
        )
        schema.add_sensor(sensor)

    return schema


def validate_modality(modality: str) -> ModalityType:
    """验证并返回 ModalityType"""
    try:
        return ModalityType(modality)
    except ValueError:
        valid = [m.value for m in ModalityType]
        raise ValueError(f"Unknown modality '{modality}'. Valid: {valid}")
