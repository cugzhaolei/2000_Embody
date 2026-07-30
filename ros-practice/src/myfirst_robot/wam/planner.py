"""
CEM 规划器 — 基于世界模型的最优动作搜索
Cross-Entropy Method: 采样→评估→选择精英→更新分布
"""
import torch
import numpy as np
from typing import Tuple


class CEMPlanner:
    """
    Cross-Entropy Method 规划器

    流程:
    1. 从分布 N(μ, σ) 采样 N 条动作序列
    2. 用世界模型评估每条序列的累积奖励
    3. 选择 top-K 精英样本
    4. 用精英样本更新 μ, σ
    5. 重复 K 轮，返回最优序列
    """

    def __init__(self, world_model, horizon: int = 15,
                 num_samples: int = 500, elite_ratio: float = 0.1,
                 iterations: int = 5, action_dim: int = 2):
        self.world_model = world_model
        self.horizon = horizon
        self.num_samples = num_samples
        self.elite_ratio = elite_ratio
        self.iterations = iterations
        self.action_dim = action_dim
        self.elite_num = max(1, int(num_samples * elite_ratio))

        # 差速驱动动作约束
        self.max_linear = 0.7   # m/s
        self.max_angular = 1.0  # rad/s

    def plan(self, current_scan: torch.Tensor) -> Tuple[torch.Tensor, float]:
        """
        规划最优动作序列
        返回: (best_action_seq [H, action_dim], max_risk)
        """
        scan = current_scan.unsqueeze(0)  # [1, scan_dim]

        mean = torch.zeros(self.horizon, self.action_dim)
        std = torch.ones(self.horizon, self.action_dim) * 0.5

        best_risk = 1.0

        for _ in range(self.iterations):
            # 1. 采样
            samples = mean + std * torch.randn(
                self.num_samples, self.horizon, self.action_dim)

            # 裁剪
            samples[..., 0] = samples[..., 0].clamp(-self.max_linear, self.max_linear)
            samples[..., 1] = samples[..., 1].clamp(-self.max_angular, self.max_angular)

            # 2. 评估 (分批)
            all_scores = []
            all_risks = []
            batch_size = 50

            for i in range(0, self.num_samples, batch_size):
                batch = samples[i:i + batch_size]
                batch_scan = scan.expand(batch.shape[0], -1)

                with torch.no_grad():
                    result = self.world_model.predict_future(batch_scan, batch)

                # 累积奖励 - 碰撞惩罚
                total_reward = result['future_rewards'].squeeze(-1).sum(dim=1)
                collision_penalty = result['collision_probs'].squeeze(-1).sum(dim=1) * 10.0
                score = total_reward - collision_penalty

                all_scores.append(score)
                all_risks.append(result['collision_probs'].mean(dim=1))

            scores = torch.cat(all_scores)
            risks = torch.cat(all_risks)

            # 3. 精英选择
            elite_idx = scores.topk(self.elite_num).indices
            elite_samples = samples[elite_idx]
            best_risk = risks[elite_idx[0]].max().item()

            # 4. 更新分布
            mean = elite_samples.mean(dim=0)
            std = elite_samples.std(dim=0) + 1e-6

        return mean, best_risk

    def safe_action(self, current_scan: torch.Tensor,
                    desired_vx: float, desired_wz: float) -> Tuple[torch.Tensor, float]:
        """
        安全过滤: 检查期望动作的碰撞风险
        返回: (safe_action [2], collision_risk)
        """
        desired = torch.tensor([desired_vx, desired_wz])

        # 构造动作序列 (期望动作重复 H 步)
        action_seq = desired.unsqueeze(0).unsqueeze(0).repeat(1, self.horizon, 1)
        scan = current_scan.unsqueeze(0)

        with torch.no_grad():
            result = self.world_model.predict_future(scan, action_seq)

        max_risk = result['collision_probs'][0].max().item()

        if max_risk > 0.5:
            return torch.zeros(2), max_risk
        elif max_risk > 0.2:
            scale = 1.0 - (max_risk - 0.2) / 0.3
            return desired * scale, max_risk
        else:
            return desired, max_risk


class SafetyVerifier:
    """动作序列安全验证器"""

    def __init__(self, world_model, max_collision_prob: float = 0.1):
        self.world_model = world_model
        self.max_prob = max_collision_prob

    def verify(self, scan: torch.Tensor, action_seq: torch.Tensor):
        with torch.no_grad():
            result = self.world_model.predict_future(
                scan.unsqueeze(0), action_seq.unsqueeze(0))

        probs = result['collision_probs'][0]
        max_prob = probs.max().item()
        risky_step = probs.argmax().item()
        is_safe = max_prob < self.max_prob
        return is_safe, max_prob, risky_step
