# ROS2 实战案例：从零搭建移动机器人 SLAM 建图与导航

> 基于 Gitee 开源项目 [idlity/myfirst_robot](https://gitee.com/idlity/myfirst_robot) 整理的 ROS2 Jazzy 全流程实战教程。

## 项目背景

本实战案例以一个差速驱动移动机器人为载体，覆盖从环境搭建、机器人建模、Gazebo 仿真、SLAM 建图到 Nav2 自主导航的完整开发流程，并配套视频录制与网页展示方案。

## 技术栈

| 组件 | 版本 | 说明 |
|------|------|------|
| Ubuntu | 24.04 LTS | 推荐操作系统 |
| ROS2 | Jazzy Jalisco | 与 Ubuntu 24.04 配套的 LTS 版本 |
| Gazebo | 8.x (Harmonic) | 新一代物理仿真引擎 |
| Nav2 | Jazzy | ROS2 官方导航框架 |
| RViz2 | Jazzy | 3D 可视化工具 |

## 目录结构

```
ros-practice/
├── README.md                         # 项目概述（本文件）
├── tutorials/                        # 实战教程
│   ├── 01-环境搭建.md                 # Ubuntu + ROS2 + Gazebo 安装
│   ├── 02-机器人模型搭建.md           # SDF 差速驱动机器人建模
│   ├── 03-Gazebo仿真环境.md          # 世界模型与仿真启动
│   ├── 04-Launch启动文件.md           # ROS2 launch 编排
│   ├── 05-SLAM建图实战.md             # slam_toolbox 建图流程
│   ├── 06-Nav2导航实战.md             # 自主导航配置与调试
│   └── 07-视频录制与回放.md           # 录制仿真过程与网页展示
├── src/                             # ROS2 源代码包
│   └── myfirst_robot/               # 机器人功能包
│       ├── model/
│       │   └── vehicle_blue.sdf     # 机器人 SDF 模型
│       ├── launch/
│       │   ├── gz_sim.launch.py      # Gazebo 仿真启动
│       │   ├── slam.launch.py        # SLAM 建图启动
│       │   └── nav2_bringup.launch.py # Nav2 导航启动
│       ├── config/
│       │   └── nav2_params.yaml      # Nav2 参数配置
│       ├── worlds/
│       │   └── warehouse.sdf         # 仓库世界模型
│       ├── urdf/
│       │   └── vehicle_blue.urdf    # URDF 版模型（备用）
│       ├── myfirst_robot/
│       │   └── teleop_keyboard.py    # 键盘遥控节点
│       ├── package.xml
│       └── setup.py
├── scripts/                         # 实用脚本
│   ├── record_video.sh             # 视频录制脚本（Gazebo + RViz）
│   ├── save_map.sh                  # 地图保存脚本
│   └── install_deps.sh              # 依赖一键安装
└── web/                             # 网页展示
    ├── index.html                   # 视频展示主页
    └── assets/
        └── style.css               # 网页样式
```

## 快速开始

```bash
# 1. 克隆项目
git clone https://gitee.com/idlity/myfirst_robot.git
cd myfirst_robot

# 2. 编译
colcon build --symlink-install

# 3. 启动仿真
source install/setup.bash
ros2 launch myfirst_robot gz_sim.launch.py

# 4. 启动 SLAM 建图（新终端）
ros2 launch myfirst_robot slam.launch.py

# 5. 键盘遥控建图（新终端）
ros2 run myfirst_robot teleop_keyboard

# 6. 保存地图
ros2 run nav2_map_server map_saver_cli -f ~/map
```

## 实战教程导航

| 教程 | 难度 | 预计耗时 | 关键产出 |
|------|------|---------|---------|
| [01-环境搭建](tutorials/01-环境搭建.md) | 入门 | 1h | Ubuntu 24.04 + ROS2 Jazzy |
| [02-机器人模型搭建](tutorials/02-机器人模型搭建.md) | 初级 | 2h | vehicle_blue.sdf |
| [03-Gazebo仿真环境](tutorials/03-Gazebo仿真环境.md) | 初级 | 1h | 仿真世界 + 机器人加载 |
| [04-Launch启动文件](tutorials/04-Launch启动文件.md) | 中级 | 1h | launch 文件编排 |
| [05-SLAM建图实战](tutorials/05-SLAM建图实战.md) | 中级 | 2h | 占据栅格地图 |
| [06-Nav2导航实战](tutorials/06-Nav2导航实战.md) | 高级 | 3h | 自主导航 demo |
| [07-视频录制与回放](tutorials/07-视频录制与回放.md) | 中级 | 1h | 录屏视频 + 网页展示 |

## 机器人参数

| 参数 | 值 | 说明 |
|------|-----|------|
| 驱动方式 | 差速驱动 | 左右轮独立驱动 + 后万向轮 |
| 车体尺寸 | 0.667 × 0.333 × 0.167 m | base_link |
| 轮距 | 0.4 m | 左右轮中心距 |
| 轮半径 | 0.133 m | 驱动轮 |
| 激光雷达 | 360 点/帧, 20m 量程, 5Hz | GPU LiDAR |
| 最大线速度 | 1.5 m/s | DiffDrive 插件限制 |
| 最大角速度 | 3.0 rad/s | DiffDrive 插件限制 |
