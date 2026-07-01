"""
SAC (Soft Actor-Critic) 算法
============================
最大熵强化学习算法，适合连续动作控制。
相比 PPO 更样本高效，且自动调节探索强度。

核心组件:
  - SACActor: 策略网络 (高斯策略)
  - SACCritic: 双 Q 网络
  - SAC: SAC 训练器

参考: "Soft Actor-Critic: Off-Policy Maximum Entropy Deep RL with a Stochastic Actor" (Haarnoja et al., 2018)
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
from typing import Tuple, Optional
from dataclasses import dataclass
import copy


@dataclass
class SACConfig:
    """SAC 超参数"""
    learning_rate: float = 3e-4
    gamma: float = 0.99
    tau: float = 0.005           # 目标网络软更新系数
    alpha: float = 0.2           # 熵正则化系数 (auto=True 时自动调节)
    auto_alpha: bool = True      # 自动调节 alpha
    target_entropy: float = None # 目标熵 (None=自动 -dim(A))
    buffer_size: int = 100000
    batch_size: int = 256
    hidden_dim: int = 256


class SACActor(nn.Module):
    """SAC 策略网络: 重参数化技巧"""

    def __init__(self, obs_dim: int, action_dim: int, hidden_dim: int = 256, action_scale: float = 1.0):
        super().__init__()
        self.action_scale = action_scale
        self.net = nn.Sequential(
            nn.Linear(obs_dim, hidden_dim), nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim), nn.ReLU(),
        )
        self.mean_head = nn.Linear(hidden_dim, action_dim)
        self.log_std_head = nn.Linear(hidden_dim, action_dim)

    def forward(self, obs: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        """返回 (action, log_prob)"""
        features = self.net(obs)
        mean = self.mean_head(features)
        log_std = self.log_std_head(features).clamp(-20, 2)
        std = torch.exp(log_std)

        # 重参数化
        normal = torch.distributions.Normal(mean, std)
        x_t = normal.rsample()
        action = torch.tanh(x_t) * self.action_scale

        # 计算 log_prob (考虑 tanh 变换)
        log_prob = normal.log_prob(x_t).sum(dim=-1)
        log_prob -= torch.log(1 - (action / self.action_scale).pow(2) + 1e-6).sum(dim=-1)

        return action, log_prob

    def get_action(self, obs: torch.Tensor) -> torch.Tensor:
        """推理: 返回确定性动作"""
        features = self.net(obs)
        mean = self.mean_head(features)
        return torch.tanh(mean) * self.action_scale


class SACCritic(nn.Module):
    """双 Q 网络"""

    def __init__(self, obs_dim: int, action_dim: int, hidden_dim: int = 256):
        super().__init__()
        self.q1 = nn.Sequential(
            nn.Linear(obs_dim + action_dim, hidden_dim), nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim), nn.ReLU(),
            nn.Linear(hidden_dim, 1),
        )
        self.q2 = nn.Sequential(
            nn.Linear(obs_dim + action_dim, hidden_dim), nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim), nn.ReLU(),
            nn.Linear(hidden_dim, 1),
        )

    def forward(self, obs: torch.Tensor, action: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        x = torch.cat([obs, action], dim=-1)
        return self.q1(x), self.q2(x)


class ReplayBuffer:
    """经验回放缓冲区"""

    def __init__(self, obs_dim: int, action_dim: int, capacity: int = 100000):
        self.capacity = capacity
        self.ptr = 0
        self.size = 0

        self.obs = np.zeros((capacity, obs_dim), dtype=np.float32)
        self.actions = np.zeros((capacity, action_dim), dtype=np.float32)
        self.rewards = np.zeros(capacity, dtype=np.float32)
        self.next_obs = np.zeros((capacity, obs_dim), dtype=np.float32)
        self.dones = np.zeros(capacity, dtype=np.float32)

    def add(self, obs, action, reward, next_obs, done):
        self.obs[self.ptr] = obs
        self.actions[self.ptr] = action
        self.rewards[self.ptr] = reward
        self.next_obs[self.ptr] = next_obs
        self.dones[self.ptr] = done
        self.ptr = (self.ptr + 1) % self.capacity
        self.size = min(self.size + 1, self.capacity)

    def sample(self, batch_size: int) -> dict:
        indices = np.random.randint(0, self.size, size=batch_size)
        return {
            "obs": torch.FloatTensor(self.obs[indices]),
            "actions": torch.FloatTensor(self.actions[indices]),
            "rewards": torch.FloatTensor(self.rewards[indices]).unsqueeze(1),
            "next_obs": torch.FloatTensor(self.next_obs[indices]),
            "dones": torch.FloatTensor(self.dones[indices]).unsqueeze(1),
        }


class SAC:
    """
    SAC 训练器

    使用方法:
      sac = SAC(obs_dim, action_dim, config)
      for step in range(total_steps):
          action = sac.select_action(obs)
          next_obs, reward, done, _, _ = env.step(action)
          sac.replay_buffer.add(obs, action, reward, next_obs, done)
          if len(sac.replay_buffer) > batch_size:
              sac.update()
    """

    def __init__(self, obs_dim: int, action_dim: int, config: Optional[SACConfig] = None, device: str = "cpu"):
        self.config = config or SACConfig()
        self.device = device
        self.action_dim = action_dim

        # 网络
        self.actor = SACActor(obs_dim, action_dim, self.config.hidden_dim).to(device)
        self.critic = SACCritic(obs_dim, action_dim, self.config.hidden_dim).to(device)
        self.critic_target = copy.deepcopy(self.critic).to(device)

        # 优化器
        self.actor_optimizer = torch.optim.Adam(self.actor.parameters(), lr=self.config.learning_rate)
        self.critic_optimizer = torch.optim.Adam(self.critic.parameters(), lr=self.config.learning_rate)

        # 自动调节 alpha
        self.auto_alpha = self.config.auto_alpha
        if self.auto_alpha:
            self.target_entropy = self.config.target_entropy or -action_dim
            self.log_alpha = torch.zeros(1, requires_grad=True, device=device)
            self.alpha_optimizer = torch.optim.Adam([self.log_alpha], lr=self.config.learning_rate)
            self.alpha = self.log_alpha.exp()
        else:
            self.alpha = self.config.alpha

        # 经验回放
        self.replay_buffer = ReplayBuffer(obs_dim, action_dim, self.config.buffer_size)

    def select_action(self, obs: np.ndarray, evaluate: bool = False) -> np.ndarray:
        """选择动作"""
        obs_tensor = torch.FloatTensor(obs).unsqueeze(0).to(self.device)
        with torch.no_grad():
            if evaluate:
                action = self.actor.get_action(obs_tensor)
            else:
                action, _ = self.actor(obs_tensor)
        return action[0].cpu().numpy()

    def update(self) -> dict:
        """SAC 更新"""
        if len(self.replay_buffer) < self.config.batch_size:
            return {}

        batch = self.replay_buffer.sample(self.config.batch_size)
        obs = batch["obs"].to(self.device)
        actions = batch["actions"].to(self.device)
        rewards = batch["rewards"].to(self.device)
        next_obs = batch["next_obs"].to(self.device)
        dones = batch["dones"].to(self.device)

        # ── Critic 更新 ──
        with torch.no_grad():
            next_actions, next_log_probs = self.actor(next_obs)
            q1_target, q2_target = self.critic_target(next_obs, next_actions)
            q_target = torch.min(q1_target, q2_target) - self.alpha * next_log_probs.unsqueeze(1)
            q_backup = rewards + self.config.gamma * (1 - dones) * q_target

        q1, q2 = self.critic(obs, actions)
        critic_loss = F.mse_loss(q1, q_backup) + F.mse_loss(q2, q_backup)

        self.critic_optimizer.zero_grad()
        critic_loss.backward()
        self.critic_optimizer.step()

        # ── Actor 更新 ──
        new_actions, log_probs = self.actor(obs)
        q1_new, q2_new = self.critic(obs, new_actions)
        q_new = torch.min(q1_new, q2_new)
        actor_loss = (self.alpha * log_probs.unsqueeze(1) - q_new).mean()

        self.actor_optimizer.zero_grad()
        actor_loss.backward()
        self.actor_optimizer.step()

        # ── Alpha 更新 ──
        if self.auto_alpha:
            alpha_loss = -(self.log_alpha * (log_probs + self.target_entropy).detach()).mean()
            self.alpha_optimizer.zero_grad()
            alpha_loss.backward()
            self.alpha_optimizer.step()
            self.alpha = self.log_alpha.exp()

        # ── 目标网络软更新 ──
        for param, target_param in zip(self.critic.parameters(), self.critic_target.parameters()):
            target_param.data.copy_(self.config.tau * param.data + (1 - self.config.tau) * target_param.data)

        return {
            "critic_loss": critic_loss.item(),
            "actor_loss": actor_loss.item(),
            "alpha": self.alpha.item() if isinstance(self.alpha, torch.Tensor) else self.alpha,
        }

    def save(self, path: str):
        torch.save({
            "actor": self.actor.state_dict(),
            "critic": self.critic.state_dict(),
            "critic_target": self.critic_target.state_dict(),
        }, path)

    def load(self, path: str):
        ckpt = torch.load(path, map_location=self.device, weights_only=False)
        self.actor.load_state_dict(ckpt["actor"])
        self.critic.load_state_dict(ckpt["critic"])
        self.critic_target.load_state_dict(ckpt["critic_target"])
