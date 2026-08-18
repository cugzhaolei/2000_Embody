"""
HDF5 存储层
===========
高性能二进制存储，适用于大规模图像、视频、连续动作数据。
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np


class HDF5Store:
    """HDF5 格式数据存储

    适用于: 大规模连续数据 (图像序列、深度图、高频传感器数据)
    特点: 高速随机访问、压缩存储、支持分块读取
    """

    def __init__(self, file_path: str):
        self.file_path = Path(file_path)
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        self._file = None

    def open(self, mode: str = "a") -> None:
        """打开 HDF5 文件"""
        try:
            import h5py
        except ImportError:
            raise RuntimeError("h5py is required for HDF5Store")
        self._file = h5py.File(str(self.file_path), mode)

    def close(self) -> None:
        """关闭 HDF5 文件"""
        if self._file is not None:
            self._file.close()
            self._file = None

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, *args):
        self.close()

    def save_episode(
        self,
        episode_id: str,
        data: Dict[str, np.ndarray],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """保存 Episode 数据到 HDF5"""
        if self._file is None:
            self.open()

        group = self._file.require_group(episode_id)

        for key, arr in data.items():
            if isinstance(arr, np.ndarray):
                # 使用压缩存储
                maxshape = (None,) + arr.shape[1:] if arr.ndim > 1 else (None,)
                dset = group.create_dataset(
                    key,
                    data=arr,
                    chunks=True,
                    maxshape=maxshape,
                    compression="gzip",
                    compression_opts=4,
                )
            elif isinstance(arr, list):
                group.attrs[key] = json.dumps(arr, ensure_ascii=False)
            else:
                group.attrs[key] = arr

        if metadata:
            meta_group = group.require_group("_metadata")
            for k, v in metadata.items():
                if isinstance(v, (str, int, float, bool)):
                    meta_group.attrs[k] = v
                else:
                    meta_group.attrs[k] = json.dumps(v, ensure_ascii=False, default=str)

    def load_episode(
        self, episode_id: str, keys: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """加载 Episode 数据"""
        if self._file is None:
            self.open()

        if episode_id not in self._file:
            raise KeyError(f"Episode '{episode_id}' not found in HDF5")

        group = self._file[episode_id]
        result = {}

        data_keys = keys or [k for k in group.keys() if k != "_metadata"]

        for key in data_keys:
            if key in group:
                dset = group[key]
                if isinstance(dset, h5py.Dataset):
                    result[key] = dset[:]
                elif isinstance(dset, h5py.Group):
                    result[key] = {
                        ak: av for ak, av in dset.attrs.items()
                    }

        # 加载元数据
        if "_metadata" in group:
            meta_group = group["_metadata"]
            result["_metadata"] = dict(meta_group.attrs)

        return result

    def list_episodes(self) -> List[str]:
        """列出所有 Episode"""
        if self._file is None:
            self.open()
        return sorted([
            k for k in self._file.keys()
            if isinstance(self._file[k], h5py.Group) and k != "_metadata"
        ])

    def get_episode_length(self, episode_id: str, key: str) -> int:
        """获取 Episode 中某数据的长度"""
        if self._file is None:
            self.open()
        return len(self._file[episode_id][key])

    def append_to_episode(
        self, episode_id: str, key: str, data: np.ndarray
    ) -> None:
        """向 Episode 追加数据 (适用于流式写入)"""
        if self._file is None:
            self.open()

        group = self._file[episode_id]
        if key not in group:
            maxshape = (None,) + data.shape[1:] if data.ndim > 1 else (None,)
            group.create_dataset(
                key, data=data, chunks=True, maxshape=maxshape,
                compression="gzip", compression_opts=4,
            )
        else:
            dset = group[key]
            old_len = len(dset)
            new_len = old_len + len(data)
            dset.resize(new_len, axis=0)
            dset[old_len:new_len] = data

    def save_metadata(self, metadata: Dict[str, Any]) -> None:
        """保存顶层元数据"""
        if self._file is None:
            self.open()
        meta_group = self._file.require_group("_global_metadata")
        for k, v in metadata.items():
            if isinstance(v, (str, int, float, bool)):
                meta_group.attrs[k] = v
            else:
                meta_group.attrs[k] = json.dumps(v, ensure_ascii=False, default=str)

    def get_stats(self) -> Dict[str, Any]:
        """获取 HDF5 文件统计"""
        if self._file is None:
            self.open()

        episodes = self.list_episodes()
        total_size = self.file_path.stat().st_size

        episode_info = {}
        for ep_id in episodes:
            group = self._file[ep_id]
            ep_keys = [k for k in group.keys() if k != "_metadata"]
            lengths = {}
            for k in ep_keys:
                if isinstance(group[k], h5py.Dataset):
                    lengths[k] = len(group[k])
            episode_info[ep_id] = lengths

        return {
            "num_episodes": len(episodes),
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "episodes": episode_info,
        }
