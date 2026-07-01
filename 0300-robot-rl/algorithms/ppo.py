"""
PPO (Proximal Policy Optimization) 算法
=======================================
从零实现的 PPO 算法，支持连续动作空间。
适用于机械臂控制、四足行走等机器人 RL 任务。

核心组件:
  - ActorCritic: 共享特征提取的 Actor-Critic 网络
  - RolloutBuffer: 经验回放缓冲区
  - PPO: PPO 训练器

参考: "Proximal Policy Optimization Algorithms" (Schulman et al., 2017)
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
from typing import Tuple, Optional
from dataclasses import dataclass


@dataclass
class PPOConfig:
    """PPO 超参数"""
    learning_rate: float = 3e-4
    gamma: float = 0.99
    gae_lambda: float = 0.95
    clip_epsilon: float = 0.2
    value_coef: float = 0.5
    entropy_coef: float = 0.01
    max_grad_norm: float = 0.5
    ppo_epochs: int = 10
    mini_batch_size: int = 64
    rollout_steps: int = 2048


class ActorCritic(nn.Module):
    """Actor-Critic 网络，共享特征提取层"""

    def __init__(self, obs_dim: int, action_dim: int, hidden_dim: int = 256):
        super().__init__()

        # 共享特征提取
        self.shared = nn.Sequential(
            nn.Linear(obs_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
        )

        # Actor: 输出动作均值和标准差
        self.actor_mean = nn.Linear(hidden_dim, action_dim)
        self.actor_log_std = nn.Parameter(torch.zeros(action_dim))

        # Critic: 输出状态价值
        self.critic = nn.Linear(hidden_dim, 1)

        # 初始化
        nn.init.orthogonal_(self.actor_mean.weight, gain=0.01)
        nn.init.orthogonal_(self.critic.weight, gain=1.0)

    def forward(self, obs: torch.Tensor) -> Tuple[torch.distributions.Normal, torch.Tensor]:
        """返回动作分布和价值估计"""
        features = self.shared(obs)
        action_mean = torch.tanh(self.actor_mean(features))
        action_std = torch.exp(self.actor_log_std).expand_as(action_mean)
        dist = torch.distributions.Normal(action_mean, action_std)
        value = self.critic(features)
        return dist, value

    def get_action(self, obs: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        """采样动作，返回 (action, log_prob, value)"""
        dist, value = self.forward(obs)
        action = dist.sample()
        log_prob = dist.log_prob(action).sum(dim=-1)
        return action, log_prob, value.squeeze(-1)

    def evaluate(self, obs: torch.Tensor, actions: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        """评估给定动作，返回 (log_prob, value, entropy)"""
        dist, value = self.forward(obs)
        log_prob = dist.log_prob(actions).sum(dim=-1)
        entropy = dist.entropy().sum(dim=-1)
        return log_prob, value.squeeze(-1), entropy


class RolloutBuffer:
    """经验回放缓冲区，存储 rollout 数据"""

    def __init__(self):
        self.obs = []
        self.actions = []
        self.log_probs = []
        self.rewards = []
        self.values = []
        self.dones = []

    def add(self, obs, action, log_prob, reward, value, done):
        self.obs.append(obs)
        self.actions.append(action)
        self.log_probs.append(log_prob)
        self.rewards.append(reward)
        self.values.append(value)
        self.dones.append(done)

    def compute_returns(self, last_value: float, gamma: float, gae_lambda: float):
        """计算 GAE (Generalized Advantage Estimation) 和 returns"""
        rewards = np.array(self.rewards)
        values = np.array(self.values + [last_value])
        dones = np.array(self.dones)

        advantages = np.zeros_like(rewards)
        last_gae = 0

        for t in reversed(range(len(rewards))):
            delta = rewards[t] + gamma * values[t + 1] * (1 - dones[t]) - values[t]
            advantages[t] = last_gae = delta + gamma * gae_lambda * (1 - dones[t]) * last_gae

        returns = advantages + np.array(self.values)

        self.advantages = advantages
        self.returns = returns

    def get_tensors(self, device: str = "cpu") -> dict:
        """转换为 PyTorch tensor"""
        return {
            "obs": torch.FloatTensor(np.array(self.obs)).to(device),
            "actions": torch.FloatTensor(np.array(self.actions)).to(device),
            "old_log_probs": torch.FloatTensor(np.array(self.log_probs)).to(device),
            "advantages": torch.FloatTensor(self.advantages).to(device),
            "returns": torch.FloatTensor(self.returns).to(device),
        }

    def clear(self):
        self.obs.clear()
        self.actions.clear()
        self.log_probs.clear()
        self.rewards.clear()
        self.values.clear()
        self.dones.clear()

    def __len__(self):
        return len(self.obs)


class PPO:
    """
    PPO 训练器

    使用方法:
      ppo = PPO(obs_dim, action_dim, config)
      for update in range(num_updates):
          buffer = ppo.collect_rollouts(env, num_steps)
          ppo.update(buffer)
    """

    def __init__(self, obs_dim: int, action_dim: int, config: Optional[PPOConfig] = None, device: str = "cpu"):
        self.config = config or PPOConfig()
        self.device = device

        self.model = ActorCritic(obs_dim, action_dim).to(device)
        self.optimizer = torch.optim.Adam(self.model.parameters(), lr=self.config.learning_rate)

    def collect_rollouts(self, env, num_steps: int) -> RolloutBuffer:
        """收集 rollout 数据"""
        buffer = RolloutBuffer()
        obs, _ = env.reset()

        for _ in range(num_steps):
            obs_tensor = torch.FloatTensor(obs).unsqueeze(0).to(self.device)
            with torch.no_grad():
                action, log_prob, value = self.model.get_action(obs_tensor)

            action_np = action[0].cpu().numpy()
            next_obs, reward, terminated, truncated, info = env.step(action_np)
            done = terminated or truncated

            buffer.add(obs, action_np, log_prob[0].cpu().item(), reward, value[0].cpu().item(), float(done))

            obs = next_obs if not done else env.reset()[0]

        # 计算优势
        with torch.no_grad():
            last_obs_tensor = torch.FloatTensor(obs).unsqueeze(0).to(self.device)
            _, last_value = self.model(last_obs_tensor)
            last_value = last_value[0].cpu().item()

        buffer.compute_returns(last_value, self.config.gamma, self.config.gae_lambda)
        return buffer

    def update(self, buffer: RolloutBuffer) -> dict:
        """PPO 更新"""
        data = buffer.get_tensors(self.device)
        advantages = data["advantages"]
        returns = data["returns"]

        # 优势归一化
        advantages = (advantages - advantages.mean()) / (advantages.std() + 1e-8)

        total_loss = 0
        num_updates = 0

        for _ in range(self.config.ppo_epochs):
            # 随机 mini-batch
            indices = torch.randperm(len(buffer))

            for start in range(0, len(buffer), self.config.mini_batch_size):
                end = start + self.config.mini_batch_size
                mb_indices = indices[start:end]

                mb_obs = data["obs"][mb_indices]
                mb_actions = data["actions"][mb_indices]
                mb_old_log_probs = data["old_log_probs"][mb_indices]
                mb_advantages = advantages[mb_indices]
                mb_returns = returns[mb_indices]

                # 评估当前策略
                new_log_probs, values, entropy = self.model.evaluate(mb_obs, mb_actions)

                # PPO clip 损失
                ratio = torch.exp(new_log_probs - mb_old_log_probs)
                surr1 = ratio * mb_advantages
                surr2 = torch.clamp(ratio, 1 - self.config.clip_epsilon, 1 + self.config.clip_epsilon) * mb_advantages
                actor_loss = -torch.min(surr1, surr2).mean()

                # 价值损失
                value_loss = F.mse_loss(values, mb_returns)

                # 熵奖励
                entropy_loss = -entropy.mean()

                # 总损失
                loss = actor_loss + self.config.value_coef * value_loss + self.config.entropy_coef * entropy_loss

                # 梯度更新
                self.optimizer.zero_grad()
                loss.backward()
                nn.utils.clip_grad_norm_(self.model.parameters(), self.config.max_grad_norm)
                self.optimizer.step()

                total_loss += loss.item()
                num_updates += 1

        return {
            "loss": total_loss / num_updates,
            "actor_loss": actor_loss.item(),
            "value_loss": value_loss.item(),
            "entropy": entropy.mean().item(),
        }

    def save(self, path: str):
        torch.save({"model": self.model.state_dict(), "optimizer": self.optimizer.state_dict()}, path)

    def load(self, path: str):
        ckpt = torch.load(path, map_location=self.device, weights_only=False)
        self.model.load_state_dict(ckpt["model"])
        self.optimizer.load_state_dict(ckpt["optimizer"])
