"""
05-MuJoCoRenderer.py — MuJoCo 机器人可视化渲染器
==================================================
用于可视化 VLA 模型预测的动作, 在 MuJoCo 物理引擎中渲染机器人执行动作。

支持两种渲染模式:
  1. MuJoCo (推荐):  3D 物理渲染, 需要 pip install mujoco
  2. Matplotlib (备用): 2D 简化可视化, 无需额外依赖

机器人模型: 简化 7-DOF 桌面操作臂 (类似 Franka/KUKA)
  - 底座旋转 (base_yaw)
  - 肩部俯仰 (shoulder_pitch)
  - 肘部俯仰 (elbow_pitch)
  - 腕部俯仰 (wrist_pitch)
  - 腕部滚转 (wrist_roll)
  - 夹爪 A (gripper_left)
  - 夹爪 B (gripper_right)

动作空间 (7维): [dx, dy, dz, droll, dpitch, dyaw, gripper]
  - dx, dy, dz:     末端位移 (m)
  - droll, dpitch, dyaw: 末端旋转变化 (rad)
  - gripper:       夹爪开合 (0=闭合, 1=张开)

使用方法:
  python 05-MuJoCoRenderer.py --demo   # 演示随机动作
  python 05-MuJoCoRenderer.py --render # 交互式渲染
"""

import os
import sys
import time
import math
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Optional, Tuple, List, Dict
import numpy as np

# ═══════════════════════════════════════════════════════════════
# 1. MuJoCo 机器人模型 (XML 生成)
# ═══════════════════════════════════════════════════════════════

ROBOT_ARM_XML = """<?xml version="1.0" encoding="utf-8"?>
<mujoco model="robot_arm">
  <compiler angle="radian" meshdir="assets"/>

  <visual>
    <global offwidth="800" offheight="600"/>
  </visual>

  <option timestep="0.002" gravity="0 0 -9.81">
    <flag contact="enable"/>
  </option>

  <asset>
    <texture type="skybox" builtin="gradient" rgb1="0.3 0.5 0.7" rgb2="0.1 0.2 0.3" width="512" height="512"/>
    <texture name="tex_plane" type="2d" builtin="checker" width="512" height="512"
             rgb1="0.2 0.3 0.4" rgb2="0.3 0.4 0.5"/>
    <material name="mat_plane" texture="tex_plane" texrepeat="5 5" reflectance="0.1"/>
    <material name="mat_base" rgba="0.3 0.3 0.3 1"/>
    <material name="mat_link1" rgba="0.2 0.6 0.8 1"/>
    <material name="mat_link2" rgba="0.8 0.3 0.2 1"/>
    <material name="mat_link3" rgba="0.2 0.8 0.3 1"/>
    <material name="mat_link4" rgba="0.8 0.7 0.1 1"/>
    <material name="mat_gripper" rgba="0.6 0.6 0.6 1"/>
    <material name="mat_target" rgba="1.0 0.2 0.2 0.6"/>
    <material name="mat_object" rgba="0.2 0.8 0.2 0.8"/>
  </asset>

  <worldbody>
    <!-- 地面 -->
    <geom name="floor" type="plane" size="1.5 1.5 0.1" material="mat_plane" pos="0 0 0"/>

    <!-- 灯光 -->
    <light directional="true" pos="1 1 1.5" dir="-1 -1 -1.5" diffuse="0.8 0.8 0.8"/>

    <!-- 底座 -->
    <body name="base" pos="0 0 0.0">
      <geom name="base_geom" type="cylinder" size="0.08 0.05" material="mat_base" pos="0 0 0.025"/>
      <joint name="base_yaw" type="hinge" axis="0 0 1" range="-3.14 3.14" damping="0.5"/>

      <!-- 肩部连杆 -->
      <body name="shoulder" pos="0 0 0.05">
        <geom name="shoulder_geom" type="capsule" size="0.04" fromto="0 0 0 0 0 0.15" material="mat_link1"/>
        <joint name="shoulder_pitch" type="hinge" axis="0 1 0" range="-2.5 1.5" damping="0.5"/>

        <!-- 上臂 -->
        <body name="upper_arm" pos="0 0 0.15">
          <geom name="upper_arm_geom" type="capsule" size="0.035" fromto="0 0 0 0.15 0 0" material="mat_link2"/>
          <joint name="elbow_pitch" type="hinge" axis="0 1 0" range="-2.5 0.5" damping="0.3"/>

          <!-- 前臂 -->
          <body name="forearm" pos="0.15 0 0">
            <geom name="forearm_geom" type="capsule" size="0.03" fromto="0 0 0 0.12 0 0" material="mat_link3"/>
            <joint name="wrist_pitch" type="hinge" axis="0 1 0" range="-2.0 2.0" damping="0.2"/>

            <!-- 腕部滚转 -->
            <body name="wrist_roll_body" pos="0.12 0 0">
              <joint name="wrist_roll" type="hinge" axis="1 0 0" range="-3.14 3.14" damping="0.1"/>
              <geom name="wrist_geom" type="capsule" size="0.02" fromto="0 0 0 0.05 0 0" material="mat_link4"/>

              <!-- 夹爪左 -->
              <body name="gripper_left" pos="0.05 0.02 0">
                <joint name="gripper_left_joint" type="slide" axis="0 1 0" range="-0.03 0.03" damping="0.5"/>
                <geom name="gripper_left_geom" type="box" size="0.015 0.005 0.02" material="mat_gripper"/>
              </body>

              <!-- 夹爪右 -->
              <body name="gripper_right" pos="0.05 -0.02 0">
                <joint name="gripper_right_joint" type="slide" axis="0 -1 0" range="-0.03 0.03" damping="0.5"/>
                <geom name="gripper_right_geom" type="box" size="0.015 0.005 0.02" material="mat_gripper"/>
              </body>

              <!-- 末端执行器 site (用于 IK 和位置追踪) -->
              <site name="end_effector" type="sphere" size="0.01" rgba="1 0 0 1" pos="0.05 0 0"/>
            </body>
          </body>
        </body>
      </body>
    </body>

    <!-- 桌面上的目标物体 -->
    <body name="target_object" pos="0.3 0.15 0.02" mocap="true">
      <geom name="target_geom" type="box" size="0.02 0.02 0.02" material="mat_target" mass="0.05"/>
    </body>

    <!-- 工作台面 -->
    <body name="table" pos="0.25 0 -0.05">
      <geom name="table_top" type="box" size="0.2 0.3 0.02" material="mat_base" rgba="0.5 0.35 0.2 1"/>
    </body>
  </worldbody>

  <actuator>
    <position name="act_base_yaw"       joint="base_yaw"       kp="100" kv="10"/>
    <position name="act_shoulder_pitch" joint="shoulder_pitch" kp="100" kv="10"/>
    <position name="act_elbow_pitch"    joint="elbow_pitch"    kp="100" kv="10"/>
    <position name="act_wrist_pitch"    joint="wrist_pitch"    kp="100" kv="10"/>
    <position name="act_wrist_roll"     joint="wrist_roll"     kp="100" kv="10"/>
    <position name="act_gripper_left"   joint="gripper_left_joint"  kp="50" kv="5"/>
    <position name="act_gripper_right"  joint="gripper_right_joint" kp="50" kv="5"/>
  </actuator>
</mujoco>
"""


