# 08 World Action Model 深度解析与 ROS2 实战

> World Action Model (WAM) 将世界模型与动作条件预测结合，使机器人具备"想象未来"的能力——在执行动作前，先在脑内模拟未来状态，从而实现预测式避障、模型规划和安全验证。

## 8.1 世界模型演进脉络

| 阶段 | 代表工作 | 年份 | 核心思想 |
|------|---------|------|---------|
| 经典控制 | Kalman Filter | 1960 | 线性高斯状态空间模型 |
| 学习型世界模型 | World Models (Ha & Schmidhuber) | 2018 | VAE+LTM+Controller |
| 梦境学习 | Dreamer / DreamerV2 / DreamerV3 | 2020-2023 | RSSM+Actor-Critic 想象训练 |
| 生成式世界模型 | GAIA-1, Sora | 2023-2024 | 自回归视频生成 |
| 嵌入预测 | JEPA (LeCun) | 2022 | 联合嵌入预测架构 |
| 具身世界模型 | UniSim, Genie | 2023-2024 | 通用具身交互世界模拟 |

### World Models (2018) 三组件架构

```
┌─────────────────────────────────────────────┐
│            World Model (Ha 2018)             │
│                                             │
│   ┌───────┐   ┌───────────┐   ┌──────────┐  │
│   │  VAE  │ → │   LSTM    │ → │Controller│  │
│   │(Vision)│   │ (Memory)  │   │ (Policy) │  │
│   └───┬───┘   └─────┬─────┘   └────┬─────┘  │
│       │              │               │       │
│    编码图像      预测下一隐态     基于隐态输出动作  │
│    z = V(o)    h_t = LSTM(h_{t-1}, z_{t-1}, a_{t-1})  │
│                          a_t = C(h_t, z_t)          │
└─────────────────────────────────────────────┘
```

**关键贡献**：将感知（VAE）、记忆（LSTM）、控制（线性策略）解耦，在压缩隐空间中"梦境"训练。

### Dreamer 的 RSSM 架构

Dreamer 引入 **Recurrent State-Space Model (RSSM)**，将确定性路径和随机性路径结合：

```
                    RSSM (Dreamer)
                    ─────────────
                         │
    ┌────────────────────┼────────────────────┐
    │                    │                    │
    │  确定性路径          │  随机性路径          │
    │  h_t = GRU(h_{t-1}, s_{t-1}, a_{t-1})  │
    │                    │                    │
    │         ┌──────────┴──────────┐         │
    │         │                     │         │
    │    先验分布              后验分布          │
    │  s_t ~ N(μ_prior,       s_t ~ N(μ_post, │
    │         σ_prior)               σ_post)   │
    │         │                     │         │
    │    从 h_t 推断          从 h_t 和 o_t 推断  │
    │         │                     │         │
    └─────────┴─────────────────────┘         │
                      │
                 解码器/预测器
              ô_t = Decoder(h_t, s_t)
              r_t = RewardHead(h_t, s_t)
```

## 8.2 RSSM 数学推导

### 状态空间模型定义

设隐状态 `s_t`，观测 `o_t`，动作 `a_t`，奖励 `r_t`：

**转移模型（先验）**：
```
h_t = f_φ(h_{t-1}, s_{t-1}, a_{t-1})           # 确定性递推（GRU）
s_t ~ p_φ(s_t | h_t) = N(μ_prior(h_t), σ_prior(h_t))  # 随机采样
```

**推断模型（后验）**：
```
s_t ~ q_φ(s_t | h_t, o_t) = N(μ_post(h_t, o_t), σ_post(h_t, o_t))
```

**观测解码**：
```
ô_t = g_φ(h_t, s_t)     # 重建观测
r̂_t = R_φ(h_t, s_t)     # 预测奖励
```

### ELBO 目标推导

联合对数似然的变分下界：

```
log p(o_{1:T}, r_{1:T} | a_{1:T-1})
= Σ_t log p(o_t | s_t, h_t) + log p(r_t | s_t, h_t) + log p(s_t | h_t) - log q(s_t | h_t, o_t)
```

引入 Jensen 不等式，得到 ELBO：

```
L_ELBO = E_q[Σ_t log p(o_t | s_t, h_t) + log p(r_t | s_t, h_t)]
         - Σ_t KL[q(s_t | h_t, o_t) || p(s_t | h_t)]
```

**三项分解**：
1. **重建损失**：`L_recon = -E[log p(o_t | s_t, h_t)]`（观测重建）
2. **奖励预测**：`L_reward = -E[log p(r_t | s_t, h_t)]`（奖励预测）
3. **KL 散度**：`L_KL = KL[q || p]`（后验逼近先验，鼓励一致性）

### 完整损失函数

```python
# Dreamer 总损失
total_loss = (
    L_recon * λ_recon +    # 观测重建权重
    L_reward * λ_reward +   # 奖励预测权重
    L_KL * λ_kl +           # KL 散度权重（通常有 β 调度）
    L_actor +               # Actor 策略损失
    L_critic                # Critic 价值损失
)
```

### Actor-Critic 在想象空间训练

