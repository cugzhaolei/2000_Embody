"""
Diffusion Policy 模型
====================
使用扩散模型生成机器人动作序列。
核心思想: 将动作生成视为去噪问题，从高斯噪声逐步去噪到动作分布。

优势:
  - 处理多模态动作分布 (同一个任务可以有多种合理动作)
  - 生成平滑、高质量的动作轨迹
  - 可直接替换 VLA 模型中的 MLP 动作头

参考: "Diffusion Policy: Visuomotor Policy Learning via Action Diffusion" (RSS 2023)

数据流:
  image ──► ViT ──► [B, D_v] ──┐
                                 ├──► Condition Encoder ──► Diffusion UNet ──► [B, chunk_size, action_dim]
  text  ──► BERT ──► [B, D_l] ──┘
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import math
from typing import Optional, Tuple
from transformers import AutoModel


class SinusoidalTimeEmbedding(nn.Module):
    """正弦时间步嵌入"""

    def __init__(self, dim: int):
        super().__init__()
        self.dim = dim

    def forward(self, t: torch.Tensor) -> torch.Tensor:
        """t: [B] → [B, dim]"""
        half_dim = self.dim // 2
        emb = math.log(10000) / (half_dim - 1)
        emb = torch.exp(torch.arange(half_dim, device=t.device).float() * -emb)
        emb = t[:, None].float() * emb[None, :]
        return torch.cat([torch.sin(emb), torch.cos(emb)], dim=-1)


class ConditionEncoder(nn.Module):
    """条件编码器: 将视觉+语言特征编码为扩散模型的条件"""

    def __init__(self, vision_dim: int, language_dim: int, state_dim: int, cond_dim: int, use_state: bool = False):
        super().__init__()
        input_dim = vision_dim + language_dim
        if use_state:
            input_dim += state_dim
        self.net = nn.Sequential(
            nn.Linear(input_dim, cond_dim),
            nn.SiLU(),
            nn.Linear(cond_dim, cond_dim),
        )

    def forward(self, vision_feat, lang_feat, state_feat=None):
        features = [vision_feat, lang_feat]
        if state_feat is not None:
            features.append(state_feat)
        return self.net(torch.cat(features, dim=-1))


class ActionUNet1D(nn.Module):
    """
    1D U-Net 去噪网络，用于动作序列去噪。

    将噪声动作序列 [B, chunk_size, action_dim] 逐步去噪为干净动作。
    条件信息通过 FiLM (Feature-wise Linear Modulation) 注入。
    """

    def __init__(
        self,
        action_dim: int,
        chunk_size: int,
        cond_dim: int,
        time_dim: int = 128,
        hidden_dim: int = 256,
        num_layers: int = 4,
    ):
        super().__init__()
        self.action_dim = action_dim
        self.chunk_size = chunk_size

        # 输入投影
        self.input_proj = nn.Linear(action_dim, hidden_dim)

        # 时间步嵌入
        self.time_embed = nn.Sequential(
            SinusoidalTimeEmbedding(time_dim),
            nn.Linear(time_dim, hidden_dim),
            nn.SiLU(),
        )

        # 条件嵌入
        self.cond_embed = nn.Sequential(
            nn.Linear(cond_dim, hidden_dim),
            nn.SiLU(),
        )

        # 下采样层
        self.down_layers = nn.ModuleList()
        for i in range(num_layers):
            self.down_layers.append(nn.Sequential(
                nn.Linear(hidden_dim, hidden_dim),
                nn.SiLU(),
                nn.Linear(hidden_dim, hidden_dim),
            ))

        # 中间层
        self.mid_layer = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim),
            nn.SiLU(),
            nn.Linear(hidden_dim, hidden_dim),
        )

        # 上采样层
        self.up_layers = nn.ModuleList()
        for i in range(num_layers):
            self.up_layers.append(nn.Sequential(
                nn.Linear(hidden_dim * 2, hidden_dim),  # skip connection
                nn.SiLU(),
                nn.Linear(hidden_dim, hidden_dim),
            ))

        # FiLM 调制层
        self.film_layers = nn.ModuleList([
            FiLMLayer(hidden_dim, hidden_dim) for _ in range(num_layers * 2 + 1)
        ])

        # 输出投影
        self.output_proj = nn.Linear(hidden_dim, action_dim)

    def forward(self, x: torch.Tensor, t: torch.Tensor, cond: torch.Tensor) -> torch.Tensor:
        """
        x: [B, chunk_size, action_dim] 噪声动作
        t: [B] 时间步
        cond: [B, cond_dim] 条件特征

        Returns: [B, chunk_size, action_dim] 预测噪声
        """
        batch_size = x.size(0)

        # 输入投影
        h = self.input_proj(x)  # [B, chunk, hidden]

        # 时间和条件嵌入
        t_emb = self.time_embed(t)  # [B, hidden]
        c_emb = self.cond_embed(cond)  # [B, hidden]

        # FiLM 调制: 注入时间和条件
        film_idx = 0
        h = self.film_layers[film_idx](h, t_emb + c_emb)
        film_idx += 1

        # 下采样 + 跳跃连接
        skips = []
        for down_layer in self.down_layers:
            h = down_layer(h)
            h = self.film_layers[film_idx](h, t_emb + c_emb)
            film_idx += 1
            skips.append(h)

        # 中间层
        h = self.mid_layer(h)
        h = self.film_layers[film_idx](h, t_emb + c_emb)
        film_idx += 1

        # 上采样 + 跳跃连接
        for up_layer, skip in zip(self.up_layers, reversed(skips)):
            h = up_layer(torch.cat([h, skip], dim=-1))

        # 输出
        return self.output_proj(h)


class FiLMLayer(nn.Module):
    """Feature-wise Linear Modulation"""

    def __init__(self, feature_dim: int, cond_dim: int):
        super().__init__()
        self.net = nn.Linear(cond_dim, feature_dim * 2)

    def forward(self, x: torch.Tensor, cond: torch.Tensor) -> torch.Tensor:
        """x: [B, L, D], cond: [B, D] → [B, L, D]"""
        gamma_beta = self.net(cond)  # [B, D*2]
        gamma, beta = gamma_beta.chunk(2, dim=-1)  # [B, D] each
        return x * (1 + gamma.unsqueeze(1)) + beta.unsqueeze(1)


class DiffusionPolicyModel(nn.Module):
    """
    Diffusion Policy: 使用扩散模型生成动作序列

    训练: 给定噪声动作，预测添加的噪声 (DDPM)
    推理: 从纯噪声逐步去噪生成动作
    """

    def __init__(
        self,
        vision_model_name: str = "google/vit-base-patch16-224",
        language_model_name: str = "bert-base-uncased",
        action_dim: int = 7,
        chunk_size: int = 16,
        num_diffusion_steps: int = 100,
        cond_dim: int = 256,
        hidden_dim: int = 256,
        use_state: bool = False,
        state_dim: int = 6,
        freeze_vision: bool = True,
        freeze_language: bool = True,
    ):
        super().__init__()

        self.action_dim = action_dim
        self.chunk_size = chunk_size
        self.num_diffusion_steps = num_diffusion_steps

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

        # 状态编码器
        self.use_state = use_state
        self.state_proj_dim = 0
        if use_state:
            self.state_encoder = nn.Sequential(
                nn.Linear(state_dim, 128), nn.ReLU(), nn.Linear(128, 128),
            )
            self.state_proj_dim = 128

        # 条件编码器
        self.condition_encoder = ConditionEncoder(
            self.vision_dim, self.language_dim, self.state_proj_dim, cond_dim, use_state,
        )

        # 去噪网络
        self.unet = ActionUNet1D(
            action_dim=action_dim,
            chunk_size=chunk_size,
            cond_dim=cond_dim,
            hidden_dim=hidden_dim,
        )

        # 噪声调度 (线性)
        self.register_buffer("betas", torch.linspace(1e-4, 0.02, num_diffusion_steps))
        alphas = 1.0 - self.betas
        self.register_buffer("alphas_cumprod", torch.cumprod(alphas, dim=0))
        self.register_buffer("sqrt_alphas_cumprod", torch.sqrt(self.alphas_cumprod))
        self.register_buffer("sqrt_one_minus_alphas_cumprod", torch.sqrt(1.0 - self.alphas_cumprod))

    def forward(
        self,
        images: torch.Tensor,
        input_ids: torch.Tensor,
        attention_mask: Optional[torch.Tensor] = None,
        state: Optional[torch.Tensor] = None,
        actions_gt: Optional[torch.Tensor] = None,
    ) -> dict:
        """
        训练前向传播: 添加噪声 → 预测噪声 → 计算损失

        Args:
            actions_gt: [B, chunk_size, action_dim] 真实动作序列

        Returns:
            dict: loss, actions_pred (去噪后)
        """
        batch_size = images.size(0)
        device = images.device

        # 编码条件
        cond = self._encode_condition(images, input_ids, attention_mask, state)

        if actions_gt is None:
            # 推理模式
            actions_pred = self._ddpm_sample(batch_size, cond, device)
            return {"actions_pred": actions_pred, "loss": torch.tensor(0.0)}

        # 训练模式: 随机选择时间步
        t = torch.randint(0, self.num_diffusion_steps, (batch_size,), device=device)

        # 添加噪声
        noise = torch.randn_like(actions_gt)
        sqrt_alpha = self.sqrt_alphas_cumprod[t].view(-1, 1, 1)
        sqrt_one_minus_alpha = self.sqrt_one_minus_alphas_cumprod[t].view(-1, 1, 1)
        noisy_actions = sqrt_alpha * actions_gt + sqrt_one_minus_alpha * noise

        # 预测噪声
        noise_pred = self.unet(noisy_actions, t, cond)

        # MSE 损失
        loss = F.mse_loss(noise_pred, noise)

        # 去噪后用于评估
        actions_pred = (noisy_actions - sqrt_one_minus_alpha * noise_pred) / sqrt_alpha

        return {"actions_pred": actions_pred, "loss": loss}

    def _encode_condition(self, images, input_ids, attention_mask, state):
        """编码视觉+语言+状态条件"""
        vision_feat = self.vision_encoder(images).last_hidden_state.mean(dim=1)
        lang_output = self.language_encoder(input_ids, attention_mask=attention_mask).last_hidden_state
        if attention_mask is not None:
            mask = attention_mask.unsqueeze(-1).float()
            lang_feat = (lang_output * mask).sum(dim=1) / mask.sum(dim=1).clamp(min=1)
        else:
            lang_feat = lang_output.mean(dim=1)

        state_feat = None
        if self.use_state and state is not None:
            state_feat = self.state_encoder(state)

        return self.condition_encoder(vision_feat, lang_feat, state_feat)

    @torch.no_grad()
    def _ddpm_sample(self, batch_size, cond, device):
        """DDPM 采样: 从纯噪声逐步去噪"""
        x = torch.randn(batch_size, self.chunk_size, self.action_dim, device=device)

        for t_idx in reversed(range(self.num_diffusion_steps)):
            t = torch.full((batch_size,), t_idx, device=device, dtype=torch.long)
            noise_pred = self.unet(x, t, cond)

            alpha = self.alphas_cumprod[t_idx]
            alpha_prev = self.alphas_cumprod[t_idx - 1] if t_idx > 0 else torch.tensor(1.0)

            # 去噪步骤
            x0_pred = (x - torch.sqrt(1 - alpha) * noise_pred) / torch.sqrt(alpha)
            x0_pred = torch.clamp(x0_pred, -1, 1)

            # 后验均值
            posterior_mean = (
                torch.sqrt(alpha_prev) * (1 - self.betas[t_idx]) / (1 - alpha) * x0_pred
                + torch.sqrt(self.betas[t_idx]) * (1 - alpha_prev) / (1 - alpha) * x
            )

            if t_idx > 0:
                noise = torch.randn_like(x)
                x = posterior_mean + torch.sqrt(self.betas[t_idx]) * noise
            else:
                x = posterior_mean

        return x

    def get_action(self, images, input_ids, attention_mask=None, state=None):
        """推理接口: 返回单步动作"""
        result = self.forward(images, input_ids, attention_mask, state, actions_gt=None)
        return result["actions_pred"][:, 0, :]  # [B, action_dim]
