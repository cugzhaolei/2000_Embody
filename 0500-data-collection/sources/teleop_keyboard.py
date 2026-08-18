"""
键盘遥操作数据源
================
通过键盘控制移动增量，逐帧采样并执行，供人工示教录制专家轨迹。

按键映射（WSAD / 方向键平移，QE 升降，夹爪 Space/Enter）:
  i/J/K/L  或 方向键:     X/Y 平面移动
  U/O              上/下 (Z)
  Space / Enter:   夹爪开合
  R:               重置

说明: 纯终端环境较难实现 GUI，此处提供两层:
  1. 若 pygame 可用 → 实时窗口按键
  2. 否则 → 每步回车读取一行指令（测试友好）
"""

from __future__ import annotations

from typing import Dict, List, Optional

import numpy as np

from .base import DataSource


class KeyboardTeleopSource(DataSource):
    """键盘遥操作数据源（人工示教）。"""

    name = "keyboard"

    def __init__(
        self,
        env_source: DataSource,
        action_scale: float = 0.05,
        base_grip: float = 1.0,
        use_gui: bool = False,
    ):
        """
        Args:
            env_source: 底层环境数据源（MuJoCo / PyBullet / 真机）
            action_scale: 单键位移增量
            use_gui: 使用 pygame 窗口（True）或逐行输入（False）
        """
        self.env = env_source
        self.action_scale = action_scale
        self.grip = base_grip
        self.use_gui = use_gui

    def reset(self, **kwargs) -> Dict[str, np.ndarray]:
        return self.env.reset(**kwargs)

    def frame(self) -> Dict[str, np.ndarray]:
        return self.env.frame()

    def step(self, action: np.ndarray) -> None:
        self.env.step(action)

    def read_command(self) -> np.ndarray:
        """读取当前遥控动作增量（7维）。调试用，实际由 cli 调用。"""
        if self.use_gui:
            return self._read_gui()
        return self._read_stdin()

    def _read_stdin(self) -> np.ndarray:
        cmd = input(">>> 方向(wasd/方向键 移动, e/q 上下, g 夹爪, r 重置): ").strip().lower()
        delta = np.zeros(7, dtype=np.float32)
        if "w" in cmd or "j" in cmd:
            delta[1] += self.action_scale
        if "s" in cmd or "k" in cmd:
            delta[1] -= self.action_scale
        if "a" in cmd or "h" in cmd:
            delta[0] -= self.action_scale
        if "d" in cmd or "l" in cmd:
            delta[0] += self.action_scale
        if "e" in cmd or "u" in cmd:
            delta[2] += self.action_scale
        if "q" in cmd or "o" in cmd:
            delta[2] -= self.action_scale
        if "g" in cmd or " " in cmd:
            self.grip = 1.0 - self.grip
            delta[6] = self.grip - (1.0 - self.grip)  # 差值信号
        return delta

    def _read_gui(self) -> np.ndarray:
        import pygame
        pygame.init()
        screen = pygame.display.set_mode((320, 240))
        screen.fill((30, 30, 30))
        pygame.display.set_caption("Teleop")
        clock = pygame.time.Clock()
        delta = np.zeros(7, dtype=np.float32)
        for _ in range(60):
            for ev in pygame.event.get():
                if ev.type == pygame.KEYDOWN:
                    if ev.key in (pygame.K_w, pygame.K_UP):
                        delta[1] += self.action_scale
                    elif ev.key in (pygame.K_s, pygame.K_DOWN):
                        delta[1] -= self.action_scale
                    elif ev.key in (pygame.K_a, pygame.K_LEFT):
                        delta[0] -= self.action_scale
                    elif ev.key in (pygame.K_d, pygame.K_RIGHT):
                        delta[0] += self.action_scale
                    elif ev.key == pygame.K_e:
                        delta[2] += self.action_scale
                    elif ev.key == pygame.K_q:
                        delta[2] -= self.action_scale
                    elif ev.key in (pygame.K_SPACE, pygame.K_RETURN):
                        self.grip = 1.0 - self.grip
                        delta[6] = 1.0 if self.grip > 0.5 else -1.0
                    elif ev.key == pygame.K_r:
                        self.env.reset()
            clock.tick(60)
        pygame.quit()
        return delta

    def close(self):
        try:
            import pygame
            pygame.quit()
        except ImportError:
            pass
        self.env.close()