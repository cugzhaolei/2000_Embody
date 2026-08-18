"""
自研轻量 JPG 视频编码器（零额外依赖）
======================================
用 Pillow 将一组图像帧合成为 MP4（采用 imageio 或 opencv 时自动回退），
读帧 + 写帧编解码复用，避免在纯参考环境下引入大体积依赖。

若安装了 imageio/opencv，优先使用更高效的编码器。
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Iterable, Optional

import numpy as np


class FrameWriter:
    """把图像帧序列写入视频 / GIF 的抽象 Writer。

    支持两种后端:
      - "gif":  Pillow 自带，零依赖，文件较大（默认）
      - "mp4":  需要 imageio-ffmpeg，文件小
      - "png":  直接落盘逐帧 PNG（视觉审计友好）
    """

    def __init__(
        self,
        out_path: str,
        backend: str = "gif",
        fps: int = 10,
        size: Optional[tuple] = None,
    ):
        self.out_path = Path(out_path)
        self.out_path.parent.mkdir(parents=True, exist_ok=True)
        self.backend = backend
        self.fps = fps
        self.size = size
        self._frames: list = []
        self._writer = None
        self._png_dir = None

    def write(self, image: np.ndarray):
        arr = np.asarray(image).astype(np.uint8)
        if arr.shape[-1] == 4:
            arr = arr[:, :, :3]
        if arr.ndim != 3:
            arr = np.stack([arr] * 3, axis=-1)
        if self.size is not None:
            from PIL import Image
            arr = np.array(Image.fromarray(arr).resize(self.size))

        if self.backend == "png":
            if self._png_dir is None:
                self._png_dir = self.out_path.with_suffix("")
                self._png_dir.mkdir(parents=True, exist_ok=True)
            from PIL import Image
            Image.fromarray(arr).save(self._png_dir / f"frame_{len(self._frames):06d}.png")
        else:
            self._frames.append(arr)

    def close(self):
        if self.backend == "png":
            return
        if not self._frames:
            # 无帧时仍生成空文件占位
            self.out_path.touch()
            return
        try:
            if self.backend == "mp4":
                self._write_mp4()
            else:
                self._write_gif()
        except ImportError:
            # 后端缺失时回退 GIF
            self._write_gif()
        except Exception as exc:
            print(f"[FrameWriter] 编码失败回退 GIF: {exc}")
            self._write_gif()

    def _write_gif(self):
        from PIL import Image
        frames = [Image.fromarray(a) for a in self._frames]
        frames[0].save(
            self.out_path,
            save_all=True,
            append_images=frames[1:],
            duration=1000.0 / self.fps,
            loop=0,
        )

    def _write_mp4(self):
        import imageio_ffmpeg  # noqa: F401  触发 ImportError 冒泡
        import imageio
        writer = imageio.get_writer(
            str(self.out_path), fps=self.fps, codec="libx264", quality=8
        )
        for a in self._frames:
            writer.append_data(a)
        writer.close()


def save_video(
    frames: Iterable[np.ndarray],
    out_path: str,
    fps: int = 10,
    backend: str = "gif",
    size: Optional[tuple] = None,
) -> str:
    """便捷函数：将帧序列存为视频。"""
    w = FrameWriter(out_path, backend=backend, fps=fps, size=size)
    for f in frames:
        w.write(f)
    w.close()
    return str(out_path)


def read_frames(
    video_path: str,
    max_frames: Optional[int] = None,
) -> list:
    """读取视频帧（GIF/MP4 均可，Pillow/imageio 读取）。"""
    path = Path(video_path)
    try:
        import imageio
        reader = imageio.get_reader(str(path))
        frames = [np.array(f) for f in reader]
        reader.close()
    except (ImportError, Exception):
        from PIL import Image
        img = Image.open(str(path))
        frames = []
        for i in range(getattr(img, "n_frames", 1)):
            img.seek(i)
            frames.append(np.array(img.convert("RGB")))
    if max_frames is not None:
        frames = frames[:max_frames]
    return frames