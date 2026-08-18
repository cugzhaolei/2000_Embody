"""
数据采集模块
===========
提供多模态数据采集器和多设备时间同步管理。

支持的采集器:
- RGBCameraCollector: RGB 相机数据采集
- DepthCameraCollector: 深度相机数据采集
- TactileCollector: 触觉传感器数据采集
- RobotStateCollector: 机器人状态数据采集
- IMUCollector: IMU 数据采集
- MultiDeviceSyncManager: 多设备时间同步管理
"""

from .base import BaseCollector, CollectorState, CollectorStats
from .rgb_camera import RGBCameraCollector
from .depth_camera import DepthCameraCollector
from .tactile_sensor import TactileCollector
from .robot_state import RobotStateCollector
from .sync_manager import MultiDeviceSyncManager

__all__ = [
    "BaseCollector",
    "CollectorState",
    "CollectorStats",
    "RGBCameraCollector",
    "DepthCameraCollector",
    "TactileCollector",
    "RobotStateCollector",
    "MultiDeviceSyncManager",
]
