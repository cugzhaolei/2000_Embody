"""
ACT (Action Chunking with Transformers) 模型
============================================
Stanford AL 论文提出的 VLA 模型架构，核心创新：
  - 动作分块 (Action Chunking): 一次预测多步动作，而非单步
  - CVAE 编码: 训练时用变分编码器学习动作分布，推理时从先验采样
  - Transformer 解码器: 将视觉+语言特征解码为动作序列

数据流:
  image ──► ViT ──► [B, D_v] ──┐
                                 ├──► Transformer Decoder ──► [B, chunk_size, action_dim]
  text  ──► BERT ──► [B, D_l] ──┘

参考: "Learning Fine-Grained Bimanual Manipulation with Low-Cost Hardware" (RSS 2023)
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import math
from typing import Optional, Tuple
from transformers import AutoModel


class PositionalEncoding(nn.Module):
    """Transformer 位置编码"""

    def __init__(self, d_model: int, max_len: int = 500):
        super().__init__()
        pe = torch.zeros(max_len, d_model)
        position = torch.arange(0, max_len, dtype=torch.float).unsqueeze(1)
        div_term = torch.exp(torch.arange(0, d_model, 2).float() * (-math.log(10000.0) / d_model))
        pe[:, 0::2] = torch.sin(position * div_term)
        pe[:, 1::2] = torch.cos(position * div_term)
        self.register_buffer("pe", pe.unsqueeze(0))  # [1, max_len, d_model]

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return x + self.pe[:, :x.size(1)]


class CVAEEncoder(nn.Module):
    """条件变分自编码器 (CVAE) 编码器"""

    def __init__(self, action_dim: int, chunk_size: int, latent_dim: int = 32, hidden_dim: int = 256):
        super().__init__()
        input_dim = action_dim * chunk_size
        self.net = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
        )
        self.fc_mu = nn.Linear(hidden_dim, latent_dim)
        self.fc_logvar = nn.Linear(hidden_dim, latent_dim)

    def forward(self, actions: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        """actions: [B, chunk_size, action_dim] → mu, logvar: [B, latent_dim]"""
        x = actions.flatten(1)  # [B, chunk_size * action_dim]
        h = self.net(x)
        return self.fc_mu(h), self.fc_logvar(h)

    def reparameterize(self, mu: torch.Tensor, logvar: torch.Tensor) -> torch.Tensor:
        std = torch.exp(0.5 * logvar)
        eps = torch.randn_like(std)
        return mu + eps * std


class ACTModel(nn.Module):
    """
    ACT: Action Chunking with Transformers

    一次预测 chunk_size 步动作，训练时使用 CVAE 风格的 KL 正则化。
    """

    def __init__(
        self,
        vision_model_name: str = "google/vit-base-patch16-224",
        language_model_name: str = "bert-base-uncased",
        action_dim: int = 7,
        chunk_size: int = 10,        # 一次预测多少步动作
        latent_dim: int = 32,         # CVAE 隐空间维度
        num_heads: int = 8,
        num_decoder_layers: int = 4,
        dim_feedforward: int = 2048,
        use_state: bool = False,
        state_dim: int = 6,
        freeze_vision: bool = True,
        freeze_language: bool = True,
    ):
        super().__init__()

        self.action_dim = action_dim
        self.chunk_size = chunk_size
        self.latent_dim = latent_dim

        # 视觉编码器
        self.vision_encoder = AutoModel.from_pretrained(vision_model_name)
        self.vision_dim = self.vision_encoder.config.hidden_size
        if freeze_vision:
            for p in self.vision_encoder.parameters():
                p.requires_grad = False

        # 语言编码器
        self.language_encoder = AutoModel.from_pretrained(language_model_name)
        self.language_dim = self.language_encoder.config.hidden_size
        if freeze_language:
            for p in self.language_encoder.parameters():
                p.requires_grad = False

        # 状态编码器 (可选)
        self.use_state = use_state
        self.state_proj_dim = 0
        if use_state:
            self.state_encoder = nn.Sequential(
                nn.Linear(state_dim, 128), nn.ReLU(), nn.Linear(128, 128),
            )
            self.state_proj_dim = 128

        # CVAE 编码器 (仅训练时使用)
        self.cvae_encoder = CVAEEncoder(action_dim, chunk_size, latent_dim)

        # Transformer 解码器
        d_model = self.vision_dim + self.language_dim + self.state_proj_dim + latent_dim

        # 查询嵌入 (每个 chunk 位置一个 query)
        self.query_embed = nn.Embedding(chunk_size, d_model)

        decoder_layer = nn.TransformerDecoderLayer(
            d_model=d_model,
            nhead=num_heads,
            dim_feedforward=dim_feedforward,
            dropout=0.1,
            batch_first=True,
        )
        self.transformer_decoder = nn.TransformerDecoder(
            decoder_layer, num_layers=num_decoder_layers,
        )

        # 动作预测头
        self.action_head = nn.Sequential(
            nn.Linear(d_model, 256),
            nn.ReLU(),
            nn.Linear(256, action_dim),
        )

        # 先验网络 (用于推理时的 latent 采样)
        self.prior_net = nn.Sequential(
            nn.Linear(self.vision_dim + self.language_dim + self.state_proj_dim, 256),
            nn.ReLU(),
        )
        self.prior_mu = nn.Linear(256, latent_dim)
        self.prior_logvar = nn.Linear(256, latent_dim)

    def forward(
        self,
        images: torch.Tensor,
        input_ids: torch.Tensor,
        attention_mask: Optional[torch.Tensor] = None,
        state: Optional[torch.Tensor] = None,
        actions_gt: Optional[torch.Tensor] = None,
    ) -> dict:
        """
        前向传播

        Args:
            images: [B, 3, H, W]
            input_ids: [B, L]
            attention_mask: [B, L]
            state: [B, S] (可选)
            actions_gt: [B, chunk_size, action_dim] (训练时提供)

        Returns:
            dict:
              actions_pred: [B, chunk_size, action_dim]
              kl_loss: KL 散度损失 (训练时)
              mu, logvar: CVAE 编码器输出
        """
        batch_size = images.size(0)

        # 编码视觉和语言
        vision_feat = self.vision_encoder(images).last_hidden_state.mean(dim=1)  # [B, D_v]
        lang_output = self.language_encoder(input_ids, attention_mask=attention_mask).last_hidden_state
        if attention_mask is not None:
            mask = attention_mask.unsqueeze(-1).float()
            lang_feat = (lang_output * mask).sum(dim=1) / mask.sum(dim=1).clamp(min=1)
        else:
            lang_feat = lang_output.mean(dim=1)  # [B, D_l]

        # 拼接条件特征
        cond_features = [vision_feat, lang_feat]
        if self.use_state and state is not None:
            state_feat = self.state_encoder(state)
            cond_features.append(state_feat)
        cond = torch.cat(cond_features, dim=-1)  # [B, D_cond]

        # CVAE: 获取 latent z
        if actions_gt is not None:
            # 训练模式: 从真实动作编码 z
            mu, logvar = self.cvae_encoder(actions_gt)
            z = self.cvae_encoder.reparameterize(mu, logvar)

            # 先验
            prior_h = self.prior_net(cond.detach())
            prior_mu = self.prior_mu(prior_h)
            prior_logvar = self.prior_logvar(prior_h)

            # KL 散度
            kl_loss = -0.5 * torch.sum(1 + logvar - prior_logvar - (mu - prior_mu).pow(2) - (logvar - prior_logvar).exp())
            kl_loss = kl_loss / batch_size
        else:
            # 推理模式: 从先验采样
            prior_h = self.prior_net(cond)
            mu = self.prior_mu(prior_h)
            logvar = self.prior_logvar(prior_h)
            z = self.cvae_encoder.reparameterize(mu, logvar)
            kl_loss = torch.tensor(0.0, device=images.device)

        # 扩展条件特征 + latent 到 chunk_size 个 query
        z_expanded = z.unsqueeze(1).expand(-1, self.chunk_size, -1)  # [B, chunk, latent]
        cond_expanded = cond.unsqueeze(1).expand(-1, self.chunk_size, -1)  # [B, chunk, D_cond]
        memory = torch.cat([cond_expanded, z_expanded], dim=-1)  # [B, chunk, D_cond + latent]

        # 查询嵌入
        queries = self.query_embed.weight.unsqueeze(0).expand(batch_size, -1, -1)  # [B, chunk, D]

        # Transformer 解码
        decoded = self.transformer_decoder(queries, memory)  # [B, chunk, D]

        # 动作预测
        actions_pred = self.action_head(decoded)  # [B, chunk, action_dim]

        return {
            "actions_pred": actions_pred,
            "kl_loss": kl_loss,
            "mu": mu,
            "logvar": logvar,
        }

    def get_action(self, images, input_ids, attention_mask=None, state=None):
        """推理接口: 返回单步动作 (chunk 的第一步)"""
        with torch.no_grad():
            result = self.forward(images, input_ids, attention_mask, state, actions_gt=None)
            return result["actions_pred"][:, 0, :]  # [B, action_dim]
