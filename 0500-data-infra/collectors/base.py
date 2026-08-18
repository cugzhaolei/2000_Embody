"""
采集器基类
==========
定义所有数据采集器的公共接口和状态管理。
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple
import time
import threading
import queue


class CollectorState(str, Enum):
    """采集器状态"""
    IDLE = "idle"
    INITIALIZING = "initializing"
    RUNNING = "running"
    PAUSED = "paused"
    ERROR = "error"
    STOPPED = "stopped"


@dataclass
class CollectorStats:
    """采集统计信息"""
    total_frames: int = 0
    dropped_frames: int = 0
    error_count: int = 0
    start_time: float = 0.0
    last_frame_time: float = 0.0
    avg_frequency_hz: float = 0.0
    buffer_usage: float = 0.0  # 0~1

    def update_frequency(self) -> None:
        if self.total_frames > 1 and self.start_time > 0:
            elapsed = time.time() - self.start_time
            self.avg_frequency_hz = self.total_frames / elapsed

    @property
    def drop_rate(self) -> float:
        total = self.total_frames + self.dropped_frames
        return self.dropped_frames / total if total > 0 else 0.0


class BaseCollector(ABC):
    """数据采集器基类

    所有采集器必须继承此类并实现 collect() 和 _setup()/_cleanup() 方法。
    采集器支持线程安全的数据回调和缓冲区管理。
    """

    def __init__(
        self,
        sensor_id: str,
        buffer_size: int = 1000,
        callback: Optional[Callable[[str, Any, float], None]] = None,
    ):
        """
        Args:
            sensor_id: 传感器唯一标识
            buffer_size: 数据缓冲区大小
            callback: 数据回调函数 (sensor_id, data, timestamp) -> None
        """
        self.sensor_id = sensor_id
        self.buffer_size = buffer_size
        self._callback = callback

        self._state = CollectorState.IDLE
        self._stats = CollectorStats()
        self._buffer: queue.Queue = queue.Queue(maxsize=buffer_size)
        self._lock = threading.Lock()
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

    @property
    def state(self) -> CollectorState:
        return self._state

    @property
    def stats(self) -> CollectorStats:
        with self._lock:
            self._stats.update_frequency()
            return self._stats

    def start(self) -> None:
        """启动采集"""
        if self._state == CollectorState.RUNNING:
            return

        self._state = CollectorState.INITIALIZING
        self._stop_event.clear()
        self._stats = CollectorStats()
        self._stats.start_time = time.time()

        try:
            self._setup()
        except Exception as e:
            self._state = CollectorState.ERROR
            self._stats.error_count += 1
            raise RuntimeError(f"Collector '{self.sensor_id}' setup failed: {e}")

        self._thread = threading.Thread(
            target=self._collect_loop, name=f"collector-{self.sensor_id}", daemon=True
        )
        self._thread.start()
        self._state = CollectorState.RUNNING

    def stop(self) -> None:
        """停止采集"""
        if self._state not in (CollectorState.RUNNING, CollectorState.PAUSED):
            return

        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=5.0)
            self._thread = None

        try:
            self._cleanup()
        except Exception:
            pass

        self._state = CollectorState.STOPPED

    def pause(self) -> None:
        """暂停采集"""
        if self._state == CollectorState.RUNNING:
            self._state = CollectorState.PAUSED

    def resume(self) -> None:
        """恢复采集"""
        if self._state == CollectorState.PAUSED:
            self._state = CollectorState.RUNNING

    def get_buffer_data(self, max_items: int = -1) -> List[Tuple[Any, float]]:
        """从缓冲区取数据，返回 [(data, timestamp), ...]"""
        items = []
        count = 0
        while not self._buffer.empty() and (max_items < 0 or count < max_items):
            try:
                items.append(self._buffer.get_nowait())
                count += 1
            except queue.Empty:
                break
        return items

    def clear_buffer(self) -> None:
        """清空缓冲区"""
        while not self._buffer.empty():
            try:
                self._buffer.get_nowait()
            except queue.Empty:
                break

    @abstractmethod
    def _setup(self) -> None:
        """初始化采集资源（子类实现）"""
        pass

    @abstractmethod
    def _collect_once(self) -> Optional[Tuple[Any, float]]:
        """执行一次采集，返回 (data, timestamp) 或 None（子类实现）"""
        pass

    @abstractmethod
    def _cleanup(self) -> None:
        """释放采集资源（子类实现）"""
        pass

    def _collect_loop(self) -> None:
        """采集主循环"""
        while not self._stop_event.is_set():
            if self._state != CollectorState.RUNNING:
                time.sleep(0.01)
                continue

            try:
                result = self._collect_once()
                if result is not None:
                    data, timestamp = result

                    # 推入缓冲区
                    try:
                        self._buffer.put_nowait((data, timestamp))
                    except queue.Full:
                        self._stats.dropped_frames += 1

                    # 触发回调
                    if self._callback:
                        try:
                            self._callback(self.sensor_id, data, timestamp)
                        except Exception:
                            self._stats.error_count += 1

                    self._stats.total_frames += 1
                    self._stats.last_frame_time = time.time()

            except Exception as e:
                self._stats.error_count += 1
                # 连续错误过多则标记为 error 状态
                if self._stats.error_count > 10:
                    self._state = CollectorState.ERROR
                    break
