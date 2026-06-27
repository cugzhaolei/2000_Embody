#!/usr/bin/env python3
"""SO-101 MuJoCo Simulation - Headless Mode with Offscreen Rendering"""

import mujoco
import numpy as np
import os

MODEL_PATH = "/home/dev/SO-ARM100/Simulation/SO101/scene.xml"
OUTPUT_DIR = "/home/dev/so101_sim_output"

print("=" * 60)
print("SO-101 MuJoCo Simulation")
print("=" * 60)

os.makedirs(OUTPUT_DIR, exist_ok=True)

print(f"Loading model from: {MODEL_PATH}")
m = mujoco.MjModel.from_xml_path(MODEL_PATH)
d = mujoco.MjData(m)

print(f"Model loaded successfully!")
print(f"  Number of joints: {m.njnt}")
print(f"  Number of actuators: {m.nu}")
print(f"  Number of bodies: {m.nbody}")
print(f"  Timestep: {m.opt.timestep}")

print("\n--- Joint Information ---")
for i in range(m.njnt):
    name = mujoco.mj_id2name(m, mujoco.mjtObj.mjOBJ_JOINT, i)
    if name:
        qpos_idx = m.jnt_qposadr[i]
        limited = m.jnt_limited[i]
        if limited:
            lo, hi = m.jnt_range[i]
            print(f"  Joint {i}: {name:20s} | qpos[{qpos_idx}] | range: [{np.degrees(lo):.1f}, {np.degrees(hi):.1f}] deg")
        else:
            print(f"  Joint {i}: {name:20s} | qpos[{qpos_idx}] | unlimited")

print("\n--- Actuator Information ---")
for i in range(m.nu):
    name = mujoco.mj_id2name(m, mujoco.mjtObj.mjOBJ_ACTUATOR, i)
    if name:
        ctrlrange = m.actuator_ctrlrange[i]
        print(f"  Actuator {i}: {name:20s} | ctrl range: [{ctrlrange[0]:.2f}, {ctrlrange[1]:.2f}]")

# Create offscreen renderer
renderer = mujoco.Renderer(m, height=480, width=640)

# Reset simulation
mujoco.mj_resetData(m, d)
mujoco.mj_forward(m, d)

# Render initial state
renderer.update_scene(d)
img = renderer.render()
from PIL import Image
Image.fromarray(img).save(os.path.join(OUTPUT_DIR, "frame_000_initial.png"))
print(f"\nSaved initial frame to {OUTPUT_DIR}/frame_000_initial.png")

# Define a simple motion sequence
motion_sequence = [
    ("Home position", list(range(6)), [0.0]*6, 50),
    ("Rotate base", [0], [np.radians(45)], 100),
    ("Lift shoulder", [1], [np.radians(-30)], 100),
    ("Bend elbow", [2], [np.radians(60)], 100),
    ("Wrist flex", [3], [np.radians(-30)], 100),
    ("Wrist roll", [4], [np.radians(45)], 100),
    ("Close gripper", [5], [np.radians(1.5)], 100),
    ("Open gripper", [5], [np.radians(0.0)], 100),
    ("Return home", list(range(6)), [0.0]*6, 150),
]

frame_count = 1
step_count = 0

print("\n--- Running Simulation ---")
for desc, joint_indices, target_angles, steps in motion_sequence:
    print(f"  Motion: {desc} ({steps} steps)")

    current = np.array([d.qpos[i] for i in range(6)])
    target = np.zeros(6)
    for idx, angle in zip(joint_indices, target_angles):
        target[idx] = angle

    for i in range(6):
        if i not in joint_indices:
            target[i] = current[i]

    for step in range(steps):
        alpha = (step + 1) / steps
        for i in range(6):
            d.qpos[i] = current[i] + alpha * (target[i] - current[i])

        mujoco.mj_forward(m, d)
        step_count += 1

        if step % 10 == 0 or step == steps - 1:
            renderer.update_scene(d)
            img = renderer.render()
            fname = f"frame_{frame_count:03d}_{desc.replace(' ', '_')}.png"
            Image.fromarray(img).save(os.path.join(OUTPUT_DIR, fname))
            frame_count += 1

print(f"\nTotal physics steps: {step_count}")
print(f"Total frames saved: {frame_count}")

# Final render with different camera angle (use -1 for default tracking cam)
renderer.update_scene(d, camera=-1)
img = renderer.render()
Image.fromarray(img).save(os.path.join(OUTPUT_DIR, "frame_final_side_view.png"))
print(f"Saved side view to {OUTPUT_DIR}/frame_final_side_view.png")

print("\n--- Final Joint Positions ---")
for i in range(6):
    name = mujoco.mj_id2name(m, mujoco.mjtObj.mjOBJ_JOINT, i)
    if name:
        print(f"  {name}: {np.degrees(d.qpos[i]):.2f} deg")

print("\nSimulation complete! Check output images in:", OUTPUT_DIR)
