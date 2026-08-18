"""
自动标注模块
============
基于规则的自动标注：操作成败、质量标签、阶段标签等，
供后处理流水线与数据飞轮使用。
"""

from .auto_labeler import LabelType, AnnotationResult, AutoLabeler

__all__ = [
    "LabelType",
    "AnnotationResult",
    "AutoLabeler",
]
