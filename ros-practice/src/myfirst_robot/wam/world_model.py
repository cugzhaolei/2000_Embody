"""
World Model — 完整世界模型
编码器(VAE) + RSSM + 解码器 + 奖励/碰撞预测头
"""
import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Dict, Optional
from .rssm import RSSM, gaussian_kl


class WorldModel(nn.Module):
    """
    世界模型: 预测未来观测和奖励

    编码器: LiDAR(360) → 128维隐向量
    RSSM:   (obs, action) → (h, s) 状态空间
    解码器: (h, s) → LiDAR(360) 重建
    奖励头: (h, s) → reward 预测
    碰撞头: (h, s) → collision_prob
    """

    def __init__(self, scan_dim: int = 360, action_dim: int = 2,
                 hidden_dim: int = 200, state_dim: int = 30, obs_dim: int = 128):
        super().__init__()
        self.scan_dim = scan_dim
        self.action_dim = action_dim

        # 观测编码器
        self.encoder = nn.Sequential(
            nn.Linear(scan_dim, 256), nn.ReLU(),
            nn.Linear(256, obs_dim), nn.ReLU(),
        )

        # RSSM
        self.rssm = RSSM(obs_dim, action_dim, hidden_dim, state_dim)

        # 解码器
        self.decoder = nn.Sequential(
            nn.Linear(hidden_dim + state_dim, 256), nn.ReLU(),
            nn.Linear(256, scan_dim),
        )

        # 奖励预测
        self.reward_head = nn.Sequential(
            nn.Linear(hidden_dim + state_dim, 128), nn.ReLU(),
            nn.Linear(128, 1),
        )

        # 碰撞预测
        self.collision_head = nn.Sequential(
            nn.Linear(hidden_dim + state_dim, 128), nn.ReLU(),
            nn.Linear(128, 1), nn.Sigmoid(),
        )

    def encode(self, scan: torch.Tensor) -> torch.Tensor:
        return self.encoder(scan)

    def forward(self, scan_seq: torch.Tensor, action_seq: torch.Tensor) -> Dict:
        """训练前向: 输入观测和动作序列"""
        B, T, _ = scan_seq.shape
        obs_seq = self.encode(scan_seq.reshape(-1, self.scan_dim)).reshape(B, T, -1)

        rssm_out = self.rssm.rollout(obs_seq, action_seq)

        recon_scans, rewards, collisions = [], [], []
        for t in range(T):
            h = rssm_out['hidden_states'][t]
            s = rssm_out['sampled_states'][t]
            hs = torch.cat([h, s], dim=-1)
            recon_scans.append(self.decoder(hs))
            rewards.append(self.reward_head(hs))
            collisions.append(self.collision_head(hs))

        return {
            'recon_scans': torch.stack(recon_scans, dim=1),
            'predicted_rewards': torch.stack(rewards, dim=1),
            'collision_probs': torch.stack(collisions, dim=1),
            'priors': rssm_out['priors'],
            'posteriors': rssm_out['posteriors'],
        }

    def predict_future(self, scan: torch.Tensor, action_seq: torch.Tensor,
                       h: Optional[torch.Tensor] = None,
                       s: Optional[torch.Tensor] = None) -> Dict:
        """推理: 从当前状态预测未来H步"""
        B = scan.shape[0]
        if h is None:
            h = torch.zeros(B, self.rssm.hidden_dim, device=scan.device)
        if s is None:
            obs = self.encode(scan)
            post_mean, post_logvar = self.rssm.posterior(h, obs)
            s = self.rssm.reparameterize(post_mean, post_logvar)

        imagined = self.rssm.imagine(h, s, action_seq)

        future_scans, future_rewards, future_collisions = [], [], []
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

    def compute_loss(self, scan_seq, action_seq, rewards, collisions) -> Dict:
        """计算训练损失"""
        result = self.forward(scan_seq, action_seq)
        B, T, _ = scan_seq.shape

        # 重建损失
        recon_loss = F.mse_loss(result['recon_scans'], scan_seq)

        # 奖励预测损失
        reward_loss = F.mse_loss(
            result['predicted_rewards'].squeeze(-1), rewards)

        # 碰撞预测损失
        collision_loss = F.binary_cross_entropy(
            result['collision_probs'].squeeze(-1), collisions.float())

        # KL 散度
        kl_loss = sum(
            gaussian_kl(pm, pl, qm, ql).mean()
            for (pm, pl), (qm, ql) in zip(result['priors'], result['posteriors'])
        ) / T

        total = recon_loss + reward_loss + collision_loss + 0.1 * kl_loss

        return {
            'total': total, 'recon': recon_loss.item(),
            'reward': reward_loss.item(), 'collision': collision_loss.item(),
            'kl': kl_loss.item() if isinstance(kl_loss, torch.Tensor) else kl_loss,
        }
