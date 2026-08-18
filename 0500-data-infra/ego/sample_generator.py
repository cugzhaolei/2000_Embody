"""
Ego 训练样本生成
================
将切分并过滤后的有效操作片段进一步加工为训练样本：

- 滑动窗口裁剪（固定长度、可重叠）
- 指令/成败标签关联
- 阶段标签注入
- JSON / Parquet(可选) 元数据导出
"""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np

from .action_phase import PhaseSpan
from .video_segmenter import EgoSegment


@dataclass
class EgoTrainingSample:
    """一个训练样本（窗口裁剪后的片段）"""
    sample_id: str
    source_video: str                    # 来源视频标识
    segment_id: str                      # 来源片段
    start_idx: int                       # 帧索引（相对原视频）
    end_idx: int
    start_time: float
    end_time: float
    instruction: str = ""                # 语言指令
    success: Optional[bool] = None       # 操作成败
    phases: List[str] = field(default_factory=list)      # 阶段标签
    quality_score: float = 1.0           # 样本质量分
    window_size: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "sample_id": self.sample_id,
            "source_video": self.source_video,
            "segment_id": self.segment_id,
            "start_idx": self.start_idx,
            "end_idx": self.end_idx,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "instruction": self.instruction,
            "success": self.success,
            "phases": self.phases,
            "quality_score": self.quality_score,
            "window_size": self.window_size,
            "metadata": self.metadata,
        }


class EgoSampleGenerator:
    """Ego 训练样本生成器

    支持:
    - 按片段滑动窗口裁剪
    - 片段级指令与成败标签传播
    - 阶段标签聚合（片段内占比最高的阶段）
    - 元数据导出（JSON / 可选 Parquet）
    """

    def __init__(
        self,
        window_size: int = 30,          # 窗口长度（帧）
        stride: int = 15,               # 窗口步长（帧）
        min_window_ratio: float = 0.5,  # 允许最后一个不完整窗口的最小占比
    ):
        self.window_size = window_size
        self.stride = stride
        self.min_window_ratio = min_window_ratio

    def generate(
        self,
        segments: List[EgoSegment],
        source_video: str = "",
        instructions: Optional[Dict[str, str]] = None,   # segment_id -> 指令
        success_labels: Optional[Dict[str, bool]] = None,  # segment_id -> 成败
        phase_spans: Optional[List[PhaseSpan]] = None,   # 片段内阶段（绝对索引）
        quality_scores: Optional[Dict[str, float]] = None,
    ) -> List[EgoTrainingSample]:
        """生成训练样本"""
        all_phase_spans = phase_spans or []
        samples: List[EgoTrainingSample] = []

        for seg in segments:
            windows = self._sliding_windows(seg)
            dominant_phase = self._dominant_phase(seg, all_phase_spans)

            for (ws, we, wsize) in windows:
                if wsize < self.window_size * self.min_window_ratio:
                    continue
                sample = EgoTrainingSample(
                    sample_id=f"sample_{ws:06d}_{we:06d}",
                    source_video=source_video,
                    segment_id=seg.segment_id,
                    start_idx=ws,
                    end_idx=we,
                    start_time=seg.start_time + (ws - seg.start_idx) / max(1.0, (seg.num_steps - 1)) * seg.duration,
                    end_time=seg.start_time + (we - seg.start_idx) / max(1.0, (seg.num_steps - 1)) * seg.duration,
                    instruction=(instructions or {}).get(seg.segment_id, ""),
                    success=(success_labels or {}).get(seg.segment_id),
                    phases=dominant_phase,
                    quality_score=(quality_scores or {}).get(seg.segment_id, 1.0),
                    window_size=wsize,
                    metadata={"segment": seg.to_dict()},
                )
                samples.append(sample)

        return samples

    # ------------------------------------------------------------------
    def _sliding_windows(self, seg: EgoSegment):
        """返回片段内窗口 (start, end_inclusive, actual_size)"""
        length = seg.num_steps
        windows = []
        start = seg.start_idx
        while start + self.window_size - 1 <= seg.end_idx:
            windows.append((start, start + self.window_size - 1, self.window_size))
            start += self.stride
        # 尾部不完整窗口
        if start <= seg.end_idx:
            windows.append((start, seg.end_idx, seg.end_idx - start + 1))
        return windows

    def _dominant_phase(
        self, seg: EgoSegment, spans: List[PhaseSpan]
    ) -> List[str]:
        """返回片段内按帧数占比排序的阶段标签（Top-2）"""
        if not spans:
            return []
        counts: Dict[str, int] = {}
        for span in spans:
            # 只统计与片段重叠部分
            overlap_start = max(span.start_idx, seg.start_idx)
            overlap_end = min(span.end_idx, seg.end_idx)
            if overlap_end >= overlap_start:
                counts[span.phase.value] = counts.get(span.phase.value, 0) + (
                    overlap_end - overlap_start + 1
                )
        ordered = sorted(counts.items(), key=lambda kv: -kv[1])
        return [phase for phase, _ in ordered[:2]]

    # ------------------------------------------------------------------
    def export_json(self, samples: List[EgoTrainingSample], path: str) -> None:
        """导出样本元数据为 JSON（训练读取侧可直接消费）"""
        out_path = Path(path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "samples": [s.to_dict() for s in samples],
            "count": len(samples),
        }
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)

    def export_parquet(self, samples: List[EgoTrainingSample], path: str) -> None:
        """可选: 导出为 Parquet（需 pandas/pyarrow）"""
        try:
            import pandas as pd
        except ImportError as e:
            raise ImportError(
                "export_parquet requires pandas/pyarrow: pip install pandas pyarrow"
            ) from e

        df = pd.DataFrame([s.to_dict() for s in samples])
        df.to_parquet(path, index=False)
