"""
多设备时间同步管理器
===================
解决多相机、多触觉传感器、机器人等异构设备之间的时间对齐和丢帧检测。
"""

import time
import threading
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np

from .base import BaseCollector, CollectorState


@dataclass
class SyncFrame:
    """同步后的数据帧"""
    timestamp: float                         # 统一时间戳
    sensor_id: str
    data: Any
    original_timestamp: float                # 原始时间戳
    sync_error_ms: float = 0.0              # 同步误差


@dataclass
class SyncStats:
    """同步统计"""
    total_syncs: int = 0
    sync_errors: List[float] = field(default_factory=list)
    dropped_frames: Dict[str, int] = field(default_factory=lambda: defaultdict(int))

    @property
    def avg_sync_error_ms(self) -> float:
        return np.mean(self.sync_errors) if self.sync_errors else 0.0

    @property
    def max_sync_error_ms(self) -> float:
        return max(self.sync_errors) if self.sync_errors else 0.0


class MultiDeviceSyncManager:
    """多设备时间同步管理器

    功能:
    - 接收多个采集器的数据流
    - 基于时间戳进行多模态数据对齐
    - 丢帧检测与异常恢复
    - 硬件/软件时间戳统一
    """

    def __init__(
        self,
        tolerance_ms: float = 5.0,
        sync_method: str = "timestamp",  # "timestamp" | "nearest" | "interpolate"
        master_sensor: str = "",  # 主时钟传感器
    ):
        """
        Args:
            tolerance_ms: 最大允许同步误差
            sync_method: 同步策略
            master_sensor: 主时钟传感器 ID
        """
        self.tolerance_ms = tolerance_ms
        self.sync_method = sync_method
        self.master_sensor = master_sensor

        self._collectors: Dict[str, BaseCollector] = {}
        self._latest_data: Dict[str, Tuple[Any, float]] = {}
        self._sync_buffers: Dict[str, List[Tuple[Any, float]]] = defaultdict(list)
        self._stats = SyncStats()
        self._lock = threading.Lock()
        self._sync_callbacks: List[Callable] = []
        self._running = False
        self._sync_thread: Optional[threading.Thread] = None

    @property
    def stats(self) -> SyncStats:
        return self._stats

    def register_collector(self, collector: BaseCollector) -> None:
        """注册采集器"""
        self._collectors[collector.sensor_id] = collector
        print(f"[SyncManager] Registered: {collector.sensor_id}")

    def add_sync_callback(self, callback: Callable[[List[SyncFrame]], None]) -> None:
        """添加同步完成回调"""
        self._sync_callbacks.append(callback)

    def start(self) -> None:
        """启动同步管理"""
        # 启动所有采集器
        for sid, collector in self._collectors.items():
            if collector.state == CollectorState.IDLE:
                collector.start()

        self._running = True
        self._sync_thread = threading.Thread(
            target=self._sync_loop, name="sync-manager", daemon=True
        )
        self._sync_thread.start()
        print("[SyncManager] Started")

    def stop(self) -> None:
        """停止同步管理"""
        self._running = False
        if self._sync_thread:
            self._sync_thread.join(timeout=5.0)

        for collector in self._collectors.values():
            collector.stop()

        print(f"[SyncManager] Stopped. Stats: avg_error={self.stats.avg_sync_error_ms:.2f}ms")

    def sync_once(self) -> Optional[List[SyncFrame]]:
        """执行一次同步，返回对齐后的帧列表"""
        with self._lock:
            # 收集所有传感器最新数据
            all_data: Dict[str, Tuple[Any, float]] = {}
            for sid, collector in self._collectors.items():
                data_list = collector.get_buffer_data(max_items=1)
                if data_list:
                    all_data[sid] = data_list[0]

            if not all_data:
                return None

            # 确定基准时间戳
            if self.master_sensor and self.master_sensor in all_data:
                ref_timestamp = all_data[self.master_sensor][1]
            else:
                # 使用中间时间戳作为基准
                timestamps = [d[1] for d in all_data.values()]
                ref_timestamp = np.median(timestamps)

            # 同步对齐
            sync_frames = []
            for sid, (data, timestamp) in all_data.items():
                sync_error_ms = abs(timestamp - ref_timestamp) * 1000.0

                self._stats.total_syncs += 1
                self._stats.sync_errors.append(sync_error_ms)

                frame = SyncFrame(
                    timestamp=ref_timestamp,
                    sensor_id=sid,
                    data=data,
                    original_timestamp=timestamp,
                    sync_error_ms=sync_error_ms,
                )
                sync_frames.append(frame)

            # 检查同步误差
            max_error = max(f.sync_error_ms for f in sync_frames) if sync_frames else 0
            if max_error > self.tolerance_ms:
                print(
                    f"[SyncManager] Warning: sync error {max_error:.2f}ms "
                    f"exceeds tolerance {self.tolerance_ms}ms"
                )

            # 触发回调
            for cb in self._sync_callbacks:
                try:
                    cb(sync_frames)
                except Exception as e:
                    print(f"[SyncManager] Callback error: {e}")

            return sync_frames

    def _sync_loop(self) -> None:
        """同步主循环"""
        while self._running:
            frames = self.sync_once()
            if frames:
                # 等待下一个同步周期
                time.sleep(0.001)  # 1ms
            else:
                time.sleep(0.01)  # 10ms

    def get_latest_state(self) -> Dict[str, Any]:
        """获取所有传感器的最新状态"""
        state = {}
        for sid, collector in self._collectors.items():
            state[sid] = {
                "state": collector.state.value,
                "stats": {
                    "total_frames": collector.stats.total_frames,
                    "dropped_frames": collector.stats.dropped_frames,
                    "avg_freq": collector.stats.avg_frequency_hz,
                },
            }
        return state
