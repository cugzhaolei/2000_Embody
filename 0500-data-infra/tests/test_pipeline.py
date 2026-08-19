"""pipeline 模块单元测试：Episode 切分、轨迹处理、坐标变换。"""

import numpy as np
import pytest

from embodied_infra.pipeline.episode import EpisodeSplitConfig, EpisodeSegmenter, SplitMethod
from embodied_infra.pipeline.trajectory import TrajectoryConverter
from embodied_infra.pipeline.coordinate import CoordinateTransformer


# ---------- episode ----------

def _timestamps(n, fps=30.0, gap_at=None):
    ts = np.arange(n) / fps
    if gap_at is not None:
        ts[gap_at:] += 2.0  # 注入 2 秒间隙
    return ts


def test_episode_segment_by_time():
    """按固定时间窗口切分：250 步 @30Hz 用 10s 窗口 -> 约 5 段。"""
    seg = EpisodeSegmenter(EpisodeSplitConfig(min_episode_length=1))
    ts = _timestamps(250)
    episodes = seg.segment_by_time(ts, window_sec=2.0)
    assert len(episodes) >= 3
    for e in episodes:
        assert e.num_steps == e.end_idx - e.start_idx
        assert e.start_time <= e.end_time


def test_episode_segment_by_gap():
    """按时间间隙切分：注入 2s 间隙后分为 2 段。"""
    cfg = EpisodeSplitConfig(min_episode_length=1)
    seg = EpisodeSegmenter(cfg)
    ts = _timestamps(120, gap_at=60)
    episodes = seg.segment_by_gap(ts, gap_threshold_sec=0.5)
    assert len(episodes) == 2
    assert episodes[0].end_time < episodes[1].start_time


def test_episode_min_length_filter():
    """min_episode_length 过滤：太短的窗口不产出。"""
    cfg = EpisodeSplitConfig(min_episode_length=100)
    seg = EpisodeSegmenter(cfg)
    ts = _timestamps(200)  # 200 步 @30Hz = 6.6s
    episodes = seg.segment_by_time(ts, window_sec=2.0)
    # 每个窗口 60 步 < 100 -> 全部被过滤
    assert len(episodes) == 0


# ---------- trajectory ----------

def test_trajectory_resample():
    """重采样：30Hz -> 15Hz 步数减半。"""
    conv = TrajectoryConverter(action_dim=7)
    traj = np.random.randn(100, 7).astype(np.float64)
    resampled = conv.resample_trajectory(traj, 30.0, 15.0)
    assert resampled.shape[1] == 7
    assert resampled.shape[0] == 50  # 100 * 0.5


def test_trajectory_abs_rel_roundtrip():
    """绝对轨迹 <-> 相对增量 往返一致（带初始位姿）。"""
    conv = TrajectoryConverter(action_dim=6)
    abs_traj = np.random.randn(50, 6).astype(np.float64)
    rel = conv.absolute_to_relative(abs_traj)
    restored = conv.relative_to_absolute(rel, abs_traj[0])
    np.testing.assert_allclose(restored, abs_traj, atol=1e-9)


def test_trajectory_smooth():
    """滑动平均平滑：降低相邻帧差分。"""
    conv = TrajectoryConverter(action_dim=3)
    noisy = np.random.randn(200, 3).astype(np.float64)
    smooth = conv.smooth_trajectory(noisy, window_size=11)
    assert smooth.shape == noisy.shape
    assert np.abs(np.diff(smooth, axis=0)).mean() < np.abs(np.diff(noisy, axis=0)).mean()


# ---------- coordinate ----------

def test_coordinate_transform_identity():
    """单位变换保持坐标不变。"""
    t = CoordinateTransformer()
    t.set_transform("base", "tool", np.eye(4))
    mat = t.get_transform("base", "tool")
    assert mat is not None
    point = np.array([1.0, 2.0, 3.0, 1.0])
    out = mat.dot(point)
    np.testing.assert_allclose(out, point, atol=1e-9)


def test_coordinate_inverse_lookup():
    """反向查找：只存 base->tool 时查询 tool->base 自动求逆。"""
    t = CoordinateTransformer()
    t.set_transform("base", "tool", np.eye(4))
    inv = t.get_transform("tool", "base")
    assert inv is not None
    np.testing.assert_allclose(inv, np.eye(4), atol=1e-9)


def test_coordinate_chain():
    """链式变换：base->link + link->tool 复合出 base->tool。"""
    t = CoordinateTransformer()
    t.set_transform("base", "link", np.eye(4))
    t.set_transform("link", "tool", np.eye(4))
    mat = t.get_transform("base", "tool")
    assert mat is not None
    np.testing.assert_allclose(mat, np.eye(4), atol=1e-9)


def test_invert_transform():
    """矩阵求逆：T * T^-1 = I。"""
    rng = np.random.default_rng(0)
    rot = rng.normal(size=(3, 3))
    q, _ = np.linalg.qr(rot)
    T = np.eye(4)
    T[:3, :3] = q
    T[:3, 3] = np.array([0.1, 0.2, 0.3])
    inv = CoordinateTransformer.invert_transform(T)
    np.testing.assert_allclose(T.dot(inv), np.eye(4), atol=1e-9)