Dreamer 的核心创新：在学到的世界模型中"想象"轨迹，直接在想象空间中训练策略。

```
想象轨迹：从当前真实状态 (h_t, s_t) 出发
  for τ = t+1, ..., t+H:
      a_τ = π_θ(h_τ, s_τ)              # 策略采样
      h_{τ+1} = f(h_τ, s_τ, a_τ)       # 确定性递推
      s_{τ+1} ~ p(s | h_{τ+1})         # 随机转移（无观测，用先验）
      r̂_{τ+1} = R(h_{τ+1}, s_{τ+1})   # 预测奖励

计算回报：
  V_τ = R_τ + γ·V_{τ+1}                # TD 误差
  G_τ = Σ_{k=0}^{H-1} γ^k · r̂_{τ+k}   # 蒙特卡洛回报

Actor 损失：L_actor = -E[G_τ]（最大化想象回报）
Critic 损失：L_critic = (V_θ(h_τ, s_τ) - G_τ)²
```

## 8.3 WAM 架构设计（ROS2 机器人专用）

### 系统架构

```
┌──────────────────────────────────────────────────────────┐
│                    WAM ROS2 节点架构                      │
│                                                          │
│  ┌─────────┐  ┌──────────┐  ┌──────────┐                │
│  │ /scan   │  │ /odom    │  │ /cmd_vel │  ← ROS2 话题   │
│  │(LiDAR)  │  │(里程计)   │  │(速度命令) │                │
│  └────┬────┘  └────┬─────┘  └────┬─────┘                │
│       │            │             │                        │
│       ▼            ▼             ▼                        │
│  ┌──────────────────────────────────────┐                │
│  │        感知编码器 (Encoder)           │                │
│  │  z_t = VAE.encode(scan_t)            │                │
│  │  pose_t = MLP(odom_t)                │                │
│  │  obs_t = concat(z_t, pose_t)        │                │
│  └────────────────┬─────────────────────┘                │
│                   │                                      │
│                   ▼                                      │
│  ┌──────────────────────────────────────┐                │
│  │        RSSM 世界模型                  │                │
│  │  h_t = GRU(h_{t-1}, s_{t-1}, a_{t-1})│               │
│  │  s_t ~ Posterior(h_t, obs_t)         │                │
│  └────────────────┬─────────────────────┘                │
│                   │                                      │
│         ┌─────────┴──────────┐                           │
│         ▼                    ▼                            │
│  ┌──────────────┐  ┌──────────────────┐                 │
│  │  未来预测器    │  │  基于模型规划器    │                 │
│  │  想象H步轨迹   │  │  CEM/MPPI搜索    │                 │
│  │  scan_{t+1:H}│  │  最优动作序列     │                 │
│  └──────┬───────┘  └────────┬─────────┘                 │
│         │                    │                            │
│         ▼                    ▼                            │
│  ┌──────────────┐  ┌──────────────────┐                 │
│  │ /wam/predict │  │ /wam/plan        │  → ROS2 话题     │
│  │ (预测未来)    │  │ (规划动作)       │                 │
│  └──────────────┘  └──────────────────┘                 │
│                                                          │
│  ┌──────────────────────────────────────┐                │
│  │      安全验证器 (Safety Check)       │                │
│  │  检查预测轨迹是否碰撞                  │                │
│  │  若碰撞 → 发布 /wam/safe_vel         │                │
│  └──────────────────────────────────────┘                │
└──────────────────────────────────────────────────────────┘
```

### ROS2 话题接口

| 话题 | 类型 | 方向 | 说明 |
|------|------|------|------|
| /scan | sensor_msgs/LaserScan | 输入 | 激光雷达扫描 |
| /odom | nav_msgs/Odometry | 输入 | 里程计位姿 |
| /cmd_vel | geometry_msgs/Twist | 输入/输出 | 速度命令（拦截/输出） |
| /wam/predicted_scan | sensor_msgs/LaserScan | 输出 | 预测的未来扫描 |
| /wam/predicted_path | nav_msgs/Path | 输出 | 预测的未来轨迹 |
| /wam/collision_risk | std_msgs/Float32 | 输出 | 碰撞风险概率 [0,1] |
| /wam/safe_vel | geometry_msgs/Twist | 输出 | 安全速度（过滤后） |
| /wam/imagination_viz | visualization_msgs/MarkerArray | 输出 | RViz 可视化 |

## 8.4 PyTorch 实现

### RSSM 核心代码