# ═══════════════════════════════════════════════════════════════
# 2. MuJoCo 渲染器
# ═══════════════════════════════════════════════════════════════

class MuJoCoRenderer:
    """
    MuJoCo 机器人渲染器: 在 3D 物理环境中可视化机器人动作。

    用法:
        renderer = MuJoCoRenderer()
        renderer.reset()
        for action in action_sequence:
            renderer.step(action)
            renderer.render()
        renderer.close()
    """

    def __init__(self, camera_name: str = "fixed", width: int = 800, height: int = 600):
        """
        Args:
            camera_name: 相机名称
            width, height: 渲染窗口尺寸
        """
        self.width = width
        self.height = height

        # 写入临时 XML 文件
        self._tmp_dir = tempfile.mkdtemp(prefix="mujoco_vla_")
        self._xml_path = os.path.join(self._tmp_dir, "robot.xml")
        with open(self._xml_path, "w") as f:
            f.write(ROBOT_ARM_XML)

        try:
            import mujoco
            self.mj = mujoco
        except ImportError:
            raise ImportError(
                "请安装 MuJoCo:\n"
                "  pip install mujoco\n"
                "或使用 MatplotlibRenderer 作为备用渲染器。"
            )

        self.model = mujoco.MjModel.from_xml_path(self._xml_path)
        self.data = mujoco.MjData(self.model)

        # 渲染器
        self.renderer = mujoco.Renderer(self.model, width, height)

        # 关节 / 执行器索引
        self._actuator_names = [
            "act_base_yaw", "act_shoulder_pitch", "act_elbow_pitch",
            "act_wrist_pitch", "act_wrist_roll",
            "act_gripper_left", "act_gripper_right",
        ]
        self._actuator_ids = [
            mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_ACTUATOR, name)
            for name in self._actuator_names
        ]

        # 关节默认位置
        self._default_qpos = self.data.qpos.copy()

        # 相机设置
        if camera_name == "fixed":
            mujoco.mjv_defaultFreeCamera(self.model, self.renderer.scene.camera)
            self.renderer.scene.camera.lookat[:] = [0.25, 0.0, 0.15]
            self.renderer.scene.camera.distance = 1.2
            self.renderer.scene.camera.elevation = -25
            self.renderer.scene.camera.azimuth = 135

        self._step_count = 0

    def reset(self, qpos: Optional[np.ndarray] = None):
        """重置机器人到初始状态"""
        self.data.qpos[:] = qpos if qpos is not None else self._default_qpos
        self.data.qvel[:] = 0
        self.mj.mj_forward(self.model, self.data)
        self._step_count = 0

    def step(self, action: np.ndarray):
        """
        执行一个动作步。

        Args:
            action: [7] 动作向量
              [dx, dy, dz, droll, dpitch, dyaw, gripper]
              支持两种模式:
                1. 绝对关节位置: 长度 = 7, 直接设置关节目标
                2. 增量位姿: 长度 = 7, 通过简单 IK 转换为关节位置
        """
        # 将动作转换为关节位置
        if len(action) == 7:
            joint_targets = self._action_to_joints(action)
        else:
            joint_targets = action

        # 设置执行器目标
        for i, target in enumerate(joint_targets):
            if i < len(self._actuator_ids):
                self.data.ctrl[self._actuator_ids[i]] = target

        # 模拟几步
        for _ in range(10):
            self.mj.mj_step(self.model, self.data)

        self._step_count += 1

    def _action_to_joints(self, action: np.ndarray) -> np.ndarray:
        """
        将 7 维动作向量转换为关节位置。

        简化策略: 将 [dx, dy, dz, droll, dpitch, dyaw, gripper] 映射到关节:
          - dx, dy → base_yaw, shoulder_pitch
          - dz → elbow_pitch
          - droll, dpitch, dyaw → wrist_pitch, wrist_roll
          - gripper → 夹爪开合
        """
        dx, dy, dz, dr, dp, dyaw, grip = action

        # 当前关节位置
        current_q = self.data.qpos.copy()

        # 映射: 增量动作 → 关节增量
        # 这是一个简化的几何映射, 实际应用中需要用 IK
        joint_delta = np.zeros(7)

        # 水平移动 → base_yaw 旋转
        joint_delta[0] = math.atan2(dy, dx + 0.3) * 0.5  # base_yaw

        # 前后移动 → shoulder_pitch
        joint_delta[1] = -dz * 1.5  # shoulder_pitch

        # 高度 → elbow_pitch
        joint_delta[2] = -dz * 1.0  # elbow_pitch

        # 旋转 → wrist
        joint_delta[3] = dp * 0.5   # wrist_pitch
        joint_delta[4] = dr * 0.5   # wrist_roll

        # 夹爪
        joint_delta[5] = grip * 0.03 - 0.015   # gripper_left
        joint_delta[6] = (1 - grip) * 0.03 - 0.015  # gripper_right

        new_q = current_q + joint_delta

        # 限制关节范围
        for i in range(7):
            if i < self.model.njnt:
                jnt_id = self.model.jnt_qposadr[i]
                low = self.model.jnt_range[i][0] if self.model.jnt_limited[i] else -np.inf
                high = self.model.jnt_range[i][1] if self.model.jnt_limited[i] else np.inf
                new_q[jnt_id] = np.clip(new_q[jnt_id], low, high)

        return new_q[:7]

    def render(self) -> np.ndarray:
        """渲染当前帧, 返回 RGB 图像 [H, W, 3]"""
        self.renderer.update_scene(self.data, camera="fixed")
        return self.renderer.render()

    def get_end_effector_pos(self) -> np.ndarray:
        """获取末端执行器位置 [x, y, z]"""
        site_id = self.mj.mj_name2id(self.model, self.mj.mjtObj.mjOBJ_SITE, "end_effector")
        return self.data.site_xpos[site_id].copy()

    def close(self):
        """清理资源"""
        self.renderer.close()
        import shutil
        shutil.rmtree(self._tmp_dir, ignore_errors=True)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


