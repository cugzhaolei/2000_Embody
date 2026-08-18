# 0500-data-collection 具身数据采集解决方案

承接现有 `0200-vla-imitation`，提供一体化、可插拔的具身数据采集方案，
统一输出 **LeRobot 兼容格式**（`meta/*.parquet` + `data/episode_*.parquet`），
可直接用于 ACT / Diffusion Policy / VLA 训练。

## 模块结构

```
0500-data-collection/
├── core/            # 核心层：schema / recorder / video / utils / verify
├── sources/         # 数据源适配层：base / namespace factory / sim / teleop / ros2
├── store/           # 存储层：lerobot 迭代器 + local 兼容转换
├── cli/             # 命令行（collect / verify / stats / replay / visualize）
├── scripts/         # 演示与冒烟脚本（smoke_test.py）
├── config.py        # dataclass 配置（CollectionConfig / DatasetConfig）
├── requirements.txt
└── run.py           # 统一入口
```

## 快速开始

### 1. 安装依赖（按需，核心框架零依赖）

```bash
# 核心采集框架（仅需 numpy / Pillow）
pip install -r 0500-data-collection/requirements.txt

# 仿真采集（MuJoCo 已有二进制 wheel）
pip install mujoco

# LeRobot 格式审计/读取（可选）
pip install pandas pyarrow
```

### 2. 数据源

| 数据源 | 说明 | 命令 |
|--------|------|------|
| `scripted` | 脚本化专家政策（自动，复用 0200-vla-imitation ScriptedExpert） | `python run.py collect -s scripted` |
| `keyboard` | 键盘遥操作示教 | `python run.py collect -s keyboard` |
| `mujoco` | MuJoCo 仿真（复用 0200-vla-imitation mujoco_env） | `python run.py collect -s mujoco` |
| `pybullet` | PyBullet 仿真 | `python run.py collect -s pybullet` |
| `dummy` | 纯随机源（冒烟/链路验证） | `python run.py collect -s dummy` |
| `ros2` | 真实机器人（订阅 /joint_states 等） | `python run.py collect -s ros2` |

> 说明: 由于目录名以数字开头，统一用 `python run.py <command>` 调用
> （等价入口 `python cli/collect.py ...` 亦可）。

### 3. 采集

```bash
# 先进入本目录
cd 0500-data-collection

# 脚本化专家自动采集（MuJoCo 环境，无需 GPU）
python run.py collect -s mujoco -n 20 -T 120 -o ./demo_data --video gif

# 键盘遥操作（人工示教）
python run.py collect -s keyboard -t "pick up the red block"

# 零环境冒烟验证
python run.py collect -s dummy -n 2 -T 10 -o ./tmp --video none
```

### 4. 数据管理

```bash
# 校验数据完整性
python run.py verify -d ./demo_data

# 统计信息
python run.py stats -d ./demo_data

# 回放轨迹（转 GIF 或逐帧图）
python run.py replay -d ./demo_data -e 0 -o ./replay.gif
```

## 数据格式（LeRobot 兼容）

```
dataset/
├── meta/
│   ├── info.json           # 数据集元信息
│   └── episodes.parquet    # 轨迹索引
├── data/
│   ├── episode_000000.parquet   # 每条轨迹: 观测+动作+状态
│   └── episode_000000.mp4       # 第一视角视频（若启用了 video 记录）
├── videos/                 # 汇总视频文件
└── README.md               # 数据集说明
```

每条 episode 包含字段：

- 指令: `instruction`（语言任务描述）
- 观测: `observation.images.*`（单目/双目的 RGB 帧路径）、`observation.state`（关节位姿）
- 动作: `action`（末端增量/关节指令，7 维或 6 维，配置可调）
- 时间: `timestamp`、`frame_index`

## 与训练链路衔接

采集 -> `common/` 校验可视化 -> `0200-vla-imitation` 数据集读取:
`0500-data-collection.store.lerobot.LeRobotDatasetIterator` 的输出可直接喂给
`0200-vla-imitation/data/dataset.py` 的 `VLADataset`；此外
`0500-data-collection.store.local.convert_to_legacy` 可一键转换为旧版
`traj_*.json + frame_*.png` 格式。

```python
# 程序化读取采集数据
import sys
sys.path.insert(0, r"0500-data-collection")
from cli._bootstrap import register_package
register_package()
from embodied_data.store.lerobot import LeRobotDatasetIterator

it = LeRobotDatasetIterator("./demo_data", action_dim=7)
for sample in it:          # image / state / action / instruction / frame_index
    ...
```

## 后续扩展

- [ ] 多相机同步（手眼 + 第三视角）
- [ ] 真机力 / 力矩记录
- [ ] DAgger 在线交互式数据采集
- [ ] HuggingFace Hub 上传/下载