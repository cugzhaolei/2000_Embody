"""
Ego 长视频 / 人类操作数据处理
============================
针对 Ego 视角长视频及大规模人类操作数据的处理模块：

- 有效操作片段切分 (video_segmenter)
- 动作阶段识别 (action_phase)
- 异常片段过滤 (abnormal_filter)
- 训练样本生成 (sample_generator)
"""

from .video_segmenter import EgoSegment, EgoVideoSegmenter
from .action_phase import PhaseType, PhaseSpan, ActionPhaseRecognizer
from .abnormal_filter import FilterVerdict, AbnormalFilterResult, EgoAbnormalFilter
from .sample_generator import EgoTrainingSample, EgoSampleGenerator

__all__ = [
    "EgoSegment",
    "EgoVideoSegmenter",
    "PhaseType",
    "PhaseSpan",
    "ActionPhaseRecognizer",
    "FilterVerdict",
    "AbnormalFilterResult",
    "EgoAbnormalFilter",
    "EgoTrainingSample",
    "EgoSampleGenerator",
]
