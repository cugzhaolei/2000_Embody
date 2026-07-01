"""
VLA 评估脚本
============
评估训练好的 VLA 模型在仿真环境中的表现。

使用方法:
  python eval_vla.py --model vla --checkpoint ./checkpoints/vla_vla/best_model.pt
  python eval_vla.py --model act --checkpoint ./checkpoints/act_vla/best_model.pt
  python eval_vla.py --model diffusion --checkpoint ./checkpoints/diffusion_vla/best_model.pt
"""

import os
import sys
import argparse
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import torch
import numpy as np
from transformers import AutoTokenizer

from common.config import VLAConfig, DeviceConfig
from common.utils import load_checkpoint
from common.visualization import save_frames_as_gif, plot_action_trajectory

from models.vlafactory import VLABaseModel
from models.act import ACTModel
from models.diffusion_policy import DiffusionPolicyModel


def build_model(model_type: str, config: VLAConfig, device: str):
    """构建模型"""
    if model_type == "vla":
        model = VLABaseModel(config.vision_model, config.language_model, config.action_dim)
    elif model_type == "act":
        model = ACTModel(config.vision_model, config.language_model, config.action_dim)
    elif model_type == "diffusion":
        model = DiffusionPolicyModel(config.vision_model, config.language_model, config.action_dim)
    else:
        raise ValueError(f"Unknown model: {model_type}")
    return model.to(device)


@torch.no_grad()
def evaluate(model, env, tokenizer, model_type, config, device, num_episodes=10, save_dir=None):
    """在仿真环境中评估模型"""
    model.eval()
    results = []

    for ep in range(num_episodes):
        obs = env.reset()
        episode_reward = 0
        episode_steps = 0
        frames = []
        actions_list = []

        instruction = "pick up the red block"
        encoded = tokenizer(instruction, max_length=config.max_text_length,
                            padding="max_length", truncation=True, return_tensors="pt")
        input_ids = encoded.input_ids.to(device)
        attention_mask = encoded.attention_mask.to(device)

        for step in range(env.max_steps):
            # 准备图像输入
            from torchvision import transforms
            from PIL import Image
            transform = transforms.Compose([
                transforms.Resize((224, 224)),
                transforms.ToTensor(),
                transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
            ])
            image_tensor = transform(Image.fromarray(obs["image"])).unsqueeze(0).to(device)

            # 模型预测
            if model_type == "vla":
                action = model(image_tensor, input_ids, attention_mask)
                action = action[0].cpu().numpy()
            elif model_type == "act":
                action = model.get_action(image_tensor, input_ids, attention_mask)
                action = action[0].cpu().numpy()
            elif model_type == "diffusion":
                action = model.get_action(image_tensor, input_ids, attention_mask)
                action = action[0].cpu().numpy()

            # 执行动作
            obs, reward, done, info = env.step(action)
            episode_reward += reward
            episode_steps += 1
            actions_list.append(action)

            if save_dir:
                frames.append(obs["image"])

            if done:
                break

        success = episode_reward > 0.5
        results.append({
            "episode": ep + 1,
            "reward": episode_reward,
            "steps": episode_steps,
            "success": success,
        })

        print(f"  Episode {ep+1}: Reward={episode_reward:.3f}, Steps={episode_steps}, Success={success}")

        # 保存轨迹
        if save_dir and frames:
            ep_dir = Path(save_dir) / f"episode_{ep+1:03d}"
            ep_dir.mkdir(parents=True, exist_ok=True)
            save_frames_as_gif(frames, str(ep_dir / "trajectory.gif"))
            plot_action_trajectory(
                np.array(actions_list),
                action_labels=["dx", "dy", "dz", "droll", "dpitch", "dyaw", "grip"],
                save_path=str(ep_dir / "actions.png"),
            )

    # 统计
    success_rate = sum(r["success"] for r in results) / len(results)
    avg_reward = np.mean([r["reward"] for r in results])
    avg_steps = np.mean([r["steps"] for r in results])

    print(f"\n{'='*40}")
    print(f"评估结果 ({num_episodes} episodes)")
    print(f"  Success Rate: {success_rate:.1%}")
    print(f"  Avg Reward:   {avg_reward:.3f}")
    print(f"  Avg Steps:    {avg_steps:.1f}")
    print(f"{'='*40}")

    return results


def main():
    parser = argparse.ArgumentParser(description="Evaluate VLA Model")
    parser.add_argument("--model", type=str, default="vla", choices=["vla", "act", "diffusion"])
    parser.add_argument("--checkpoint", type=str, required=True, help="Path to checkpoint")
    parser.add_argument("--env", type=str, default="mujoco", choices=["mujoco", "pybullet"])
    parser.add_argument("--num_episodes", type=int, default=10)
    parser.add_argument("--save_dir", type=str, default="./eval_output")
    args = parser.parse_args()

    config = VLAConfig()
    device = DeviceConfig().resolve_device()

    # 加载模型
    print("加载模型...")
    model = build_model(args.model, config, device)
    ckpt = load_checkpoint(args.checkpoint, model, device=device)
    print(f"  Loaded from epoch {ckpt['epoch']+1}")

    tokenizer = AutoTokenizer.from_pretrained(config.language_model)

    # 创建环境
    print("创建环境...")
    if args.env == "mujoco":
        from envs.mujoco_env import MuJoCoArmEnv
        env = MuJoCoArmEnv(render=False, image_size=(224, 224))
    else:
        from envs.pybullet_env import PyBulletArmEnv
        env = PyBulletArmEnv(render=False, image_size=(224, 224))

    # 评估
    print(f"评估 {args.num_episodes} 个 episode...")
    evaluate(model, env, tokenizer, args.model, config, device,
             num_episodes=args.num_episodes, save_dir=args.save_dir)
    env.close()


if __name__ == "__main__":
    main()
