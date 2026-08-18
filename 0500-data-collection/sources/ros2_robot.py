"""
ROS2 真实机器人数据源
====================
订阅真实机器人的话题采集：
  - /joint_states         JointState  -> 本体状态
  - 相机话题(自行指定)     Image/CompressedImage -> 图像
  - 可选: /odom /imu      补充观测

动作侧: 订阅动作用于表示记录（例如 follow_joint_trajectory 回调），
或由键盘遥操作生成。

使用前提: 在 ROS2 环境 (source /opt/ros/humble/setup.bash) 中运行。
"""

from __future__ import annotations

from typing import Dict, List, Optional

import numpy as np

from .base import DataSource


def _import_rclpy():
    try:
        import rclpy  # noqa: F401
        return rclpy
    except ImportError:
        raise RuntimeError(
            "ROS2 环境不可用。请在安装 ROS2 的机器上运行: "
            "source /opt/ros/humble/setup.bash"
        )


class ROS2RobotSource(DataSource):
    """ROS2 真机数据源。"""

    name = "ros2"

    def __init__(
        self,
        node_name: str = "embody_collector",
        joint_states_topic: str = "/joint_states",
        image_topic: str = "/camera/rgb/image_raw",
        action_dim: int = 7,
        timeout_sec: float = 30.0,
        use_compressed_image: bool = False,
    ):
        rclpy = _import_rclpy()
        rclpy.init()
        self.node = rclpy.create_node(node_name)

        self._joint_state = None
        self._image = None
        self._action = np.zeros(action_dim, dtype=np.float32)
        self._timeout = timeout_sec

        from sensor_msgs.msg import JointState
        from sensor_msgs.msg import Image as RosImage
        from sensor_msgs.msg import CompressedImage
        from std_msgs.msg import Float32MultiArray

        self._sub_joint = self.node.create_subscription(
            JointState, joint_states_topic, self._cb_joint, 10)
        if use_compressed_image:
            image_cls = CompressedImage
        else:
            image_cls = RosImage
        self._sub_image = self.node.create_subscription(
            image_cls, image_topic, self._cb_image, 10)
        self._sub_action = self.node.create_subscription(
            Float32MultiArray, "/embody/action", self._cb_action, 10)

    def _cb_joint(self, msg):
        self._joint_state = np.asarray(msg.position, dtype=np.float32)

    def _cb_image(self, msg):
        if hasattr(msg, "data") and msg.data and not hasattr(msg, "width"):
            # CompressedImage
            import cv2
            import numpy as _np
            buf = _np.frombuffer(msg.data, dtype=_np.uint8)
            self._image = cv2.imdecode(buf, cv2.IMREAD_COLOR)[:, :, ::-1]
        elif hasattr(msg, "width"):
            import numpy as _np
            h, w = msg.height, msg.width
            if msg.encoding in ("rgb8", "bgr8", "mono8"):
                arr = _np.frombuffer(msg.data, dtype=_np.uint8).reshape(h, w, -1)
                self._image = arr[:, :, :3]

    def _cb_action(self, msg):
        self._action = np.asarray(msg.data, dtype=np.float32)

    def reset(self, **kwargs) -> Dict[str, np.ndarray]:
        import time
        t0 = time.time()
        while self._joint_state is None and (time.time() - t0) < self._timeout:
            import rclpy
            rclpy.spin_once(self.node, timeout_sec=0.1)
        return self.frame()

    def frame(self) -> Dict[str, np.ndarray]:
        out: Dict[str, np.ndarray] = {}
        if self._image is not None:
            out["image_wrist"] = self._image
        if self._joint_state is not None:
            out["state"] = self._joint_state
        return out

    def step(self, action: np.ndarray) -> None:
        self._action = np.asarray(action, dtype=np.float32)

    def close(self):
        import rclpy
        self.node.destroy_node()
        rclpy.shutdown()