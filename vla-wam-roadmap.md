# VLA-WAM 具身智能学习路线图

> 承接 Mini-VLA 基础，分三大模块，循序渐进

## 一、整体学习路线

### 模块划分

| 序号 | 模块 | 核心技术 | 优先级 |
|------|------|---------|--------|
| 1 | 具身模仿学习 | VLA 视觉语言动作模型 | **优先落地** |
| 2 | 机器人强化学习 | PPO、Diffusion Policy、多关节连续控制 | 进阶 |
| 3 | 世界模型 | DreamerV3、视觉预测模型、想象式训练 | 高阶 |

### 学习顺序

```
先跑通 VLA 抓取仿真 → 再做机器人 RL 控制 → 最后上手世界模型 MBRL
```

---

## 二、第一部分：具身智能 VLA + 模仿学习

> 最贴合现有代码，从 MiniVLA 直接衔接

### 1）首选实战项目（零基础可复现）

#### ① Hugging Face LeRobot（全网入门首选，强烈推荐）

- **定位**：开源机器人学习框架，支持 MuJoCo/PyBullet 仿真+真机，内置机械臂抓取数据集、BC 行为克隆、ACT、Diffusion Policy
- **教程**：
  - 官方文档（中文注释丰富）：https://huggingface.co/docs/lerobot/index
  - B站完整实操：《LeRobot 机械臂模仿学习，从零训练抓取策略》
- **可直接复用**：把 Mini-VLA 的网络结构嵌入 LeRobot 数据流水线
- **可做项目**：收集 100 条专家轨迹，训练视觉+状态条件的动作策略，完美衔接 state+tokens 双输入模型

#### ② OpenVLA（斯坦福开源 VLA，Mini-VLA 的工业升级版）

- **代码仓库**：https://github.com/openvla/openvla
- **优质图文教程**（含 LoRA 微调+仿真部署）：
  1. CSDN：【OpenVLA】视觉语言动作模型原理+MuJoCo 机械臂部署
  2. Markaicode 英文实操教程（环境安装+推理+少量数据微调）
- **核心实践**：
  - 零样本指令抓取
  - 用自己的仿真数据做 LoRA 轻量化微调，和之前训练流程完全一致（MSE 损失、Adam 优化器）

#### ③ Berkeley Octo 通用机器人策略

- 多机器人跨域 VLA，支持图像+本体观测，适合进阶研究

### 2）仿真环境入门教程（免费、不吃显卡）

| 环境 | 特点 | 教程资源 |
|------|------|---------|
| PyBullet | CPU 就能跑，入门首选 | B站：《PyBullet 机械臂仿真+专家轨迹录制+行为克隆训练》，全程纯 Python |
| MuJoCo 2.3+ | 机器人控制标准环境 | 官方文档+B站全套教程：机械臂 6 自由度控制、抓取场景搭建 |
| NVIDIA Isaac Lab | GPU 大规模并行训练，工业级 | 官方 QuickStart+RSL-RL 的 PPO 人形行走案例 |

### 3）文字课程与专栏

1. 智源社区《具身智能原理与实践》配套专栏，覆盖 VLA、模仿学习、3D 感知、Sim2Real
2. CSDN 专栏：《从零搭建机器人 VLA 系统：数据集→模型→训练→仿真闭环》，逐行拆解数据预处理、动作归一化、多模态特征拼接

---

## 三、第二部分：机器人强化学习（连续动作控制）

### 1）入门级项目（优先跑通）

#### 1. 基础连续控制（MuJoCo + PPO）

- **开源代码库**：stable-baselines3
- **B站教程**：《SB3 手把手训练机械臂抓取、四足机器人行走》，一行代码切换 PPO/SAC 算法

#### 2. 人形/四足机器人实战（工业开源代码）

- **Unitree 宇树开源**：unitree_rl_gym
  - 支持 Isaac Gym + MuJoCo 双环境
  - 包含 G1/H1 人形机器人行走、跌倒起立
  - 附带完整奖励函数、域随机化、Sim2Real 虚实迁移教程

