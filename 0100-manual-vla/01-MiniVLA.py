import torch
import torch.nn as nn
from transformers import AutoModel, AutoTokenizer


class MiniVLA(nn.Module):
    """
    MiniVLA: 一个极简的 Vision-Language-Action 模型骨架，用于理解 VLA 的核心原理。

    数据流:
       图像 (image) ──► Vision Encoder ──► [B, D_v] ──┐
                                                        ├──► Concat ──► Projector ──► Action Head ──► 动作
       文本 (text)  ──► Language Encoder ──► [B, D_l] ──┘

    Vision Encoder:  将图像编码为视觉特征（如 ViT）
    Language Encoder: 将自然语言指令编码为语义特征（如 BERT/T5）
    Projector:       将视觉+语言特征映射到统一的动作空间
    Action Head:     MLP，预测最终的动作值（如末端位姿、关节角度、夹爪开合）
    """

    def __init__(self, vision_model_name: str, language_model_name: str, action_dim: int):
        """
        Args:
            vision_model_name:   HuggingFace 视觉模型名，如 "google/vit-base-patch16-224"
            language_model_name: HuggingFace 语言模型名，如 "bert-base-uncased"
            action_dim:          动作空间的维度（比如 7: xyz + 四元数 + 夹爪）
        """
        super().__init__()

        # ── 1. 加载预训练编码器 ──
        self.vision_encoder = AutoModel.from_pretrained(vision_model_name)
        self.language_encoder = AutoModel.from_pretrained(language_model_name)

        # ── 2. 从模型配置中动态获取隐藏层维度，无需硬编码 ──
        vision_hidden = self.vision_encoder.config.hidden_size   # 常见: ViT-Base → 768
        language_hidden = self.language_encoder.config.hidden_size  # 常见: BERT-Base → 768

        self.vision_dim = vision_hidden
        self.language_dim = language_hidden
        self.multimodal_dim = vision_hidden + language_hidden  # 拼接后的总维度

        # ── 3. 多模态融合层 (Projector) ──
        # 将 vision + language 拼接特征映射到统一的隐空间
        self.projector = nn.Sequential(
            nn.Linear(self.multimodal_dim, 512),
            nn.ReLU(),
            nn.Dropout(0.1),
        )

        # ── 4. 动作预测头 (Action Head) ──
        # 从融合特征回归出连续动作值
        self.action_head = nn.Sequential(
            nn.Linear(512, 256),
            nn.ReLU(),
            nn.Dropout(0.1),
            nn.Linear(256, action_dim),
        )

    def forward(self, images: torch.Tensor, text_tokens: torch.Tensor) -> torch.Tensor:
        """
        Args:
            images:      图像批次, shape [batch_size, 3, H, W]
            text_tokens: 文本 token IDs, shape [batch_size, seq_len]
        Returns:
            actions:     预测动作, shape [batch_size, action_dim]
        """
        batch_size = images.shape[0]

        # ── Step 1: 视觉编码 ──
        # ViT 输出 [batch_size, num_patches + 1, hidden_dim]
        # 取 last_hidden_state，然后做 mean pooling 得到全局视觉特征
        vision_output = self.vision_encoder(images).last_hidden_state
        vision_features = vision_output.mean(dim=1)  # [B, D_v]

        # ── Step 2: 语言编码 ──
        # 语言模型输出 [batch_size, seq_len, hidden_dim]
        # 同样做 mean pooling（用 attention_mask 加权更精确，这里先简化）
        lang_output = self.language_encoder(text_tokens).last_hidden_state
        lang_features = lang_output.mean(dim=1)  # [B, D_l]

        # ── Step 3: 多模态融合 ──
        # 沿特征维度拼接 visual + language
        combined = torch.cat([vision_features, lang_features], dim=-1)  # [B, D_v + D_l]

        # ── Step 4: 特征投影 + 动作预测 ──
        projected = self.projector(combined)  # [B, 512]
        actions = self.action_head(projected)  # [B, action_dim]

        return actions


# ═══════════════════════════════════════════════════════════════
# 快速验证: 构造假数据跑一遍前向传播
# ═══════════════════════════════════════════════════════════════
if __name__ == "__main__":
    print("=" * 60)
    print("MiniVLA 前向传播验证")
    print("=" * 60)

    # 选择轻量模型做快速验证（首次运行会自动下载）
    VISION_MODEL = "google/vit-base-patch16-224"
    LANGUAGE_MODEL = "bert-base-uncased"
    ACTION_DIM = 7  # 示例: x, y, z, qx, qy, qz, qw, gripper

    print(f"\n[1/4] 加载模型...")
    print(f"  Vision:   {VISION_MODEL}")
    print(f"  Language: {LANGUAGE_MODEL}")
    print(f"  Action Dim: {ACTION_DIM}")

    model = MiniVLA(VISION_MODEL, LANGUAGE_MODEL, ACTION_DIM)

    print(f"\n  Vision Hidden Dim:   {model.vision_dim}")
    print(f"  Language Hidden Dim:  {model.language_dim}")
    print(f"  Multimodal Dim:       {model.multimodal_dim}")
    total_params = sum(p.numel() for p in model.parameters()) / 1e6
    print(f"  Total Params:         {total_params:.2f}M")

    print(f"\n[2/4] 构造假数据...")
    # 模拟一批 4 张 224x224 RGB 图像
    dummy_images = torch.randn(4, 3, 224, 224)
    print(f"  Images shape:     {dummy_images.shape}")

    # 加载 tokenizer 并编码一段假指令
    tokenizer = AutoTokenizer.from_pretrained(LANGUAGE_MODEL)
    dummy_texts = ["pick up the red block", "move to the left", "push forward", "open gripper"]
    dummy_tokens = tokenizer(dummy_texts, return_tensors="pt", padding=True).input_ids
    print(f"  Text tokens shape: {dummy_tokens.shape}")

    print(f"\n[3/4] 前向传播...")
    model.eval()
    with torch.no_grad():
        actions = model(dummy_images, dummy_tokens)

    print(f"\n[4/4] 输出结果:")
    print(f"  Actions shape: {actions.shape}")
    print(f"  Actions (前两个样本):")
    for i in range(min(2, len(dummy_texts))):
        print(f"    [{i}] \"{dummy_texts[i]}\"")
        # 取前3个理解为 xyz 平移
        print(f"        xyz: {actions[i][:3].numpy().round(4)}")
        # 其余为旋转+夹爪
        print(f"        rotation+grip: {actions[i][3:].numpy().round(4)}")

    print(f"\n{'=' * 60}")
    print("验证通过! 前向传播无报错.")
    print(f"{'=' * 60}")