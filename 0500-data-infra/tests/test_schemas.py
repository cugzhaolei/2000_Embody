"""schemas 模块单元测试：多模态 Schema 定义与校验。"""

import pytest

from embodied_infra.schemas.multimodal import (
    ModalityType,
    SensorConfig,
    TimeSyncConfig,
    SensorSchema,
)


def test_modality_type_enum():
    """模态类型枚举完整覆盖 13 种模态。"""
    assert ModalityType.RGB.value == "rgb"
    assert ModalityType.DEPTH.value == "depth"
    assert ModalityType.TACTILE.value == "tactile"
    assert ModalityType.ROBOT_STATE.value == "robot_state"
    assert ModalityType.EEF_POSE.value == "eef_pose"
    assert ModalityType.JOINT_STATE.value == "joint_state"
    assert ModalityType.ACTION.value == "action"
    assert ModalityType.IMU.value == "imu"
    assert ModalityType.HAND_STATE.value == "hand_state"
    assert ModalityType.LANGUAGE.value == "language"
    assert ModalityType.GRIPPER.value == "gripper"
    assert ModalityType.FORCE_TORQUE.value == "force_torque"


def test_sensor_config_validation():
    """SensorConfig.validate()：缺 sensor_id 或非法频率抛错。"""
    with pytest.raises(ValueError):
        SensorConfig(name="cam", modality=ModalityType.RGB, sensor_id="").validate()
    with pytest.raises(ValueError):
        SensorConfig(name="cam", modality=ModalityType.RGB, sensor_id="c1", frequency_hz=0).validate()
    cfg = SensorConfig(name="cam", modality=ModalityType.RGB, sensor_id="c1")
    assert cfg.validate() is True


def test_time_sync_config():
    """时间同步配置：容差毫秒转秒。"""
    cfg = TimeSyncConfig(method="hardware", tolerance_ms=5.0)
    assert cfg.get_sync_threshold_sec() == pytest.approx(0.005)


def test_sensor_schema_add_and_query():
    """SensorSchema：添加/按模态筛选/按 id 查找。"""
    schema = SensorSchema(name="demo")
    schema.add_sensor(SensorConfig(name="cam", modality=ModalityType.RGB, sensor_id="c1", frequency_hz=30))
    schema.add_sensor(SensorConfig(name="depth", modality=ModalityType.DEPTH, sensor_id="d1", frequency_hz=30))
    schema.add_sensor(SensorConfig(name="robot", modality=ModalityType.JOINT_STATE, sensor_id="r1", frequency_hz=125))

    rbg_sensors = schema.get_sensors_by_modality(ModalityType.RGB)
    assert len(rbg_sensors) == 1
    assert rbg_sensors[0].sensor_id == "c1"

    assert schema.get_sensor_by_id("d1").name == "depth"
    assert schema.get_sensor_by_id("nope") is None

    modalities = schema.get_modalities()
    assert set(modalities) == {ModalityType.RGB, ModalityType.DEPTH, ModalityType.JOINT_STATE}


def test_sensor_schema_roundtrip_dict():
    """SensorSchema：to_dict / from_dict 往返一致。"""
    schema = SensorSchema(name="rt")
    schema.add_sensor(SensorConfig(name="cam", modality=ModalityType.RGB, sensor_id="c1", frequency_hz=30.0))
    d = schema.to_dict()
    restored = SensorSchema.from_dict(d)
    assert restored.name == "rt"
    assert len(restored.sensors) == 1
    assert restored.sensors[0].sensor_id == "c1"
