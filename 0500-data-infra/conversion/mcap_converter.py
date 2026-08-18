"""
MCAP 格式转换器
==============
支持 Foxglove MCAP 格式的读写和转换。
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np


class MCAPConverter:
    """MCAP 格式转换器

    MCAP 是 Foxglove 的高性能机器人数据记录格式:
    - 支持多种消息序列化格式 (CDR, Protobuf, JSON)
    - 高效的索引和随机访问
    - 支持附件和元数据
    """

    def __init__(self, output_dir: str):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def read_mcap(self, mcap_path: str) -> Dict[str, Any]:
        """读取 MCAP 文件"""
        try:
            from mcap.reader import make_reader

            data = {"channels": {}, "messages": {}, "metadata": {}}

            with open(mcap_path, "rb") as f:
                reader = make_reader(f)

                # 读取概要信息
                summary = reader.get_summary()
                if summary:
                    data["metadata"] = {
                        "statistics": {
                            "message_count": summary.statistics.message_count if summary.statistics else 0,
                            "channel_count": summary.statistics.channel_count if summary.statistics else 0,
                        }
                    }

                    for channel_id, channel in summary.channels.items():
                        data["channels"][channel_id] = {
                            "topic": channel.topic,
                            "schema_name": channel.schema.name if channel.schema else "",
                            "message_encoding": channel.message_encoding,
                        }

                # 读取消息
                for schema, channel, message in reader.iter_messages():
                    topic = channel.topic
                    if topic not in data["messages"]:
                        data["messages"][topic] = []

                    data["messages"][topic].append({
                        "timestamp": message.log_time,
                        "data": self._decode_message(
                            message.data, channel.message_encoding
                        ),
                    })

            return data

        except ImportError:
            raise RuntimeError("mcap library not available. Install: pip install mcap")

    def _decode_message(self, data: bytes, encoding: str) -> Any:
        """解码消息"""
        if encoding == "json":
            return json.loads(data)
        elif encoding == "protobuf":
            return {"raw_bytes": list(data[:100])}  # 简化处理
        else:
            return {"raw": True, "size": len(data)}

    def convert_to_internal(
        self,
        mcap_data: Dict[str, Any],
        topic_mapping: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """将 MCAP 数据转换为内部格式"""
        if topic_mapping is None:
            topic_mapping = {}

        internal = {}
        messages = mcap_data.get("messages", {})

        for topic, msg_list in messages.items():
            modality = topic_mapping.get(topic, topic.strip("/").replace("/", "_"))
            if msg_list:
                timestamps = np.array([m["timestamp"] for m in msg_list]) / 1e9
                data_list = [m["data"] for m in msg_list]
                internal[modality] = {
                    "data": data_list,
                    "timestamps": timestamps,
                }

        return internal

    def from_internal_dataset(
        self,
        episode_data: Dict[str, Any],
        output_path: str,
        channel_config: Optional[Dict[str, str]] = None,
    ) -> str:
        """将内部数据写入 MCAP 文件"""
        try:
            from mcap.writer import Writer
        except ImportError:
            raise RuntimeError("mcap library not available")

        if channel_config is None:
            channel_config = {
                "joint_state": "/joint_states",
                "eef_pose": "/robot/eef_pose",
                "rgb": "/camera/image_raw",
            }

        writer = Writer()
        writer.start(output_path)

        # 注册 channels
        channels = {}
        for modality, topic_name in channel_config.items():
            if modality in episode_data:
                channel_id = writer.register_channel(
                    topic=topic_name,
                    message_encoding="json",
                    schema_name=f"embodied_{modality}",
                )
                channels[modality] = channel_id

        # 写入数据
        for modality, channel_id in channels.items():
            data = episode_data[modality]
            if isinstance(data, dict) and "data" in data:
                msg_list = data["data"]
                timestamps = data.get("timestamps", np.arange(len(msg_list)))

                for i, msg in enumerate(msg_list):
                    ts = int(timestamps[i] * 1e9) if i < len(timestamps) else 0
                    serialized = json.dumps(msg, default=str).encode("utf-8")
                    writer.add_message(channel_id, ts, serialized)

        writer.finish()
        return output_path

    def list_mcap_info(self, mcap_path: str) -> Dict[str, Any]:
        """获取 MCAP 文件信息"""
        try:
            from mcap.reader import make_reader

            with open(mcap_path, "rb") as f:
                reader = make_reader(f)
                summary = reader.get_summary()

                if summary is None:
                    return {"error": "No summary available"}

                channels = []
                for ch_id, ch in summary.channels.items():
                    channels.append({
                        "topic": ch.topic,
                        "schema": ch.schema.name if ch.schema else "",
                        "encoding": ch.message_encoding,
                    })

                return {
                    "file": mcap_path,
                    "channels": len(channels),
                    "message_count": summary.statistics.message_count if summary.statistics else 0,
                    "channel_details": channels,
                }
        except ImportError:
            return {"error": "mcap not available"}
