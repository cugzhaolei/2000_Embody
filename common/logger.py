"""
日志工具
========
统一日志管理，支持控制台输出和文件记录。
"""

import logging
import sys
from pathlib import Path
from typing import Optional


def setup_logger(
    name: str = "embody",
    level: int = logging.INFO,
    log_file: Optional[str] = None,
    fmt: Optional[str] = None,
) -> logging.Logger:
    """创建统一格式的 logger"""
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # 防止重复添加 handler
    if logger.handlers:
        return logger

    if fmt is None:
        fmt = "[%(asctime)s] %(levelname)s %(name)s | %(message)s"

    formatter = logging.Formatter(fmt, datefmt="%H:%M:%S")

    # 控制台 handler
    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(formatter)
    logger.addHandler(console)

    # 文件 handler
    if log_file is not None:
        Path(log_file).parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


class MetricLogger:
    """训练指标记录器"""

    def __init__(self, log_file: Optional[str] = None):
        self.metrics = {}
        self._log_file = log_file

    def log(self, key: str, value: float, step: int):
        if key not in self.metrics:
            self.metrics[key] = []
        self.metrics[key].append({"step": step, "value": value})

    def get(self, key: str) -> list:
        return self.metrics.get(key, [])

    def latest(self, key: str) -> Optional[float]:
        entries = self.get(key)
        return entries[-1]["value"] if entries else None

    def save(self, path: Optional[str] = None):
        import json
        save_path = path or self._log_file
        if save_path is None:
            return
        Path(save_path).parent.mkdir(parents=True, exist_ok=True)
        with open(save_path, "w") as f:
            json.dump(self.metrics, f, indent=2)