```python
import torch
import torch.nn as nn
import torch.nn.functional as F

class RSSM(nn.Module):
    """Recurrent State-Space Model (Dreamer架构)"""

    def __init__(self, obs_dim, action_dim, hidden_dim=200, state_dim=30):
        super().__init__()
        self.hidden_dim = hidden_dim  # 确定性隐状态维度
        self.state_dim = state_dim     # 随机隐状态维度

        # 确定性递推（GRU）
        self.gru = nn.GRUCell(action_dim + state_dim, hidden_dim)

        # 先验分布：p(s_t | h_t)
        self.prior_net = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
        )
        self.prior_mean = nn.Linear(hidden_dim, state_dim)
        self.prior_logvar = nn.Linear(hidden_dim, state_dim)

        # 后验分布：q(s_t | h_t, o_t)
        self.post_net = nn.Sequential(
            nn.Linear(hidden_dim + obs_dim, hidden_dim),
            nn.ReLU(),
        )
        self.post_mean = nn.Linear(hidden_dim, state_dim)
        self.post_logvar = nn.Linear(hidden_dim, state_dim)

    def prior(self, h):
        """先验分布：无观测时从 h 推断 s"""
        x = self.prior_net(h)
        mean = self.prior_mean(x)
        logvar = self.prior_logvar(x)
        return mean, logvar

    def posterior(self, h, obs):
        """后验分布：有观测时从 h 和 obs 推断 s"""
        x = self.post_net(torch.cat([h, obs], dim=-1))
        mean = self.post_mean(x)
        logvar = self.post_logvar(x)
        return mean, logvar

    def sample(self, mean, logvar):
        """重参数化采样：s = mean + std * ε"""
        std = torch.exp(0.5 * logvar)
        eps = torch.randn_like(std)
        return mean + std * eps

    def rollout(self, obs_seq, action_seq, h0=None):
        """
        训练时前向展开（有观测）
        obs_seq:   [B, T, obs_dim]
        action_seq:[B, T, action_dim]
        返回: priors, posteriors, hidden_states
        """
        B, T, _ = obs_seq.shape
        if h0 is None:
            h = torch.zeros(B, self.hidden_dim, device=obs_seq.device)
        else:
            h = h0

        priors, posteriors, hidden_states = [], [], []
        for t in range(T):
            # 后验（有观测）
            post_mean, post_logvar = self.posterior(h, obs_seq[:, t])
            s = self.sample(post_mean, post_logvar)

            # 先验（无观测，用于 KL 计算）
            prior_mean, prior_logvar = self.prior(h)

            priors.append((prior_mean, prior_logvar))
            posteriors.append((post_mean, post_logvar))
            hidden_states.append(h)

            # 确定性递推
            h = self.gru(
                torch.cat([s, action_seq[:, t]], dim=-1), h
            )

        return {
            'priors': priors,
            'posteriors': posteriors,
            'hidden_states': hidden_states,
        }

    def imagine(self, h, s, action_seq):
        """
        想象模式（无观测，仅用先验预测未来）
        用于 Dreamer 的 Actor-Critic 训练
        """
        imagined = []
        h_t, s_t = h, s
        for a in action_seq:
            h_t = self.gru(torch.cat([s_t, a], dim=-1), h_t)
            prior_mean, prior_logvar = self.prior(h_t)
            s_t = self.sample(prior_mean, prior_logvar)
            imagined.append((h_t, s_t))
        return imagined
```

### 世界模型完整实现

```python
class WorldModel(nn.Module):
    """完整世界模型：编码器 + RSSM + 解码器 + 奖励预测"""

    def __init__(self, scan_dim=360, action_dim=2, hidden_dim=200, state_dim=30):
        super().__init__()

        # 观测编码器（将360维LiDAR压缩到低维）
        self.encoder = nn.Sequential(
            nn.Linear(scan_dim, 256),
            nn.ReLU(),
            nn.Linear(256, 128),
            nn.ReLU(),
        )
        obs_dim = 128  # 编码后的观测维度

        # RSSM 核心
        self.rssm = RSSM(obs_dim, action_dim, hidden_dim, state_dim)

        # 观测解码器（重建LiDAR扫描）
        self.decoder = nn.Sequential(
            nn.Linear(hidden_dim + state_dim, 256),
            nn.ReLU(),
            nn.Linear(256, scan_dim),
        )

        # 奖励预测器
        self.reward_head = nn.Sequential(
            nn.Linear(hidden_dim + state_dim, 128),
            nn.ReLU(),
            nn.Linear(128, 1),
        )

        # 碰撞预测器（二分类）
        self.collision_head = nn.Sequential(
            nn.Linear(hidden_dim + state_dim, 128),
            nn.ReLU(),
            nn.Linear(128, 1),
            nn.Sigmoid(),
        )

    def encode(self, scan):
        """编码LiDAR扫描为低维观测向量"""
        return self.encoder(scan)

    def forward(self, scan_seq, action_seq):
        """训练前向传播"""
        # 编码观测序列
        obs_seq = self.encode(scan_seq)  # [B, T, 128]

        # RSSM 展开
        rssm_out = self.rssm.rollout(obs_seq, action_seq)

        # 解码重建
        recon_scans = []
        predicted_rewards = []
        collision_probs = []

        for t in range(len(rssm_out['hidden_states'])):
            h = rssm_out['hidden_states'][t]
            post_mean, post_logvar = rssm_out['posteriors'][t]
            s = self.rssm.sample(post_mean, post_logvar)

            # 解码
            hs = torch.cat([h, s], dim=-1)
            recon = self.decoder(hs)
            recon_scans.append(recon)

            # 奖励预测
            reward = self.reward_head(hs)
            predicted_rewards.append(reward)

            # 碰撞预测
            collision = self.collision_head(hs)
            collision_probs.append(collision)

        return {
            'recon_scans': torch.stack(recon_scans, dim=1),
            'predicted_rewards': torch.stack(predicted_rewards, dim=1),
            'collision_probs': torch.stack(collision_probs, dim=1),
            'priors': rssm_out['priors'],
            'posteriors': rssm_out['posteriors'],
        }

    def predict_future(self, scan, action_seq, h=None, s=None):
        """
        推理时预测未来（给定当前状态和动作序列）
        scan:       [B, scan_dim]  当前LiDAR扫描
        action_seq: [B, H, action_dim]  未来动作序列
        返回: 预测的未来扫描、奖励、碰撞概率
        """
        B = scan.shape[0]

        # 初始化隐状态
        if h is None:
            h = torch.zeros(B, self.rssm.hidden_dim, device=scan.device)
        if s is None:
            obs = self.encode(scan)
            post_mean, post_logvar = self.rssm.posterior(h, obs)
            s = self.rssm.sample(post_mean, post_logvar)

        # 想象未来
        imagined = self.rssm.imagine(h, s, action_seq)

        # 解码预测
        future_scans = []
        future_rewards = []
        future_collisions = []

        for h_t, s_t in imagined:
            hs = torch.cat([h_t, s_t], dim=-1)
            future_scans.append(self.decoder(hs))
            future_rewards.append(self.reward_head(hs))
            future_collisions.append(self.collision_head(hs))

        return {
            'future_scans': torch.stack(future_scans, dim=1),
            'future_rewards': torch.stack(future_rewards, dim=1),
            'collision_probs': torch.stack(future_collisions, dim=1),
        }
```

