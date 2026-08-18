# 具身智能全栈学习指南：从 OpenVLA 到 World Action Model

> **从 VLA 到世界动作模型，从仿真到真机部署，从 AI 到 AIoT 的完整学习路径**
>
> 最后更新：2026-06-01

---

## 目录

- [一、全景路线图](#一全景路线图)
- [二、阶段一：VLA 基础 — OpenVLA 入门](#二阶段一vla-基础--openvla-入门)
- [三、阶段二：VLA 进化 — OpenVLA-OFT 与 π₀](#三阶段二vla-进化--openvla-oft-与-π₀)
- [四、阶段三：仿真训练 — Isaac Sim 与 Isaac Lab](#四阶段三仿真训练--isaac-sim-与-isaac-lab)
- [五、阶段四：开源实战 — LeRobot 框架](#五阶段四开源实战--lerobot-框架)
- [六、阶段五：范式革命 — World Action Model](#六阶段五范式革命--world-action-model)
- [七、阶段六：NVIDIA 全栈 — Cosmos 与 GR00T](#七阶段六nvidia-全栈--cosmos-与-gr00t)
- [八、AIoT 与工业数字化延伸](#八aiot-与工业数字化延伸)
- [九、核心论文与资源索引](#九核心论文与资源索引)
- [十、学习时间线建议](#十学习时间线建议)

---

## 一、全景路线图

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     具身智能技术演进全景图                                │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  第一代：VLA (2024)                                                     │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐                          │
│  │ OpenVLA  │───→│  RT-2-X  │───→│  Octo    │   视觉+语言→动作         │
│  │ 7B, 自回归│    │ 55B, 闭源│    │ Diffusion│   自回归/扩散生成动作     │
│  └──────────┘    └──────────┘    └──────────┘                          │
│       │                                                                │
│       ▼ 推理慢、离散化损失、无物理理解                                   │
│                                                                         │
│  第二代：VLA+ (2025)                                                    │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐                          │
│  │OpenVLA-  │───→│  π₀/     │───→│  SmolVLA │   并行解码+动作分块      │
│  │  OFT     │    │ OpenPI   │    │  (LeRobot)│   连续动作+Flow Matching │
│  │ 26×加速  │    │ Flow Match│   │  轻量VLA  │                          │
│  └──────────┘    └──────────┘    └──────────┘                          │
│       │                                                                │
│       ▼ 仍不理解物理世界、泛化有限                                       │
│                                                                         │
│  第三代：World Action Model (2025-2026)                                 │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐                          │
│  │DreamZero │───→│  Motus/  │───→│  STI-WM  │   世界理解+动作生成       │
│  │ (NVIDIA) │    │Motubrain │    │ (眸深智能)│   统一时空建模            │
│  │ 14B WAM  │    │ 生数科技  │    │ 时空一体  │   物理一致性约束          │
│  └──────────┘    └──────────┘    └──────────┘                          │
│       │                                                                │
│       ▼ 需要大规模仿真数据+算力                                          │
│                                                                         │
│  基础设施层                                                             │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐                          │
│  │Isaac Sim │───→│  Cosmos  │───→│  Newton  │   仿真+世界模型+物理引擎  │
│  │ /Lab 3.0 │    │ Predict3 │    │ (物理引擎)│   数据工厂+训练+部署      │
│  └──────────┘    └──────────┘    └──────────┘                          │
│                                                                         │
│  开源工具层                                                             │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐                          │
│  │ LeRobot  │───→│  MuJoCo  │───→│  ROS 2   │   数据采集+训练+部署      │
│  │ (HF)     │    │Playground│    │  中间件   │   端到端工作流           │
│  └──────────┘    └──────────┘    └──────────┘                          │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 核心概念关系

| 概念 | 定义 | 与其他概念的关系 |
|------|------|-----------------|
| **VLA** | Vision-Language-Action，视觉+语言→动作的端到端模型 | WAM 的子集/前身，只做动作生成不理解世界 |
| **World Model** | 预测未来世界状态的模型 | WAM 的"世界理解"组件 |
| **WAM** | World Action Model，统一世界理解与动作生成 | VLA + World Model 的原生融合 |
| **Sim2Real** | 仿真到真实世界的迁移 | 所有方法都需要解决的核心问题 |
| **Action Chunking** | 一次预测多步动作 | VLA-OFT 和 π₀ 的关键技术 |
| **Flow Matching** | 基于流匹配的动作生成方法 | π₀ 的核心架构，替代自回归 |

---

## 二、阶段一：VLA 基础 — OpenVLA 入门

### 2.1 OpenVLA 是什么

OpenVLA 是第一个开源的视觉-语言-动作模型，7B 参数，基于 Llama-2 7B，在 970K 条机器人轨迹（Open X-Embodiment 数据集）上训练。

**核心架构：**
```
输入图像 (224×224)          输入指令 (文本)
      │                         │
      ▼                         ▼
┌──────────────┐         ┌──────────────┐
│  DINOv2 ViT-L │  concat │  Llama-2     │
│  (空间推理)    │────────→│  Tokenizer   │
│  1024维特征    │         └──────────────┘
└──────────────┘               │
┌──────────────┐               │
│  SigLIP ViT   │              │
│  (语义对齐)    │              │
│  1152维特征    │              │
└──────────────┘               │
      │                        │
      ▼                        ▼
  MLP 投影层 → 4096维 → Llama-2 7B 解码器
                           │
                           ▼
                    Action Tokenizer 解码
                           │
                           ▼
                    7-DoF 连续动作
              [dx, dy, dz, droll, dpitch, dyaw, gripper]
```

### 2.2 关键算法

| 算法 | 说明 |
|------|------|
| **Action Tokenizer** | 将连续动作离散化为 256 个 bin，映射到 LLM 词表末尾 256 个 token |
| **双视觉编码器融合** | DINOv2（空间推理）+ SigLIP（语义对齐）特征拼接 |
| **自回归动作生成** | Llama-2 逐 token 生成 7 个动作 token |
| **动作反归一化** | 用训练数据的 1%/99% 分位数将 [-1,1] 映射回真实物理单位 |
| **LoRA 微调** | 只训练 1.4% 参数，8× 计算量缩减 |

### 2.3 OpenVLA 的局限性

| 局限性 | 详细说明 |
|--------|----------|
| 仅支持单张图像输入 | 无法利用本体感知、历史帧、腕部相机 |
| 推理速度慢 | ~3-5 Hz，远不够高频控制（ALOHA 需要 50Hz） |
| 位置鲁棒性极弱 | 目标物体必须放在训练时见过的位置 |
| 离散化信息损失 | 256-bin 离散化丢失动作精度 |
| 不支持动作分块 | 每次只预测一步动作 |
| 不理解物理世界 | 纯模式匹配，无物理因果推理 |

### 2.4 实践步骤

```bash
# 1. 克隆项目
git clone https://github.com/princeton-vl/openvla.git
cd openvla

# 2. 创建环境（需要 GPU ≥16GB 显存才能运行完整模型）
conda create -n openvla python=3.10
conda activate openvla
pip install -r requirements-min.txt

# 3. 推理示例
python -c "
from transformers import AutoModelForVision2Seq, AutoProcessor
from PIL import Image

processor = AutoProcessor.from_pretrained('openvla/openvla-7b', trust_remote_code=True)
vla = AutoModelForVision2Seq.from_pretrained(
    'openvla/openvla-7b', torch_dtype=torch.bfloat16, trust_remote_code=True
).to('cuda:0')

image = Image.open('robot_camera.jpg')
prompt = 'In: What action should the robot take to pick up the cup?\nOut:'
inputs = processor(prompt, image).to('cuda:0', dtype=torch.bfloat16)
action = vla.predict_action(**inputs, unnorm_key='bridge_orig', do_sample=False)
print(action)  # [dx, dy, dz, droll, dpitch, dyaw, gripper]
"
```

### 2.5 关键资源

| 资源 | 链接 |
|------|------|
| OpenVLA GitHub | https://github.com/princeton-vl/openvla |
| OpenVLA 论文 | https://arxiv.org/abs/2406.09246 |
| OpenVLA 模型权重 | https://huggingface.co/openvla/openvla-7b |
| Open X-Embodiment 数据集 | https://robotics-transformer-x.github.io/ |
| 本地指南文件 | `C:\Users\admin\Desktop\dev\OpenVLA 程序运行与使用指南.md` |

---

## 三、阶段二：VLA 进化 — OpenVLA-OFT 与 π₀

### 3.1 OpenVLA-OFT：VLA 的优化微调方案 (2025.02)

OpenVLA-OFT 是 OpenVLA 一作 Moo Jin Kim 的改进版，解决了原始 OpenVLA 的三大核心问题。

**三大关键改进：**

| 改进 | 原始 OpenVLA | OpenVLA-OFT |
|------|-------------|-------------|
| 解码方式 | 自回归逐 token 生成 | **并行解码**（完形填空式一次性生成），推理提速 25-50× |
| 动作表示 | 256-bin 离散化 | **连续动作 + L1 回归**，精度更高 |
| 动作预测 | 每次预测一步 | **Action Chunking**（动作分块），一次预测多步 |

**LIBERO 基准结果：**
- OpenVLA：76.5% 平均成功率
- OpenVLA-OFT：**97.1%** 平均成功率
- 动作生成吞吐量提升 **26×**

```bash
# OpenVLA-OFT 使用
git clone https://github.com/moojink/openvla-oft.git
cd openvla-oft
# 微调示例
torchrun --standalone --nnodes 1 --nproc-per-node 1 vla-scripts/finetune.py \
  --vla_path "openvla/openvla-7b" \
  --data_root_dir /path/to/datasets \
  --dataset_name bridge_orig \
  --use_action_chunking \
  --use_l1_regression \
  --lora_rank 32
```

### 3.2 π₀ / OpenPI：Physical Intelligence (2025)

π₀ 是 Physical Intelligence 公司推出的 VLA 模型，采用 **Flow Matching** 架构。

**核心特点：**
- **Flow Matching**：非自回归的动作生成，比扩散模型更灵活
- **π₀-FAST**：基于 FAST action tokenizer 的自回归版本，速度更快
- **π₀.₇**：2026年4月发布，增强开放世界泛化能力，涌现能力
- 在 10,000+ 小时机器人数据上预训练

**π₀ 的架构优势：**
```
传统 VLA (自回归):  token1 → token2 → ... → token7  (慢，串行)
π₀ (Flow Matching): 噪声 ──→ 去噪 ──→ 动作  (快，并行)
```

```bash
# OpenPI 使用
git clone https://github.com/Physical-Intelligence/openpi.git
cd openpi
pip install -e .
# 训练和推理示例见项目 README
```

### 3.3 其他重要竞品

| 模型 | 特点 | 链接 |
|------|------|------|
| **RT-2-X** (Google) | 闭源 55B VLA，OpenVLA 的对标对象 | https://robotics-transformer-x.github.io/ |
| **Octo** (UC Berkeley) | 基于 Diffusion 的通用机器人策略 | https://octo-models.github.io/ |
| **FAST** (Physical Intelligence) | 新型 action tokenizer，推理提速 15× | 论文：https://arxiv.org/abs/2504.04468 |
| **RDT-1B** | 1B 参数的机器人扩散 Transformer | https://rdt-robotics.github.io/ |
| **Diffusion Policy** | 基于扩散的策略学习 | https://diffusion-policy.cs.columbia.edu/ |
| **BEAST** | B-spline 编码的动作序列分词器 | https://intuitive-robots.github.io/beast_website/ |

### 3.4 关键资源

| 资源 | 链接 |
|------|------|
| OpenVLA-OFT GitHub | https://github.com/moojink/openvla-oft |
| OpenVLA-OFT 论文 | https://arxiv.org/abs/2502.19645 |
| OpenVLA-OFT 项目页 | https://openvla-oft.github.io |
| OpenPI GitHub | https://github.com/Physical-Intelligence/openpi |
| π₀ 博客 | https://www.physicalintelligence.company/blog/pi0 |
| π₀.₇ 论文 | https://arxiv.org/abs/2604.15483 |

---

## 四、阶段三：仿真训练 — Isaac Sim 与 Isaac Lab

### 4.1 为什么需要仿真

具身智能的核心瓶颈是**数据**：
- LLM 有万亿 token 的互联网数据
- 机器人只有百万级的遥操作数据
- **差距：100,000×**

NVIDIA 的解决方案：**用仿真数据填补数据鸿沟**

```
数据金字塔：
    ┌─────────────┐
    │  真实世界数据  │  ← 少量、昂贵、24h/天
    │  (遥操作)     │
    ├─────────────┤
    │  合成数据     │  ← 无限、GPU生成、GB/GPU/天
    │  (仿真+世界模型)│
    ├─────────────┤
    │  网络数据     │  ← 海量、非结构化、EB/天
    │  (视频/文本)  │
    └─────────────┘
```

### 4.2 Isaac Sim vs Isaac Lab

| 特性 | Isaac Sim | Isaac Lab |
|------|-----------|-----------|
| 定位 | 物理仿真平台 | 机器人学习框架 |
| 基于 | NVIDIA Omniverse | Isaac Sim 之上 |
| 功能 | 高保真物理渲染、USD 场景构建 | RL/IL 训练、策略评估、部署 |
| 训练支持 | 需要自己写训练循环 | 内置 RSL-RL、RL-Games、SB3 等 |
| 当前版本 | 4.5+ | 2.3 (2025.09) / 3.0 (2026.03) |

### 4.3 Isaac Lab 核心工作流

```
1. Asset Input → 2. Configuration → 3. Task Design → 4. Gymnasium Register
                                                      │
5. Env Wrapping → 6. Training → 7. Testing → Deployment
```

**Isaac Lab 2.3 新特性：**
- 全身控制（WBC）+ 增强遥操作
- 支持 Meta Quest VR 和 Manus 手套数据采集
- 灵巧操作任务（DexPBT、Dextrah-RGB）
- 自动域随机化（ADR）+ 群体训练（PBT）
- 支持宇树 G1 机器人遥操作

**Isaac Lab 3.0 (GTC 2026)：**
- 与 GR00T N2 深度集成
- Newton 物理引擎集成
- 大规模并行训练优化

### 4.4 实践步骤

```bash
# 1. 安装 Isaac Sim（需要 NVIDIA GPU + Ubuntu）
# 从 NVIDIA Omniverse Launcher 安装

# 2. 安装 Isaac Lab
git clone https://github.com/isaac-sim/IsaacLab.git
cd IsaacLab
./isaaclab.sh --install

# 3. 训练一个四足机器人运动策略
./isaaclab.sh -p scripts/reinforcement_learning/rsl_rl/train.py \
  --task Isaac-Velocity-Flat-Unitree-Go1-v0 \
  --num_envs 4096 --headless

# 4. 导出策略
./isaaclab.sh -p scripts/reinforcement_learning/rsl_rl/play.py \
  --task Isaac-Velocity-Flat-Unitree-Go1-v0 \
  --num_envs 64

# 5. 部署到真实机器人
# 参考: https://docs.isaacsim.omniverse.nvidia.com/4.2.0/isaac_lab_tutorials/tutorial_policy_deployment.html
```

### 4.5 Newton 物理引擎

Newton 是 NVIDIA、Google DeepMind、Disney Research 联合开发的开源物理引擎：
- 基于 NVIDIA Warp 和 OpenUSD
- MuJoCo Warp 集成，比 MJX 快 152×（运动）和 313×（操作）
- 支持多物理求解器（MuJoCo Warp、Disney Kamino 等）
- GitHub: https://github.com/newton-physics/newton

### 4.6 关键资源

| 资源 | 链接 |
|------|------|
| Isaac Sim 文档 | https://docs.isaacsim.omniverse.nvidia.com/ |
| Isaac Lab GitHub | https://github.com/isaac-sim/IsaacLab |
| Isaac Lab 参考架构 | https://isaac-sim.github.io/IsaacLab/v2.0.1/source/refs/reference_architecture/index.html |
| Newton GitHub | https://github.com/newton-physics/newton |
| Isaac Lab 训练教程 | https://isaac-sim.github.io/IsaacLab/main/source/tutorials/03_envs/run_rl_training.html |
| 策略部署教程 | https://docs.isaacsim.omniverse.nvidia.com/4.2.0/isaac_lab_tutorials/tutorial_policy_deployment.html |

---

## 五、阶段四：开源实战 — LeRobot 框架

### 5.1 LeRobot 是什么

LeRobot 是 Hugging Face 推出的开源机器人学习平台，目标是**让普通人也能训练机器人**。

**三大核心优势：**
1. **硬件易用性**：SO-101 机械臂单臂 114 欧元，千元级成本
2. **算法模块化**：ACT、Diffusion Policy、TDMPC、SmolVLA 即插即用
3. **数据标准化**：LeRobotDataset 统一格式，Parquet + MP4 + JSONL

### 5.2 LeRobot 内置算法

| 算法 | 类型 | 说明 |
|------|------|------|
| **ACT** | 模仿学习 | Action-Conditioned Transformer，基于 Transformer 的条件动作生成 |
| **Diffusion Policy** | 模仿学习 | 通过扩散过程实现高鲁棒性动作预测 |
| **TDMPC** | 强化学习 | Transformer-based Deep Model Predictive Control |
| **SmolVLA** | VLA | Hugging Face 原创的高效视觉语言动作模型 |

### 5.3 LeRobot 工作流

```
Phase 1: 数据采集              Phase 2: 策略训练              Phase 3: 部署推理
┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐
│ 遥操作采集演示数据  │───→│ 选择算法+训练策略  │───→│ 部署到真实机器人   │
│ (SO-101/键盘/VR)  │    │ (ACT/DP/SmolVLA) │    │ (实时推理)        │
└──────────────────┘    └──────────────────┘    └──────────────────┘
```

### 5.4 实践步骤

```bash
# 1. 安装 LeRobot
conda create -y -n lerobot python=3.10
conda activate lerobot
conda install ffmpeg -c conda-forge
git clone https://github.com/huggingface/lerobot.git
cd lerobot
pip install -e .

# 2. 训练 Diffusion Policy（PushT 任务）
python lerobot/scripts/train.py \
  policy.type=diffusion \
  env.type=pusht \
  wandb.enable=false

# 3. 使用 HuggingFace 数据集
python -c "
from lerobot.common.datasets.lerobot_dataset import LeRobotDataset
dataset = LeRobotDataset('lerobot/pusht')
print(f'Episodes: {dataset.num_episodes}')
print(f'Frames: {dataset.num_frames}')
"

# 4. 采集自己的数据（需要 SO-101 机械臂）
python lerobot/scripts/control_robot.py \
  --robot.type=so100 \
  --control.type=teleoperate

# 5. 训练自定义策略
python lerobot/scripts/train.py \
  --dataset.path=your_dataset \
  --policy.type=act \
  --training.num_steps=5000
```

### 5.5 LeRobot 与 VLA 的关系

LeRobot 是一个**通用的机器人学习框架**，而 VLA 是其中的一种策略类型：
- LeRobot 支持传统 IL（ACT、Diffusion Policy）和 VLA（SmolVLA）
- LeRobot 提供数据采集、训练、评估、部署的完整工作流
- LeRobot 的数据格式与 Open X-Embodiment 兼容
- 可以在 LeRobot 中微调 π₀ 等大型 VLA 模型

### 5.6 关键资源

| 资源 | 链接 |
|------|------|
| LeRobot GitHub | https://github.com/huggingface/lerobot |
| LeRobot 文档 | https://huggingface.co/docs/lerobot |
| SO-101 机械臂 | https://github.com/TheRobotStudio/SO-ARM100 |
| LeRobot 数据集 | https://huggingface.co/datasets?other=LeRobot |
| AMD ROCm + LeRobot 教程 | https://rocm.blogs.amd.com/artificial-intelligence/rocm-lerobot/README.html |

---

## 六、阶段五：范式革命 — World Action Model

### 6.1 为什么 VLA 已死？

NVIDIA 机器人负责人 Jim Fan (2025年底)：
> "The next frontier of embodied AI is not more teleoperation data, not bigger VLA models — it's World Action Models."

**VLA 的 5 大致命缺陷：**

| 缺陷 | 说明 |
|------|------|
| **不理解物理** | 纯模式匹配，不知道"杯子被推倒水会流出来" |
| **数据饥渴** | 需要大量遥操作数据，成本极高 |
| **泛化灾难** | 换场景/物体/指令，成功率骤降 40%+ |
| **复合错误** | 单步误差累积，长时序任务崩溃 |
| **无法规划** | 只能反应式执行，无法做前瞻性推理 |

### 6.2 WAM 的核心思想

**World Action Model = World Model + Action Model 的原生融合**

```
传统 VLA:  视觉 + 语言 ──→ 动作         (不理解世界)
世界模型:  视觉 + 动作 ──→ 未来状态      (不生成动作)
WAM:       视觉 + 语言 ──→ 未来状态 + 动作  (同时理解和行动)
```

**WAM 的三大组件：**
1. **世界理解模块**：预测"如果我做动作 A，世界会变成什么样"
2. **动作生成模块**：基于世界理解，生成最优动作序列
3. **闭环纠偏模块**：实时观测 → 动态重规划 → 执行纠错

### 6.3 DreamZero (NVIDIA, 2026.02)

DreamZero 是 NVIDIA 发布的 14B 参数 World Action Model：
- **仅用 30 分钟遥操作数据**（55 条轨迹）实现零样本泛化
- 从未见过的机器人和物体也能操作
- 基于 Cosmos 世界模型构建
- 是 GR00T N2 的技术基础

**DreamZero 的惊人结果：**
- 遥操作花了 10 年没解决的问题，WAM 用 30 分钟解决了
- 零样本泛化到新机器人：成功率 2× 于传统 VLA

### 6.4 Motus / Motubrain (生数科技, 2025-2026)

- **Motus** (2025.12)：开源版，首次明确提出并验证 WAM 核心思想
- **Motubrain** (2026.05)：商业版，通用世界行动模型

**Motubrain 四大核心能力：**
1. **一脑多能**：任务越多，能力越强（正向 Scaling）
2. **UniDiffuser**：统一建模 video 和 action 两个连续模态
3. **三流 MoT 架构**：视频生成 + 动作 + 语言，融合预训练基座
4. **五种推理模式**：VLA / 世界模型 / 视频生成 / 逆动力学 / 视频动作联合预测

### 6.5 STI-WM (眸深智能, 2026)

STI-WM (Spatiotemporally Integrated World Model) 时空一体世界动作模型：
- **时空一体化建模**：统一编码空间结构 + 时间演化
- **物理一致性约束**：三维几何约束 + 动力学校验
- **端到端原生融合**：非 VLA + 世界模型拼接，而是原生统一
- **长时序规划**：百秒级任务推演 + 全局轨迹规划
- **闭环执行**：理解世界 → 推演未来 → 规划动作 → 执行纠错

### 6.6 Genie Envisioner (AgiBot, 2025)

AgiBot 推出的统一世界基础平台：
- **GE-Base**：大规模指令条件视频扩散模型
- **GE-Act**：世界动作模型，Flow Matching 解码器
- **GE-Sim**：动作条件神经仿真器
- **EWMBench**：标准化具身世界模型基准

### 6.7 WAM 技术路线对比

| 路线 | 代表 | 核心思路 | 优势 | 挑战 |
|------|------|----------|------|------|
| 统一世界模型 | Google RT, Octo | 一个模型覆盖感知到执行 | 架构统一 | 训练复杂 |
| 先想象再行动 | 视频生成+VLA | 先预测未来再指导动作 | 利用海量视频数据 | 想象≠可执行 |
| 同步推演+生成 | DreamZero, Motubrain | 边推演边行动 | 物理可行 | 计算量大 |

### 6.8 关键资源

| 资源 | 链接 |
|------|------|
| DreamZero 项目页 | https://dreamzero0.github.io/ |
| Motus/Motubrain | 生数科技 (https://www.shengshu.ai/) |
| Genie Envisioner 论文 | https://arxiv.org/abs/2508.05635 |
| Genie Envisioner 项目页 | https://genie-envisioner.github.io/ |
| WAM 综述博客 | https://zyxin.xyz/blog/2026-03/embodied-world-action-model/ |
| CSDN WAM 前沿解读 | https://blog.csdn.net/qq_73472828/article/details/160778091 |

---

## 七、阶段六：NVIDIA 全栈 — Cosmos 与 GR00T

### 7.1 NVIDIA 具身 AI 五层架构

```
┌─────────────────────────────────────────────┐
│  Layer 5: 机器人本体                          │
│  (Boston Dynamics, Unitree, Figure AI...)   │
├─────────────────────────────────────────────┤
│  Layer 4: 基础模型 (GR00T N2)                │
│  (World Action Model, VLA)                  │
├─────────────────────────────────────────────┤
│  Layer 3: 世界模型 (Cosmos)                   │
│  (Predict, Transfer, Reason)                │
├─────────────────────────────────────────────┤
│  Layer 2: 仿真平台 (Isaac Sim/Lab)           │
│  (物理仿真, 大规模并行训练)                    │
├─────────────────────────────────────────────┤
│  Layer 1: 算力基础设施 (DGX, Jetson)         │
│  (训练: DGX B200, 部署: Jetson Thor)         │
└─────────────────────────────────────────────┘
```

### 7.2 NVIDIA Cosmos

Cosmos 是 NVIDIA 的世界基础模型平台，包含三大核心模型：

| 模型 | 功能 | 说明 |
|------|------|------|
| **Cosmos Predict** | 世界生成 | 从文本/图像/视频生成 30s 预测视频，2B/14B 模型 |
| **Cosmos Transfer** | 仿真到真实转换 | 将仿真渲染转为照片级真实图像 |
| **Cosmos Reason** | 视觉推理 | VLM，链式思维推理，物理常识理解 |

**辅助工具：**
- **Cosmos Curator**：大规模数据过滤、标注、去重
- **Cosmos Dataset Search**：数据集查询和场景检索
- **Cosmos Evaluator**：生成视频质量评估
- **Cosmos RL**：后训练框架，可构建 VLA 模型

### 7.3 GR00T N2 (GTC 2026)

GR00T N2 是 NVIDIA 第二代人形机器人基础模型：
- 基于 DreamZero WAM 架构
- **零样本泛化成功率 2× 于传统 VLA**
- 双系统架构：System 2（推理规划）+ System 1（快速执行）
- 支持 Boston Dynamics、Unitree、Figure AI 等机器人

**GR00T 版本演进：**
| 版本 | 时间 | 特点 |
|------|------|------|
| GR00T N1 | 2025.03 | 首个开源人形机器人基础模型 |
| GR00T N1.5 | 2025.06 | GR00T-Dreams 合成数据训练，36h 完成 |
| GR00T N1.6 | 2025.09 | 增强环境适应 |
| GR00T N2 | 2026.03 | DreamZero WAM，2× 泛化提升 |

### 7.4 GR00T-Dreams 工作流

```
单张图像 + 语言指令
        │
        ▼
┌──────────────────┐
│ Cosmos Predict    │──→ 生成未来视频轨迹
└──────────────────┘
        │
        ▼
┌──────────────────┐
│ Cosmos Reason    │──→ 提取动作标签
└──────────────────┘
        │
        ▼
┌──────────────────┐
│ 合成轨迹数据       │──→ 大规模训练数据
└──────────────────┘
        │
        ▼
┌──────────────────┐
│ 训练 GR00T 模型   │──→ 部署到真实机器人
└──────────────────┘
```

### 7.5 关键资源

| 资源 | 链接 |
|------|------|
| Cosmos 官网 | https://www.nvidia.com/en-us/ai/cosmos/ |
| Cosmos Predict GitHub | https://github.com/nvidia-cosmos/cosmos-predict2.5 |
| Cosmos Transfer GitHub | https://github.com/nvidia-cosmos/cosmos-transfer2.5 |
| Cosmos Reason GitHub | https://github.com/nvidia-cosmos/cosmos-reason2 |
| Cosmos Cookbook | https://nvidia-cosmos.github.io/cosmos-cookbook/ |
| GR00T-Dreams GitHub | https://github.com/nvidia/gr00t-dreams |
| GR00T 开发者页面 | https://developer.nvidia.com/isaac/gr00t |
| GR00T Wiki | https://aiwiki.ai/wiki/isaac_gr00t |

---

## 八、AIoT 与工业数字化延伸

### 8.1 具身智能与 AIoT 的交汇

具身智能和 AIoT 在工业场景中深度融合：

```
┌─────────────────────────────────────────────────┐
│              工业具身智能系统                      │
├─────────────────────────────────────────────────┤
│                                                 │
│  感知层: 视觉传感器 + 力传感器 + IoT 设备          │
│    ↓                                            │
│  通信层: 5G/WiFi6 + 边缘计算 + MQTT/OPC-UA       │
│    ↓                                            │
│  智能层: VLA/WAM 模型 + 数字孪生 + 世界模型        │
│    ↓                                            │
│  执行层: 机械臂 + AGV + 人形机器人                 │
│    ↓                                            │
│  反馈层: 实时监控 + 质量检测 + 自适应优化           │
│                                                 │
└─────────────────────────────────────────────────┘
```

### 8.2 关键应用场景

| 场景 | 具身智能角色 | AIoT 角色 |
|------|-------------|----------|
| 智能制造 | 机器人操作 + 质检 | 设备互联 + 数据采集 |
| 智慧仓储 | 分拣 + 搬运机器人 | RFID + 库存管理 |
| 巡检维护 | 机器人巡检 + 故障诊断 | 传感器网络 + 预测性维护 |
| 协作装配 | 人机协作 + 灵巧操作 | 工位感知 + 安全监控 |
| 数字孪生 | 仿真训练 + 策略优化 | 实时同步 + 状态映射 |

### 8.3 机器视觉与工业检测

具身智能的视觉能力直接应用于工业检测：
- **缺陷检测**：VLA 的视觉编码器可用于产品表面缺陷识别
- **位姿估计**：6D 位姿估计用于机器人抓取定位
- **三维重建**：NeRF/3DGS 用于数字孪生场景构建
- **多模态融合**：RGB-D + 力觉 + 温度多传感器融合

### 8.4 AIoT 学习资源

| 资源 | 说明 | 链接 |
|------|------|------|
| AWS IoT Core | 云端 IoT 平台 | https://aws.amazon.com/iot/ |
| Azure IoT | 微软 IoT 平台 | https://azure.microsoft.com/en-us/overview/iot/ |
| EMQX | MQTT 消息 broker | https://www.emqx.io/ |
| ThingsBoard | 开源 IoT 平台 | https://thingsboard.io/ |
| OPC Foundation | 工业通信标准 | https://opcfoundation.org/ |
| MQTT 协议 | IoT 通信协议 | https://mqtt.org/ |

---

## 九、核心论文与资源索引

### 9.1 必读论文（按时间顺序）

| # | 论文 | 年份 | 核心贡献 | 链接 |
|---|------|------|----------|------|
| 1 | OpenVLA | 2024.06 | 首个开源 VLA | https://arxiv.org/abs/2406.09246 |
| 2 | RT-2-X | 2024 | 闭源 VLA 基线 | https://robotics-transformer-x.github.io/ |
| 3 | Octo | 2024 | 通用机器人策略 | https://arxiv.org/abs/2405.12213 |
| 4 | π₀ | 2024.10 | Flow Matching VLA | https://www.physicalintelligence.company/blog/pi0 |
| 5 | FAST | 2025.02 | 新型 action tokenizer | https://arxiv.org/abs/2504.04468 |
| 6 | OpenVLA-OFT | 2025.02 | 优化微调方案 | https://arxiv.org/abs/2502.19645 |
| 7 | Diffusion Policy | 2024 | 扩散策略学习 | https://arxiv.org/abs/2303.04137 |
| 8 | ACT | 2023 | Action Chunking with Transformers | https://tonyzhaozh.github.io/act/ |
| 9 | DreamZero | 2026.02 | World Action Model | https://dreamzero0.github.io/ |
| 10 | Genie Envisioner | 2025.08 | 统一世界基础平台 | https://arxiv.org/abs/2508.05635 |
| 11 | π₀.₇ | 2026.04 | 涌现能力的 VLA | https://arxiv.org/abs/2604.15483 |
| 12 | BEAST | 2025 | B-spline 动作分词器 | NeurIPS 2025 |
| 13 | 基于大模型的具身智能系统综述 | 2025.01 | 中文综述 | 自动化学报, 10.16383/j.aas.c240542 |

### 9.2 开源项目索引

| 项目 | 类型 | GitHub | 说明 |
|------|------|--------|------|
| OpenVLA | VLA | https://github.com/princeton-vl/openvla | 首个开源 VLA |
| OpenVLA-OFT | VLA+ | https://github.com/moojink/openvla-oft | 优化微调版 |
| OpenPI | VLA | https://github.com/Physical-Intelligence/openpi | π₀ 开源版 |
| LeRobot | 框架 | https://github.com/huggingface/lerobot | HF 机器人学习平台 |
| Isaac Lab | 仿真 | https://github.com/isaac-sim/IsaacLab | NVIDIA 机器人学习框架 |
| Newton | 物理 | https://github.com/newton-physics/newton | 开源物理引擎 |
| Cosmos Predict | 世界模型 | https://github.com/nvidia-cosmos/cosmos-predict2.5 | 世界生成模型 |
| Cosmos Transfer | 世界模型 | https://github.com/nvidia-cosmos/cosmos-transfer2.5 | 仿真到真实转换 |
| GR00T-Dreams | 数据生成 | https://github.com/nvidia/gr00t-dreams | 合成轨迹数据 |
| MuJoCo Playground | 仿真 | https://playground.mujoco.org/ | DeepMind 仿真平台 |
| Octo | 策略 | https://github.com/octo-models/octo | 通用机器人策略 |
| Diffusion Policy | 策略 | https://github.com/real-stanford/diffusion_policy | 扩散策略 |

### 9.3 数据集索引

| 数据集 | 规模 | 说明 | 链接 |
|--------|------|------|------|
| Open X-Embodiment | 970K 轨迹 | 22 种机器人，多任务 | https://robotics-transformer-x.github.io/ |
| BridgeData V2 | 24K 轨迹 | WidowX 机器人 | https://rail-berkeley.github.io/bridgedata/ |
| LIBERO | 130 任务 | 仿真基准 | https://libero-project.github.io/ |
| LeRobot Datasets | 多种 | HF 托管的机器人数据 | https://huggingface.co/datasets?other=LeRobot |
| DROID | 76K 轨迹 | 多机器人操作 | https://droid-dataset.github.io/ |

### 9.4 课程与教材

| 资源 | 类型 | 说明 | 链接 |
|------|------|------|------|
| Stanford CS231N | 课程 | 计算机视觉基础 | http://cs231n.stanford.edu/ |
| Stanford CS229 | 课程 | 机器学习基础 | https://cs229.stanford.edu/ |
| Berkeley CS285 | 课程 | 深度强化学习 | http://rail.eecs.berkeley.edu/deeprlcourse/ |
| Modern Robotics | 教材 | 机器人学基础 | http://hades.mech.northwestern.edu/index.php/Modern_Robotics |
| ROS 2 教程 | 教程 | 机器人操作系统 | https://docs.ros.org/en/humble/Tutorials.html |
| HuggingFace LeRobot 教程 | 教程 | 机器人学习实战 | https://huggingface.co/docs/lerobot |
| Isaac Lab 教程 | 教程 | 仿真训练实战 | https://isaac-sim.github.io/IsaacLab/main/source/tutorials/index.html |
| 具身智能机器人系统 | 教材 | 甘一鸣等，电子工业出版社 2024 | - |
| 具身智能学习路径 (CSDN) | 博客 | 2026 版全栈学习路径 | https://blog.csdn.net/hiwangwenbing/article/details/159208452 |

### 9.5 社区与资讯

| 平台 | 说明 | 链接 |
|------|------|------|
| HuggingFace | 模型/数据集/LeRobot | https://huggingface.co/ |
| NVIDIA Developer | Isaac/Cosmos 开发者资源 | https://developer.nvidia.com/ |
| Arxiv cs.RO | 机器人论文预印本 | https://arxiv.org/list/cs.RO/recent |
| Robotics Reddit | 机器人社区 | https://www.reddit.com/r/robotics/ |
| 知乎具身智能 | 中文社区 | 搜索"具身智能"话题 |
| 机器之心 | AI 资讯 | https://www.jiqizhixin.com/ |
| 量子位 | AI 资讯 | https://www.qbitai.com/ |

---

## 十、学习时间线建议

### 阶段一：基础筑基（1-3 个月）

**目标**：理解 VLA 原理，跑通 OpenVLA 演示

| 周 | 任务 | 产出 |
|----|------|------|
| 1-2 | 学习 PyTorch + Transformer 基础 | 能手写简单 Transformer |
| 3-4 | 阅读 OpenVLA 论文 + 本地指南 | 理解 Action Tokenizer 和双视觉编码器 |
| 5-6 | 运行 OpenVLA 演示（模拟数据） | 跑通 VLA pipeline |
| 7-8 | 学习机器人学基础（FK/IK/动力学） | 理解 7-DoF 动作空间 |
| 9-12 | 深入 OpenVLA 源码 | 能修改和扩展 VLA |

### 阶段二：算法进阶（3-6 个月）

**目标**：掌握 VLA+ 技术，理解 Flow Matching 和 Action Chunking

| 周 | 任务 | 产出 |
|----|------|------|
| 1-4 | 阅读 OpenVLA-OFT 论文，理解并行解码 | 能解释 OFT 的三大改进 |
| 5-8 | 阅读 π₀ 论文，理解 Flow Matching | 能对比自回归 vs Flow Matching |
| 9-12 | 在 LeRobot 中训练 Diffusion Policy | 完成 PushT 任务训练 |
| 13-16 | 使用 LeRobot 采集数据 + 训练自定义策略 | 端到端工作流实践 |
| 17-24 | 阅读 ACT、BEAST 等论文 | 理解动作分块和分词器设计 |

### 阶段三：仿真实战（6-9 个月）

**目标**：在 Isaac Lab 中训练策略并部署

| 周 | 任务 | 产出 |
|----|------|------|
| 1-4 | 安装 Isaac Sim + Isaac Lab | 环境搭建完成 |
| 5-8 | 训练四足机器人运动策略 | 完成 Go1 运动控制 |
| 9-12 | 训练机械臂操作策略 | 完成 Franka 抓取任务 |
| 13-16 | 学习域随机化 + Sim2Real | 理解迁移技术 |
| 17-20 | 使用 Newton 物理引擎 | 多物理仿真实践 |
| 21-24 | 策略部署到仿真机器人 | 完成闭环验证 |

### 阶段四：前沿探索（9-12 个月）

**目标**：理解 World Action Model，跟踪最新研究

| 周 | 任务 | 产出 |
|----|------|------|
| 1-4 | 阅读 DreamZero 论文 | 理解 WAM 架构 |
| 5-8 | 阅读 Motus/Motubrain 相关资料 | 理解 UniDiffuser 和三流 MoT |
| 9-12 | 学习 Cosmos 平台 | 跑通 GR00T-Dreams 示例 |
| 13-16 | 阅读 Genie Envisioner 论文 | 理解 GE-Act + GE-Sim |
| 17-20 | 复现 WAM 实验（基于开源代码） | 实践 WAM 训练 |
| 21-24 | 探索 AIoT + 具身智能融合 | 设计工业应用方案 |

---

## 附录：术语表

| 术语 | 全称 | 中文 |
|------|------|------|
| VLA | Vision-Language-Action | 视觉-语言-动作模型 |
| WAM | World Action Model | 世界动作模型 |
| WM | World Model | 世界模型 |
| FM | Flow Matching | 流匹配 |
| IL | Imitation Learning | 模仿学习 |
| RL | Reinforcement Learning | 强化学习 |
| Sim2Real | Simulation to Reality | 仿真到真实迁移 |
| ADR | Automatic Domain Randomization | 自动域随机化 |
| WBC | Whole Body Control | 全身控制 |
| FK/IK | Forward/Inverse Kinematics | 正/逆运动学 |
| DoF | Degrees of Freedom | 自由度 |
| OXE | Open X-Embodiment | 开放跨实体数据集 |
| USD | Universal Scene Description | 通用场景描述 |
| MoT | Mixture of Transformers | Transformer 混合 |
| VLM | Vision-Language Model | 视觉-语言模型 |
| RLDS | RL Dataset | 强化学习数据集格式 |
| PBT | Population Based Training | 群体训练 |
| NeRF | Neural Radiance Fields | 神经辐射场 |
| 3DGS | 3D Gaussian Splatting | 三维高斯溅射 |
| AIoT | AI + IoT | 人工智能物联网 |
