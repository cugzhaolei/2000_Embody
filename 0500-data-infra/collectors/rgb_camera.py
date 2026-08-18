"""
RGB 相机采集器
=============
支持 OpenCV / V4L2 / GStreamer 等多种后端，采集 RGB 图像数据。
"""

import time
from typing import Any, Callable, Optional, Tuple

import numpy as np

from .base import BaseCollector


class RGBCameraCollector(BaseCollector):
    """RGB 相机数据采集器

    支持:
    - OpenCV VideoCapture (USB / RTSP / 文件)
    - 分辨率和帧率配置
    - 帧时间戳同步
    """

    def __init__(
        self,
        sensor_id: str,
        camera_id: int = 0,
        source: str = "",
        width: int = 640,
        height: int = 480,
        fps: float = 30.0,
        buffer_size: int = 1000,
        callback: Optional[Callable] = None,
    ):
        """
        Args:
            sensor_id: 传感器 ID
            camera_id: 摄像头设备 ID (当 source 为空时使用)
            source: 视频源路径 (RTSP URL / 视频文件路径)
            width: 图像宽度
            height: 图像高度
            fps: 目标帧率
        """
        super().__init__(sensor_id, buffer_size, callback)
        self.camera_id = camera_id
        self.source = source
        self.width = width
        self.height = height
        self.fps = fps
        self._cap = None

    def _setup(self) -> None:
        try:
            import cv2
        except ImportError:
            raise RuntimeError("OpenCV is required for RGBCameraCollector")

        if self.source:
            self._cap = cv2.VideoCapture(self.source)
        else:
            self._cap = cv2.VideoCapture(self.camera_id)

        if not self._cap.isOpened():
            raise RuntimeError(f"Cannot open camera: {self.source or self.camera_id}")

        self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        self._cap.set(cv2.CAP_PROP_FPS, self.fps)

        # 验证实际参数
        actual_w = int(self._cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        actual_h = int(self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        actual_fps = self._cap.get(cv2.CAP_PROP_FPS)
        print(
            f"[{self.sensor_id}] Camera opened: {actual_w}x{actual_h} @ {actual_fps:.1f}fps"
        )

    def _collect_once(self) -> Optional[Tuple[Any, float]]:
        import cv2

        if self._cap is None or not self._cap.isOpened():
            return None

        ret, frame = self._cap.read()
        if not ret or frame is None:
            return None

        # BGR -> RGB
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        timestamp = time.time()
        return frame_rgb, timestamp

    def _cleanup(self) -> None:
        if self._cap is not None:
            self._cap.release()
            self._cap = None

    def get_resolution(self) -> Tuple[int, int]:
        return (self.width, self.height)


class RGBCameraSimCollector(BaseCollector):
    """模拟 RGB 相机采集器（用于测试）"""

    def __init__(
        self,
        sensor_id: str,
        width: int = 640,
        height: int = 480,
        fps: float = 30.0,
        buffer_size: int = 1000,
        callback: Optional[Callable] = None,
    ):
        super().__init__(sensor_id, buffer_size, callback)
        self.width = width
        self.height = height
        self.fps = fps
        self._frame_count = 0

    def _setup(self) -> None:
        print(f"[{self.sensor_id}] Simulated RGB camera initialized: {self.width}x{self.height} @ {self.fps}fps")

    def _collect_once(self) -> Optional[Tuple[Any, float]]:
        # 生成随机模拟帧
        frame = np.random.randint(0, 255, (self.height, self.width, 3), dtype=np.uint8)
        timestamp = time.time()
        self._frame_count += 1

        # 模拟帧率
        time.sleep(1.0 / self.fps)
        return frame, timestamp

    def _cleanup(self) -> None:
        self._frame_count = 0
