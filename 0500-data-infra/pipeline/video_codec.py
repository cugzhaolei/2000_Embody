"""
视频编解码模块
=============
支持 FFmpeg / PyAV / OpenCV 进行 H.264/H.265/AV1/MJPEG 编解码。
"""

import io
import time
from pathlib import Path
from typing import Any, BinaryIO, Generator, List, Optional, Tuple, Union

import numpy as np


class VideoEncoder:
    """视频编码器

    支持格式: H.264, H.265, MJPEG
    支持后端: FFmpeg (subprocess), PyAV, OpenCV
    """

    def __init__(
        self,
        codec: str = "h264",
        fps: float = 30.0,
        quality: int = 23,  # CRF 值 (0=lossless, 23=default, 51=worst)
        pixel_format: str = "yuv420p",
        backend: str = "ffmpeg",  # "ffmpeg" | "pyav" | "opencv"
    ):
        self.codec = codec
        self.fps = fps
        self.quality = quality
        self.pixel_format = pixel_format
        self.backend = backend
        self._process = None
        self._container = None
        self._stream = None

    def open(self, output_path: str, width: int, height: int) -> None:
        """打开编码器"""
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        if self.backend == "ffmpeg":
            self._open_ffmpeg(output_path, width, height)
        elif self.backend == "pyav":
            self._open_pyav(output_path, width, height)
        elif self.backend == "opencv":
            self._open_opencv(output_path, width, height)
        else:
            raise ValueError(f"Unknown backend: {self.backend}")

    def encode_frame(self, frame: np.ndarray) -> None:
        """编码一帧"""
        if self.backend == "ffmpeg":
            self._encode_ffmpeg(frame)
        elif self.backend == "pyav":
            self._encode_pyav(frame)
        elif self.backend == "opencv":
            self._encode_opencv(frame)

    def close(self) -> None:
        """关闭编码器"""
        if self.backend == "ffmpeg" and self._process:
            self._process.stdin.close()
            self._process.wait()
        elif self.backend == "pyav" and self._container:
            self._stream.close()
            self._container.close()
        elif self.backend == "opencv" and self._writer:
            self._writer.release()

    def _open_ffmpeg(self, output_path: str, width: int, height: int) -> None:
        import subprocess

        codec_map = {
            "h264": ["-c:v", "libx264", "-crf", str(self.quality)],
            "h265": ["-c:v", "libx265", "-crf", str(self.quality)],
            "mjpeg": ["-c:v", "mjpeg", "-q:v", str(max(1, 51 - self.quality))],
        }

        cmd = [
            "ffmpeg", "-y",
            "-f", "rawvideo",
            "-vcodec", "rawvideo",
            "-s", f"{width}x{height}",
            "-pix_fmt", "rgb24",
            "-r", str(self.fps),
            "-i", "-",
        ]
        cmd.extend(codec_map.get(self.codec, codec_map["h264"]))
        cmd.extend(["-pix_fmt", self.pixel_format, output_path])

        self._process = subprocess.Popen(
            cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )

    def _encode_ffmpeg(self, frame: np.ndarray) -> None:
        if self._process and self._process.stdin:
            self._process.stdin.write(frame.tobytes())

    def _open_pyav(self, output_path: str, width: int, height: int) -> None:
        import av

        self._container = av.open(output_path, mode="w")
        codec_name = {"h264": "h264", "h265": "hevc", "mjpeg": "mjpeg"}.get(self.codec, "h264")
        self._stream = self._container.add_stream(codec_name, rate=int(self.fps))
        self._stream.width = width
        self._stream.height = height
        self._stream.pix_fmt = "yuv420p"
        if hasattr(self._stream, "codec_context"):
            self._stream.codec_context.quality = self.quality

    def _encode_pyav(self, frame: np.ndarray) -> None:
        import av

        img = av.VideoFrame.from_ndarray(frame, format="rgb24")
        for packet in self._stream.encode(img):
            self._container.mux(packet)

    def _open_opencv(self, output_path: str, width: int, height: int) -> None:
        import cv2

        fourcc = {
            "h264": cv2.VideoWriter_fourcc(*"avc1"),
            "h265": cv2.VideoWriter_fourcc(*"hevc"),
            "mjpeg": cv2.VideoWriter_fourcc(*"MJPG"),
        }.get(self.codec, cv2.VideoWriter_fourcc(*"avc1"))

        self._writer = cv2.VideoWriter(output_path, fourcc, self.fps, (width, height))

    def _encode_opencv(self, frame: np.ndarray) -> None:
        import cv2

        frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        self._writer.write(frame_bgr)


