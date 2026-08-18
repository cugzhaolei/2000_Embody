"""
Parquet 存储层
=============
高性能列式存储，支持 PyArrow / Pandas 读写。
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import numpy as np


class ParquetStore:
    """Parquet 格式数据存储

    适用于: 结构化数据 (机器人状态、动作、元数据)
    特点: 列式存储、压缩高效、支持 Schema Evolution
    """

    def __init__(self, base_dir: str):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def save_episode(
        self,
        episode_id: str,
        data: Dict[str, np.ndarray],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """保存 Episode 到 Parquet 文件"""
        try:
            import pandas as pd
        except ImportError:
            raise RuntimeError("pandas is required for ParquetStore")

        df_data = {}
        for key, arr in data.items():
            if isinstance(arr, np.ndarray):
                if arr.ndim == 1:
                    df_data[key] = arr
                elif arr.ndim == 2:
                    # 每列作为独立列
                    for i in range(arr.shape[1]):
                        df_data[f"{key}_{i}"] = arr[:, i]
                else:
                    # 高维数据展平存储
                    df_data[key] = [arr[i].tobytes() for i in range(len(arr))]

        df = pd.DataFrame(df_data)

        # 添加元数据
        if metadata:
            for k, v in metadata.items():
                if isinstance(v, (str, int, float, bool)):
                    df.attrs[k] = v

        file_path = self.base_dir / f"{episode_id}.parquet"
        df.to_parquet(str(file_path), engine="pyarrow", index=False)

        # 保存 JSON 元数据
        if metadata:
            meta_path = self.base_dir / f"{episode_id}.meta.json"
            with open(meta_path, "w", encoding="utf-8") as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False, default=str)

        return str(file_path)

    def load_episode(
        self, episode_id: str, columns: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """加载 Episode 数据"""
        try:
            import pandas as pd
        except ImportError:
            raise RuntimeError("pandas is required for ParquetStore")

        file_path = self.base_dir / f"{episode_id}.parquet"
        if not file_path.exists():
            raise FileNotFoundError(f"Episode not found: {episode_id}")

        df = pd.read_parquet(str(file_path), columns=columns, engine="pyarrow")

        result = {}
        for col in df.columns:
            result[col] = df[col].values

        # 加载元数据
        meta_path = self.base_dir / f"{episode_id}.meta.json"
        if meta_path.exists():
            with open(meta_path, "r", encoding="utf-8") as f:
                result["_metadata"] = json.load(f)

        return result

    def list_episodes(self) -> List[str]:
        """列出所有 Episode ID"""
        return sorted([
            p.stem for p in self.base_dir.glob("*.parquet")
        ])

    def save_dataset_metadata(self, metadata: Dict[str, Any]) -> None:
        """保存 Dataset 级别元数据"""
        meta_path = self.base_dir / "dataset_metadata.json"
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False, default=str)

    def load_dataset_metadata(self) -> Dict[str, Any]:
        """加载 Dataset 元数据"""
        meta_path = self.base_dir / "dataset_metadata.json"
        if meta_path.exists():
            with open(meta_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def get_stats(self) -> Dict[str, Any]:
        """获取存储统计"""
        episodes = self.list_episodes()
        total_size = sum(p.stat().st_size for p in self.base_dir.glob("*.parquet"))
        return {
            "num_episodes": len(episodes),
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "base_dir": str(self.base_dir),
        }


class ParquetStreamWriter:
    """流式 Parquet 写入器

    适用于大数据量的增量写入场景。
    """

    def __init__(self, output_path: str, batch_size: int = 1000):
        self.output_path = Path(output_path)
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        self.batch_size = batch_size
        self._buffer: List[Dict[str, Any]] = []
        self._writer = None

    def write_row(self, row: Dict[str, Any]) -> None:
        """写入一行数据"""
        self._buffer.append(row)
        if len(self._buffer) >= self.batch_size:
            self._flush()

    def _flush(self) -> None:
        if not self._buffer:
            return

        try:
            import pandas as pd
        except ImportError:
            raise RuntimeError("pandas is required")

        df = pd.DataFrame(self._buffer)

        if self._writer is None:
            self._writer = pd.DataFrame()
            df.to_parquet(str(self.output_path), engine="pyarrow", index=False)
        else:
            existing = pd.read_parquet(str(self.output_path))
            combined = pd.concat([existing, df], ignore_index=True)
            combined.to_parquet(str(self.output_path), engine="pyarrow", index=False)

        self._buffer.clear()

    def close(self) -> None:
        self._flush()