### 基于模型的规划器（CEM）

```python
class CEMPlanner:
    """Cross-Entropy Method 规划器：使用世界模型搜索最优动作序列"""

    def __init__(self, world_model, horizon=10, num_samples=500,
                 elite_ratio=0.1, iterations=5, action_dim=2):
        self.world_model = world_model
        self.horizon = horizon          # 预测步长
        self.num_samples = num_samples   # 每轮采样数
        self.elite_ratio = elite_ratio   # 精英比例
        self.iterations = iterations     # CEM 迭代次数
        self.action_dim = action_dim     # 动作维度(vx, ωz)
        self.elite_num = int(num_samples * elite_ratio)

        # 动作约束（差速驱动）
        self.max_linear = 0.7    # m/s
        self.max_angular = 1.0   # rad/s

    def plan(self, current_scan):
        """
        给定当前LiDAR扫描，规划最优动作序列
        返回：最优动作序列 [H, action_dim]
        """
        scan = current_scan.unsqueeze(0)  # [1, scan_dim]

        # 初始化动作分布
        mean = torch.zeros(self.horizon, self.action_dim)
        std = torch.ones(self.horizon, self.action_dim) * 0.5

        for _ in range(self.iterations):
            # 1. 采样动作序列
            samples = mean + std * torch.randn(
                self.num_samples, self.horizon, self.action_dim
            )

            # 动作裁剪
            samples[..., 0] = samples[..., 0].clamp(-self.max_linear, self.max_linear)
            samples[..., 1] = samples[..., 1].clamp(-self.max_angular, self.max_angular)

            # 2. 用世界模型评估每个动作序列
            rewards = []
            collision_risks = []

            for i in range(0, self.num_samples, 50):  # 分批评估
                batch = samples[i:i+50]  # [50, H, action_dim]
                batch_scan = scan.expand(batch.shape[0], -1)

                with torch.no_grad():
                    result = self.world_model.predict_future(
                        batch_scan, batch
                    )

                # 累积奖励 - 碰撞惩罚
                total_reward = result['future_rewards'].squeeze(-1).sum(dim=1)
                collision_penalty = result['collision_probs'].squeeze(-1).sum(dim=1) * 10.0
                score = total_reward - collision_penalty

                rewards.append(score)
                collision_risks.append(result['collision_probs'].mean(dim=1))

            rewards = torch.cat(rewards)
            collision_risks = torch.cat(collision_risks)

            # 3. 选择精英样本
            elite_indices = rewards.topk(self.elite_num).indices
            elite_samples = samples[elite_indices]

            # 4. 更新分布参数
            mean = elite_samples.mean(dim=0)
            std = elite_samples.std(dim=0)

        # 返回最优动作序列（取均值的第一步）
        return mean, collision_risks[elite_indices[0]]

    def safe_action(self, current_scan, desired_vel):
        """
        安全过滤：检查期望速度是否安全
        如果预测碰撞风险 > 阈值，则减速
        """
        desired_action = torch.tensor([desired_vel.linear.x, desired_vel.angular.z])
        action_seq = desired_action.unsqueeze(0).unsqueeze(0)  # [1, 1, 2]
        action_seq = action_seq.repeat(1, self.horizon, 1)

        scan = current_scan.unsqueeze(0)
        with torch.no_grad():
            result = self.world_model.predict_future(scan, action_seq)

        max_collision_prob = result['collision_probs'].max().item()

        if max_collision_prob > 0.5:
            # 高碰撞风险：紧急制动
            return torch.zeros(2), max_collision_prob
        elif max_collision_prob > 0.2:
            # 中等风险：减速
            scale = 1.0 - (max_collision_prob - 0.2) / 0.3
            return desired_action * scale, max_collision_prob
        else:
            # 安全：全速通过
            return desired_action, max_collision_prob
```

