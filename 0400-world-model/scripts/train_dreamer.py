"""
DreamerV3 训练脚本
==================
世界模型训练 + 虚拟梦境 Actor-Critic 训练。

使用方法:
  python train_dreamer.py --total_steps 500000
  python train_dreamer.py --quick
"""

import os
import sys
import argparse
import time
from pathlib import Path
from collections import deque

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np

from common.config import WorldModelConfig, DeviceConfig
from common.utils import set_seed, save_metrics
from common.logger import setup_logger

from models.dreamerv3 import (
    DreamerConfig, WorldModel, DreamerActor, DreamerCritic
)


class ReplayBuffer:
    """简单经验回放缓冲区"""

    def __init__(self, capacity: int = 100000, obs_dim: int = 12, action_dim: int = 5):
        self.capacity = capacity
        self.ptr = 0
        self.size = 0
        self.obs = np.zeros((capacity, obs_dim), dtype=np.float32)
        self.actions = np.zeros((capacity, action_dim), dtype=np.float32)
        self.rewards = np.zeros(capacity, dtype=np.float32)
        self.dones = np.zeros(capacity, dtype=np.float32)

    def add(self, obs, action, reward, done):
        self.obs[self.ptr] = obs
        self.actions[self.ptr] = action
        self.rewards[self.ptr] = reward
        self.dones[self.ptr] = float(done)
        self.ptr = (self.ptr + 1) % self.capacity
        self.size = min(self.size + 1, self.capacity)

    def sample_sequence(self, batch_size: int, seq_len: int):
        """采样序列数据 (用于世界模型训练)"""
        indices = np.random.randint(0, self.size - seq_len, size=batch_size)
        obs_seq = np.stack([self.obs[i:i+seq_len] for i in indices])
        action_seq = np.stack([self.actions[i:i+seq_len] for i in indices])
        reward_seq = np.stack([self.rewards[i:i+seq_len] for i in indices])
        done_seq = np.stack([self.dones[i:i+seq_len] for i in indices])
        return (
            torch.FloatTensor(obs_seq),
            torch.FloatTensor(action_seq),
            torch.FloatTensor(reward_seq),
            torch.FloatTensor(done_seq),
        )


def make_env(env_name: str = "mujoco_arm"):
    """创建环境"""
    if env_name == "mujoco_arm":
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from envs.mujoco_rl_env import MuJoCoRLEnv
        return MuJoCoRLEnv(task="reach", reward_type="dense")
    else:
        import gymnasium as gym
        return gym.make(env_name)


