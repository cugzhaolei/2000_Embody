"""
RSSM (Recurrent State-Space Model) — Dreamer 架构核心
世界模型的确定性-随机双路径状态空间模型
"""
import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Dict, List, Tuple


class RSSM(nn.Module):
    """
    Recurrent State-Space Model

    确定性路径: h_t = GRU(h_{t-1}, s_{t-1}, a_{t-1})
    随机路径(先验): s_t ~ N(μ_prior(h_t), σ_prior(h_t))
    随机路径(后验): s_t ~ N(μ_post(h_t, o_t), σ_post(h_t, o_t))

    训练时使用后验（有观测），推理/想象时使用先验（无观测）。
    """

    def __init__(self, obs_dim: int = 128, action_dim: int = 2,
                 hidden_dim: int = 200, state_dim: int = 30):
        super().__init__()
        self.hidden_dim = hidden_dim
        self.state_dim = state_dim
        self.obs_dim = obs_dim
        self.action_dim = action_dim

        # 确定性递推 (GRU)
        self.gru = nn.GRUCell(action_dim + state_dim, hidden_dim)

        # 先验: p(s_t | h_t)
        self.prior_net = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim), nn.ReLU())
        self.prior_mean = nn.Linear(hidden_dim, state_dim)
        self.prior_logvar = nn.Linear(hidden_dim, state_dim)

        # 后验: q(s_t | h_t, o_t)
        self.post_net = nn.Sequential(
            nn.Linear(hidden_dim + obs_dim, hidden_dim), nn.ReLU())
        self.post_mean = nn.Linear(hidden_dim, state_dim)
        self.post_logvar = nn.Linear(hidden_dim, state_dim)

    def prior(self, h: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        x = self.prior_net(h)
        return self.prior_mean(x), self.prior_logvar(x)

    def posterior(self, h: torch.Tensor, obs: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        x = self.post_net(torch.cat([h, obs], dim=-1))
        return self.post_mean(x), self.post_logvar(x)

    @staticmethod
    def reparameterize(mean: torch.Tensor, logvar: torch.Tensor) -> torch.Tensor:
        std = torch.exp(0.5 * logvar)
        return mean + std * torch.randn_like(std)

    def rollout(self, obs_seq: torch.Tensor, action_seq: torch.Tensor,
                h0: torch.Tensor = None) -> Dict:
        B, T, _ = obs_seq.shape
        h = h0 if h0 is not None else torch.zeros(B, self.hidden_dim, device=obs_seq.device)

        priors, posteriors, hidden_states, sampled_states = [], [], [], []

        for t in range(T):
            # 后验
            post_mean, post_logvar = self.posterior(h, obs_seq[:, t])
            s = self.reparameterize(post_mean, post_logvar)

            # 先验 (用于 KL)
            prior_mean, prior_logvar = self.prior(h)

            priors.append((prior_mean, prior_logvar))
            posteriors.append((post_mean, post_logvar))
            hidden_states.append(h)
            sampled_states.append(s)

            # 递推
            h = self.gru(torch.cat([s, action_seq[:, t]], dim=-1), h)

        return {
            'priors': priors, 'posteriors': posteriors,
            'hidden_states': hidden_states, 'sampled_states': sampled_states,
        }

    def imagine(self, h: torch.Tensor, s: torch.Tensor,
                action_seq: torch.Tensor) -> List[Tuple[torch.Tensor, torch.Tensor]]:
        """想象模式: 无观测，仅用先验预测未来"""
        imagined = []
        h_t, s_t = h, s
        for a in action_seq:
            h_t = self.gru(torch.cat([s_t, a], dim=-1), h_t)
            prior_mean, prior_logvar = self.prior(h_t)
            s_t = self.reparameterize(prior_mean, prior_logvar)
            imagined.append((h_t, s_t))
        return imagined


def gaussian_kl(mean1, logvar1, mean2, logvar2):
    """KL(q||p) for diagonal Gaussians"""
    return 0.5 * torch.sum(
        logvar2 - logvar1 - 1 + torch.exp(logvar1 - logvar2)
        + (mean1 - mean2) ** 2 / torch.exp(logvar2), dim=-1)
