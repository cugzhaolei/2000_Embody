"""
数据后处理流水线
===============
包括视频编解码、轨迹转换、坐标变换、数据清洗、Episode 切分、异常检测等。
"""

from .video_codec import VideoCodec, VideoEncoder, VideoDecoder
from .trajectory import TrajectoryConverter, ActionTransformer
from .coordinate import CoordinateTransformer
from .cleaning import DataCleaner, CleaningRule
from .episode import EpisodeSegmenter, EpisodeSplitter
from .quality_check import PipelineQualityChecker

__all__ = [
    "VideoCodec",
    "VideoEncoder",
    "VideoDecoder",
    "TrajectoryConverter",
    "ActionTransformer",
    "CoordinateTransformer",
    "DataCleaner",
    "CleaningRule",
    "EpisodeSegmenter",
    "EpisodeSplitter",
    "PipelineQualityChecker",
]