# ═══════════════════════════════════════════════════════════════
# 3. Matplotlib 备用渲染器 (无需 MuJoCo)
# ═══════════════════════════════════════════════════════════════

class MatplotlibRenderer:
    """
    2D 简化可视化: 用 matplotlib 绘制机器人末端执行器轨迹。
    不需要 MuJoCo, 适合快速验证和调试。
    """

    def __init__(self):
        self.trajectory: List[Tuple[float, float, float]] = []
        self.gripper_states: List[float] = []
        self.fig = None
        self.ax = None

    def reset(self):
        self.trajectory = [(0.0, 0.0, 0.0)]
        self.gripper_states = [0.0]

    def step(self, action: np.ndarray):
        """记录动作产生的位姿变化"""
        dx, dy, dz = action[0], action[1], action[2]
        grip = action[6] if len(action) > 6 else 0.0

        last = self.trajectory[-1]
        new_pos = (last[0] + dx, last[1] + dy, last[2] + dz)
        self.trajectory.append(new_pos)
        self.gripper_states.append(grip)

    def render(self) -> np.ndarray:
        """渲染 2D 轨迹图, 返回 RGB 图像"""
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        if self.fig is None:
            self.fig, self.axes = plt.subplots(1, 2, figsize=(12, 5))
            self.ax_xy = self.axes[0]
            self.ax_xz = self.axes[1]

        self.ax_xy.clear()
        self.ax_xz.clear()

        xs = [p[0] for p in self.trajectory]
        ys = [p[1] for p in self.trajectory]
        zs = [p[2] for p in self.trajectory]

        # XY 平面
        colors = plt.cm.coolwarm(np.array(self.gripper_states))
        self.ax_xy.scatter(xs, ys, c=colors, s=30, alpha=0.8)
        self.ax_xy.plot(xs, ys, "gray", alpha=0.3, linewidth=0.5)
        # 起点和终点
        self.ax_xy.scatter(xs[0], ys[0], c="green", s=100, marker="o", label="Start", zorder=5)
        self.ax_xy.scatter(xs[-1], ys[-1], c="red", s=100, marker="*", label="End", zorder=5)
        self.ax_xy.set_xlabel("X (m)")
        self.ax_xy.set_ylabel("Y (m)")
        self.ax_xy.set_title("Top View (XY)")
        self.ax_xy.legend()
        self.ax_xy.grid(True, alpha=0.3)
        self.ax_xy.set_aspect("equal")

        # XZ 平面
        self.ax_xz.scatter(xs, zs, c=colors, s=30, alpha=0.8)
        self.ax_xz.plot(xs, zs, "gray", alpha=0.3, linewidth=0.5)
        self.ax_xz.scatter(xs[0], zs[0], c="green", s=100, marker="o", label="Start", zorder=5)
        self.ax_xz.scatter(xs[-1], zs[-1], c="red", s=100, marker="*", label="End", zorder=5)
        self.ax_xz.set_xlabel("X (m)")
        self.ax_xz.set_ylabel("Z (m)")
        self.ax_xz.set_title("Side View (XZ)")
        self.ax_xz.legend()
        self.ax_xz.grid(True, alpha=0.3)
        self.ax_xz.set_aspect("equal")

        sm = plt.cm.ScalarMappable(cmap="coolwarm")
        sm.set_array([0, 1])
        self.fig.colorbar(sm, ax=self.axes, label="gripper (0=closed, 1=open)", shrink=0.6)

        self.fig.tight_layout()
        self.fig.canvas.draw()

        # 转换为 numpy 数组
        img = np.frombuffer(self.fig.canvas.tostring_rgb(), dtype=np.uint8)
        img = img.reshape(self.fig.canvas.get_width_height()[::-1] + (3,))
        return img

    def close(self):
        import matplotlib.pyplot as plt
        plt.close("all")