## 8.5 ROS2 节点集成

### WAM ROS2 节点

```python
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import LaserScan
from nav_msgs.msg import Odometry, Path
from geometry_msgs.msg import Twist, PoseStamped
from std_msgs.msg import Float32
from visualization_msgs.msg import Marker, MarkerArray
import numpy as np
import torch

class WAMNode(Node):
    """World Action Model ROS2 节点"""

    def __init__(self):
        super().__init__('wam_node')

        # 参数
        self.declare_parameter('model_path', '/tmp/wam_model.pt')
        self.declare_parameter('horizon', 10)
        self.declare_parameter('collision_threshold', 0.3)
        self.declare_parameter('use_safety_filter', True)

        # 加载世界模型
        self.world_model = WorldModel(scan_dim=360, action_dim=2)
        model_path = self.get_parameter('model_path').value
        if model_path and torch.load(model_path, exist_ok=True):
            self.world_model.load_state_dict(torch.load(model_path))
            self.get_logger().info(f'加载世界模型: {model_path}')
        else:
            self.get_logger().warn('未找到训练好的模型，使用随机初始化')

        self.world_model.eval()
        self.horizon = self.get_parameter('horizon').value
        self.collision_threshold = self.get_parameter('collision_threshold').value
        self.use_safety_filter = self.get_parameter('use_safety_filter').value

        # 规划器
        self.planner = CEMPlanner(self.world_model, horizon=self.horizon)

        # 状态缓存
        self.current_scan = None
        self.current_odom = None
        self.rssm_h = None  # RSSM 隐状态
        self.rssm_s = None

        # ROS2 订阅
        self.scan_sub = self.create_subscription(
            LaserScan, '/scan', self.scan_callback, 10)
        self.odom_sub = self.create_subscription(
            Odometry, '/odom', self.odom_callback, 10)
        self.cmd_vel_sub = self.create_subscription(
            Twist, '/cmd_vel_raw', self.cmd_vel_callback, 10)

        # ROS2 发布
        self.predicted_scan_pub = self.create_publisher(
            LaserScan, '/wam/predicted_scan', 10)
        self.collision_risk_pub = self.create_publisher(
            Float32, '/wam/collision_risk', 10)
        self.safe_vel_pub = self.create_publisher(
            Twist, '/cmd_vel', 10)
        self.path_pub = self.create_publisher(
            Path, '/wam/predicted_path', 10)
        self.viz_pub = self.create_publisher(
            MarkerArray, '/wam/imagination_viz', 10)

        # 定时器：10Hz 预测循环
        self.timer = self.create_timer(0.1, self.prediction_loop)

        self.get_logger().info('WAM 节点已启动')

    def scan_callback(self, msg):
        """处理LiDAR扫描"""
        scan = np.array(msg.ranges)
        # 降采样到360点（如果原始更多）
        if len(scan) != 360:
            indices = np.linspace(0, len(scan)-1, 360, dtype=int)
            scan = scan[indices]
        scan = np.nan_to_num(scan, nan=20.0, posinf=20.0, neginf=0.0)
        scan = np.clip(scan, 0, 20)
        self.current_scan = torch.FloatTensor(scan)

    def odom_callback(self, msg):
        self.current_odom = msg

    def cmd_vel_callback(self, msg):
        """拦截速度命令，进行安全过滤"""
        if not self.use_safety_filter or self.current_scan is None:
            self.safe_vel_pub.publish(msg)
            return

        # 使用世界模型预测碰撞风险
        with torch.no_grad():
            safe_action, risk = self.planner.safe_action(
                self.current_scan, msg
            )

        # 发布安全速度
        safe_msg = Twist()
        safe_msg.linear.x = float(safe_action[0])
        safe_msg.angular.z = float(safe_action[1])
        self.safe_vel_pub.publish(safe_msg)

        # 发布碰撞风险
        risk_msg = Float32()
        risk_msg.data = float(risk)
        self.collision_risk_pub.publish(risk_msg)

    def prediction_loop(self):
        """10Hz 预测循环：想象未来并发布可视化"""
        if self.current_scan is None:
            return

        # 预测未来H步
        with torch.no_grad():
            # 使用零动作序列（假设保持当前速度）
            zero_actions = torch.zeros(1, self.horizon, 2)
            result = self.world_model.predict_future(
                self.current_scan, zero_actions
            )

        # 发布预测的LiDAR扫描（第5步预测）
        predicted_scan = result['future_scans'][0, 4]
        self.publish_predicted_scan(predicted_scan)

        # 发布碰撞风险
        collision_prob = result['collision_probs'][0].max().item()
        risk_msg = Float32()
        risk_msg.data = collision_prob
        self.collision_risk_pub.publish(risk_msg)

        # 发布RViz可视化
        self.publish_visualization(result)

    def publish_predicted_scan(self, predicted_scan):
        """发布预测的LiDAR扫描"""
        msg = LaserScan()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = 'laser_link'
        msg.angle_min = 0.0
        msg.angle_max = 6.2831853
        msg.angle_increment = 0.0174533  # 1度
        msg.range_min = 0.01
        msg.range_max = 20.0
        msg.ranges = predicted_scan.cpu().numpy().tolist()
        self.predicted_scan_pub.publish(msg)

    def publish_visualization(self, result):
        """发布RViz可视化标记"""
        markers = MarkerArray()

        # 为每个预测步创建一个标记
        for t in range(self.horizon):
            marker = Marker()
            marker.header.frame_id = 'map'
            marker.header.stamp = self.get_clock().now().to_msg()
            marker.ns = 'wam_prediction'
            marker.id = t
            marker.type = Marker.SPHERE
            marker.action = Marker.ADD

            # 使用碰撞概率着色（绿→黄→红）
            prob = result['collision_probs'][0, t].item()
            if prob < 0.3:
                marker.color.r = 0.0
                marker.color.g = 1.0
            elif prob < 0.7:
                marker.color.r = 1.0
                marker.color.g = 1.0
            else:
                marker.color.r = 1.0
                marker.color.g = 0.0
            marker.color.b = 0.0
            marker.color.a = 0.6

            marker.scale.x = 0.1
            marker.scale.y = 0.1
            marker.scale.z = 0.1
            markers.markers.append(marker)

        self.viz_pub.publish(markers)
```

