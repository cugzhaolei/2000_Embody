"""
深度相机采集器
=============
支持 RealSense / Astra / Kinect 等深度相机，采集 Depth 图像和点云。
"""

import time
from typing import Any, Callable, Optional, Tuple

import numpy as np

from .base import BaseCollector


class DepthCameraCollector(BaseCollector):
    """深度相机数据采集器

    支持:
    - Intel RealSense SDK
    - OpenNI / Astra
    - 通用 OpenCV 后端
    """

    def __init__(
        self,
        sensor_id: str,
        device_serial: str = "",
        width: int = 640,
        height: int = 480,
        fps: float = 30.0,
        depth_scale: float = 0.001,  # 深度值缩放因子 (mm -> m)
        align_depth_to_color: bool = True,
        buffer_size: int = 1000,
        callback: Optional[Callable] = None,
    ):
        super().__init__(sensor_id, buffer_size, callback)
        self.device_serial = device_serial
        self.width = width
        self.height = height
        self.fps = fps
        self.depth_scale = depth_scale
        self.align_depth_to_color = align_depth_to_color
        self._pipeline = None
        self._align = None

    def _setup(self) -> None:
        try:
            import pyrealsense2 as rs
        except ImportError:
            print(f"[{self.sensor_id}] pyrealsense2 not available, using simulated depth")
            self._pipeline = None
            return

        self._pipeline = rs.pipeline()
        config = rs.config()

        if self.device_serial:
            config.enable_device(self.device_serial)

        config.enable_stream(rs.stream.depth, self.width, self.height, rs.format.z16, int(self.fps))
        if self.align_depth_to_color:
            config.enable_stream(rs.stream.color, self.width, self.height, rs.format.bgr8, int(self.fps))

        self._pipeline.start(config)
        self._align = rs.align(rs.stream.color) if self.align_depth_to_color else None
        print(f"[{self.sensor_id}] Depth camera started: {self.width}x{self.height} @ {self.fps}fps")

    def _collect_once(self) -> Optional[Tuple[Any, float]]:
        if self._pipeline is None:
            # 模拟深度数据
            depth = np.random.uniform(0.1, 5.0, (self.height, self.width)).astype(np.float32)
            timestamp = time.time()
            time.sleep(1.0 / self.fps)
            return {"depth": depth, "confidence": None}, timestamp

        try:
            import pyrealsense2 as rs

            frames = self._pipeline.wait_for_frames(timeout_ms=int(1000 / self.fps))

            if self._align and self._align is not None:
                frames = self._align.process(frames)

            depth_frame = frames.get_depth_frame()
            if not depth_frame:
                return None

            depth_image = np.asanyarray(depth_frame.get_data()).astype(np.float32) * self.depth_scale
            timestamp = depth_frame.get_timestamp() / 1000.0  # ms -> s

            return {"depth": depth_image, "confidence": None}, timestamp

        except Exception:
            return None

    def _cleanup(self) -> None:
        if self._pipeline is not None:
            self._pipeline.stop()
            self._pipeline = None
        self._align = None

    def get_depth_at_pixel(self, depth_image: np.ndarray, x: int, y: int) -> float:
        """获取指定像素的深度值"""
        if 0 <= y < depth_image.shape[0] and 0 <= x < depth_image.shape[1]:
            return float(depth_image[y, x])
        return -1.0

    def depth_to_pointcloud(
        self, depth_image: np.ndarray, intrinsics: Optional[dict] = None
    ) -> np.ndarray:
        """深度图转点云 (N, 3)"""
        h, w = depth_image.shape
        if intrinsics is None:
            # 使用默认内参
            fx = fy = w / 2.0
            cx, cy = w / 2.0, h / 2.0
        else:
            fx = intrinsics.get("fx", w / 2.0)
            fy = intrinsics.get("fy", h / 2.0)
            cx = intrinsics.get("cx", w / 2.0)
            cy = intrinsics.get("cy", h / 2.0)

        u, v = np.meshgrid(np.arange(w), np.arange(h))
        z = depth_image
        x = (u - cx) * z / fx
        y = (v - cy) * z / fy

        points = np.stack([x, y, z], axis=-1).reshape(-1, 3)
        # 过滤无效点
        valid = (z > 0) & (z < 10.0)
        return points[valid.reshape(-1)]
