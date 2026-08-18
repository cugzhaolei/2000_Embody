"""
LeRobot 格式转换器
=================
支持 HuggingFace LeRobot Dataset 格式的读写和转换。
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np


class LeRobotConverter:
    """LeRobot Dataset 格式转换

    LeRobot 是 HuggingFace 的开源机器人数据集格式，支持:
    - 视频帧 (mp4/webm)
    - 机器人状态 (parquet)
    - 动作序列 (parquet)
    - 语言指令 (jsonl)
    """

    def __init__(self, output_dir: str):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def from_internal_dataset(
        self,
        episodes: List[Dict[str, Any]],
        dataset_name: str = "embodied_dataset",
        robot_type: str = "so101",
        fps: float = 30.0,
    ) -> str:
        """将内部数据格式转换为 LeRobot 格式

        Args:
            episodes: Episode 数据列表
            dataset_name: 数据集名称
            robot_type: 机器人类型
            fps: 帧率

        Returns:
            LeRobot 数据集目录路径
        """
        repo_dir = self.output_dir / dataset_name
        repo_dir.mkdir(parents=True, exist_ok=True)

        # 创建元数据
        metadata = {
            "robot_type": robot_type,
            "fps": fps,
            "total_episodes": len(episodes),
            "total_frames": sum(len(ep.get("action", [])) for ep in episodes),
            "total_tasks": len(set(ep.get("task_name", "") for ep in episodes)),
            "modality": {
                "video": True,
                "state": True,
                "action": True,
                "language": True,
            },
        }

        # 转换每个 Episode
        for i, ep in enumerate(episodes):
            ep_dir = repo_dir / f"episode_{i:06d}"
            ep_dir.mkdir(exist_ok=True)

            # 保存视频帧
            if "rgb" in ep and isinstance(ep["rgb"], np.ndarray):
                self._save_frames_as_video(ep["rgb"], str(ep_dir / "observation_video.mp4"), fps)

            # 保存状态和动作
            parquet_data = {}
            if "joint_state" in ep:
                parquet_data["observation.state"] = ep["joint_state"]
            if "eef_pose" in ep:
                parquet_data["observation.eef_pose"] = ep["eef_pose"]
            if "action" in ep:
                parquet_data["action"] = ep["action"]
            if "gripper" in ep:
                parquet_data["observation.gripper"] = ep["gripper"]

            if parquet_data:
                self._save_parquet(parquet_data, str(ep_dir / "data.parquet"))

            # 保存语言指令
            if "language" in ep:
                instruction = ep["language"] if isinstance(ep["language"], str) else str(ep["language"])
                with open(ep_dir / "instruction.json", "w", encoding="utf-8") as f:
                    json.dump({"instruction": instruction}, f, ensure_ascii=False)

        # 保存数据集信息
        with open(repo_dir / "meta", "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False, default=str)

        print(f"LeRobot dataset saved to: {repo_dir}")
        return str(repo_dir)

    def to_internal_dataset(self, lerobot_path: str) -> List[Dict[str, Any]]:
        """从 LeRobot 格式转换为内部格式"""
        repo_dir = Path(lerobot_path)
        episodes = []

        # 读取元数据
        meta_file = repo_dir / "meta"
        metadata = {}
        if meta_file.exists():
            with open(meta_file) as f:
                metadata = json.load(f)

        # 遍历 episodes
        ep_dirs = sorted([d for d in repo_dir.iterdir() if d.is_dir() and d.name.startswith("episode_")])

        for ep_dir in ep_dirs:
            ep_data = {"episode_id": ep_dir.name}

            # 加载 parquet 数据
            parquet_file = ep_dir / "data.parquet"
            if parquet_file.exists():
                try:
                    import pandas as pd
                    df = pd.read_parquet(str(parquet_file))
                    for col in df.columns:
                        ep_data[col] = df[col].values
                except ImportError:
                    pass

            # 加载语言指令
            instr_file = ep_dir / "instruction.json"
            if instr_file.exists():
                with open(instr_file) as f:
                    ep_data["language"] = json.load(f).get("instruction", "")

            episodes.append(ep_data)

        return episodes

    def _save_frames_as_video(
        self, frames: np.ndarray, output_path: str, fps: float
    ) -> None:
        """将帧序列保存为视频"""
        try:
            import cv2
            h, w = frames.shape[1], frames.shape[2]
            fourcc = cv2.VideoWriter_fourcc(*"mp4v")
            writer = cv2.VideoWriter(output_path, fourcc, fps, (w, h))
            for frame in frames:
                if frame.ndim == 3 and frame.shape[-1] == 3:
                    writer.write(cv2.cvtColor(frame, cv2.COLOR_RGB2BGR))
            writer.release()
        except ImportError:
            # Fallback: 保存为 numpy 文件
            np.save(output_path.replace(".mp4", ".npy"), frames)

    def _save_parquet(self, data: Dict[str, np.ndarray], output_path: str) -> None:
        """保存为 Parquet"""
        try:
            import pandas as pd
            df_data = {}
            for key, arr in data.items():
                if isinstance(arr, np.ndarray):
                    if arr.ndim == 1:
                        df_data[key] = arr
                    else:
                        for i in range(arr.shape[1]):
                            df_data[f"{key}.{i}"] = arr[:, i]
            pd.DataFrame(df_data).to_parquet(output_path, index=False)
        except ImportError:
            np.savez(output_path.replace(".parquet", ".npz"), **data)

    def create_lerobot_metadata(
        self,
        robot_type: str = "so101",
        fps: float = 30.0,
        features: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """创建 LeRobot 兼容的元数据"""
        default_features = {
            "observation.video": {
                "dtype": "video",
                "shape": [480, 640, 3],
                "names": ["height", "width", "channel"],
            },
            "observation.state": {
                "dtype": "float32",
                "shape": [6],
                "names": ["joint_0", "joint_1", "joint_2", "joint_3", "joint_4", "joint_5"],
            },
            "action": {
                "dtype": "float32",
                "shape": [6],
                "names": ["joint_0", "joint_1", "joint_2", "joint_3", "joint_4", "joint_5"],
            },
        }

        if features:
            default_features.update(features)

        return {
            "robot_type": robot_type,
            "fps": fps,
            "features": default_features,
        }