## 8.6 实战场景

### 场景一：预测式碰撞避免

**目标**：机器人在Nav2导航时，WAM预测未来10步的LiDAR扫描，若预测到障碍物逼近，提前减速。

```python
# 场景配置
scenario_1 = {
    'name': '预测式避障',
    'description': 'WAM在Nav2导航层之上运行，预测前方2秒状态',
    'topics': {
        'input': ['/scan', '/odom', '/cmd_vel_raw'],  # Nav2输出原始速度
        'output': ['/cmd_vel', '/wam/collision_risk'], # 过滤后安全速度
    },
    'params': {
        'horizon': 20,             # 2秒@10Hz
        'collision_threshold': 0.3,
        'use_safety_filter': True,
    },
    'test': '让Nav2规划穿过窄门，观察WAM是否减速'
}
```

```bash
# 运行场景一
# 终端1：Gazebo仿真
ros2 launch myfirst_robot gz_sim.launch.py

# 终端2：Nav2导航（输出到 /cmd_vel_raw）
ros2 launch myfirst_robot nav2_bringup.launch.py
# 修改：将 controller_server 的 cmd_vel_topic 改为 /cmd_vel_raw

# 终端3：WAM安全过滤节点
ros2 run myfirst_robot wam_node --ros-args \
  -p use_safety_filter:=true \
  -p collision_threshold:=0.3

# 终端4：RViz观察预测
# 添加 /wam/predicted_scan 和 /wam/imagination_viz
```

### 场景二：模型规划（CEM搜索最优动作）

**目标**：不使用Nav2，直接用世界模型 + CEM规划器搜索最优动作序列。

```python
class CEMPlanningNode(Node):
    """基于CEM的模型规划节点"""

    def __init__(self):
        super().__init__('cem_planner')
        self.world_model = WorldModel(scan_dim=360, action_dim=2)
        self.planner = CEMPlanner(
            self.world_model,
            horizon=15,       # 1.5秒规划
            num_samples=500,  # 每轮500条采样
            iterations=5,     # 5轮CEM迭代
        )

        self.scan_sub = self.create_subscription(
            LaserScan, '/scan', self.scan_callback, 10)
        self.cmd_pub = self.create_publisher(
            Twist, '/cmd_vel', 10)

        self.timer = self.create_timer(0.1, self.plan_loop)
        self.current_scan = None

    def plan_loop(self):
        if self.current_scan is None:
            return

        # CEM 搜索最优动作
        best_actions, risk = self.planner.plan(self.current_scan)

        # 执行第一步动作
        msg = Twist()
        msg.linear.x = float(best_actions[0, 0])
        msg.angular.z = float(best_actions[0, 1])
        self.cmd_pub.publish(msg)

        self.get_logger().info(
            f'CEM规划: v={msg.linear.x:.2f} ω={msg.angular.z:.2f} risk={risk:.2f}'
        )
```

### 场景三：Dreamer 式训练（Gazebo数据采集→世界模型训练）