#### 3. 动作生成进阶：Diffusion Policy（当前具身控制 SOTA）

- **官方项目**：https://github.com/robot-learning-freiburg/DiffusionPolicy
- **优质教程**：B站《扩散策略：多模态机器人动作生成，解决多模态动作歧义》
- **适配场景**：多步骤整理、精细操作，可直接替换 Mini-VLA 最后的 MLP 头

### 2）系统化文字教程

1. RSL-RL 官方教程（IsaacLab 标配 PPO 框架，机器人行业工业标准）
2. 51CTO 专栏：《具身机器人强化学习：从 MDP 设计到域随机化与虚实迁移》

---

## 四、第三部分：世界模型 World Model + 基于模型的强化学习

> 以 DreamerV3 为主线

### 1）首选入门项目：DreamerV3（谷歌 DeepMind）

**核心思想**：先学习环境动力学预测模型（世界模型），在虚拟梦境里训练策略，极大减少真实环境交互次数，非常适合机器人数据稀缺场景。

**资源清单**：

1. **官方源码**：https://github.com/danijar/dreamerv3
   - 支持图像视觉输入+低维状态输入
   - 一键运行 100+ benchmarks
2. **B站教程**：《DreamerV3：在虚拟梦境中训练机器人策略》
3. **关键特性**：
   - 无需调超参，单组超参横扫所有任务
   - 离散/连续动作空间通用
   - 基于 RSSM 的循环状态空间模型

### 2）进阶：TD-MPC2（Model-Based + MPC）

- **官方源码**：https://github.com/nicklashansen/tdmpc2
- 特点：世界模型 + 模型预测控制（MPC），在线规划，适合需要实时决策的机器人控制
- 相比 DreamerV3：更侧重在线规划，DreamerV3 更侧重虚拟训练

### 3）视觉世界模型（Transformer-based）

- **IRIS**（DeepMind）：https://github.com/google-deepmind/iris
  - 纯 Transformer 世界模型，用 VQ-VAE 编码视觉帧
  - 在虚拟环境中训练策略
- **TD7**：高效世界模型基线，适合快速实验

### 4）世界模型学习路径

```
DreamerV3 (入门) → TD-MPC2 (在线规划) → IRIS (视觉Transformer) → 自定义世界模型
```

---

## 五、项目代码结构（对应三大模块）

```
2000_Embody/
├── 0100-manual-vla/          # 已完成：MiniVLA 手动实现
├── 0200-vla-imitation/       # 模块1：VLA 模仿学习
│   ├── envs/                 # 仿真环境 (PyBullet/MuJoCo)
│   ├── data/                 # 数据采集与管理
│   ├── models/               # VLA 模型 (ACT, Diffusion Policy)
│   └── scripts/              # 训练/评估脚本
├── 0300-robot-rl/            # 模块2：机器人强化学习
│   ├── envs/                 # RL 环境
│   ├── algorithms/           # RL 算法 (PPO, SAC)
│   └── scripts/              # 训练/评估脚本
├── 0400-world-model/         # 模块3：世界模型
│   ├── models/               # DreamerV3, TD-MPC2
│   └── scripts/              # 训练/评估脚本
├── common/                   # 公共基础设施
│   ├── config.py             # 统一配置管理
│   ├── logger.py             # 日志工具
│   ├── utils.py              # 通用工具函数
│   └── visualization.py      # 可视化工具
└── vla-wam-roadmap.md        # 本路线图
```

---

## 六、硬件与依赖建议

### 基础环境（模块1即可）

- Python 3.10+
- PyTorch 2.0+
- CUDA 11.8+（GPU 训练）
- MuJoCo 2.3+ / PyBullet

### 进阶环境（模块2-3）

- NVIDIA Isaac Lab（需 RTX 3090+）
- stable-baselines3
- tensorflow_datasets（OXE 数据加载）

### 最小依赖安装

```bash
pip install torch torchvision transformers mujoco pybullet
pip install stable-baselines3 gymnasium
pip install wandb tensorboard  # 实验追踪
```
