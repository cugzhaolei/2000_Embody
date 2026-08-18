"""
数据 Schema 定义
================
定义数据集 / episode / step 的统一数据结构，
输出为 LeRobot 兼容的 dict 与 parquet 字段约定。

约定:
  所有观测键使用点分格式，如 "observation.images.wrist"、"observation.state"，
  与 LeRobot 数据集规范保持一致。
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import numpy as np


# 标准动作维度与含义 (与 0200-vla-imitation 的 action_dim=7 对齐)
ACTION_NAMES = [
    "dx", "dy", "dz",          # 末端平移增量 (m)
    "droll", "dpitch", "dyaw", # 末端旋转增量 (rad)
    "gripper",                 # 夹爪开合 [0, 1]
]

# 标准本体状态 (关节位姿)
STATE_NAMES = [
    "joint_0", "joint_1", "joint_2",
    "joint_3", "joint_4", "joint_5",
]


class Frame:
    """单帧观测数据。

    Attributes:
        timestamp: 采集时间戳（秒，相对于采集开始）
        images:   图像 dict，键为相机名，值为 np.ndarray uint8 [H, W, 3]
        state:    本体状态 np.ndarray（如 6 关节角度）
        extras:   额外观测（力/力矩/imu 等），任选
    """

    __slots__ = ("timestamp", "images", "state", "extras")

    def __init__(
        self,
        images: Optional[Dict[str, np.ndarray]] = None,
        state: Optional[np.ndarray] = None,
        timestamp: float = 0.0,
        extras: Optional[Dict[str, Any]] = None,
    ):
        self.images = images or {}
        self.state = state if state is not None else np.zeros(0, dtype=np.float32)
        self.timestamp = timestamp
        self.extras = extras or {}

    def to_dict(self, image_dir: Optional[str] = None, encode_jpeg: bool = False) -> Dict[str, Any]:
        """转为可写入 parquet 的 flat dict。

        Args:
            image_dir: 图像参考根目录，传则把图像写成相对路径字符串；
                       否则把图像对象原样放入 dict（供视频编码用）。
            encode_jpeg: True 时把图像编码为 JPEG bytes（parquet 友好）。
        """
        out: Dict[str, Any] = {
            "timestamp": float(self.timestamp),
            "observation.state": np.asarray(self.state, dtype=np.float32),
        }
        for cam, img in self.images.items():
            key = f"observation.images.{cam}"
            if image_dir is not None and img is not None:
                out[key] = str(image_dir)
            elif encode_jpeg and img is not None:
                out[key] = _encode_jpeg(np.asarray(img))
            else:
                out[key] = img
        for k, v in self.extras.items():
            out[f"observation.extra.{k}"] = v
        return out


def build_step_dict(
    frame: Frame,
    action: np.ndarray,
    instruction: str,
    frame_index: int,
    image_dir: Optional[str] = None,
    encode_jpeg: bool = False,
) -> Dict[str, Any]:
    """构造一个 step 记录（LeRobot 风格）。

    Returns:
        dict，可直接 append 进 DataFrame 一列：
        包含 instruction / frame_index / action 与 frame 的观测字段。
    """
    step = frame.to_dict(image_dir=image_dir, encode_jpeg=encode_jpeg)
    step.update({
        "instruction": instruction,
        "frame_index": int(frame_index),
        "action": np.asarray(action, dtype=np.float32),
    })
    return step


def validate_frame(frame: Frame) -> List[str]:
    """校验一帧数据，返回问题列表（空列表表示合法）。"""
    problems: List[str] = []
    for cam, img in frame.images.items():
        if img is None:
            continue
        arr = np.asarray(img)
        if arr.ndim != 3 or arr.shape[-1] not in (3, 4):
            problems.append(f"camera '{cam}': 期望 RGB(A) [H,W,3/4]，实际 shape={arr.shape}")
    if frame.state.ndim != 1:
        problems.append(f"state: 期望 1D 向量，实际 shape={frame.state.shape}")
    return problems


def _encode_jpeg(img: np.ndarray) -> bytes:
    """把 RGB 图像编码为 JPEG bytes。Pillow 缺失时退回原始 ndarray 序列化。"""
    from io import BytesIO
    arr = np.asarray(img)
    if arr.dtype != np.uint8:
        if arr.dtype.kind == "f":
            if arr.max() <= 1.0:
                arr = (arr * 255).astype(np.uint8)
            else:
                arr = arr.astype(np.uint8)
        else:
            arr = arr.astype(np.uint8)
    if arr.shape[-1] == 4:
        arr = arr[:, :, :3]
    try:
        from PIL import Image
        buf = BytesIO()
        Image.fromarray(arr).save(buf, format="JPEG", quality=80)
        return buf.getvalue()
    except ImportError:
        return arr.tobytes()



def decode_image_bytes(value) -> Optional[np.ndarray]:
    """从 parquet 中解码图像（bytes -> ndarray）。"""
    import base64
    if value is None:
        return None
    if isinstance(value, str):
        try:
            value = base64.b64decode(value)
        except Exception:
            return None
    if not isinstance(value, (bytes, bytearray, memoryview)):
        if isinstance(value, (list, tuple)):
            return np.asarray(value, dtype=np.uint8)
        return None
    data = bytes(value)
    try:
        from io import BytesIO
        from PIL import Image
        return np.array(Image.open(BytesIO(data)).convert("RGB"))
    except Exception:
        try:
            return np.frombuffer(data, dtype=np.uint8)
        except Exception:
            return None