"""
时间同步检查
===========
检测多传感器之间的时间对齐误差和丢帧问题。
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np


@dataclass
class SyncCheckResult:
    """同步检查结果"""
    sensor_pairs: Dict[str, float] = field(default_factory=dict)  # (s1,s2) -> max error ms
    max_sync_error_ms: float = 0.0
    avg_sync_error_ms: float = 0.0
    dropped_frames: Dict[str, int] = field(default_factory=dict)
    gap_events: List[Dict[str, Any]] = field(default_factory=list)
    success: bool = True
    issues: List[str] = field(default_factory=list)


class SyncChecker:
    """时间同步质量检测器

    检测维度:
    - 多传感器时间戳对齐误差
    - 数据丢帧检测
    - 时间间隔异常 (gap)
    - 频率稳定性
    """

    def __init__(
        self,
        max_sync_error_ms: float = 10.0,
        max_gap_sec: float = 0.5,
        expected_freq: float = 30.0,
        freq_tolerance: float = 0.1,
    ):
        self.max_sync_error_ms = max_sync_error_ms
        self.max_gap_sec = max_gap_sec
        self.expected_freq = expected_freq
        self.freq_tolerance = freq_tolerance

    def check_sync(
        self,
        sensor_timestamps: Dict[str, np.ndarray],
    ) -> SyncCheckResult:
        """检查多传感器同步质量"""
        result = SyncCheckResult()

        sensors = list(sensor_timestamps.keys())
        if len(sensors) < 2:
            return result

        # 检查每对传感器的同步误差
        for i in range(len(sensors)):
            for j in range(i + 1, len(sensors)):
                s1, s2 = sensors[i], sensors[j]
                ts1 = sensor_timestamps[s1]
                ts2 = sensor_timestamps[s2]

                pair_key = f"{s1} <-> {s2}"
                max_error = self._compute_pair_sync_error(ts1, ts2)
                result.sensor_pairs[pair_key] = max_error

                if max_error > self.max_sync_error_ms:
                    result.issues.append(
                        f"Sync error {pair_key}: {max_error:.2f}ms > {self.max_sync_error_ms}ms"
                    )

        # 检查每个传感器的丢帧
        for sensor_id, timestamps in sensor_timestamps.items():
            dropped = self._detect_dropped_frames(timestamps)
            if dropped > 0:
                result.dropped_frames[sensor_id] = dropped
                result.issues.append(f"Dropped frames in {sensor_id}: {dropped}")

            # 检查时间间隔异常
            gaps = self._detect_time_gaps(timestamps)
            if gaps:
                result.gap_events.extend([
                    {"sensor": sensor_id, "start_idx": g[0], "gap_sec": g[1]}
                    for g in gaps
                ])
                result.issues.append(
                    f"Time gaps in {sensor_id}: {len(gaps)} gaps detected"
                )

        # 汇总
        if result.sensor_pairs:
            result.max_sync_error_ms = max(result.sensor_pairs.values())
            result.avg_sync_error_ms = np.mean(list(result.sensor_pairs.values()))

        result.success = len(result.issues) == 0
        return result

    def _compute_pair_sync_error(
        self, ts1: np.ndarray, ts2: np.ndarray
    ) -> float:
        """计算两个传感器对的最大同步误差"""
        if len(ts1) == 0 or len(ts2) == 0:
            return 0.0

        # 使用最近邻匹配
        if len(ts1) != len(ts2):
            # 对齐到较短的长度
            min_len = min(len(ts1), len(ts2))
            ts1 = ts1[:min_len]
            ts2 = ts2[:min_len]

        diffs = np.abs(ts1 - ts2) * 1000.0  # 转换为毫秒
        return float(diffs.max()) if len(diffs) > 0 else 0.0

    def _detect_dropped_frames(self, timestamps: np.ndarray) -> int:
        """检测丢帧数量"""
        if len(timestamps) < 2:
            return 0

        dt = np.diff(timestamps)
        median_dt = np.median(dt)
        expected_interval = 1.0 / self.expected_freq

        # 如果时间间隔超过期望值的 2 倍，认为丢帧
        dropped_threshold = expected_interval * 2.0
        num_dropped = int((dt > dropped_threshold).sum())

        return num_dropped

    def _detect_time_gaps(
        self, timestamps: np.ndarray
    ) -> List[Tuple[int, float]]:
        """检测时间间隔异常"""
        if len(timestamps) < 2:
            return []

        dt = np.diff(timestamps)
        gap_indices = np.where(dt > self.max_gap_sec)[0]

        gaps = []
        for idx in gap_indices:
            gap_sec = float(dt[idx])
            gaps.append((int(idx), gap_sec))

        return gaps

    def check_frequency_stability(
        self, timestamps: np.ndarray
    ) -> Dict[str, Any]:
        """检查频率稳定性"""
        if len(timestamps) < 3:
            return {"stable": True, "avg_freq": 0, "std_freq": 0}

        dt = np.diff(timestamps)
        freqs = 1.0 / dt

        avg_freq = float(np.mean(freqs))
        std_freq = float(np.std(freqs))
        is_stable = abs(avg_freq - self.expected_freq) < self.expected_freq * self.freq_tolerance

        return {
            "stable": is_stable,
            "avg_freq": avg_freq,
            "std_freq": std_freq,
            "expected_freq": self.expected_freq,
            "min_freq": float(freqs.min()),
            "max_freq": float(freqs.max()),
        }

    def generate_report(
        self,
        sensor_timestamps: Dict[str, np.ndarray],
    ) -> Dict[str, Any]:
        """生成完整同步质量报告"""
        sync_result = self.check_sync(sensor_timestamps)

        freq_reports = {}
        for sensor_id, timestamps in sensor_timestamps.items():
            freq_reports[sensor_id] = self.check_frequency_stability(timestamps)

        return {
            "sync_check": {
                "success": sync_result.success,
                "max_sync_error_ms": sync_result.max_sync_error_ms,
                "avg_sync_error_ms": sync_result.avg_sync_error_ms,
                "sensor_pairs": sync_result.sensor_pairs,
                "dropped_frames": sync_result.dropped_frames,
                "gap_events": len(sync_result.gap_events),
                "issues": sync_result.issues,
            },
            "frequency": freq_reports,
        }
