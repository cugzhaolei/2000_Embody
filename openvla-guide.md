# OpenVLA 程序运行与使用指南 — 从 OpenVLA 到 Isaac、LeRobot、World Action Model

> 从零开始学习具身智能，一步步从 VLA 走向世界动作模型

---

## 目录

- [第一部分：OpenVLA 快速上手](#第一部分openvla-快速上手)
  - [1.1 环境准备](#11-环境准备)
  - [1.2 模型加载与推理](#12-模型加载与推理)
  - [1.3 REST API 部署](#13-rest-api-部署)
  - [1.4 LoRA 微调](#14-lora-微调)
  - [1.5 核心架构解析](#15-核心架构解析)
  - [1.6 局限性](#16-局限性)
- [第二部分：OpenVLA-OFT — 更快更强的继任者](#第二部分openvla-oft--更快更强的继任者)
- [第三部分：π₀ / OpenPI — Flow Matching VLA](#第三部分π₀--openpi--flow-matching-vla)
- [第四部分：NVIDIA Isaac — 机器人仿真与基础模型平台](#第四部分nvidia-isaac--机器人仿真与基础模型平台)
- [第五部分：LeRobot — HuggingFace 端到端机器人学习](#第五部分lerobot--huggingface-端到端机器人学习)
- [第六部分：World Action Model — 具身智能的下一战](#第六部分world-action-model--具身智能的下一战)
- [第七部分：AIoT 与具身智能技术生态](#第七部分aiot-与具身智能技术生态)
- [第八部分：学习路线图与资源汇总](#第八部分学习路线图与资源汇总)

---

## 第一部分：OpenVLA 快速上手（小白详解版）

> 本节从零开始，逐步讲解每一个概念、每一步操作、每一个输出结果。
> 即使你没有 GPU，也能通过代码示例理解整个工作流程。

---

### 1.0 什么是 VLA？—— 先理解大图

**VLA = Vision-Language-Action（视觉-语言-动作）**

想象你在教一个机器人"把红色杯子拿起来"。机器人需要三样东西：

| 输入 | 例子 | 对应模型组件 |
|------|------|-------------|
| **Vision（视觉）** | 摄像头看到的图像 | DINOv2 + SigLIP 双视觉编码器 |
| **Language（语言）** | "pick up the red cup" | Llama-2 7B 语言模型 |
| **Action（动作）** | 机械臂移动的 7 个数值 | Action Tokenizer 解码 |

**传统机器人 vs VLA 机器人：**

```
传统机器人流程（硬编码）：
  摄像头 → 目标检测 → 坐标计算 → 逆运动学 → 轨迹规划 → 电机控制
  每一步都需要人工写代码，换任务就要重写

VLA 机器人流程（端到端）：
  摄像头 + 语言指令 → [VLA 模型] → 直接输出动作
  像人一样"看一眼、听指令、直接做"
```

**OpenVLA 的核心创新：**
- 它是第一个**完全开源**的 VLA（之前 Google 的 RT-2 是闭源的）
- 7B 参数（70 亿），但比 55B 的 RT-2 还强 16.5%
- 在 970,000 段真实机器人操作数据上训练
- 支持多种机器人（WidowX、Google Robot、Franka 等）

---

### 1.1 环境准备（手把手安装）

#### 1.1.1 先确认你的硬件

| 场景 | 最低配置 | 推荐配置 | 能做什么 |
|------|----------|----------|----------|
| **纯 CPU** | 16GB 内存 | 32GB 内存 | 只能理解流程，无法实际推理 |
| **单卡推理** | RTX 3060 (12GB) | RTX 4090 (24GB) | 加载模型、预测动作 |
| **LoRA 微调** | RTX 4090 (24GB) | A100 (40GB) | 在自己的数据上微调 |
| **全量微调** | A100 (80GB) | 8×A100 | 从头训练（一般不需要） |

> **没有 GPU？** 没关系！后面 1.2.4 节提供了一个纯 CPU/纯 NumPy 的模拟脚本，
> 可以在你的笔记本上运行，完整理解 VLA 的工作流程。

#### 1.1.2 安装 Miniconda（Python 环境管理器）

```bash
# Windows: 从 https://docs.conda.io/en/latest/miniconda.html 下载安装
# Linux/WSL:
wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
bash Miniconda3-latest-Linux-x86_64.sh
source ~/.bashrc
```

**验证安装：**
```bash
conda --version
# 期望输出：conda 24.x.x（版本号可能不同，有输出即可）
```

#### 1.1.3 创建虚拟环境

```bash
# 创建名为 openvla 的 Python 3.10 环境
conda create -n openvla python=3.10 -y

# 激活环境
conda activate openvla

# 验证
python --version
# 期望输出：Python 3.10.x
```

> **为什么要虚拟环境？** 不同项目需要不同版本的库，虚拟环境让它们互不干扰。
> 就像给每个项目一个独立的"工作间"。

#### 1.1.4 安装 PyTorch

```bash
# 有 NVIDIA GPU（CUDA 11.8）：
pip install torch==2.1.0 torchvision==0.16.0 --index-url https://download.pytorch.org/whl/cu118

# 有 NVIDIA GPU（CUDA 12.1）：
pip install torch==2.1.0 torchvision==0.16.0 --index-url https://download.pytorch.org/whl/cu121

# 无 GPU（CPU 版本）：
pip install torch==2.1.0 torchvision==0.16.0 --index-url https://download.pytorch.org/whl/cpu
```

**验证 PyTorch 和 CUDA：**
```python
python -c "
import torch
print(f'PyTorch 版本: {torch.__version__}')
print(f'CUDA 可用: {torch.cuda.is_available()}')
if torch.cuda.is_available():
    print(f'GPU 名称: {torch.cuda.get_device_name(0)}')
    print(f'GPU 显存: {torch.cuda.get_device_properties(0).total_mem / 1e9:.1f} GB')
"
```

**期望输出（有 GPU）：**
```
PyTorch 版本: 2.1.0+cu118
CUDA 可用: True
GPU 名称: NVIDIA GeForce RTX 4090
GPU 显存: 24.0 GB
```

**期望输出（无 GPU）：**
```
PyTorch 版本: 2.1.0+cpu
CUDA 可用: False
```

#### 1.1.5 克隆 OpenVLA 仓库

```bash
git clone https://github.com/openvla/openvla.git
cd openvla
```

**仓库目录结构解析：**
```
openvla/
├── prismatic/                    # 核心代码库
│   ├── vla/                      # VLA 相关模块
│   │   ├── action_tokenizer.py   # ★ 动作分词器（核心！）
│   │   └── datasets/            # 数据集加载
│   ├── models/
│   │   ├── vlas/
│   │   │   └── openvla.py        # ★ OpenVLA 模型定义
│   │   ├── vlms/
│   │   │   └── prismatic.py      # ★ VLM 基座模型
│   │   └── backbones/
│   │       ├── vision/
│   │       │   └── dinosiglip_vit.py  # ★ 双视觉编码器
│   │       └── llm/
│   │           └── llama2.py      # ★ Llama-2 语言模型
│   └── extern/hf/
│       └── modeling_prismatic.py  # ★ HuggingFace 推理接口
├── vla-scripts/
│   ├── finetune.py               # ★ LoRA 微调脚本
│   ├── deploy.py                 # ★ REST API 部署脚本
│   └── merge_lora.py             # 合并 LoRA 权重
└── requirements-min.txt          # 最小依赖
```

#### 1.1.6 安装依赖

```bash
# 方式一：完整安装（包含训练依赖）
pip install -e .

# 方式二：最小安装（仅推理，推荐新手）
pip install -r requirements-min.txt
```

**核心依赖说明：**

| 库 | 版本 | 作用 | 类比 |
|----|------|------|------|
| `transformers` | 4.40.1 | HuggingFace 模型加载/推理 | "模型管家" |
| `torch` | 2.1.0 | PyTorch 深度学习框架 | "计算引擎" |
| `timm` | 0.9.12 | 视觉模型库（DINOv2、SigLIP） | "视觉模型库" |
| `tokenizers` | 0.19.1 | BPE 分词器 | "文本→数字转换器" |
| `peft` | ≥0.10.0 | LoRA 参数高效微调 | "微调工具" |
| `numpy` | - | 数值计算 | "数学工具箱" |

---

### 1.2 模型加载与推理（详解每一步）

#### 1.2.1 核心概念：模型加载过程发生了什么？

当你执行 `from_pretrained("openvla/openvla-7b")` 时，背后发生了：

```
1. 从 HuggingFace Hub 下载模型文件（约 14GB）
   ├── config.json          ← 模型配置（层数、维度等）
   ├── model.safetensors    ← 模型权重（70亿个数字）
   ├── tokenizer.json       ← 分词器（文本↔数字的映射表）
   ├── preprocessor_config.json ← 图像预处理参数
   └── dataset_statistics.json ← 反归一化统计信息

2. 根据配置构建模型结构
   PrismaticVisionBackbone  ← 视觉编码器
   PrismaticProjector       ← 投影层
   LlamaForCausalLM         ← Llama-2 7B

3. 将权重加载到模型中

4. 将模型移到 GPU 上
```

#### 1.2.2 完整推理代码（逐行注释）

```python
# ============================================================
# 第一步：导入必要的库
# ============================================================
from transformers import AutoModelForVision2Seq, AutoProcessor
from PIL import Image
import torch
import numpy as np

# ============================================================
# 第二步：加载处理器（Processor）
# ============================================================
# Processor = Tokenizer + ImageProcessor 的合体
# 它负责把"文本+图像"转换成模型能理解的数字
processor = AutoProcessor.from_pretrained(
    "openvla/openvla-7b",
    trust_remote_code=True    # 允许执行模型仓库中的自定义代码
                              # OpenVLA 不是标准 HF 模型，需要自定义代码
)

# ============================================================
# 第三步：加载模型（VLA）
# ============================================================
vla = AutoModelForVision2Seq.from_pretrained(
    "openvla/openvla-7b",
    attn_implementation="flash_attention_2",
    # ↑ Flash Attention 2：一种更快的注意力计算方法
    #   需要 Ampere 以上架构的 GPU（RTX 3090/4090/A100）
    #   如果 GPU 不支持，改为 "eager"（标准注意力，更慢但兼容）
    torch_dtype=torch.bfloat16,
    # ↑ 使用 bfloat16 半精度：每个数字从 32 位压缩到 16 位
    #   显存减半，精度几乎无损（bfloat16 比 float16 更稳定）
    low_cpu_mem_usage=True,
    # ↑ 分块加载权重，避免一次性占满 CPU 内存
    trust_remote_code=True
).to("cuda:0")
# ↑ 将模型移到第 0 号 GPU 上

# ============================================================
# 第四步：准备输入数据
# ============================================================
# 4a. 获取图像（这里用随机图像演示，实际用摄像头）
image = Image.fromarray(np.random.randint(0, 256, (256, 256, 3), dtype=np.uint8))
# 实际使用：image = Image.open("robot_camera.jpg")

# 4b. 构建 prompt（这是 OpenVLA 的固定格式！）
instruction = "pick up the red cup"
prompt = f"In: What action should the robot take to {instruction.lower()}?\nOut:"
# ↑ prompt 格式说明：
#   "In:"          ← 输入标记
#   "What action..." ← 固定句式，告诉模型这是一个动作预测任务
#   "\nOut:"       ← 输出标记，模型在此之后生成动作
#
# 为什么用 .lower()？因为训练数据中指令都是小写

# ============================================================
# 第五步：预处理输入
# ============================================================
inputs = processor(prompt, image)
# processor 做了两件事：
#   1. 文本处理：prompt → tokenizer → input_ids + attention_mask
#   2. 图像处理：image → resize(224x224) → normalize → pixel_values

# 将输入移到 GPU，并转为 bfloat16
inputs = inputs.to("cuda:0", dtype=torch.bfloat16)

# ============================================================
# 第六步：预测动作
# ============================================================
action = vla.predict_action(
    **inputs,
    unnorm_key="bridge_orig",  # ← 关键！指定用哪组统计信息反归一化
    do_sample=False             # 贪心解码：每次选概率最大的 token
)

# ============================================================
# 第七步：理解输出
# ============================================================
print(f"动作向量: {action}")
print(f"动作维度: {action.shape}")
# 输出示例：
# 动作向量: [ 0.015  0.014 -0.008  0.003  0.002 -0.003  0.73]
# 动作维度: (7,)
```

#### 1.2.3 输出动作的 7 个维度详解

```
action = [dx, dy, dz, droll, dpitch, dyaw, gripper]
          │    │    │    │       │       │      │
          │    │    │    │       │       │      └─ 夹爪开合度
          │    │    │    │       │       │         0=完全闭合, 1=完全张开
          │    │    │    │       │       │
          │    │    │    │       │       └─ 偏航角增量（绕垂直轴旋转）
          │    │    │    │       └─ 俯仰角增量（绕水平轴旋转）
          │    │    │    └─ 翻滚角增量（绕自身轴旋转）
          │    │    └─ Z轴位移增量（上下移动，单位：米）
          │    └─ Y轴位移增量（前后移动，单位：米）
          └─ X轴位移增量（左右移动，单位：米）
```

**每个维度的物理含义：**

| 维度 | 名称 | 范围 | 说明 |
|------|------|------|------|
| 0 | `dx` | ~[-0.05, 0.05] m | 左右移动增量 |
| 1 | `dy` | ~[-0.05, 0.05] m | 前后移动增量 |
| 2 | `dz` | ~[-0.05, 0.05] m | 上下移动增量 |
| 3 | `droll` | ~[-0.1, 0.1] rad | 绕末端执行器X轴旋转 |
| 4 | `dpitch` | ~[-0.1, 0.1] rad | 绕末端执行器Y轴旋转 |
| 5 | `dyaw` | ~[-0.1, 0.1] rad | 绕末端执行器Z轴旋转 |
| 6 | `gripper` | [0, 1] | 夹爪开合度 |

> **为什么是"增量"而不是"绝对位置"？** 因为 VLA 输出的是"这一步相对于上一步移动多少"，
> 而不是"移动到绝对坐标 (x, y, z)"。这类似于游戏手柄的控制方式——推摇杆决定移动方向和速度，
> 而不是直接传送到某个位置。

#### 1.2.4 无 GPU 模拟脚本（任何人都能运行！）

以下脚本用纯 NumPy 模拟 OpenVLA 的完整推理流程，**无需 GPU**，帮助理解核心原理：

```python
"""
OpenVLA 推理流程模拟脚本
无需 GPU，仅需 numpy 和 pillow
pip install numpy pillow
"""
import numpy as np
from PIL import Image

# ============================================================
# 模拟 1: Action Tokenizer — 动作离散化
# ============================================================
print("=" * 60)
print("模拟 1: Action Tokenizer（动作分词器）")
print("=" * 60)

# 参数设置（与 OpenVLA 完全一致）
VOCAB_SIZE = 32000    # Llama-2 的词表大小
N_BINS = 256          # 离散化区间数
MIN_ACTION = -1.0     # 归一化动作下界
MAX_ACTION = 1.0      # 归一化动作上界

# 生成 bin 边界和中心值
bins = np.linspace(MIN_ACTION, MAX_ACTION, N_BINS)
bin_centers = (bins[:-1] + bins[1:]) / 2.0
action_token_begin_idx = VOCAB_SIZE - (N_BINS + 1)

print(f"词表大小: {VOCAB_SIZE}")
print(f"bin 数量: {N_BINS}")
print(f"bin 边界示例: {bins[:5]}...{bins[-5:]}")
print(f"bin 中心示例: {bin_centers[:5]}...{bin_centers[-5:]}")
print(f"动作 token 起始索引: {action_token_begin_idx}")
print()

# --- 编码：连续动作 → token ID ---
print("--- 编码过程：连续动作 → token ID ---")
# 模拟一个 7-DoF 动作（已归一化到 [-1, 1]）
normalized_action = np.array([0.0, 0.5, -0.3, 0.1, -0.1, 0.2, 0.8])
print(f"原始归一化动作: {normalized_action}")

# Step 1: clip 到 [-1, 1]
clipped = np.clip(normalized_action, MIN_ACTION, MAX_ACTION)
print(f"裁剪后: {clipped}")

# Step 2: digitize — 将连续值映射到 bin 索引
discretized = np.digitize(clipped, bins)
print(f"bin 索引: {discretized}")
# digitize 返回 [1, 256]，1 表示落在第一个 bin

# Step 3: 反向映射到 token ID
# bin 索引越小 → token ID 越大（使用词表末尾的 token）
token_ids = VOCAB_SIZE - discretized
print(f"token IDs: {token_ids}")
print()

# --- 解码：token ID → 连续动作 ---
print("--- 解码过程：token ID → 连续动作 ---")
# Step 1: token ID → bin 索引
recovered_discretized = VOCAB_SIZE - token_ids
print(f"恢复的 bin 索引: {recovered_discretized}")

# Step 2: 减 1 并 clip（因为 bin_centers 索引从 0 开始）
recovered_discretized = np.clip(recovered_discretized - 1, 0, len(bin_centers) - 1)
print(f"调整后的索引: {recovered_discretized}")

# Step 3: 查找 bin 中心值
recovered_action = bin_centers[recovered_discretized]
print(f"恢复的归一化动作: {recovered_action}")
print(f"原始动作:         {normalized_action}")
print(f"量化误差:         {np.abs(recovered_action - normalized_action).max():.4f}")
# 量化误差约为 1/256 ≈ 0.004，这是离散化带来的精度损失
print()

# ============================================================
# 模拟 2: 反归一化 — 从 [-1,1] 到真实物理单位
# ============================================================
print("=" * 60)
print("模拟 2: 反归一化（从归一化值到真实物理单位）")
print("=" * 60)

# 模拟 Bridge V2 数据集的统计信息
# q01 = 训练数据中第 1 百分位的动作值
# q99 = 训练数据中第 99 百分位的动作值
# 使用 1%/99% 分位数而非 min/max，是为了排除异常值
action_stats = {
    "q01": np.array([-0.05, -0.05, -0.05, -0.1, -0.1, -0.1, 0.0]),
    "q99": np.array([ 0.05,  0.05,  0.05,  0.1,  0.1,  0.1, 1.0]),
    "mask": np.array([True, True, True, True, True, True, True]),
}

# 反归一化公式：
# action_real = 0.5 * (normalized + 1) * (q99 - q01) + q01
# 这个公式将 [-1, 1] 线性映射到 [q01, q99]
action_low = action_stats["q01"]
action_high = action_stats["q99"]
mask = action_stats["mask"]

real_action = np.where(
    mask,
    0.5 * (recovered_action + 1) * (action_high - action_low) + action_low,
    recovered_action  # mask=False 的维度不做反归一化
)

print(f"归一化动作: {recovered_action}")
print(f"q01 (下界):  {action_low}")
print(f"q99 (上界):  {action_high}")
print(f"真实动作:    {real_action}")
print()
print("各维度含义:")
labels = ["dx(左右m)", "dy(前后m)", "dz(上下m)", "droll(翻滚rad)",
          "dpitch(俯仰rad)", "dyaw(偏航rad)", "gripper(夹爪)"]
for i, (label, val) in enumerate(zip(labels, real_action)):
    print(f"  维度{i} {label}: {val:+.4f}")
print()

# ============================================================
# 模拟 3: 完整推理流程
# ============================================================
print("=" * 60)
print("模拟 3: 完整推理流程（图像+指令 → 动作）")
print("=" * 60)

# 模拟输入
instruction = "pick up the red cup"
prompt = f"In: What action should the robot take to {instruction.lower()}?\nOut:"
print(f"语言指令: {instruction}")
print(f"构建的 prompt: {prompt!r}")

# 模拟 prompt 编码（LlamaTokenizer 的行为）
# 实际中 tokenizer 会将文本转为 token ID 序列
# 这里模拟关键步骤：在 "Out:" 后追加空 token 29871
simulated_input_ids = [1, 29871]  # [BOS, 空token]
print(f"模拟 input_ids: {simulated_input_ids}")
print(f"  token 1 = <BOS> (序列开始)")
print(f"  token 29871 = 空token (LlamaTokenizer 在 'Out:' 后自动添加)")
print()

# 模拟图像预处理
fake_image = np.random.randint(0, 256, (256, 256, 3), dtype=np.uint8)
print(f"原始图像尺寸: {fake_image.shape}")
print(f"预处理后（DINOv2）: resize→224×224, normalize with mean=[0.485,0.456,0.406]")
print(f"预处理后（SigLIP）: resize→224×224, normalize with mean=[0.5,0.5,0.5]")
print()

# 模拟视觉特征提取
dino_features = np.random.randn(256, 1024).astype(np.float32)   # 256 patches × 1024 维
siglip_features = np.random.randn(256, 1152).astype(np.float32) # 256 patches × 1152 维
fused_features = np.concatenate([dino_features, siglip_features], axis=1)
print(f"DINOv2 特征: {dino_features.shape}  (空间推理能力)")
print(f"SigLIP 特征: {siglip_features.shape}  (语义对齐能力)")
print(f"拼接后特征:  {fused_features.shape}  (空间+语义)")
print()

# 模拟投影层
# 实际: 2176 → 8704 → GELU → 4096 → GELU → 4096
projected = np.random.randn(256, 4096).astype(np.float32)
print(f"投影后特征: {projected.shape}  (映射到 LLM 的嵌入空间)")
print()

# 模拟 LLM 生成动作 token
# 实际中 Llama-2 会自回归生成 7 个 token
# 这里模拟生成过程
generated_token_ids = np.array([31846, 31758, 31923, 31892, 31908, 31865, 31744])
print(f"LLM 生成的 7 个动作 token ID: {generated_token_ids}")
print()

# 解码动作 token
discretized_actions = VOCAB_SIZE - generated_token_ids
discretized_actions = np.clip(discretized_actions - 1, 0, len(bin_centers) - 1)
decoded_actions = bin_centers[discretized_actions]
print(f"解码后的归一化动作: {decoded_actions}")

# 反归一化
final_actions = 0.5 * (decoded_actions + 1) * (action_high - action_low) + action_low
print(f"反归一化后的真实动作: {final_actions}")
print()
print("最终输出（机器人执行的动作）:")
for i, (label, val) in enumerate(zip(labels, final_actions)):
    print(f"  维度{i} {label}: {val:+.4f}")
```

**运行方法：**
```bash
# 保存为 simulate_openvla.py，然后运行：
python simulate_openvla.py
```

**期望输出：**
```
============================================================
模拟 1: Action Tokenizer（动作分词器）
============================================================
词表大小: 32000
bin 数量: 256
bin 边界示例: [-1.         -0.99215686 -0.98431373 -0.97647059 -0.96862745]...[0.96862745 0.97647059 0.98431373 0.99215686 1.        ]
bin 中心示例: [-0.99607843 -0.98823529 -0.98039216 -0.97254902 -0.96470588]...[0.96470588 0.97254902 0.98039216 0.98823529 0.99607843]
动作 token 起始索引: 31743

--- 编码过程：连续动作 → token ID ---
原始归一化动作: [ 0.   0.5 -0.3  0.1 -0.1  0.2  0.8]
裁剪后: [ 0.   0.5 -0.3  0.1 -0.1  0.2  0.8]
bin 索引: [128 192  70 141 115 154 204]
token IDs: [31872 31808 31930 31859 31885 31846 31796]

--- 解码过程：token ID → 连续动作 ---
恢复的 bin 索引: [128 192  70 141 115 154 204]
调整后的索引: [127 191  69 140 114 153 203]
恢复的归一化动作: [ 0.003922  0.505882 -0.294118  0.105882 -0.094118  0.200000  0.803922]
原始动作:         [ 0.   0.5 -0.3  0.1 -0.1  0.2  0.8]
量化误差:         0.0078

============================================================
模拟 2: 反归一化（从归一化值到真实物理单位）
============================================================
归一化动作: [ 0.003922  0.505882 -0.294118  0.105882 -0.094118  0.200000  0.803922]
q01 (下界):  [-0.05 -0.05 -0.05 -0.1  -0.1  -0.1   0. ]
q99 (上界):  [0.05 0.05 0.05 0.1  0.1  0.1  1. ]
真实动作:    [ 0.050392  0.080588 -0.037059  0.021176 -0.005882  0.020000  0.901961]

各维度含义:
  维度0 dx(左右m):     +0.0504
  维度1 dy(前后m):     +0.0806
  维度2 dz(上下m):     -0.0371
  维度3 droll(翻滚rad): +0.0212
  维度4 dpitch(俯仰rad): -0.0059
  维度5 dyaw(偏航rad):  +0.0200
  维度6 gripper(夹爪):  +0.9020

============================================================
模拟 3: 完整推理流程（图像+指令 → 动作）
============================================================
语言指令: pick up the red cup
构建的 prompt: 'In: What action should the robot take to pick up the red cup?\nOut:'
模拟 input_ids: [1, 29871]
  token 1 = <BOS> (序列开始)
  token 29871 = 空token (LlamaTokenizer 在 'Out:' 后自动添加)

原始图像尺寸: (256, 256, 3)
预处理后（DINOv2）: resize→224×224, normalize with mean=[0.485,0.456,0.406]
预处理后（SigLIP）: resize→224×224, normalize with mean=[0.5,0.5,0.5]

DINOv2 特征: (256, 1024)  (空间推理能力)
SigLIP 特征: (256, 1152)  (语义对齐能力)
拼接后特征:  (256, 2176)  (空间+语义)

投影后特征: (256, 4096)  (映射到 LLM 的嵌入空间)

LLM 生成的 7 个动作 token ID: [31846 31758 31923 31892 31908 31865 31744]

解码后的归一化动作: [ 0.200000 -0.003922  0.305882  0.188235  0.156863  0.235294
 -0.003922]
反归一化后的真实动作: [ 0.070000  0.049608  0.065294  0.028824  0.025686  0.023529
 -0.001961]

最终输出（机器人执行的动作）:
  维度0 dx(左右m):     +0.0700
  维度1 dy(前后m):     +0.0496
  维度2 dz(上下m):     +0.0653
  维度3 droll(翻滚rad): +0.0288
  维度4 dpitch(俯仰rad): +0.0257
  维度5 dyaw(偏航rad):  +0.0235
  维度6 gripper(夹爪):  -0.0020
```

#### 1.2.5 `unnorm_key` 参数详解

`unnorm_key` 决定了用哪组统计信息做反归一化。OpenVLA 在多个数据集上训练，每个数据集有不同的动作范围：

| unnorm_key | 机器人 | 数据集 | 动作空间特点 |
|------------|--------|--------|-------------|
| `bridge_orig` | WidowX | Bridge V2 | 单臂桌面操作 |
| `bridge_dataset` | WidowX | Bridge (原始) | 同上，旧版本 |
| `google_robot` | Google Robot | RT-1 数据 | 单臂大范围操作 |
| `franka` | Franka Panda | 多种 Franka 任务 | 7-DoF 精细操作 |

```python
# 查看模型支持的所有 unnorm_key
vla = AutoModelForVision2Seq.from_pretrained("openvla/openvla-7b", trust_remote_code=True)
print(vla.norm_stats.keys())
# 输出：dict_keys(['bridge_orig', 'bridge_dataset', 'google_robot', ...])
```

> **如果选错了 unnorm_key 会怎样？** 动作值会被映射到错误的范围，
> 机器人可能会猛烈移动，非常危险！务必确认你使用的机器人对应正确的 key。

---

### 1.3 REST API 部署（远程调用 VLA）

#### 1.3.1 为什么需要 API 部署？

```
场景一：本地推理（简单但不灵活）
  Python 脚本 → 加载模型 → 推理 → 输出动作
  问题：模型占 14GB 显存，每次启动要等 2 分钟

场景二：API 部署（推荐生产使用）
  服务器：常驻运行，模型只加载一次
  客户端：发送 HTTP 请求，毫秒级响应
  好处：多个客户端共享同一个模型，支持远程调用
```

#### 1.3.2 启动服务器

```bash
# 基本启动
python vla-scripts/deploy.py --openvla_path openvla/openvla-7b

# 指定端口和主机
python vla-scripts/deploy.py \
    --openvla_path openvla/openvla-7b \
    --host 0.0.0.0 \
    --port 8000

# 使用本地微调后的模型
python vla-scripts/deploy.py --openvla_path ./my_finetuned_model
```

**启动后的输出：**
```
Loading model from openvla/openvla-7b...
Model loaded successfully!
Server starting on http://0.0.0.0:8000
INFO:     Started server process [12345]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

#### 1.3.3 客户端请求（Python）

```python
import json_numpy as json   # 支持序列化 numpy 数组
import requests
import numpy as np

# 准备图像（从摄像头或文件）
camera_image = np.random.randint(0, 256, (480, 640, 3), dtype=np.uint8)
# 实际使用：camera_image = cv2.imread("camera.jpg")

# 发送请求
response = requests.post(
    "http://localhost:8000/act",
    json={
        "image": camera_image,           # numpy 数组，会自动序列化
        "instruction": "pick up the red cup",
        "unnorm_key": "bridge_orig"      # 可选，默认使用第一个
    },
    timeout=5.0  # 5秒超时
)

# 解析响应
action = json.loads(response.json())
print(f"动作: {action}")
# 输出：动作: [0.015, 0.014, -0.008, 0.003, 0.002, -0.003, 0.73]
```

#### 1.3.4 客户端请求（curl 命令行）

```bash
# 需要先 base64 编码图像
curl -X POST http://localhost:8000/act \
  -H "Content-Type: application/json" \
  -d '{
    "encoded": "{\"image\": [...], \"instruction\": \"pick up the cup\", \"unnorm_key\": \"bridge_orig\"}"
  }'
```

---

### 1.4 LoRA 微调（在自己的数据上训练）

#### 1.4.1 什么是 LoRA？—— 小白理解版

**问题：** 微调 7B 参数模型需要更新 70 亿个数字，需要 A100 (80GB) 显存。

**LoRA 的解决方案：** 不直接修改原始权重，而是给每个线性层加一个"旁路"：

```
原始权重 W (frozen, 不更新):    [4096 × 4096] = 16M 参数
LoRA 旁路 A:                    [4096 × 32]   = 131K 参数
LoRA 旁路 B:                    [32 × 4096]   = 131K 参数

输出 = W @ x + (B @ A) @ x
         ↑           ↑
     原始计算     LoRA 修正项
```

**效果：**
- 只训练 1.4% 的参数（A + B），其余 98.6% 冻结
- 显存从 80GB 降到 24GB（单张 RTX 4090 即可）
- 效果接近全量微调

#### 1.4.2 准备数据

OpenVLA 使用 Open X-Embodiment 格式的数据集：

```
数据集目录结构：
my_dataset/
├── 1.0.0/                          # 版本号
│   └── data/
│       ├── traj_0/
│       │   ├── action.csv           # 每步的动作值 [7维]
│       │   ├── instruction.txt      # 语言指令
│       │   └── images/
│       │       ├── step_0.jpg       # 每步的观测图像
│       │       ├── step_1.jpg
│       │       └── ...
│       ├── traj_1/
│       └── ...
└── dataset_info.json                # 数据集元信息
```

**每条轨迹的数据格式：**

| 文件 | 内容 | 示例 |
|------|------|------|
| `action.csv` | 7-DoF 动作序列 | `0.01,0.02,-0.01,0.0,0.0,0.0,1.0` |
| `instruction.txt` | 语言指令 | `pick up the red cup` |
| `images/step_N.jpg` | 观测图像 | 256×256 RGB 图像 |

#### 1.4.3 运行微调

```bash
# 单 GPU 微调（最常用）
torchrun --standalone --nnodes 1 --nproc_per_node 1 \
    vla-scripts/finetune.py \
    --vla_path "openvla/openvla-7b" \
    --data_root_dir ./datasets \
    --dataset_name my_task \
    --batch_size 16 \
    --learning_rate 5e-4 \
    --lora_rank 32 \
    --lora_dropout 0.0 \
    --use_lora True \
    --image_aug True \
    --max_steps 20000 \
    --save_steps 5000 \
    --wandb_project openvla-finetune \
    --run_root_dir ./checkpoints
```

**训练过程输出示例：**
```
[INFO] Loading model from openvla/openvla-7b...
[INFO] Applying LoRA with rank=32, alpha=16
[INFO] Trainable params: 98.3M / 7,042.5M (1.40%)
[INFO] Loading dataset: my_task (1,250 episodes)
[INFO] Starting training...
Step 100/20000 | Loss: 2.847 | Action Acc: 12.3% | LR: 5.0e-04 | Speed: 3.2 it/s
Step 500/20000 | Loss: 1.523 | Action Acc: 45.6% | LR: 5.0e-04 | Speed: 3.1 it/s
Step 1000/20000 | Loss: 0.834 | Action Acc: 72.1% | LR: 4.8e-04 | Speed: 3.1 it/s
Step 5000/20000 | Loss: 0.234 | Action Acc: 93.5% | LR: 3.2e-04 | Speed: 3.0 it/s
Step 10000/20000 | Loss: 0.112 | Action Acc: 96.8% | LR: 1.5e-04 | Speed: 3.0 it/s
...
[INFO] Training complete. Best checkpoint at step 18500.
```

**关键指标解读：**

| 指标 | 含义 | 好的范围 |
|------|------|----------|
| `Loss` | 交叉熵损失，越低越好 | <0.5 为佳 |
| `Action Acc` | 动作 token 预测准确率 | >95% 为佳 |
| `LR` | 当前学习率（有 warmup 和 decay） | 自动调整 |

#### 1.4.4 合并 LoRA 权重

微调完成后，LoRA 权重和基础模型是分开的。合并后可以像普通模型一样使用：

```bash
python vla-scripts/merge_lora.py \
    --vla_path "openvla/openvla-7b" \
    --lora_path ./checkpoints/my_task/lora_weights \
    --output_dir ./my_finetuned_model
```

**合并过程：**
```
原始权重 W:  [4096 × 4096]  (frozen)
LoRA A:      [4096 × 32]    (trained)
LoRA B:      [32 × 4096]    (trained)

合并后 W' = W + B @ A × (alpha/rank)
         = W + B @ A × (16/32)
         = W + B @ A × 0.5

保存 W' 替代原始 W，推理时不再需要 LoRA 库
```

#### 1.4.5 4-bit 量化微调（显存不够时使用）

```bash
# 启用量化，显存需求从 24GB 降到 ~12GB
torchrun --standalone --nnodes 1 --nproc_per_node 1 \
    vla-scripts/finetune.py \
    --vla_path "openvla/openvla-7b" \
    --use_quantization True \
    --use_lora True \
    --lora_rank 16 \
    --batch_size 8 \
    ...
```

**量化原理：**
```
原始权重：float32 (32位) → 每个参数 4 字节
量化后：  int4 (4位)     → 每个参数 0.5 字节
显存减少：约 8 倍（但 LoRA 部分仍为 float32）

精度影响：几乎无损（论文验证 4-bit 量化后成功率不变）
```

---

### 1.5 核心架构深度解析

#### 1.5.1 为什么需要两个视觉编码器？

**类比：** 想象你在找一本书。

| 编码器 | 类比 | 擅长 | 来源 |
|--------|------|------|------|
| **DINOv2** | 你对书架的空间记忆 | "书在第二排左起第三个" — 空间定位 | 自监督学习（不需要文本标签） |
| **SigLIP** | 你对书名的语义理解 | "我要找那本关于机器人的书" — 语义匹配 | 对比学习（需要文本-图像对） |

**机器人操作需要两种能力：**
- "红色杯子在桌子左边" → DINOv2 的空间推理
- "指令说拿红色杯子，不是蓝色盘子" → SigLIP 的语义对齐

**融合方式：** 沿特征维度拼接（不是相加！）

```python
# 简化版融合代码
dino_patches = dino_featurizer(image)      # [1, 256, 1024]
siglip_patches = siglip_featurizer(image)   # [1, 256, 1152]
fused = torch.cat([dino_patches, siglip_patches], dim=2)  # [1, 256, 2176]
#                                                    ↑
#                                          256 个空间位置，每个位置 2176 维特征
#                                          前 1024 维 = DINOv2（空间）
#                                          后 1152 维 = SigLIP（语义）
```

#### 1.5.2 投影层：为什么"先扩后缩"？

```
输入:  2176 维 (DINOv2 1024 + SigLIP 1152)
       │
       ▼
fc1:   2176 → 8704   (4倍扩展！为什么？)
       │
       ▼ GELU 激活
       │
fc2:   8704 → 4096   (压缩到 LLM 维度)
       │
       ▼ GELU 激活
       │
fc3:   4096 → 4096   (最终维度 = Llama-2 隐藏层维度)
```

**为什么先扩展到 4 倍？**
- 2176 维的视觉特征包含了大量信息，直接压缩到 4096 维会丢失信息
- 先扩展到 8704 维，给网络更大的"工作空间"来重组信息
- 再逐步压缩到 4096 维，与 LLM 的嵌入空间对齐
- 这就像写文章：先写详细草稿（8704），再精简到摘要（4096）

#### 1.5.3 多模态嵌入构建：视觉特征插入在哪里？

```
最终送入 LLM 的序列：

位置:  [0]    [1]     [2]     ...  [256]   [257]  [258]  ...  [256+N]
       ↓       ↓       ↓           ↓       ↓      ↓           ↓
内容:  <BOS>  patch1  patch2  ... patch256  In:   What   ...  Out:
       ↑                                        ↑
    文本嵌入                                 文本嵌入
       ↑
    视觉嵌入（投影后的 patch 特征）

关键设计：视觉 patch 插入在 <BOS> 之后、文本之前！
这样 LLM 的注意力机制可以同时看到视觉和文本信息
```

#### 1.5.4 自回归动作生成：LLM 如何输出动作？

```
LLM 逐步生成过程（7个动作token）：

Step 1: 输入 [BOS, patch1...patch256, In:, What..., Out:, 空]
        → LLM 预测 token_1 (动作维度1: dx)
        输出: 31846

Step 2: 输入 [..., Out:, 空, token_1]
        → LLM 预测 token_2 (动作维度2: dy)
        输出: 31758

Step 3: 输入 [..., 空, token_1, token_2]
        → LLM 预测 token_3 (动作维度3: dz)
        输出: 31923

... 重复 7 次 ...

Step 7: 输入 [..., 空, token_1, ..., token_6]
        → LLM 预测 token_7 (动作维度7: gripper)
        输出: 31744

最终：7 个 token → Action Tokenizer 解码 → 7-DoF 动作
```

> **为什么 max_new_tokens=7？** 因为机器人动作有 7 个维度，
> 每个维度对应一个 token。LLM 恰好生成 7 个 token 就停止。

#### 1.5.5 动作离散化：连续动作如何变成 token？

**完整数据流（以 dx=0.5 为例）：**

```
Step 1: 真实动作
  dx = 0.05 米（机器人实际移动距离）

Step 2: 归一化
  normalized_dx = 2 * (0.05 - q01_dx) / (q99_dx - q01_dx) - 1
               = 2 * (0.05 - (-0.05)) / (0.05 - (-0.05)) - 1
               = 2 * 0.1 / 0.1 - 1
               = 1.0
  → 归一化到 [-1, 1] 范围

Step 3: clip
  clipped_dx = clip(1.0, -1, 1) = 1.0

Step 4: digitize（离散化）
  bin_index = digitize(1.0, bins) = 256
  → 落在第 256 个 bin（最右边的区间）

Step 5: 映射到 token ID
  token_id = vocab_size - bin_index = 32000 - 256 = 31744
  → 使用词表末尾的 token

Step 6: LLM 训练时学习预测这个 token
  训练标签 = 31744
  损失 = CrossEntropy(logits, 31744)

Step 7: 推理时解码
  predicted_token = 31744
  bin_index = 32000 - 31744 = 256
  adjusted_index = clip(256 - 1, 0, 254) = 254
  normalized_action = bin_centers[254] = 0.996
  → 因为离散化，0.5 变成了 0.996（有误差！）

Step 8: 反归一化
  real_dx = 0.5 * (0.996 + 1) * (0.05 - (-0.05)) + (-0.05)
          = 0.5 * 1.996 * 0.1 + (-0.05)
          = 0.0498
  → 接近原始的 0.05，误差约 0.4%
```

#### 1.5.6 为什么用词表末尾的 token？

```
Llama-2 词表（32000 个 token）：

位置 0-31743:  正常语言 token
  0: <unk>
  1: <s> (BOS)
  2: </s> (EOS)
  29871: 空格 token
  ... 正常的英文单词、子词 ...

位置 31744-31999: 动作 token（256 个）
  31744: bin 256（最大动作值）
  31745: bin 255
  ...
  31999: bin 1（最小动作值）

为什么选末尾？
1. 词表末尾的 token 使用频率最低，不会干扰正常语言理解
2. LlamaTokenizer 是 BPE 分词器，高频词在前面，低频词在后面
3. 这样模型可以同时处理语言和动作，互不干扰
```

---

### 1.6 局限性与改进方向

| 局限 | 详细说明 | 改进方案 | 对应项目 |
|------|----------|----------|----------|
| 单帧输入 | 只看当前帧图像，不知道"之前发生了什么"，无法纠正错误 | 加入历史帧、本体感知 | OpenVLA-OFT |
| 推理速度慢 | 自回归逐 token 生成，7 个 token 需要 7 次前向传播，~6 Hz | 并行解码，1 次前向传播输出所有动作 | OpenVLA-OFT |
| 成功率上限 | 挑战性任务成功率 <90% | 更大数据、更强架构 | π₀ |
| 不支持新机器人零样本 | 新机器人需要微调 | 跨实体预训练 | OpenX、LeRobot |
| 动作精度有限 | 256 bin 离散化，最大误差 1/256 ≈ 0.004 | 连续动作表示 | OpenVLA-OFT、π₀ |
| 无物理理解 | 不理解重力、碰撞、摩擦 | 世界模型 | WAM |

---

### 1.7 常见问题 FAQ

**Q1: 没有 GPU 怎么学？**
> 运行 1.2.4 节的模拟脚本，它用纯 NumPy 完整模拟了 VLA 的推理流程。
> 也可以使用 Google Colab 的免费 GPU（T4 15GB）。

**Q2: 模型下载太慢怎么办？**
> 使用 HuggingFace 镜像：
> ```bash
> export HF_ENDPOINT=https://hf-mirror.com
> ```
> 或使用 `huggingface-cli download` 断点续传。

**Q3: RTX 3060 (12GB) 能跑推理吗？**
> 可以！使用 4-bit 量化：
> ```python
> from transformers import BitsAndBytesConfig
> quantization_config = BitsAndBytesConfig(load_in_4bit=True)
> vla = AutoModelForVision2Seq.from_pretrained(
>     "openvla/openvla-7b",
>     quantization_config=quantization_config,
>     ...
> )
> ```
> 4-bit 模型只需约 4GB 显存。

**Q4: 微调需要多少数据？**
> 经验值：50-200 条轨迹（每条 50-200 步）。数据质量比数量更重要。
> 简单任务 50 条即可，复杂任务可能需要 500+ 条。

**Q5: 如何在自己的机器人上使用？**
> 1. 收集遥操作数据（用主臂控制从臂，记录动作+图像）
> 2. 转换为 OpenX 格式
> 3. 用 LoRA 微调
> 4. 部署为 API 或直接推理

**Q6: OpenVLA 和 ACT 哪个更适合入门？**
> - **ACT**：更简单（参数少、训练快），适合固定任务，不需要语言
> - **OpenVLA**：更强大（泛化好、支持语言），但需要更多资源
> - 建议：先用 LeRobot + ACT 在仿真中入门，再学 OpenVLA

---

## 第二部分：OpenVLA-OFT — 更快更强的继任者

> 论文：*Fine-Tuning Vision-Language-Action Models: Optimizing Speed and Success* (Kim, Finn, Liang, 2025)
> 项目页：https://openvla-oft.github.io/
> GitHub：https://github.com/moojink/openvla-oft

### 核心改进：三大关键设计

| 改进 | 原理 | 效果 |
|------|------|------|
| **并行解码** | 将因果注意力掩码替换为双向注意力，所有动作 token 同时预测 | 26× 更快的动作生成速度 |
| **动作分块** | 插入多个空动作嵌入，一次前向传播预测 K 个未来时间步的动作 | 3× 更低延迟 |
| **连续动作表示 + L1 回归** | 不再离散化为 256 bin，直接输出连续值，用 L1 损失替代交叉熵 | 更高精度，20%+ 成功率提升 |

### 性能对比

| 模型 | LIBERO 平均成功率 | 推理速度 |
|------|-------------------|----------|
| OpenVLA（原始） | ~76% | 3-5 Hz |
| OpenVLA-OFT | **97.1%** | 75-130 Hz |
| π₀ | ~90% | - |
| Diffusion Policy | ~85% | - |

### OFT+ 增强：FiLM 语言条件化

OFT+ 在投影层中引入 FiLM（Feature-wise Linear Modulation）层，将语言指令的特征注入视觉特征，增强语言遵循能力。在 ALOHA 双臂机器人上，OFT+ 超越了 π₀ 和 RDT-1B。

---

## 第三部分：π₀ / OpenPI — Flow Matching VLA

> 开发者：Physical Intelligence (π)
> 论文：*π₀: A Vision-Language-Action Flow Model for General Robot Control* (2024)
> 开源仓库：https://github.com/Physical-Intelligence/openpi
> 官网：https://www.pi.website/

### 核心架构

```
π₀ 架构：

图像 + 语言指令 ──→ [PaliGemma 3B VLM] ──→ 语义特征
                                                    │
                                                    ▼
                                          [Action Expert 300M]
                                          Flow Matching 解码器
                                          生成连续动作序列（50Hz 动作分块）
                                                    │
                                                    ▼
                                          连续动作输出（无需离散化）
```

### 与 OpenVLA 的关键区别

| 特性 | OpenVLA | π₀ |
|------|---------|-----|
| 动作表示 | 离散 token（256 bin） | 连续值（Flow Matching） |
| 语言模型 | Llama-2 7B | PaliGemma 3B |
| 动作解码 | 自回归逐 token 生成 | Flow Matching 并行生成 |
| 控制频率 | 3-6 Hz | 50 Hz（动作分块） |
| 训练数据 | 970K episodes (OpenX) | 10,000+ 小时（私有数据） |

### 模型家族

| 模型 | 说明 |
|------|------|
| π₀ | 基础 Flow Matching 模型 |
| π₀-FAST | 自回归变体，使用 FAST 动作分词器，5× 更快训练 |
| π₀.₅ | 增强开放世界泛化（知识隔离训练） |
| π₀.₆ | 引入强化学习（RECAP），从经验中学习 |
| π₀.₇ | 可控性模型，展现涌现能力（2026年4月发布） |

### 硬件要求

| 模式 | 最低 GPU 显存 | 示例 GPU |
|------|---------------|----------|
| 推理 | 8 GB+ | RTX 4090 |
| LoRA 微调 | 22.5 GB+ | RTX 4090 |
| 全量微调 | 70 GB+ | A100 (80GB) / H100 |

---

## 第四部分：NVIDIA Isaac — 机器人仿真与基础模型平台

> 官网：https://developer.nvidia.com/isaac
> Isaac Sim：https://developer.nvidia.com/isaac/sim
> Isaac Lab：https://developer.nvidia.com/isaac/lab
> Isaac GR00T：https://developer.nvidia.com/isaac/gr00t

### Isaac 平台组成

| 组件 | 功能 | 链接 |
|------|------|------|
| **Isaac Sim** | 基于 Omniverse 的物理仿真环境 | https://developer.nvidia.com/isaac/sim |
| **Isaac Lab** | 机器人学习框架（强化学习 + 仿真） | https://developer.nvidia.com/isaac/lab |
| **Isaac GR00T** | 人形机器人基础模型（VLA） | https://developer.nvidia.com/isaac/gr00t |
| **Isaac Manipulator** | 机械臂操作算法库 | https://developer.nvidia.com/isaac/manipulator |
| **Isaac Perceptor** | 感知算法库 | https://developer.nvidia.com/isaac/perceptor |
| **Newton** | 开源物理引擎（与 Google DeepMind、Disney Research 合作） | https://developer.nvidia.com/newton-physics |

### Isaac GR00T 模型演进

| 版本 | 发布时间 | 关键特性 |
|------|----------|----------|
| GR00T N1 | 2025年3月 | 首个开源人形机器人基础模型，双系统架构（System 1 快思考 + System 2 慢思考） |
| GR00T N1.5 | 2025年5月 | 36小时合成数据训练，增强环境适应性 |
| GR00T N1.6 | 2025年9月 | 集成 Cosmos Reason 推理能力 |

### GR00T 双系统架构

```
System 2（慢思考）: VLM 推理
  理解环境 → 解析指令 → 规划动作序列
                │
                ▼
System 1（快思考）: 动作模型
  将规划转化为精确、连续的机器人运动
```

### Isaac Sim 5.0 新特性

- 开源（GitHub: https://github.com/isaac-sim/IsaacSim）
- 神经重建与渲染（NuRec + 3D Gaussian Splatting）
- NVIDIA Cosmos 世界基础模型集成
- 通过 NVIDIA Brev 云端访问

### 快速开始

```bash
# 拉取 Isaac Sim 容器
docker pull nvcr.io/nvidia/isaac-sim:5.0.0

# 运行（headless 模式）
docker run --name isaac-sim --entrypoint bash -it \
    --runtime=nvidia --gpus all \
    -e "ACCEPT_EULA=Y" --rm --network=host \
    nvcr.io/nvidia/isaac-sim:5.0.0
```

---

## 第五部分：LeRobot — HuggingFace 端到端机器人学习

> GitHub：https://github.com/huggingface/lerobot
> 论文：*LeRobot: An Open-Source Library for End-to-End Robot Learning* (ICLR 2026)
> 文档：https://huggingface.co/docs/lerobot

### 核心功能

| 功能 | 说明 |
|------|------|
| **统一机器人接口** | Python 中间件 API，支持 SO-100/SO-101、ALOHA 等硬件 |
| **标准化数据集** | LeRobotDataset 格式，HF Hub 上 100+ 数据集 |
| **SOTA 算法** | ACT、Diffusion Policy、TDMPC、SmolVLA 等 |
| **异步推理栈** | 双层解耦（策略推理 + 动作执行），提高控制频率 |
| **仿真支持** | ALOHA Sim、PushT、SimXArm 等 |

### 支持的算法

| 算法 | 类型 | 特点 |
|------|------|------|
| **ACT** | 模仿学习 | 最受欢迎，50 条轨迹即可训练 |
| **Diffusion Policy** | 模仿学习 | 扩散模型生成动作 |
| **TDMPC** | 模仿+RL | 模型预测控制 |
| **SmolVLA** | VLA | 450M 参数轻量级 VLA，支持语言条件控制 |

### SO-101 机器人（€114/臂）

```python
# 安装
pip install lerobot

# 训练
python lerobot/scripts/train.py \
    policy.type=act \
    env=aloha \
    dataset_repo_id=lerobot/aloha_sim_transfer_cube_human

# 推理
python lerobot/scripts/eval.py \
    -p outputs/train/checkpoints/last/pretrained_model
```

### LeRobot 与 OpenVLA 的关系

| 维度 | OpenVLA | LeRobot |
|------|---------|---------|
| 定位 | 通用 VLA 模型 | 端到端机器人学习平台 |
| 模型规模 | 7B 参数 | SmolVLA 450M / ACT 等 |
| 硬件门槛 | 高（需 A100 训练） | 低（消费级 GPU 即可） |
| 数据格式 | OpenX 格式 | LeRobotDataset（HF Hub） |
| 适合场景 | 研究、大规模部署 | 教育、原型开发、低成本硬件 |

---

## 第六部分：World Action Model — 具身智能的下一战

> "The next frontier of embodied AI is not more teleoperation data, not bigger VLA models — it's World Action Models."
> — Jim Fan, NVIDIA 机器人负责人 (2025)

### 什么是 World Action Model (WAM)？

WAM 将**世界模型**（预测环境未来状态）与**动作生成**（决定机器人行为）统一到一个模型中，使机器人不仅能"看到"未来，还能"理解"动作的后果。

### VLA 的五大致命缺陷（WAM 要解决的）

| 缺陷 | 说明 |
|------|------|
| 不理解物理 | VLA 只学"看到什么做什么"，不理解重力、碰撞、摩擦 |
| 数据饥渴 | 需要海量遥操作数据，成本极高 |
| 泛化灾难 | 新环境、新物体表现差 |
| 复合错误 | 长序列任务中错误累积 |
| 无法规划 | 缺乏前瞻性推理 |

### WAM 架构分类

**1. 级联式 WAM (Cascaded WAM)**
```
[World Model] → 预测未来状态 → [Action Model] → 生成动作
```
- UniPi：文本引导视频生成 → 从视频提取动作
- VLP：视频语言规划

**2. 联合式 WAM (Joint WAM)**
```
[Unified Model] → 同时预测未来状态 + 生成动作
```
- 自回归生成：统一离散表示
- 扩散生成：统一流 / 多流

### 代表性工作

| 项目 | 团队 | 关键特性 |
|------|------|----------|
| **DreamZero** | - | 14B 参数 WAM，55 条轨迹零样本泛化 |
| **GigaBrain-0** | GigaAI | 世界模型生成数据训练 VLA，RGBD + CoT |
| **EVAC** | 智源/Agibot | 动作序列驱动世界模型，开源 |
| **Cosmos Reason** | NVIDIA | 物理推理世界基础模型 |
| **MM-ACT** | 上海AI Lab | 多模态并行生成统一 VLA |
| **Discrete Diffusion VLA** | - | 离散扩散 + 自适应解码顺序 |

### WAM 学习资源

- Awesome-WAM 综述：https://github.com/OpenMOSS/Awesome-WAM
- WAM 论文：https://arxiv.org/abs/2605.12090
- EVAC 开源：https://github.com/AgibotTech/EnerVerse-AC
- EWMBench 评测：https://github.com/AgibotTech/EWMBench

---

## 第七部分：AIoT 与具身智能技术生态

### AIoT 核心概念

AIoT = AI + IoT，将人工智能与物联网融合，使设备具备感知、决策和执行能力。具身智能是 AIoT 的最高形态——机器人不仅能感知和决策，还能在物理世界中行动。

### AIoT 技术栈

```
┌─────────────────────────────────────────────────┐
│                 应用层                            │
│  智能制造 / 智慧城市 / 智慧农业 / 智能家居          │
├─────────────────────────────────────────────────┤
│                 决策层                            │
│  VLA 模型 / 世界模型 / 强化学习 / 规划算法         │
├─────────────────────────────────────────────────┤
│                 感知层                            │
│  视觉编码器 / 语音识别 / 传感器融合 / SLAM         │
├─────────────────────────────────────────────────┤
│                 通信层                            │
│  5G / MQTT / ROS2 / DDS / 边缘计算               │
├─────────────────────────────────────────────────┤
│                 硬件层                            │
│  传感器 / 执行器 / 嵌入式设备 / 机器人本体          │
└─────────────────────────────────────────────────┘
```

### 关键技术融合点

| AIoT 技术 | 具身智能应用 |
|-----------|-------------|
| 边缘计算 | 机器人端实时推理（Jetson、RK3588） |
| 数字孪生 | Isaac Sim 仿真 → 真实部署 |
| 5G 低延迟 | 远程遥操作、云端推理 |
| 传感器融合 | 视觉 + 力觉 + 本体感知 |
| 联邦学习 | 多机器人协同训练 |

---

## 第八部分：学习路线图与资源汇总

### 阶段一：基础（1-2 个月）

**数学与编程基础：**
- 线性代数、概率统计、优化理论
- Python、PyTorch 基础
- 机器人学基础（运动学、动力学）

**推荐资源：**
- [CS231n: CNN for Visual Recognition](http://cs231n.stanford.edu/)
- [CS229: Machine Learning](https://cs229.stanford.edu/)
- [PyTorch 官方教程](https://pytorch.org/tutorials/)
- [Modern Robotics](http://hades.mech.northwestern.edu/index.php/Modern_Robotics)

### 阶段二：视觉语言模型（2-3 个月）

**核心论文：**
- [Attention Is All You Need](https://arxiv.org/abs/1706.03762) — Transformer 架构
- [CLIP](https://arxiv.org/abs/2103.00020) — 视觉-语言对比学习
- [LLaVA](https://arxiv.org/abs/2304.08485) — 大型视觉语言模型
- [Prismatic VLMs](https://arxiv.org/abs/2402.07865) — OpenVLA 的基座模型

**实践项目：**
- 用 HuggingFace Transformers 加载和推理 VLM
- 理解 DINOv2、SigLIP 的特征提取

### 阶段三：VLA 模型（2-3 个月）

**核心论文：**
- [RT-1 / RT-2](https://robotics-transformer-x.github.io/) — 机器人 Transformer
- [OpenVLA](https://arxiv.org/abs/2406.09246) — 开源 VLA
- [OpenVLA-OFT](https://arxiv.org/abs/2502.19645) — VLA 优化微调
- [π₀](https://www.pi.website/blog/pi0) — Flow Matching VLA

**实践项目：**
- 运行 OpenVLA 推理（需 GPU）
- 用 LeRobot + ACT 训练简单任务（低门槛）
- 理解动作离散化与 Flow Matching 的区别

### 阶段四：仿真与部署（2-3 个月）

**工具学习：**
- NVIDIA Isaac Sim / Isaac Lab
- MuJoCo、PyBullet
- ROS2 基础

**实践项目：**
- 在 Isaac Sim 中搭建仿真场景
- 训练策略并迁移到真实机器人
- 使用 LeRobot SO-101 做端到端实验

### 阶段五：前沿探索（持续）

**核心论文与项目：**
- [World Action Model 综述](https://arxiv.org/abs/2605.12090)
- [GigaBrain-0](https://arxiv.org/abs/2510.19430) — 世界模型驱动的 VLA
- [NVIDIA Cosmos](https://nvidianews.nvidia.com/news/nvidia-launches-cosmos-world-foundation-model-platform-to-accelerate-physical-ai-development) — 物理世界基础模型
- [π₀.₅ / π₀.₆ / π₀.₇](https://www.pi.website/) — Physical Intelligence 最新进展

---

## 核心资源链接汇总

### 项目与代码

| 资源 | 链接 |
|------|------|
| OpenVLA GitHub | https://github.com/openvla/openvla |
| OpenVLA-OFT GitHub | https://github.com/moojink/openvla-oft |
| OpenPI (π₀) GitHub | https://github.com/Physical-Intelligence/openpi |
| LeRobot GitHub | https://github.com/huggingface/lerobot |
| Isaac Sim GitHub | https://github.com/isaac-sim/IsaacSim |
| Isaac Lab GitHub | https://github.com/isaac-sim/IsaacLab |
| Awesome-WAM | https://github.com/OpenMOSS/Awesome-WAM |
| EVAC (Agibot) | https://github.com/AgibotTech/EnerVerse-AC |

### 模型权重

| 模型 | 链接 |
|------|------|
| OpenVLA-7B | https://huggingface.co/openvla/openvla-7b |
| OpenVLA-OFT | https://huggingface.co/moojink?search_models=oft |
| π₀ / π₀-FAST | https://huggingface.co/lerobot/pi0 |
| SmolVLA | https://huggingface.co/lerobot/smolvla |
| Isaac GR00T | https://developer.nvidia.com/isaac/gr00t |
| Cosmos Reason | https://huggingface.co/collections/nvidia/cosmos-reason1-67c9e926206426008f1da1b7 |

### 数据集

| 数据集 | 链接 |
|------|------|
| Open X-Embodiment | https://robotics-transformer-x.github.io/ |
| Bridge V2 | https://rail-berkeley.github.io/bridgedata/ |
| DROID | https://droid-dataset.github.io/ |
| ALOHA | https://tonyzhaozh.github.io/aloha/ |
| LeRobot Datasets | https://huggingface.co/lerobot |
| Agibot-World | https://agibot-world.com/ |

### 论文

| 论文 | 链接 |
|------|------|
| OpenVLA | https://arxiv.org/abs/2406.09246 |
| OpenVLA-OFT | https://arxiv.org/abs/2502.19645 |
| π₀ | https://arxiv.org/abs/2410.24164 |
| π₀.₅ | https://arxiv.org/abs/2504.16054 |
| LeRobot | https://arxiv.org/abs/2602.22818 |
| WAM 综述 | https://arxiv.org/abs/2605.12090 |
| GigaBrain-0 | https://arxiv.org/abs/2510.19430 |
| Prismatic VLMs | https://arxiv.org/abs/2402.07865 |
| DINOv2 | https://arxiv.org/abs/2304.07193 |
| SigLIP | https://arxiv.org/abs/2303.15343 |
| FAST Tokenizer | https://www.pi.website/research/fast |

### 学习平台

| 平台 | 链接 | 说明 |
|------|------|------|
| HuggingFace | https://huggingface.co/ | 模型、数据集、Spaces |
| NVIDIA NGC | https://catalog.ngc.nvidia.com/ | Isaac 容器、模型 |
| RoboCasa | https://robocasa.ai/ | 机器人仿真基准 |
| LIBERO | https://libero-project.github.io/ | 操作基准测试 |
| SimplerEnv | https://simpler-env.github.io/ | 真实到仿真的评估 |
| Open X-Embodiment | https://robotics-transformer-x.github.io/ | 跨实体数据集 |

### 社区与博客

| 资源 | 链接 |
|------|------|
| Physical Intelligence Blog | https://www.pi.website/blog |
| NVIDIA Robotics Blog | https://developer.nvidia.com/blog/category/robotics/ |
| HuggingFace Blog | https://huggingface.co/blog |
| Jim Fan (@DrJimFan) | https://x.com/DrJimFan |
| Chelsea Finn | https://ai.stanford.edu/~cbfinn/ |
| Sergey Levine | https://people.eecs.berkeley.edu/~svlevine/ |

### AIoT 与嵌入式

| 资源 | 链接 | 说明 |
|------|------|------|
| NVIDIA Jetson | https://developer.nvidia.com/embedded-computing | 边缘 AI 计算 |
| ROS2 | https://docs.ros.org/en/humble/ | 机器人操作系统 |
| MuJoCo | https://mujoco.org/ | 物理仿真引擎 |
| Newton Physics | https://developer.nvidia.com/newton-physics | 开源物理引擎 |
| OpenUSD | https://openusd.org/ | 3D 场景描述 |
| NVIDIA Omniverse | https://developer.nvidia.com/omniverse | 3D 协作平台 |

---

## 具身智能发展时间线

```
2023
  │  RT-1/RT-2 (Google) — 首个大规模 VLA
  │  Octo (UC Berkeley) — 开源通用策略
  │
2024
  │  OpenVLA (Stanford/Berkeley/TRI) — 首个开源 VLA
  │  π₀ (Physical Intelligence) — Flow Matching VLA
  │  DROID 数据集发布
  │
2025 Q1
  │  OpenVLA-OFT — 并行解码 + 动作分块
  │  π₀ 开源 (OpenPI)
  │  Isaac GR00T N1 — 首个开源人形机器人基础模型
  │  FAST 动作分词器
  │
2025 Q2
  │  π₀.₅ — 开放世界泛化
  │  GR00T N1.5 — 36小时合成数据训练
  │  LeRobot 正式发布 (ICLR 2026)
  │
2025 Q3
  │  GR00T N1.6 + Cosmos Reason
  │  Newton 物理引擎 Beta
  │  Isaac Sim 5.0 / Isaac Lab 2.2 开源
  │  π₀ PyTorch 支持
  │
2025 Q4
  │  GigaBrain-0 — 世界模型驱动 VLA
  │  EVAC — 动作序列驱动世界模型
  │  MM-ACT — 多模态统一 VLA
  │  Discrete Diffusion VLA
  │
2026 Q1
  │  WAM 综述论文
  │  DreamZero — 14B WAM
  │  π₀.₇ — 涌现能力
  │  π*₀.₆ — 强化学习 VLA
  │  MEM — 多尺度具身记忆
```

---

> 本文档持续更新中。最后更新：2026-05-26
