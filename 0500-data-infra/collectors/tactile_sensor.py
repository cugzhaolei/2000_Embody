"""
触觉传感器采集器
===============
支持 GelSight / Digit / 自研触觉传感器等数据采集。
"""

import time
from typing import Any, Callable, Optional, Tuple

import numpy as np

from .base import BaseCollector


class TactileCollector(BaseCollector):
    """触觉传感器数据采集器

    支持:
    - GelSight 系列 (图像型触觉)
    - Digit 系列
    - 压阻/电容式阵列触觉
    """

    def __init__(
        self,
        sensor_id: str,
        sensor_type: str = "gelsight",  # "gelsight" | "digit" | "array"
        resolution: Tuple[int, int] = (320, 240),
        num_taxels: int = 0,  # 阵列式触觉的 taxel 数量
        fps: float = 100.0,
        buffer_size: int = 5000,
        callback: Optional[Callable] = None,
        source: str = "",
    ):
        super().__init__(sensor_id, buffer_size, callback)
        self.sensor_type = sensor_type
        self.resolution = resolution
        self.num_taxels = num_taxels
        self.fps = fps
        self.source = source
        self._cap = None

    def _setup(self) -> None:
        if self.sensor_type in ("gelsight", "digit"):
            try:
                import cv2
                self._cap = cv2.VideoCapture(self.source if self.source else 0)
                if self._cap.isOpened():
                    self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.resolution[0])
                    self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.resolution[1])
                    print(f"[{self.sensor_id}] Tactile sensor ({self.sensor_type}) opened")
                    return
            except ImportError:
                pass

        print(f"[{self.sensor_id}] Tactile sensor ({self.sensor_type}) simulated")

    def _collect_once(self) -> Optional[Tuple[Any, float]]:
        timestamp = time.time()

        if self.sensor_type in ("gelsight", "digit") and self._cap is not None:
            import cv2
            ret, frame = self._cap.read()
            if ret:
                return {
                    "image": cv2.cvtColor(frame, cv2.COLOR_BGR2RGB),
                    "touch": self._extract_touch_features(frame),
                }, timestamp
            return None

        # 模拟数据
        if self.sensor_type == "array" and self.num_taxels > 0:
            taxels = np.random.uniform(0, 1, (self.num_taxels,)).astype(np.float32)
            return {"taxels": taxels, "image": None}, timestamp
        else:
            image = np.random.randint(0, 255, (self.resolution[1], self.resolution[0], 3), dtype=np.uint8)
            return {"image": image, "touch": self._extract_touch_features(image)}, timestamp

    def _extract_touch_features(self, frame: Any) -> dict:
        """从触觉图像提取接触特征"""
        if isinstance(frame, np.ndarray) and frame.ndim >= 2:
            gray = frame.mean(axis=-1) if frame.ndim == 3 else frame
            contact_mask = gray > 128
            return {
                "contact_area": float(contact_mask.sum()),
                "centroid": (
                    float(contact_mask.sum(axis=1).argmax()),
                    float(contact_mask.sum(axis=0).argmax()),
                ) if contact_mask.any() else (0, 0),
                "max_pressure": float(gray.max()) / 255.0,
            }
        return {"contact_area": 0, "centroid": (0, 0), "max_pressure": 0}

    def _cleanup(self) -> None:
        if self._cap is not None:
            self._cap.release()
            self._cap = None
