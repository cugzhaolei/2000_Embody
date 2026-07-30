"""
WAM 训练器 — 世界模型离线训练
从采集的轨迹数据训练 RSSM 世界模型
"""
import os
import numpy as np
import torch
from torch.utils.data import Dataset, DataLoader
from .world_model import WorldModel


class TrajectoryDataset(Dataset):
    """轨迹数据集: 从npy文件加载(scan, action, reward, collision)序列"""

    def __init__(self, data_dir: str, seq_len: int = 50, scan_dim: int = 360):
        self.seq_len = seq_len
        self.scan_dim = scan_dim
        self.episodes = []

        for f in sorted(os.listdir(data_dir)):
            if f.endswith('.npy'):
                data = np.load(os.path.join(data_dir, f), allow_pickle=True)
                self.episodes.append(data)

    def __len__(self):
        total = 0
        for ep in self.episodes:
            total += max(0, len(ep) - self.seq_len)
        return total

    def __getitem__(self, idx):
        for ep in self.episodes:
            n = max(0, len(ep) - self.seq_len)
            if idx < n:
                seq = ep[idx:idx + self.seq_len]
                scans = torch.FloatTensor(
                    [np.resize(s['scan'], (self.scan_dim,)) for s in seq])
                actions = torch.FloatTensor([s['action'] for s in seq])
                rewards = torch.FloatTensor([s['reward'] for s in seq])
                collisions = torch.FloatTensor([s['collision'] for s in seq])
                return scans, actions, rewards, collisions
            idx -= n
        raise IndexError


class WAMTrainer:
    """世界模型训练器"""

    def __init__(self, data_dir: str, scan_dim: int = 360,
                 action_dim: int = 2, lr: float = 1e-4):
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.world_model = WorldModel(scan_dim, action_dim).to(self.device)
        self.optimizer = torch.optim.Adam(self.world_model.parameters(), lr=lr)
        self.data_dir = data_dir
        self.scan_dim = scan_dim

    def train(self, epochs: int = 100, batch_size: int = 32, seq_len: int = 50):
        dataset = TrajectoryDataset(self.data_dir, seq_len, self.scan_dim)
        if len(dataset) == 0:
            print(f"错误: 数据目录 {self.data_dir} 无数据")
            return

        loader = DataLoader(dataset, batch_size=batch_size, shuffle=True)

        print(f"训练数据: {len(dataset)} 个序列, {epochs} epochs")
        print(f"设备: {self.device}")

        for epoch in range(epochs):
            total_loss = 0
            n_batches = 0

            for scans, actions, rewards, collisions in loader:
                scans = scans.to(self.device)
                actions = actions.to(self.device)
                rewards = rewards.to(self.device)
                collisions = collisions.to(self.device)

                self.optimizer.zero_grad()
                losses = self.world_model.compute_loss(
                    scans, actions, rewards, collisions)
                losses['total'].backward()
                torch.nn.utils.clip_grad_norm_(
                    self.world_model.parameters(), 10.0)
                self.optimizer.step()

                total_loss += losses['total'].item()
                n_batches += 1

            avg_loss = total_loss / max(1, n_batches)
            if (epoch + 1) % 10 == 0:
                print(f"Epoch {epoch+1}/{epochs} | Loss: {avg_loss:.4f} | "
                      f"recon={losses['recon']:.4f} kl={losses['kl']:.4f}")

        # 保存模型
        save_path = os.path.expanduser('~/wam_model.pt')
        torch.save(self.world_model.state_dict(), save_path)
        print(f"模型已保存: {save_path}")


def main():
    import argparse
    parser = argparse.ArgumentParser(description='WAM 训练器')
    parser.add_argument('--data_dir', default='/tmp/wam_data',
                        help='训练数据目录')
    parser.add_argument('--epochs', type=int, default=100)
    parser.add_argument('--batch_size', type=int, default=32)
    parser.add_argument('--seq_len', type=int, default=50)
    args = parser.parse_args()

    trainer = WAMTrainer(args.data_dir)
    trainer.train(args.epochs, args.batch_size, args.seq_len)


if __name__ == '__main__':
    main()
