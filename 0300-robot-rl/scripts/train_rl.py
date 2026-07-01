"""
RL 训练脚本
===========
支持 PPO / SAC 在 MuJoCo 机械臂环境上的训练。

使用方法:
  # PPO 训练
  python train_rl.py --algo ppo --total_steps 500000

  # SAC 训练
  python train_rl.py --algo sac --total_steps 500000

  # Gymnasium 标准环境
  python train_rl.py --algo ppo --env HalfCheetah-v4
"""

import os
import sys
import argparse
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import torch
import numpy as np

from common.config import RLConfig, DeviceConfig
from common.utils import set_seed, save_metrics
from common.logger import setup_logger

from algorithms.ppo import PPO, PPOConfig
from algorithms.sac import SAC, SACConfig


def make_env(env_name: str, task: str = "reach"):
    """创建环境"""
    if env_name == "mujoco_arm":
        from envs.mujoco_rl_env import MuJoCoRLEnv
        return MuJoCoRLEnv(task=task, reward_type="dense")
    else:
        try:
            import gymnasium as gym
            return gym.make(env_name)
        except Exception:
            raise ValueError(f"Unknown environment: {env_name}")


def train_ppo(env, config: RLConfig, device: str):
    """PPO 训练"""
    obs_dim = env.observation_space.shape[0]
    action_dim = env.action_space.shape[0]

    ppo_config = PPOConfig(
        learning_rate=config.learning_rate,
        gamma=config.gamma,
        gae_lambda=config.gae_lambda,
        rollout_steps=config.rollout_steps,
        ppo_epochs=config.ppo_epochs,
        mini_batch_size=config.mini_batch_size,
    )

    ppo = PPO(obs_dim, action_dim, ppo_config, device)
    save_dir = Path(config.save_dir) / config.experiment_name
    save_dir.mkdir(parents=True, exist_ok=True)

    print(f"PPO Training: obs_dim={obs_dim}, action_dim={action_dim}")
    print(f"Total timesteps: {config.total_timesteps}")

    episode_rewards = []
    episode_lengths = []
    current_reward = 0
    current_length = 0
    total_steps = 0
    num_updates = config.total_timesteps // config.rollout_steps

    for update in range(num_updates):
        buffer = ppo.collect_rollouts(env, config.rollout_steps)
        metrics = ppo.update(buffer)
        total_steps += len(buffer)

        # 记录
        if (update + 1) % config.log_interval == 0:
            print(f"  Update {update+1}/{num_updates} | Steps: {total_steps} | Loss: {metrics.get('loss', 0):.4f}")

        # 保存
        if (update + 1) % 50 == 0:
            ppo.save(str(save_dir / f"ppo_update_{update+1}.pt"))

    ppo.save(str(save_dir / "ppo_final.pt"))
    print(f"Model saved → {save_dir}")


def train_sac(env, config: RLConfig, device: str):
    """SAC 训练"""
    obs_dim = env.observation_space.shape[0]
    action_dim = env.action_space.shape[0]

    sac_config = SACConfig(
        learning_rate=config.learning_rate,
        gamma=config.gamma,
        buffer_size=100000,
        batch_size=256,
    )

    sac = SAC(obs_dim, action_dim, sac_config, device)
    save_dir = Path(config.save_dir) / config.experiment_name
    save_dir.mkdir(parents=True, exist_ok=True)

    print(f"SAC Training: obs_dim={obs_dim}, action_dim={action_dim}")

    obs, _ = env.reset()
    episode_reward = 0
    episode = 0

    for step in range(config.total_timesteps):
        # 选择动作
        if step < 5000:
            action = env.action_space.sample()  # 随机探索
        else:
            action = sac.select_action(obs, evaluate=False)

        # 执行动作
        next_obs, reward, terminated, truncated, info = env.step(action)
        done = terminated or truncated

        # 存储经验
        sac.replay_buffer.add(obs, action, reward, next_obs, float(done))
        episode_reward += reward

        # 更新
        if step >= 5000:
            metrics = sac.update()

        # Episode 结束
        if done:
            episode += 1
            if episode % config.log_interval == 0:
                print(f"  Episode {episode} | Step {step} | Reward: {episode_reward:.2f}")
            obs, _ = env.reset()
            episode_reward = 0
        else:
            obs = next_obs

        # 保存
        if (step + 1) % 50000 == 0:
            sac.save(str(save_dir / f"sac_step_{step+1}.pt"))

    sac.save(str(save_dir / "sac_final.pt"))
    print(f"Model saved → {save_dir}")


def main():
    parser = argparse.ArgumentParser(description="Train RL Agent")
    parser.add_argument("--algo", type=str, default="ppo", choices=["ppo", "sac"])
    parser.add_argument("--env", type=str, default="mujoco_arm", help="Environment name")
    parser.add_argument("--task", type=str, default="reach", help="Task for mujoco_arm")
    parser.add_argument("--total_steps", type=int, default=500000)
    parser.add_argument("--lr", type=float, default=3e-4)
    parser.add_argument("--save_dir", type=str, default="./checkpoints")
    args = parser.parse_args()

    config = RLConfig()
    config.total_timesteps = args.total_steps
    config.learning_rate = args.lr
    config.save_dir = args.save_dir
    config.experiment_name = f"{args.algo}_{args.env}"

    device = DeviceConfig().resolve_device()
    set_seed(42)

    print("=" * 60)
    print(f"RL Training — {config.experiment_name}")
    print(f"Algo: {args.algo} | Env: {args.env} | Device: {device}")
    print("=" * 60)

    env = make_env(args.env, args.task)

    if args.algo == "ppo":
        train_ppo(env, config, device)
    elif args.algo == "sac":
        train_sac(env, config, device)

    env.close()
    print("Training complete!")


if __name__ == "__main__":
    main()
