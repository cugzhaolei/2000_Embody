"""quality + annotation + versioning 模块单元测试。"""

import numpy as np
import pytest

from embodied_infra.quality.image_quality import ImageQualityChecker
from embodied_infra.quality.sync_check import SyncChecker
from embodied_infra.quality.trajectory_check import TrajectoryChecker
from embodied_infra.annotation.auto_labeler import AutoLabeler
from embodied_infra.versioning.dataset_version import DatasetVersionManager
from embodied_infra.schemas.dataset import EpisodeMetadata


# ---------- quality/image ----------

def test_image_quality_clear_frame():
    """清晰帧：Laplacian 方差（blur 评分）高，亮度正常。"""
    checker = ImageQualityChecker()
    frame = np.full((64, 64, 3), 128, dtype=np.uint8)
    frame[10:50, 10:50] = 200  # 有对比度
    report = checker.check_frame(frame)
    assert report["blur"] > 0  # 有边缘 -> 方差 > 0
    assert 10 <= report["brightness"] <= 245
    assert report["contrast"] >= 0


def test_image_quality_blur_detection():
    """模糊帧：纯色帧 Laplacian 方差接近 0（比清晰帧低）。"""
    checker = ImageQualityChecker()
    sharp = np.random.default_rng(0).integers(0, 255, (64, 64, 3), dtype=np.uint8)
    flat = np.full((64, 64, 3), 100, dtype=np.uint8)  # 全平 -> 无边缘
    s = checker.check_frame(sharp)
    f = checker.check_frame(flat)
    assert f["blur"] < s["blur"]
    assert f["blur"] < 1.0  # 纯色帧方差趋零


def test_occlusion_detection():
    """遮挡检测：全黑帧被判定为遮挡（返回 np.bool_，用 bool() 包装）。"""
    black = np.zeros((64, 64, 3), dtype=np.uint8)
    assert bool(ImageQualityChecker.detect_camera_occlusion(black, threshold=0.8)) is True
    noise = np.random.default_rng(1).integers(0, 255, (64, 64, 3), dtype=np.uint8)
    assert bool(ImageQualityChecker.detect_camera_occlusion(noise, threshold=0.8)) is False


# ---------- quality/sync ----------

def test_sync_check_dropped_frames():
    """丢帧检测：双传感器中缺失时间戳的序列被识别（按超阈间隔计数）。"""
    checker = SyncChecker()
    ts1 = np.arange(100) / 30.0
    ts2 = np.arange(100) / 30.0
    ts2 = np.delete(ts2, [30, 31])  # 丢掉 2 帧 -> 产生 1 个 2 帧间隔
    result = checker.check_sync({"sensor_a": ts1, "sensor_b": ts2})
    assert result.dropped_frames.get("sensor_b", 0) >= 1


def test_sync_check_pair_error():
    """双传感器同步误差：偏移超过容差被记录到 issues。"""
    checker = SyncChecker(max_sync_error_ms=5.0)
    ts1 = np.arange(100) / 30.0
    ts2 = ts1 + 0.02  # 20ms 偏移
    result = checker.check_sync({"a": ts1, "b": ts2})
    assert result.sensor_pairs  # 有传感器对
    assert any("Sync error" in i for i in result.issues)


def test_sync_check_frequency():
    """频率稳定性：返回 dict，稳定 30Hz 序列 stable=True。"""
    checker = SyncChecker(expected_freq=30.0)
    stable = np.arange(100) / 30.0
    report = checker.check_frequency_stability(stable)
    assert report["stable"] is True
    assert report["avg_freq"] == pytest.approx(30.0)


# ---------- quality/trajectory ----------

def test_trajectory_check_jumps():
    """轨迹跳变检测：注入大跳变应被计数。"""
    checker = TrajectoryChecker(max_position_jump=0.05)
    traj = np.zeros((100, 6))
    traj[:, 0] = np.linspace(0, 1.0, 100)
    traj[50:, 0] += 5.0  # 跳变
    result = checker.check(traj)
    assert result.jump_count >= 1
    assert not result.success


def test_trajectory_check_smooth_ok():
    """平滑轨迹无异常。"""
    checker = TrajectoryChecker(max_position_jump=0.05, max_velocity=2.0)
    traj = np.zeros((100, 6))
    traj[:, 0] = np.linspace(0, 1.0, 100)  # 匀速平滑
    result = checker.check(traj)
    assert result.jump_count == 0
    assert result.velocity_violations == 0
    assert result.success


# ---------- annotation ----------

def test_auto_labeler_success():
    """自动标注：平滑轨迹标记为成功。"""
    labeler = AutoLabeler()
    T = 100
    good = np.zeros((T, 6))
    good[:, 0] = np.linspace(0, 1.5, T)
    result = labeler.label_episode({"eef_pose": good}, "ep_good")
    assert result.labels["success"] is True


def test_auto_labeler_failure_jump():
    """自动标注：跳变轨迹标记为失败并给出原因。"""
    labeler = AutoLabeler()
    T = 100
    bad = np.zeros((T, 6))
    bad[:, 0] = np.linspace(0, 1.5, T)
    bad[50:, 0] += 0.5
    result = labeler.label_episode({"eef_pose": bad}, "ep_bad")
    assert result.labels["success"] is False
    assert len(result.reasons) >= 1


# ---------- versioning ----------

def test_version_manager_flow(tmp_path):
    """版本管理：创建/查询/列出版本。"""
    vm = DatasetVersionManager(str(tmp_path / "versions"))
    ep = EpisodeMetadata(episode_id="ep_1", task_name="pick_cup", num_steps=100, success=True)
    vm.create_version("v1", [ep], description="initial")
    vm.create_version("v2", [ep], description="second")

    assert vm.get_current_version().version == "v2"
    assert vm.get_version("v1").description == "initial"
    assert len(vm.list_versions()) == 2