# ═══════════════════════════════════════════════════════════════
# 4. 渲染器工厂函数
# ═══════════════════════════════════════════════════════════════

def create_renderer(backend: str = "auto", **kwargs):
    """
    创建渲染器。

    Args:
        backend: "mujoco" | "matplotlib" | "auto"
            "auto" 优先尝试 MuJoCo, 不可用则回退到 matplotlib
    """
    if backend == "mujoco" or (backend == "auto" and _mujoco_available()):
        return MuJoCoRenderer(**kwargs)
    elif backend == "matplotlib" or backend == "auto":
        return MatplotlibRenderer()
    else:
        raise ValueError(f"Unknown backend: {backend}")


def _mujoco_available() -> bool:
    try:
        import mujoco
        return True
    except ImportError:
        return False


# ═══════════════════════════════════════════════════════════════
# 5. 可视化 VLA 模型预测
# ═══════════════════════════════════════════════════════════════

def visualize_vla_predictions(
    model,
    dataloader,
    renderer=None,
    num_steps: int = 50,
    save_dir: Optional[str] = None,
    device: str = "cpu",
):
    """
    使用 VLA 模型预测动作, 并在渲染器中可视化。

    Args:
        model:       MiniVLA 模型实例
        dataloader:  数据加载器 (取一个 batch)
        renderer:    渲染器 (None 则自动创建)
        num_steps:   可视化步数
        save_dir:    保存渲染图像的目录 (None 则不保存)
        device:      计算设备
    """
    if renderer is None:
        renderer = create_renderer()

    model.eval()
    batch = next(iter(dataloader))

    images = batch["images"][:1].to(device)     # 取第一个样本的图像
    input_ids = batch["input_ids"][:1].to(device)  # 取第一个样本的文本

    renderer.reset()
    frames = []

    print(f"Visualizing {num_steps} steps...")
    for step in range(num_steps):
        with torch.no_grad():
            action = model(images, input_ids)  # [1, 7]
        action_np = action[0].cpu().numpy()

        renderer.step(action_np)
        frame = renderer.render()
        frames.append(frame)

        if save_dir:
            os.makedirs(save_dir, exist_ok=True)
            from PIL import Image
            Image.fromarray(frame).save(os.path.join(save_dir, f"frame_{step:04d}.png"))

    renderer.close()
    print(f"Done! {len(frames)} frames rendered.")

    # 保存为 GIF
    if save_dir and frames:
        _save_gif(frames, os.path.join(save_dir, "animation.gif"))

    return frames