def train_dreamer(config: DreamerConfig, total_steps: int = 500000, device: str = "cpu"):
    """DreamerV3 训练主循环"""
    env = make_env()

    obs_dim = env.observation_space.shape[0]
    action_dim = env.action_space.shape[0]
    config.obs_dim = obs_dim
    config.action_dim = action_dim

    stochastic_size = config.rssm_stochastic * config.rssm_discrete
    state_size = config.rssm_deterministic + stochastic_size

    # 初始化模型
    world_model = WorldModel(config, use_image=False).to(device)
    actor = DreamerActor(state_size, action_dim, config.actor_hidden).to(device)
    critic = DreamerCritic(state_size, config.critic_hidden).to(device)

    # 优化器
    wm_optimizer = torch.optim.Adam(world_model.parameters(), lr=config.learning_rate)
    actor_optimizer = torch.optim.Adam(actor.parameters(), lr=config.actor_lr)
    critic_optimizer = torch.optim.Adam(critic.parameters(), lr=config.critic_lr)

    # 经验回放
    buffer = ReplayBuffer(capacity=100000, obs_dim=obs_dim, action_dim=action_dim)

    save_dir = Path("./checkpoints/dreamer_v1")
    save_dir.mkdir(parents=True, exist_ok=True)

    # 收集初始数据
    print("收集初始经验...")
    obs, _ = env.reset()
    for _ in range(5000):
        action = env.action_space.sample()
        next_obs, reward, terminated, truncated, _ = env.step(action)
        buffer.add(obs, action, reward, terminated or truncated)
        obs = next_obs if not (terminated or truncated) else env.reset()[0]

    print(f"开始 DreamerV3 训练 (total_steps={total_steps})...")

    obs, _ = env.reset()
    episode_reward = 0
    episode = 0
    step = 0

    while step < total_steps:
        # ── 环境交互 ──
        obs_tensor = torch.FloatTensor(obs).unsqueeze(0).to(device)

        with torch.no_grad():
            if buffer.size < 5000:
                action = env.action_space.sample()
            else:
                # 用世界模型编码当前状态，然后用 actor 选择动作
                obs_embed = world_model.encoder(obs_tensor)
                rssm_state = world_model.rssm.initial_state(1, device)
                # 简化: 直接用观测编码作为状态
                state_cat = torch.cat([rssm_state["deterministic"], rssm_state["stochastic"]], dim=-1)
                action = actor(obs_embed).cpu().numpy()[0]

        next_obs, reward, terminated, truncated, _ = env.step(action)
        done = terminated or truncated

        buffer.add(obs, action, reward, done)
        episode_reward += reward
        step += 1

        if done:
            episode += 1
            if episode % 10 == 0:
                print(f"  Episode {episode} | Step {step} | Reward: {episode_reward:.2f}")
            obs, _ = env.reset()
            episode_reward = 0
        else:
            obs = next_obs

        # ── 世界模型训练 ──
        if buffer.size >= 5000 and step % 10 == 0:
            obs_seq, action_seq, reward_seq, done_seq = buffer.sample_sequence(
                config.batch_size, config.sequence_length
            )
            obs_seq = obs_seq.to(device)
            action_seq = action_seq.to(device)
            reward_seq = reward_seq.to(device)
            done_seq = done_seq.to(device)

            # 世界模型更新
            wm_result = world_model(obs_seq, action_seq, reward_seq, done_seq)
            wm_optimizer.zero_grad()
            wm_result["total_loss"].backward()
            torch.nn.utils.clip_grad_norm_(world_model.parameters(), 100.0)
            wm_optimizer.step()

            # ── Actor-Critic 在梦境中训练 ──
            if step % 20 == 0:
                # 获取初始状态
                init_obs = torch.FloatTensor(
                    np.stack([buffer.obs[np.random.randint(0, buffer.size)] for _ in range(config.batch_size)])
                ).to(device)

                with torch.no_grad():
                    obs_embed = world_model.encoder(init_obs)
                    rssm_state = world_model.rssm.initial_state(config.batch_size, device)
                    result = world_model.rssm(rssm_state, torch.zeros(config.batch_size, action_dim).to(device), obs_embed)
                    init_state = result["state"]

                # 在梦境中想象
                imagined = world_model.imagine(init_state, actor, config.imagination_horizon)

                # Actor 更新
                imagined_states = imagined["states"].detach()
                imagined_rewards = imagined["rewards"].detach()
                imagined_continues = imagined["continues"].detach()

                # 计算 returns
                returns = torch.zeros_like(imagined_rewards)
                running_return = torch.zeros(config.batch_size, device=device)
                for t in reversed(range(imagined_rewards.size(1))):
                    running_return = imagined_rewards[:, t] + config.gamma * imagined_continues[:, t] * running_return
                    returns[:, t] = running_return

                # Actor loss: 最大化 returns
                actions_pred = actor(imagined_states.flatten(0, 1)).view(config.batch_size, config.imagination_horizon, -1)
                actor_loss = -returns.mean()

                actor_optimizer.zero_grad()
                actor_loss.backward()
                torch.nn.utils.clip_grad_norm_(actor.parameters(), 100.0)
                actor_optimizer.step()

                # Critic 更新
                value_pred = critic(imagined_states.flatten(0, 1)).view(config.batch_size, config.imagination_horizon, -1)
                # 简化: 用 MSE
                critic_target = returns.unsqueeze(-1).expand_as(value_pred[:, :, :1])
                critic_loss = F.mse_loss(value_pred[:, :, :1], critic_target.detach())

                critic_optimizer.zero_grad()
                critic_loss.backward()
                torch.nn.utils.clip_grad_norm_(critic.parameters(), 100.0)
                critic_optimizer.step()

        # 保存
        if step % 50000 == 0 and step > 0:
            torch.save({
                "world_model": world_model.state_dict(),
                "actor": actor.state_dict(),
                "critic": critic.state_dict(),
            }, str(save_dir / f"dreamer_step_{step}.pt"))

    # 保存最终模型
    torch.save({
        "world_model": world_model.state_dict(),
        "actor": actor.state_dict(),
        "critic": critic.state_dict(),
    }, str(save_dir / "dreamer_final.pt"))

    print(f"Training complete! Model saved → {save_dir}")
    env.close()


def main():
    parser = argparse.ArgumentParser(description="Train DreamerV3")
    parser.add_argument("--total_steps", type=int, default=500000)
    parser.add_argument("--quick", action="store_true", help="Quick test")
    parser.add_argument("--device", type=str, default=None)
    args = parser.parse_args()

    device_config = DeviceConfig()
    device = args.device or device_config.resolve_device()
    set_seed(42)

    config = DreamerConfig()
    if args.quick:
        args.total_steps = 5000

    print("=" * 60)
    print(f"DreamerV3 Training | Device: {device} | Steps: {args.total_steps}")
    print("=" * 60)

    train_dreamer(config, args.total_steps, device)


if __name__ == "__main__":
    main()
