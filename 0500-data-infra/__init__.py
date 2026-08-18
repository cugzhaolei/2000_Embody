"""
具身数据基础设施 (Embodied Data Infrastructure)
=============================================
统一、高可靠、可扩展的多模态数据采集、处理和管理平台。

支持的数据模态:
- RGB 图像/视频
- Depth 深度图
- Tactile 触觉
- Robot State 机器人状态
- EEF Pose 末端执行器位姿
- Joint State 关节状态
- Action 动作
- IMU 惯性测量
- Hand State 手部状态
- Language Instruction 语言指令

支持的格式转换:
- LeRobot Dataset
- ROS/ROS2 Bag
- MCAP

数据后处理与增值能力:
- Ego 长视频有效片段切分 / 动作阶段识别 / 异常过滤 / 样本生成 (ego)
- 规则化自动标注 (annotation)
- Dataset 版本管理与全链路追溯 (versioning)
- 训练/评估/失败 Case 关联管理 (tracking)
- 具身数据飞轮: 失败数据自动回流与再训练 (flywheel)
"""

__version__ = "0.1.0"

from .schemas import (
    ModalityType,
    SensorSchema,
    DatasetSchema,
    create_schema,
)
from .ego import (
    EgoSegment,
    EgoVideoSegmenter,
    PhaseType,
    PhaseSpan,
    ActionPhaseRecognizer,
    FilterVerdict,
    AbnormalFilterResult,
    EgoAbnormalFilter,
    EgoTrainingSample,
    EgoSampleGenerator,
)
from .annotation import LabelType, AnnotationResult, AutoLabeler
from .tracking import (
    JobStatus,
    FailureStatus,
    TrainingJob,
    ModelVersion,
    BenchmarkResult,
    RealWorldEval,
    FailureCase,
    TrainingRegistry,
)
from .flywheel import (
    FailureIngester,
    CuratedPool,
    FlywheelCurator,
    DataFlywheel,
    FlywheelReport,
)
