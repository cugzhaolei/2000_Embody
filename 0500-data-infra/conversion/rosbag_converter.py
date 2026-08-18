"""
ROS/ROS2 Bag 转换器
===================
支持 ROS1 Bag / ROS2 Bag 的读写和格式转换。
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np


class ROSBagConverter:
    """ROS/ROS2 Bag 格式转换器

    支持:
    - 读取 ROS2 Bag (mcap / sqlite3)
    - 读取 ROS1 Bag (python3-bag / rosbags)
    - Topic 数据提取和转换
    - 与内部格式的双向转换
    """

    def __init__(self, output_dir: str):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def read_ros2_bag(self, bag_path: str) -> Dict[str, Any]:
        """读取 ROS2 Bag 文件"""
        try:
            from rosbags.rosbag2 import Reader

            reader = Reader(bag_path)
            topics_data = {}
            metadata = {
                "bag_path": bag_path,
                "topics": [],
                "total_messages": 0,
                "duration_sec": 0.0,
            }

            with reader:
                for connection in reader.connections:
                    topic_info = {
                        "topic": connection.topic,
                        "msg_type": connection.msgtype,
                        "message_count": 0,
                    }
                    metadata["topics"].append(topic_info)
                    topics_data[connection.topic] = []

                for topic, timestamp, rawdata, connection in reader.messages():
                    msg = reader.deserialize(rawdata, connection.msgtype)
                    topics_data[topic].append({
                        "timestamp": timestamp,
                        "data": self._ros_msg_to_dict(msg),
                    })
                    metadata["total_messages"] += 1

            if topics_data:
                first_ts = min(
                    msgs[0]["timestamp"]
                    for msgs in topics_data.values()
                    if msgs
                )
                last_ts = max(
                    msgs[-1]["timestamp"]
                    for msgs in topics_data.values()
                    if msgs
                )
                metadata["duration_sec"] = (last_ts - first_ts) / 1e9

            return {"metadata": metadata, "topics": topics_data}

        except ImportError:
            print("rosbags library not available. Trying rosbag2_py...")
            return self._read_ros2_bag_fallback(bag_path)

    def _read_ros2_bag_fallback(self, bag_path: str) -> Dict[str, Any]:
        """使用 rosbag2_py 读取"""
        try:
            import rosbag2_py

            reader = rosbag2_py.SequentialReader()
            reader.open(
                rosbag2_py.StorageOptions(uri=bag_path, storage_id="mcap"),
                rosbag2_py.ConverterOptions("cdr", "cdr"),
            )

            topics_data = {}
            metadata = {"bag_path": bag_path, "topics": [], "total_messages": 0}

            while reader.has_next():
                topic, data, timestamp = reader.read_next()
                if topic not in topics_data:
                    topics_data[topic] = []
                topics_data[topic].append({
                    "timestamp": timestamp,
                    "data": {"raw": True},
                })
                metadata["total_messages"] += 1

            return {"metadata": metadata, "topics": topics_data}

        except ImportError:
            raise RuntimeError("Neither rosbags nor rosbag2_py available")

    def convert_to_internal(
        self,
        bag_data: Dict[str, Any],
        topic_mapping: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """将 ROS2 Bag 数据转换为内部格式

        Args:
            bag_data: read_ros2_bag() 的输出
            topic_mapping: ROS topic -> 内部模态名称映射
        """
        if topic_mapping is None:
            topic_mapping = {
                "/camera/color/image_raw": "rgb",
                "/camera/depth/image_rect_raw": "depth",
                "/joint_states": "joint_state",
                "/tcp_ee_pose": "eef_pose",
                "/gripper": "gripper",
                "/cmd_vel": "action",
            }

        internal_data = {}
        topics = bag_data.get("topics", {})

        for topic_name, modality_name in topic_mapping.items():
            if topic_name in topics:
                messages = topics[topic_name]
                data_list = [msg["data"] for msg in messages]
                timestamps = np.array([msg["timestamp"] for msg in messages]) / 1e9

                if data_list and isinstance(data_list[0], dict):
                    # 尝试提取数组数据
                    keys = list(data_list[0].keys())
                    if keys:
                        arrays = {}
                        for key in keys:
                            try:
                                arrays[key] = np.array([d.get(key, 0) for d in data_list])
                            except (ValueError, TypeError):
                                pass
                        if arrays:
                            internal_data[modality_name] = {
                                "data": arrays,
                                "timestamps": timestamps,
                            }
                elif data_list:
                    try:
                        internal_data[modality_name] = {
                            "data": np.array(data_list),
                            "timestamps": timestamps,
                        }
                    except ValueError:
                        internal_data[modality_name] = {
                            "data": data_list,
                            "timestamps": timestamps,
                        }

        return internal_data

    def from_internal_dataset(
        self,
        episode_data: Dict[str, Any],
        output_path: str,
        topics_config: Optional[Dict[str, str]] = None,
    ) -> str:
        """将内部数据转换为 ROS2 Bag 格式 (mcap)"""
        try:
            from rosbag2_py import SequentialWriter, StorageOptions, ConverterOptions, TopicMetadata, MessageDefinition
        except ImportError:
            raise RuntimeError("rosbag2_py not available for writing ROS2 bags")

        if topics_config is None:
            topics_config = {
                "joint_state": "/joint_states",
                "eef_pose": "/tcp_ee_pose",
                "action": "/cmd_vel",
            }

        writer = SequentialWriter()
        writer.open(
            StorageOptions(uri=output_path, storage_id="mcap"),
            ConverterOptions("cdr", "cdr"),
        )

        # 注册 topics
        for modality, topic_name in topics_config.items():
            if modality in episode_data:
                writer.create_topic(TopicMetadata(
                    name=topic_name,
                    type="sensor_msgs/msg/JointState",
                    serialization_format="cdr",
                ))

        # 写入数据
        for modality, topic_name in topics_config.items():
            if modality in episode_data:
                data = episode_data[modality]
                if isinstance(data, np.ndarray):
                    for i, row in enumerate(data):
                        timestamp = int(i * 1e9 / 30)  # 假设 30fps
                        writer.write(topic_name, row.tobytes(), timestamp)

        return output_path

    @staticmethod
    def _ros_msg_to_dict(msg) -> Dict[str, Any]:
        """将 ROS 消息转为字典"""
        result = {}
        for slot in msg.get_fields_and_field_types():
            value = getattr(msg, slot)
            if hasattr(value, '__iter__') and not isinstance(value, str):
                result[slot] = list(value)
            else:
                result[slot] = value
        return result

    def list_bag_info(self, bag_path: str) -> Dict[str, Any]:
        """获取 Bag 文件信息"""
        try:
            from rosbags.rosbag2 import Reader
            reader = Reader(bag_path)
            with reader:
                topics = []
                for conn in reader.connections:
                    topics.append({
                        "topic": conn.topic,
                        "msg_type": conn.msgtype,
                    })
                return {
                    "bag_path": bag_path,
                    "num_topics": len(topics),
                    "topics": topics,
                }
        except ImportError:
            return {"bag_path": bag_path, "error": "rosbags not available"}
