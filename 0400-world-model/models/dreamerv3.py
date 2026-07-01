"""
DreamerV3 世界模型
=================
基于 RSSM (Recurrent State Space Model) 的世界模型实现。
核心思想: 学习环境动力学模型，在虚拟"梦境"中训练策略，大幅减少真实交互次数。

组件:
  1. Encoder: 观测 → 隐特征
  2. RSSM: 递归状态空间模型 (先验/后验)
  3. Decoder: 隐特征 → 观测重建
  4. Reward Predictor: 隐特征 → 奖励预测
  5. Continue Predictor: 隐特征 → 是否继续 (done)
  6. Actor/Critic: 在梦境中训练的策略和价值网络

参考: "Mastering Diverse Domains through World Models" (Hafner et al., 2023)
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
from typing import Tuple, Optional, Dict
from dataclasses import dataclass


@dataclass
class DreamerConfig:
    """DreamerV3 超参数"""
    # RSSM
    rssm_hidden: int = 512
    rssm_deterministic: int = 512
    rssm_stochastic: int = 32
    rssm_discrete: int = 32       # 离散随机变量数量
    action_dim: int = 5
    obs_dim: int = 12             # 低维状态观测

    # 训练
    learning_rate: float = 1e-4
    batch_size: int = 50
    sequence_length: int = 50
    imagination_horizon: int = 15

    # 奖励
    gamma: float = 0.99
    lambda_: float = 0.95

    # Actor-Critic
    actor_hidden: int = 512
    critic_hidden: int = 512
    actor_lr: float = 3e-5
    critic_lr: float = 3e-4


class ConvEncoder(nn.Module):
    """图像编码器 (CNN)"""

    def __init__(self, in_channels: int = 3, hidden_dim: int = 512):
        super().__init__()
        self.net = nn.Sequential(
            nn.Conv2d(in_channels, 32, 4, stride=2), nn.ReLU(),
            nn.Conv2d(32, 64, 4, stride=2), nn.ReLU(),
            nn.Conv2d(64, 128, 4, stride=2), nn.ReLU(),
            nn.Conv2d(128, 256, 4, stride=2), nn.ReLU(),
            nn.Flatten(),
        )
        self.fc = nn.Linear(256 * 2 * 2, hidden_dim)  # 假设 64x64 输入

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.fc(self.net(x))


class StateEncoder(nn.Module):
    """低维状态编码器 (MLP)"""

    def __init__(self, obs_dim: int, hidden_dim: int = 512):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(obs_dim, 256), nn.ELU(),
            nn.Linear(256, 256), nn.ELU(),
            nn.Linear(256, hidden_dim),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)


class RSSM(nn.Module):
    """
    递归状态空间模型 (Recurrent State Space Model)

    先验 (prior): h_t → s_t (基于确定性状态预测随机状态)
    后验 (posterior): h_t + o_t → s_t (观测修正随机状态)

    确定性状态: h_t = GRU(h_{t-1}, s_{t-1}, a_{t-1})
    随机状态: s_t = Discrete(prior/posterior)
    """

    def __init__(self, config: DreamerConfig):
        super().__init__()
        self.config = config
        stochastic_size = config.rssm_stochastic * config.rssm_discrete

        # 确定性状态转移 (GRU)
        self.rnn = nn.GRUCell(
            input_size=stochastic_size + config.action_dim,
            hidden_size=config.rssm_deterministic,
        )

        # 先验网络: h → s
        self.prior_net = nn.Sequential(
            nn.Linear(config.rssm_deterministic, config.rssm_hidden), nn.ELU(),
        )
        self.prior_logits = nn.Linear(config.rssm_hidden, stochastic_size)

        # 后验网络: h + o → s
        self.posterior_net = nn.Sequential(
            nn.Linear(config.rssm_deterministic + config.rssm_hidden, config.rssm_hidden), nn.ELU(),
        )
        self.posterior_logits = nn.Linear(config.rssm_hidden, stochastic_size)

    def initial_state(self, batch_size: int, device: str = "cpu") -> Dict[str, torch.Tensor]:
        """初始化隐状态"""
        return {
            "deterministic": torch.zeros(batch_size, self.config.rssm_deterministic, device=device),
            "stochastic": torch.zeros(batch_size, self.config.rssm_stochastic * self.config.rssm_discrete, device=device),
        }

    def forward(self, prev_state: Dict, action: torch.Tensor, obs_embed: Optional[torch.Tensor] = None) -> Dict:
        """
        单步前向传播

        Args:
            prev_state: 上一时刻的隐状态
            action: 动作 [B, A]
            obs_embed: 观测编码 [B, D] (训练时有，推理时无)

        Returns:
            新隐状态 + 先验/后验分布
        """
        # 确定性状态转移
        rnn_input = torch.cat([prev_state["stochastic"], action], dim=-1)
        deterministic = self.rnn(rnn_input, prev_state["deterministic"])

        # 先验
        prior_h = self.prior_net(deterministic)
        prior_logits = self.prior_logits(prior_h)
        prior_logits = prior_logits.view(-1, self.config.rssm_stochastic, self.config.rssm_discrete)
        prior = torch.distributions.OneHotCategorical(logits=prior_logits)
        prior_sample = F.one_hot(prior.probs.argmax(dim=-1), self.config.rssm_discrete).flatten(-2).float()

        if obs_embed is not None:
            # 后验 (训练模式)
            post_input = torch.cat([deterministic, obs_embed], dim=-1)
            post_h = self.posterior_net(post_input)
            post_logits = self.posterior_logits(post_h)
            post_logits = post_logits.view(-1, self.config.rssm_stochastic, self.config.rssm_discrete)
            posterior = torch.distributions.OneHotCategorical(logits=post_logits)
            post_sample = F.one_hot(posterior.probs.argmax(dim=-1), self.config.rssm_discrete).flatten(-2).float()
        else:
            posterior = prior
            post_sample = prior_sample

        new_state = {
            "deterministic": deterministic,
            "stochastic": post_sample,
        }

        return {
            "state": new_state,
            "prior": prior,
            "posterior": posterior,
            "prior_sample": prior_sample,
            "posterior_sample": post_sample,
        }


class WorldModel(nn.Module):
    """
    完整世界模型 = Encoder + RSSM + Decoder + Reward + Continue

    训练目标:
      1. 重建损失: 重建观测
      2. KL 损失: 先验接近后验
      3. 奖励预测损失: 预测即时奖励
      4. 继续预测损失: 预测是否 done
    """

    def __init__(self, config: DreamerConfig, use_image: bool = False):
        super().__init__()
        self.config = config
        self.use_image = use_image
        stochastic_size = config.rssm_stochastic * config.rssm_discrete
        state_size = config.rssm_deterministic + stochastic_size

        # 编码器
        if use_image:
            self.encoder = ConvEncoder(hidden_dim=config.rssm_hidden)
        else:
            self.encoder = StateEncoder(config.obs_dim, hidden_dim=config.rssm_hidden)

        # RSSM
        self.rssm = RSSM(config)

        # 解码器
        if use_image:
            self.decoder = nn.Sequential(
                nn.Linear(state_size, 256), nn.ELU(),
                nn.Linear(256, 3 * 64 * 64),
            )
        else:
            self.decoder = nn.Sequential(
                nn.Linear(state_size, 256), nn.ELU(),
                nn.Linear(256, config.obs_dim),
            )

        # 奖励预测器
        self.reward_head = nn.Sequential(
            nn.Linear(state_size, 256), nn.ELU(),
            nn.Linear(256, 255),  # 两部分: 前254是离散分布, 最后1个是偏移
        )

        # 继续预测器
        self.continue_head = nn.Sequential(
            nn.Linear(state_size, 256), nn.ELU(),
            nn.Linear(256, 2),  # 二分类
        )

    def forward(self, observations, actions, rewards=None, dones=None):
        """
        训练前向传播: 给定序列数据，计算世界模型损失

        Args:
            observations: [B, T, obs_dim]
            actions: [B, T, action_dim]
            rewards: [B, T] (可选)
            dones: [B, T] (可选)

        Returns:
            dict: 各项损失
        """
        batch_size, seq_len = observations.shape[:2]
        device = observations.device

        # 初始化状态
        state = self.rssm.initial_state(batch_size, device)

        kl_losses = []
        recon_losses = []
        reward_losses = []
        continue_losses = []

        for t in range(seq_len):
            obs_t = observations[:, t]
            action_t = actions[:, t]
            obs_embed = self.encoder(obs_t)

            # RSSM 前向
            result = self.rssm(state, action_t, obs_embed)
            state = result["state"]

            # KL 散度损失
            kl = torch.distributions.kl_divergence(result["posterior"], result["prior"])
            kl = kl.sum(dim=-1).mean()
            kl_losses.append(kl)

            # 重建损失
            state_cat = torch.cat([state["deterministic"], state["stochastic"]], dim=-1)
            recon = self.decoder(state_cat)
            if self.use_image:
                recon = recon.view(-1, 3, 64, 64)
                recon_loss = F.mse_loss(recon, obs_t.view(-1, 3, 64, 64))
            else:
                recon_loss = F.mse_loss(recon, obs_t)
            recon_losses.append(recon_loss)

            # 奖励预测损失
            if rewards is not None:
                reward_pred = self.reward_head(state_cat)
                # 简化: 使用 MSE
                reward_loss = F.mse_loss(reward_pred.mean(dim=-1, keepdim=True), rewards[:, t:t+1])
                reward_losses.append(reward_loss)

            # 继续预测损失
            if dones is not None:
                cont_pred = self.continue_head(state_cat)
                cont_target = (1 - dones[:, t]).long()
                cont_loss = F.cross_entropy(cont_pred, cont_target)
                continue_losses.append(cont_loss)

        # 汇总损失
        total_kl = torch.stack(kl_losses).mean()
        total_recon = torch.stack(recon_losses).mean()
        total_reward = torch.stack(reward_losses).mean() if reward_losses else torch.tensor(0.0)
        total_continue = torch.stack(continue_losses).mean() if continue_losses else torch.tensor(0.0)

        # KL free bits (防止 KL 崩塌)
        kl_free = max(total_kl.item(), 1.0)

        total_loss = total_recon + kl_free + 0.5 * total_reward + 0.1 * total_continue

        return {
            "total_loss": total_loss,
            "kl_loss": total_kl,
            "recon_loss": total_recon,
            "reward_loss": total_reward,
            "continue_loss": total_continue,
        }

    @torch.no_grad()
    def imagine(self, initial_state, policy, horizon: int) -> Dict:
        """
        在虚拟梦境中想象轨迹，供 Actor-Critic 训练

        Args:
            initial_state: 初始隐状态
            policy: 策略网络 state → action
            horizon: 想象步数

        Returns:
            想象的状态序列、奖励序列等
        """
        state = initial_state
        imagined_states = []
        imagined_rewards = []
        imagined_continues = []

        for _ in range(horizon):
            state_cat = torch.cat([state["deterministic"], state["stochastic"]], dim=-1)

            # 策略选择动作
            action = policy(state_cat)

            # 在梦境中前进一步 (无观测，用先验)
            result = self.rssm(state, action, obs_embed=None)
            state = result["state"]

            state_cat = torch.cat([state["deterministic"], state["stochastic"]], dim=-1)

            # 预测奖励和继续
            reward = self.reward_head(state_cat).mean(dim=-1)
            cont = F.softmax(self.continue_head(state_cat), dim=-1)[:, 0]

            imagined_states.append(state_cat)
            imagined_rewards.append(reward)
            imagined_continues.append(cont)

        return {
            "states": torch.stack(imagined_states, dim=1),
            "rewards": torch.stack(imagined_rewards, dim=1),
            "continues": torch.stack(imagined_continues, dim=1),
        }


class DreamerActor(nn.Module):
    """DreamerV3 Actor: 在隐空间中决策"""

    def __init__(self, state_size: int, action_dim: int, hidden_dim: int = 512):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(state_size, hidden_dim), nn.ELU(),
            nn.Linear(hidden_dim, hidden_dim), nn.ELU(),
            nn.Linear(hidden_dim, action_dim),
            nn.Tanh(),
        )

    def forward(self, state: torch.Tensor) -> torch.Tensor:
        return self.net(state)


class DreamerCritic(nn.Module):
    """DreamerV3 Critic: 价值函数"""

    def __init__(self, state_size: int, hidden_dim: int = 512):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(state_size, hidden_dim), nn.ELU(),
            nn.Linear(hidden_dim, hidden_dim), nn.ELU(),
            nn.Linear(hidden_dim, 255),  # 离散价值分布
        )

    def forward(self, state: torch.Tensor) -> torch.Tensor:
        return self.net(state)