```python
class DataCollectorNode(Node):
    """在Gazebo中采集训练数据"""

    def __init__(self):
        super().__init__('data_collector')
        self.scan_sub = self.create_subscription(
            LaserScan, '/scan', self.scan_callback, 10)
        self.cmd_sub = self.create_subscription(
            Twist, '/cmd_vel', self.cmd_callback, 10)

        self.buffer = []
        self.episode = []

    def scan_callback(self, msg):
        if self.current_cmd is not None:
            scan = np.array(msg.ranges)
            self.episode.append({
                'scan': scan,
                'action': [self.current_cmd.linear.x,
                          self.current_cmd.angular.z],
                'reward': 0.0,  # 由环境标注
                'collision': False
            })

    def save_episode(self):
        """保存一轮数据到磁盘"""
        if len(self.episode) > 0:
            np.save(f'/tmp/wam_data/episode_{self.episode_id}.npy',
                    self.episode)
            self.episode_id += 1
            self.episode = []


# 训练脚本
class WAMTrainer:
    """世界模型训练器"""

    def __init__(self, data_dir='/tmp/wam_data'):
        self.world_model = WorldModel(scan_dim=360, action_dim=2)
        self.optimizer = torch.optim.Adam(
            self.world_model.parameters(), lr=1e-4
        )
        self.data_dir = data_dir

    def compute_loss(self, batch):
        """计算世界模型总损失"""
        scans = batch['scans']         # [B, T, 360]
        actions = batch['actions']     # [B, T, 2]
        rewards = batch['rewards']     # [B, T]
        collisions = batch['collisions']  # [B, T]

        result = self.world_model(scans, actions)

        # 1. 重建损失
        recon_loss = F.mse_loss(result['recon_scans'], scans)

        # 2. 奖励预测损失
        reward_loss = F.mse_loss(
            result['predicted_rewards'].squeeze(-1), rewards
        )

        # 3. 碰撞预测损失
        collision_loss = F.binary_cross_entropy(
            result['collision_probs'].squeeze(-1), collisions.float()
        )

        # 4. KL 散度
        kl_loss = 0
        for t in range(len(result['priors'])):
            post_mean, post_logvar = result['posteriors'][t]
            prior_mean, prior_logvar = result['priors'][t]
            kl_loss += gaussian_kl(
                post_mean, post_logvar, prior_mean, prior_logvar
            ).mean()
        kl_loss /= len(result['priors'])

        # 总损失
        total = recon_loss + reward_loss + collision_loss + 0.1 * kl_loss

        return {
            'total': total,
            'recon': recon_loss.item(),
            'reward': reward_loss.item(),
            'collision': collision_loss.item(),
            'kl': kl_loss.item(),
        }

    def train(self, epochs=100, batch_size=32, seq_len=50):
        """训练循环"""
        dataset = WAMDataset(self.data_dir, seq_len=seq_len)
        loader = torch.utils.data.DataLoader(
            dataset, batch_size=batch_size, shuffle=True
        )

        for epoch in range(epochs):
            for batch in loader:
                self.optimizer.zero_grad()
                losses = self.compute_loss(batch)
                losses['total'].backward()
                torch.nn.utils.clip_grad_norm_(
                    self.world_model.parameters(), 10.0)
                self.optimizer.step()

            print(f'Epoch {epoch}: {losses}')

        torch.save(self.world_model.state_dict(), '/tmp/wam_model.pt')


def gaussian_kl(mean1, logvar1, mean2, logvar2):
    """两个高斯分布之间的KL散度"""
    return 0.5 * torch.sum(
        logvar2 - logvar1 - 1 +
        torch.exp(logvar1 - logvar2) +
        (mean1 - mean2)**2 / torch.exp(logvar2),
        dim=-1
    )
```

### 场景四：安全验证（动作序列风险评估）

```python
class SafetyVerifier:
    """动作序列安全验证器"""

    def __init__(self, world_model, max_collision_prob=0.1):
        self.world_model = world_model
        self.max_prob = max_collision_prob

    def verify_action_sequence(self, scan, action_seq):
        """
        验证动作序列是否安全
        返回: (is_safe, max_risk, risky_step)
        """
        with torch.no_grad():
            result = self.world_model.predict_future(
                scan.unsqueeze(0), action_seq.unsqueeze(0)
            )

        collision_probs = result['collision_probs'][0]  # [H]
        max_prob = collision_probs.max().item()
        risky_step = collision_probs.argmax().item()

        is_safe = max_prob < self.max_prob
        return is_safe, max_prob, risky_step

    def find_safe_alternative(self, scan, desired_action):
        """
        如果期望动作不安全，搜索最近的安全替代动作
        """
        # 构造候选动作集（螺旋搜索）
        candidates = []
        for r in np.linspace(0, 1, 10):
            for theta in np.linspace(0, 2*np.pi, 16):
                v = desired_action[0] * (1 - r)
                w = desired_action[1] + r * np.sin(theta)
                candidates.append([v, w])

        candidates = torch.FloatTensor(candidates)
        scan_batch = scan.unsqueeze(0).expand(len(candidates), -1)

        with torch.no_grad():
            result = self.world_model.predict_future(
                scan_batch,
                candidates.unsqueeze(1).repeat(1, 10, 1)
            )

        risks = result['collision_probs'][:, 0, 0]
        safe_indices = (risks < self.max_prob).nonzero()

        if len(safe_indices) > 0:
            # 选择与期望动作最接近的安全动作
            best_idx = safe_indices[
                torch.argmin(torch.norm(
                    candidates[safe_indices.squeeze()] -
                    torch.tensor(desired_action), dim=-1
                ))
            ]
            return candidates[best_idx].squeeze(), risks[best_idx].item()
        else:
            # 没有安全替代，紧急停止
            return torch.zeros(2), 1.0
```

