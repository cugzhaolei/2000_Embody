"""
VLA 基础模型
============
基于 ViT + BERT 的 Vision-Language-Action 模型。
从 0100-manual-vla/01-MiniVLA.py 衍生，增加了：
  - 状态输入支持 (joint positions)
  - 动作归一化
  - 可选的 LoRA 微调支持

数据流:
  image ──► ViT ──► [B, D_v] ──┐
                                 ├──► Concat ──► Projector ──► Action Head ──► action
  text  ──► BERT ──► [B, D_l] ──┤
  state ──► MLP  ──► [B, D_s] ──┘
"""

import torch
import torch.nn as nn
from transformers import AutoModel, AutoTokenizer
from typing import Optional


class VLABaseModel(nn.Module):
    """
    VLA 基础模型：视觉+语言(+状态) → 动作预测

    支持:
      - 图像观测 (ViT)
      - 语言指令 (BERT)
      - 本体状态 (可选, MLP)
      - 动作归一化 (running stats)
    """

    def __init__(
        self,
        vision_model_name: str = "google/vit-base-patch16-224",
        language_model_name: str = "bert-base-uncased",
        action_dim: int = 7,
        use_state: bool = False,
        state_dim: int = 6,
        projector_dim: int = 512,
        action_hidden_dim: int = 256,
        freeze_vision: bool = False,
        freeze_language: bool = False,
    ):
        super().__init__()

        self.use_state = use_state
        self.action_dim = action_dim

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
        self.state_dim = state_dim
        if use_state:
            self.state_encoder = nn.Sequential(
                nn.Linear(state_dim, 128),
                nn.ReLU(),
                nn.Linear(128, 128),
            )
            self.state_proj_dim = 128
        else:
            self.state_encoder = None
            self.state_proj_dim = 0

        # 多模态融合
        fusion_dim = self.vision_dim + self.language_dim + self.state_proj_dim
        self.projector = nn.Sequential(
            nn.Linear(fusion_dim, projector_dim),
            nn.ReLU(),
            nn.Dropout(0.1),
        )

        # 动作预测头
        self.action_head = nn.Sequential(
            nn.Linear(projector_dim, action_hidden_dim),
            nn.ReLU(),
            nn.Dropout(0.1),
            nn.Linear(action_hidden_dim, action_dim),
        )

        # 动作归一化统计 (running mean/std)
        self.register_buffer("action_mean", torch.zeros(action_dim))
        self.register_buffer("action_std", torch.ones(action_dim))
        self._stats_initialized = False

    def update_action_stats(self, actions: torch.Tensor):
        """更新动作归一化统计量"""
        self.action_mean = actions.mean(dim=0).detach()
        self.action_std = actions.std(dim=0).clamp(min=1e-6).detach()
        self._stats_initialized = True

    def normalize_actions(self, actions: torch.Tensor) -> torch.Tensor:
        """归一化动作"""
        if self._stats_initialized:
            return (actions - self.action_mean) / self.action_std
        return actions

    def denormalize_actions(self, actions: torch.Tensor) -> torch.Tensor:
        """反归一化动作"""
        if self._stats_initialized:
            return actions * self.action_std + self.action_mean
        return actions

    def forward(
        self,
        images: torch.Tensor,
        input_ids: torch.Tensor,
        attention_mask: Optional[torch.Tensor] = None,
        state: Optional[torch.Tensor] = None,
    ) -> torch.Tensor:
        """
        前向传播

        Args:
            images: [B, 3, H, W]
            input_ids: [B, L]
            attention_mask: [B, L] (可选)
            state: [B, S] (可选)

        Returns:
            actions: [B, action_dim]
        """
        # 视觉编码
        vision_output = self.vision_encoder(images).last_hidden_state
        vision_features = vision_output.mean(dim=1)  # [B, D_v]

        # 语言编码
        lang_output = self.language_encoder(input_ids, attention_mask=attention_mask).last_hidden_state
        if attention_mask is not None:
            # 加权平均 pooling
            mask = attention_mask.unsqueeze(-1).float()
            lang_features = (lang_output * mask).sum(dim=1) / mask.sum(dim=1).clamp(min=1)
        else:
            lang_features = lang_output.mean(dim=1)  # [B, D_l]

        # 多模态融合
        features = [vision_features, lang_features]

        if self.use_state and state is not None and self.state_encoder is not None:
            state_features = self.state_encoder(state)  # [B, 128]
            features.append(state_features)

        combined = torch.cat(features, dim=-1)  # [B, D_v + D_l + D_s]

        # 投影 + 动作预测
        projected = self.projector(combined)  # [B, projector_dim]
        actions = self.action_head(projected)  # [B, action_dim]

        return actions