def _save_gif(frames: List[np.ndarray], path: str, duration: float = 0.05):
    """保存帧序列为 GIF"""
    try:
        from PIL import Image
        pil_frames = [Image.fromarray(f) for f in frames]
        pil_frames[0].save(
            path,
            save_all=True,
            append_images=pil_frames[1:],
            duration=duration * 1000,
            loop=0,
        )
        print(f"GIF saved → {path}")
    except Exception as e:
        print(f"GIF save failed: {e}")


# ═══════════════════════════════════════════════════════════════
# 6. 演示入口
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="MuJoCo Renderer Demo")
    parser.add_argument("--demo", action="store_true", help="演示随机动作")
    parser.add_argument("--render", action="store_true", help="渲染并保存图像")
    parser.add_argument("--backend", type=str, default="auto", choices=["auto", "mujoco", "matplotlib"])
    parser.add_argument("--steps", type=int, default=100, help="仿真步数")
    parser.add_argument("--save", type=str, default=None, help="保存帧到目录")
    args = parser.parse_args()

    print("=" * 60)
    print(f"MuJoCo Renderer Demo  (backend={args.backend})")
    print("=" * 60)

    if args.backend == "mujoco" or (args.backend == "auto" and _mujoco_available()):
        print("Using MuJoCo 3D renderer")
        renderer = MuJoCoRenderer()
        renderer.reset()

        # 生成随机动作序列
        for step in range(args.steps):
            # 随机动作: 小范围随机游走
            action = np.random.randn(7) * 0.02
            action[5:] = np.clip(action[5:], -0.5, 0.5)  # 夹爪范围限制
            renderer.step(action)

            if args.render or args.save:
                frame = renderer.render()
                if args.save:
                    os.makedirs(args.save, exist_ok=True)
                    from PIL import Image
                    Image.fromarray(frame).save(os.path.join(args.save, f"frame_{step:04d}.png"))

            if step % 20 == 0:
                ee_pos = renderer.get_end_effector_pos()
                print(f"  Step {step:3d}: EE pos = [{ee_pos[0]:.3f}, {ee_pos[1]:.3f}, {ee_pos[2]:.3f}]")

        renderer.close()
    else:
        print("Using Matplotlib 2D renderer")
        renderer = MatplotlibRenderer()
        renderer.reset()

        for step in range(args.steps):
            action = np.random.randn(7) * 0.02
            renderer.step(action)

        frame = renderer.render()
        if args.save:
            os.makedirs(args.save, exist_ok=True)
            from PIL import Image
            Image.fromarray(frame).save(os.path.join(args.save, "trajectory.png"))
            print(f"Saved → {os.path.join(args.save, 'trajectory.png')}")

        renderer.close()

    print(f"\n{'=' * 60}")
    print("渲染完成!")
    print(f"{'=' * 60}")