### 场景五：域随机化 Sim-to-Real

```python
class DomainRandomizer:
    """
    在世界模型训练时加入域随机化
    提高从仿真到真实环境的泛化能力
    """

    def __init__(self):
        # LiDAR噪声参数随机化
        self.noise_std_range = (0.001, 0.05)    # 测距噪声
        self.dropout_rate_range = (0.0, 0.1)    # 随机遮挡
        self.bias_range = (-0.02, 0.02)         # 系统偏置
        self.max_range_range = (15.0, 25.0)      # 量程变化

    def randomize_scan(self, scan):
        """对LiDAR扫描施加域随机化"""
        # 1. 高斯噪声
        noise_std = np.random.uniform(*self.noise_std_range)
        scan = scan + np.random.randn(*scan.shape) * noise_std

        # 2. 随机遮挡（模拟遮挡/玻璃）
        dropout = np.random.rand(*scan.shape) < np.random.uniform(*self.dropout_rate_range)
        scan[dropout] = 20.0  # 最大量程

        # 3. 系统偏置
        bias = np.random.uniform(*self.bias_range)
        scan = scan + bias

        # 4. 量程变化
        max_range = np.random.uniform(*self.max_range_range)
        scan = np.clip(scan, 0, max_range)

        return scan

    def randomize_dynamics(self, action):
        """对动作施加动力学随机化"""
        # 模拟电机响应延迟和摩擦
        latency = np.random.randint(1, 5)  # 1-4步延迟
        noise = np.random.randn(2) * 0.05  # 5%动作噪声
        return action + noise, latency
```

## 8.7 完整 Launch 文件

```python
# wam_demo.launch.py
"""
WAM 完整 Demo 启动文件
启动：Gazebo仿真 + Nav2导航 + WAM世界模型 + 安全过滤
"""
import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

def generate_launch_description():
    pkg_share = get_package_share_directory('myfirst_robot')

    # WAM 节点
    wam_node = Node(
        package='myfirst_robot',
        executable='wam_node',
        name='wam_node',
        parameters=[{
            'model_path': os.path.expanduser('~/wam_model.pt'),
            'horizon': 20,
            'collision_threshold': 0.3,
            'use_safety_filter': True,
        }],
        output='screen'
    )

    # CEM 规划节点（可选）
    cem_planner = Node(
        package='myfirst_robot',
        executable='cem_planner',
        name='cem_planner',
        parameters=[{
            'horizon': 15,
            'num_samples': 500,
        }],
        output='screen'
    )

    # 数据采集节点（训练时使用）
    data_collector = Node(
        package='myfirst_robot',
        executable='data_collector',
        name='data_collector',
        output='screen'
    )

    return LaunchDescription([
        wam_node,
        # 取消注释以使用 CEM 规划器替代 Nav2
        # cem_planner,
        # 取消注释以采集训练数据
        # data_collector,
    ])
```

## 8.8 训练与评估

### 训练流程

```
1. 数据采集阶段
   - 在 Gazebo 中遥控机器人探索（teleop_keyboard）
   - data_collector 节点自动记录 (scan, action, reward, collision)
   - 目标：100 episodes × 1000 steps = 100K 样本

2. 离线训练阶段
   - python3 wam_trainer.py --data_dir /tmp/wam_data --epochs 100
   - 监控：recon_loss < 0.01, kl_loss < 1.0, collision_acc > 90%

3. 在线评估阶段
   - 启动 wam_node 加载训练好的模型
   - 观察 /wam/predicted_scan 与真实 /scan 的对比
   - 测量：预测误差 RMSE、碰撞检出率、误报率

4. 部署集成阶段
   - 将 WAM 作为 Nav2 的安全过滤层
   - 对比：有/无 WAM 的碰撞次数和到达率
```

### 评估指标

| 指标 | 计算方式 | 合格标准 |
|------|---------|---------|
| 重建RMSE | √(mean((scan-ô)²)) | <0.5m |
| KL散度 | KL[q‖p] | <1.0 nats |
| 碰撞预测准确率 | TP+TN/总数 | >90% |
| 碰撞预测召回率 | TP/(TP+FN) | >95% |
| 预测延迟 | 前向推理时间 | <50ms |
| 安全过滤效果 | 碰撞减少率 | >80% |

## 8.9 与课程模块的关联

| 课程模块 | WAM 关联点 |
|---------|-----------|
| 模块六-传感器感知 | LiDAR数据预处理、编码器设计 |
| 模块七-导航SLAM | WAM作为Nav2安全层、预测式避障 |
| 模块九-具身智能 | Dreamer算法、世界模型训练、ACT对比 |
| 模块八-软件架构 | 节点生命周期、安全过滤模式 |

---

**返回**：[README](../README.md) | [上一课](07-视频录制与回放.md)