class VideoDecoder:
    """视频解码器"""

    def __init__(self, backend: str = "ffmpeg"):
        self.backend = backend
        self._container = None

    def decode_frames(
        self, video_path: str, max_frames: int = -1
    ) -> Generator[Tuple[np.ndarray, float], None, None]:
        """解码视频帧，生成 (frame_rgb, timestamp)"""
        if self.backend == "pyav":
            yield from self._decode_pyav(video_path, max_frames)
        elif self.backend == "opencv":
            yield from self._decode_opencv(video_path, max_frames)
        else:
            yield from self._decode_ffmpeg(video_path, max_frames)

    def _decode_pyav(self, video_path: str, max_frames: int):
        import av

        container = av.open(video_path)
        stream = container.streams.video[0]
        time_base = float(stream.time_base)

        count = 0
        for frame in container.decode(stream):
            img = frame.to_ndarray(format="rgb24")
            timestamp = frame.pts * time_base
            yield img, timestamp
            count += 1
            if 0 < max_frames <= count:
                break
        container.close()

    def _decode_opencv(self, video_path: str, max_frames: int):
        import cv2

        cap = cv2.VideoCapture(video_path)
        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        count = 0

        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            timestamp = count / fps
            yield cv2.cvtColor(frame, cv2.COLOR_BGR2RGB), timestamp
            count += 1
            if 0 < max_frames <= count:
                break
        cap.release()

    def _decode_ffmpeg(self, video_path: str, max_frames: int):
        import subprocess

        cmd = [
            "ffmpeg", "-i", video_path,
            "-f", "rawvideo", "-pix_fmt", "rgb24",
            "-v", "quiet", "-",
        ]
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        # 需要知道视频尺寸，这里简化处理
        # 实际使用应先通过 ffprobe 获取分辨率
        width, height = 640, 480
        frame_size = width * height * 3
        count = 0

        while True:
            raw = proc.stdout.read(frame_size)
            if len(raw) < frame_size:
                break
            frame = np.frombuffer(raw, dtype=np.uint8).reshape((height, width, 3))
            yield frame, count / 30.0
            count += 1
            if 0 < max_frames <= count:
                break
        proc.terminate()


class VideoCodec:
    """统一视频编解码接口"""

    def __init__(self, backend: str = "ffmpeg"):
        self.backend = backend

    def encode(
        self,
        frames: List[np.ndarray],
        output_path: str,
        fps: float = 30.0,
        codec: str = "h264",
        quality: int = 23,
    ) -> str:
        """将帧序列编码为视频文件"""
        if not frames:
            raise ValueError("No frames to encode")

        h, w = frames[0].shape[:2]
        encoder = VideoEncoder(codec=codec, fps=fps, quality=quality, backend=self.backend)
        encoder.open(output_path, w, h)

        for frame in frames:
            if frame.ndim == 2:
                frame = np.stack([frame] * 3, axis=-1)
            encoder.encode_frame(frame)

        encoder.close()
        return output_path

    def decode(
        self, video_path: str, max_frames: int = -1
    ) -> List[Tuple[np.ndarray, float]]:
        """解码视频文件为帧列表"""
        decoder = VideoDecoder(backend=self.backend)
        return list(decoder.decode_frames(video_path, max_frames))

    def extract_clip(
        self,
        video_path: str,
        start_sec: float,
        end_sec: float,
        output_path: str,
    ) -> str:
        """提取视频片段"""
        import subprocess

        cmd = [
            "ffmpeg", "-y",
            "-i", video_path,
            "-ss", str(start_sec),
            "-to", str(end_sec),
            "-c", "copy",
            output_path,
        ]
        subprocess.run(cmd, capture_output=True)
        return output_path
