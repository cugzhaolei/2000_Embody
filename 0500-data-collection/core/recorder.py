"""
Episode 录制器
==============
负责把「数据源」的输出（观测帧 + 动作）按固定 FPS 录制为一条完整 episode，
最终以 LeRobot 兼容格式落盘。

设计: Recorder 与 DataSource 解耦。
  - Recorder: 采样时钟、帧缓冲、action 记录、落盘
  - DataSource: 提供 current_frame() 与 step(action)

使用示例 (见 cli/collect.py):
  source = ScriptedSource(env, instruction="pick up the red block")
  recorder = EpisodeRecorder(source, out_root="./data/episodes", fps=10)
  recorder.run(episodes=5, steps_per_episode=120)
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np

from .schema import Frame, build_step_dict, validate_frame, decode_image_bytes
from .video import FrameWriter


def _camera_key(key: str) -> str:
    """把源字典键归一为相机名。

    "image" -> "wrist"；"image_wrist" -> "wrist"；"image_head" -> "head"。
    """
    name = key[len("image"):].lstrip("_")
    return name if name else "wrist"


@dataclass
class EpisodeRecord:
    """单条 episode 的内存表示（录制完成前暂存）。"""
    instruction: str = ""
    steps: List[Dict] = field(default_factory=list)
    frames: List[Frame] = field(default_factory=list)
    started_at: float = 0.0
    t0: float = 0.0

    @property
    def num_steps(self) -> int:
        return len(self.steps)

    @property
    def duration(self) -> float:
        return (self.steps[-1]["timestamp"] - self.steps[0]["timestamp"]) if len(self.steps) > 1 else 0.0


class EpisodeRecorder:
    """录制控制器。

    Args:
        source: 数据源（需实现 frame() 与 step(action)）
        out_root: 输出根目录
        fps: 采样帧率
        action_dim: 动作维度
        video_backend: "gif" | "mp4" | "png" | "none"
        save_episode_png: 是否额外把视频抽帧 PNG 存档
    """

    def __init__(
        self,
        source,
        out_root: str = "./data/episodes",
        fps: int = 10,
        action_dim: int = 7,
        video_backend: str = "gif",
        min_episode_len: int = 4,
    ):
        self.source = source
        self.out_root = Path(out_root)
        self.fps = fps
        self.action_dim = action_dim
        self.video_backend = video_backend
        self.min_episode_len = min_episode_len
        self.dt = 1.0 / max(fps, 1)

        # 采集会话元信息
        self.meta: Dict = {
            "schema_version": "lerobot.1",
            "fps": fps,
            "action_dim": action_dim,
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "episodes": [],
        }
        self._episode_idx = 0

    def create_episode(self, instruction: str = "", **kwargs) -> EpisodeRecord:
        """开始新 episode（重置数据源场景）。"""
        self.source.reset(**kwargs)
        ep = EpisodeRecord(instruction=instruction)
        ep.started_at = time.time()
        ep.t0 = ep.started_at
        return ep

    @staticmethod
    def _parse_obs(obs) -> Frame:
        """把数据源返回的 dict 观测解析为 Frame。

        支持两种形式:
          - dict: {"image_wrist": ndarray, "state": ndarray, "joint_positions": ndarray}
          - 裸 ndarray: 视为 wrist 相机图
        """
        images: Dict[str, np.ndarray] = {}
        state = np.zeros(0, dtype=np.float32)

        if isinstance(obs, dict):
            for k, v in obs.items():
                if v is None:
                    continue
                if k.startswith("image"):
                    cam = _camera_key(k)
                    if isinstance(v, (dict, str)):
                        continue  # 视频文件夹引用，跳过（视频编码阶段补帧）
                    images[cam] = np.asarray(v)
                elif k in ("state", "joint_positions"):
                    state = np.asarray(v, dtype=np.float32).reshape(-1)
                else:
                    pass  # 其余字段忽略
        elif obs is not None:
            images["wrist"] = np.asarray(obs)

        return Frame(images=images, state=state)

    @staticmethod
    def _parse_obs(obs) -> Frame:
        """把数据源返回的 dict 观测解析为 Frame。

        支持两种形式:
          - dict: {"image_wrist": ndarray, "state": ndarray, "joint_positions": ndarray}
          - 裸 ndarray: 视为 wrist 相机图
        """
        images: Dict[str, np.ndarray] = {}
        state = np.zeros(0, dtype=np.float32)

        if isinstance(obs, dict):
            for k, v in obs.items():
                if v is None:
                    continue
                if k.startswith("image"):
                    cam = _camera_key(k)
                    if isinstance(v, (dict, str)):
                        continue  # 视频文件夹引用，跳过（视频编码阶段补帧）
                    images[cam] = np.asarray(v)
                elif k in ("state", "joint_positions"):
                    state = np.asarray(v, dtype=np.float32).reshape(-1)
                else:
                    pass  # 其余字段忽略
        elif obs is not None:
            images["wrist"] = np.asarray(obs)

        return Frame(images=images, state=state)

    def record_step(self, ep: EpisodeRecord, action: np.ndarray) -> bool:
        """录制一步（帧采样 + 动作）。返回是否录到有效帧。"""
        frame = self._parse_obs(self.source.frame())
        frame.timestamp = time.time() - ep.t0
        ep.frames.append(frame)

        # 录像走原始帧（内存），落盘步骤走 JPEG bytes（parquet 友好）
        step = build_step_dict(
            frame, np.asarray(action, dtype=np.float32),
            ep.instruction, ep.num_steps,
            encode_jpeg=True,
        )
        ep.steps.append(step)
        return True

    def finish_episode(self, ep: EpisodeRecord, **info) -> Optional[int]:
        """结束 episode 并落盘。返回 episode 索引，失败返回 None。"""
        if ep.num_steps < self.min_episode_len:
            print(f"[recorder] 丢弃过短 episode ({ep.num_steps} < {self.min_episode_len})")
            return None

        idx = self._episode_idx
        self._episode_idx += 1

        ep_dir = self.out_root / "data" / f"episode_{idx:06d}"
        ep_dir.mkdir(parents=True, exist_ok=True)

        # 1) 落盘步骤 parquet/JSON
        self._write_steps(ep, ep_dir, idx)

        # 2) 视频存档（取帧率最高的相机视角）
        video_path = None
        if self.video_backend != "none" and ep.frames:
            cam = self._pick_video_camera(ep.frames)
            frames = [f.images.get(cam, np.zeros((64, 64, 3), dtype=np.uint8)) for f in ep.frames]
            if self.video_backend == "gif":
                video_path = self.out_root / "data" / f"episode_{idx:06d}.gif"
            elif self.video_backend == "mp4":
                video_path = self.out_root / "data" / f"episode_{idx:06d}.mp4"
            else:
                video_path = self.out_root / "data" / f"episode_{idx:06d}"
            writer = FrameWriter(str(video_path), backend=self.video_backend, fps=self.fps)
            for f in frames:
                writer.write(f)
            writer.close()
            if not frames:
                video_path = None

        # 3) episode 元数据
        ep_meta = {
            "episode_index": idx,
            "num_steps": ep.num_steps,
            "task": ep.instruction,
            "duration_sec": round(ep.duration, 3),
            "video": str(video_path) if video_path else None,
            **info,
        }
        self.meta["episodes"].append(ep_meta)
        self._write_session_meta()
        return idx

    def _write_steps(self, ep: EpisodeRecord, ep_dir: Path, idx: int):
        """步骤数据落盘。优先 pandas+pyarrow（parquet），缺失则 JSON。

        JSON 路径会把图像 bytes 用 base64 编码，保证可逆读取。
        """
        rows = ep.steps
        try:
            import pandas as pd
            df = pd.DataFrame(rows)
            df.to_parquet(ep_dir / "steps.parquet", index=False)
        except ImportError:
            self._write_steps_json(ep_dir, rows)
        except Exception as exc:
            print(f"[recorder] parquet 写入失败，回退 JSON: {exc}")
            self._write_steps_json(ep_dir, rows)

    @staticmethod
    def _write_steps_json(ep_dir: Path, rows: List[Dict]):
        import base64
        import numpy as _np

        def _default(o):
            if isinstance(o, (_np.ndarray,)):
                return o.tolist()
            if isinstance(o, (_np.generic,)):
                return o.item()
            if isinstance(o, (bytes, bytearray, memoryview)):
                return base64.b64encode(bytes(o)).decode("ascii")
            return str(o)

        # 所有可能被 pandas 展开为 float 的字段已在 parquet 路径处理；
        # JSON 下把图像 bytes 统一 base64，state/action 转 list
        clean = []
        for r in rows:
            clean.append({k: v for k, v in r.items()})
        with open(ep_dir / "steps.json", "w", encoding="utf-8") as f:
            json.dump(clean, f, ensure_ascii=False, default=_default)

    @staticmethod
    def _pick_video_camera(frames: List[Frame]) -> str:
        """选择帧数最多、尺寸最稳定的相机视角。"""
        counts: Dict[str, int] = {}
        for f in frames:
            for cam in f.images:
                counts[cam] = counts.get(cam, 0) + 1
        if not counts:
            return ""
        # 出镜率最高的相机
        return max(counts, key=counts.get)

    def _write_session_meta(self):
        meta_path = self.out_root / "meta" / "info.json"
        meta_path.parent.mkdir(parents=True, exist_ok=True)
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(self.meta, f, indent=2, ensure_ascii=False)

    def export_summary(self) -> Dict:
        """导出最终统计信息（供 cli/stats 使用）。"""
        return {
            "num_episodes": len(self.meta["episodes"]),
            "total_steps": sum(e["num_steps"] for e in self.meta["episodes"]),
            "out_root": str(self.out_root),
        }