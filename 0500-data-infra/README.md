# 0500-data-infra — 具身数据基础设施

机器人具身多模态数据采集、处理与管理平台。按"具身数据基础设施工程师"岗位职责搭建，
覆盖从设备采集、标准定义、后处理、格式转换、版本管理、自动质检到数据飞轮的完整链路。

## 快速开始

```sh
# 环境要求：Python 3.10+，numpy；Web 平台另需 fastapi + uvicorn

# 1) 冒烟测试（验证 ego / annotation / tracking / flywheel 四大模块闭环）
python 0500-data-infra/scripts/smoke_new_modules.py

# 2) 启动 Web 可视化平台（自带演示数据）
python 0500-data-infra/web/run_web.py --host 0.0.0.0 --port 8000
# 浏览器打开 http://127.0.0.1:8000
```

## 模块结构（对应职责）

| 模块 | 职责 | 关键文件 |
|---|---|---|
| `schemas/` | 多模态数据标准：13 种模态类型、传感器配置、时间同步参数 | `multimodal.py`、`dataset.py` |
| `collectors/` | 数据采集：RGB/深度/触觉/机器人状态 + 多设备同步管理 | `sync_manager.py`、`rgb_camera.py` |
| `pipeline/` | 后处理流水线：视频编解码、轨迹处理、清洗、Episode 切分、坐标变换、质检 | `video_codec.py`、`episode.py`、`cleaning.py` |
| `conversion/` | 格式转换：LeRobot / ROS2 Bag / MCAP / HF-LeRobot | `lerobot_converter.py`、`rosbag_converter.py`、`mcap_converter.py` |
| `storage/` | 存储：Parquet / HDF5 + 元数据管理 | `parquet_store.py`、`hdf5_store.py`、`metadata.py` |
| `versioning/` | Dataset 版本管理与快照 | `dataset_version.py` |
| `quality/` | 自动质检：图像质量、时间同步误差、轨迹异常 | `image_quality.py`、`sync_check.py`、`trajectory_check.py` |
| `annotation/` | 自动标注：成败判定、轨迹跳变/模糊检测、元数据回写 | `auto_labeler.py` |
| `tracking/` | 训练评估关联管理：Job/模型/基准/实机评估/失败 Case 血缘追溯 | `registry.py`、`models.py` |
| `flywheel/` | 数据飞轮：实机失败回流、低成功率筛选、自动再训练闭环 | `loop.py`、`failure_ingest.py`、`curation.py` |
| `ego/` | Ego 长视频处理：有效片段切分、动作阶段识别、异常过滤、样本生成 | `video_segmenter.py`、`action_phase.py` |
| `web/` | FastAPI 可视化平台：Dashboard / Ego / Tracking / Flywheel / Annotation | `app.py`、`routers/`、`static/` |
| `configs/` | 全平台默认配置（schema/采集/流水线/存储/质量/飞轮等） | `default.yaml` |

## 配置

所有可调参数集中在 [`configs/default.yaml`](configs/default.yaml)：
时间同步容差、视频编解码、轨迹插值、Episode 切分规则、质检阈值、
飞轮回流参数（`max_per_task` / `low_success_threshold` / `verify_threshold`）等。

## Web API 一览

| 端点 | 方法 | 说明 |
|---|---|---|
| `/api/dashboard/summary` | GET | 平台聚合状态 |
| `/api/ego/demo` | POST | Ego 演示数据 |
| `/api/ego/process` | POST | Ego 视频处理 |
| `/api/annotation/label` | POST | 单 Episode 自动标注（`demo` 或 `eef_pose`） |
| `/api/tracking/models` `/jobs` `/benchmarks` `/evals` `/failures` | GET | 训练评估关联查询 |
| `/api/tracking/lineage/{model_id}` | GET | 模型血缘追溯 |
| `/api/tracking/low-success` | GET | 低成功率任务识别 |
| `/api/flywheel/state` `/history` | GET | 飞轮状态/历史 |
| `/api/flywheel/run` `/eval` | POST | 飞轮一轮 / 实机评估回灌 |

## 数据目录约定

- `data/`、`checkpoints/`、`so101_sim_output/`、`openvla/` 及 `**/.venv/` 不入库（见 `.gitignore`）；
- Web 演示数据在 `web/data/`（registry / versions 的 JSON 种子）。
