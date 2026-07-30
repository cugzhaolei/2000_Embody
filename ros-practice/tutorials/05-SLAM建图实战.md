# 05 SLAM 建图实战

## 5.1 SLAM 算法概述

### slam_toolbox 模式对比

| 模式 | 可执行文件 | 适用场景 | 特点 |
|------|-----------|---------|------|
| 在线异步 | `async_slam_toolbox_node` | 实时建图 | 非阻塞，适合大地图 |
| 在线同步 | `sync_slam_toolbox_node` | 高精度建图 | 阻塞式优化，精度更高 |
| 定位模式 | `lifecycle_slam_toolbox_node` | 已有地图定位 | 仅定位不建图 |
| 离线 | `map_merger` | 多地图合并 | 后处理工具 |

> 本项目使用同步模式，适合小范围仓库建图。

### SLAM 核心流程

```
LiDAR /scan → 扫描匹配(扫描配准) → 位姿估计 → 地图更新 → 回环检测 → 图优化
     ↑                                                         ↓
里程计 /odom ←←←←←←← TF 变换 ←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←
```

## 5.2 建图前准备

### 检查话题数据流

```bash
# 终端1：启动仿真
ros2 launch myfirst_robot gz_sim.launch.py

# 终端2：验证传感器数据
ros2 topic list
# 必须存在: /scan, /odom, /tf, /cmd_vel

# 检查 LiDAR 数据格式
ros2 topic echo /scan --once
# 应看到: angle_min, angle_max, ranges[360], ...

# 检查里程计
ros2 topic echo /odom --once
# 应看到: pose.position, pose.orientation, twist

# 检查 TF 树
ros2 run tf2_tools view_frames
# 应生成 frames.pdf，包含 odom→base_footprint→base_link→laser_link
```

### TF 树预期结构

```
odom
 └── base_footprint
      └── base_link
           ├── left_wheel
           ├── right_wheel
           ├── caster_wheel
           └── laser_cylinder_link
                └── laser_link
```

## 5.3 启动 SLAM 建图

```bash
# 终端1：Gazebo 仿真（已启动）
ros2 launch myfirst_robot gz_sim.launch.py

# 终端2：启动 SLAM
ros2 launch myfirst_robot slam.launch.py

# 终端3：启动键盘遥控（如 launch 未自动启动）
ros2 run myfirst_robot teleop_keyboard
```

### 键盘控制说明

```
控制键:
   w    前进
   x    后退
   a    左转
   d    右转
   s    停止

速度档位:
   1-9  线速度 0.1~0.9 m/s
   Q-Z  角速度 0.1~1.0 rad/s
```

## 5.4 建图策略

### 小地图建图路径规划

```
建议建图路线（仓库环境）：

    ┌─────────────────────┐
    │                     │
    │   ┌───┐    ┌───┐   │
    │   │shelf│   │shelf│  │
    │   │ 1  │    │ 2  │   │
    │   └───┘    └───┘   │
    │                     │
    │  ←←←←←←←←←  ←←←   │  ← 第3圈：外围绕行
    │  ↓                ↑ │
    │  ↓                ↑ │
    │  ↓→→→→→→→→→→→→→↑ │
    │  起点              │
    └─────────────────────┘

策略：
1. 先沿中央通道直行（测试里程计）
2. 绕货架S形走（覆盖所有区域）
3. 外围绕行一圈（闭合回环）
```

### 建图参数调优

| 参数 | 默认值 | 调优建议 | 影响 |
|------|--------|---------|------|
| resolution | 0.05 | 小地图0.02, 大地图0.10 | 分辨率越小地图越精细但计算量大 |
| max_laser_range | 20.0 | 室内10.0即可 | 减小可降低噪声干扰 |
| minimum_time_interval | 0.5 | 快速移动0.3 | 控制关键帧频率 |
| loop_search_maximum_distance | 3.0 | 大环境5.0 | 回环检测范围 |

## 5.5 RViz 可视化配置

### 必要的 RViz 显示项

| Display | Topic | 用途 |
|---------|-------|------|
| RobotModel | /robot_description | 机器人3D模型 |
| LaserScan | /scan | 激光雷达点云 |
| Map | /map | SLAM 实时地图 |
| TF | — | 坐标变换树 |
| Odometry | /odom | 里程计轨迹 |
| Path | /slam_toolbox/graph_visualization | SLAM 位姿图 |

### 常见问题：地图空白

```bash
# 检查 /map 话题
ros2 topic echo /map --once
# 如果 occupancy_grid 全是 -1（未知），说明 SLAM 未收到数据

# 检查 /scan 时间戳
ros2 topic hz /scan  # 应为 5Hz

# 检查 use_sim_time
ros2 param get /slam_toolbox use_sim_time
# 应为 true
```

## 5.6 保存地图

```bash
# 方法1：命令行保存
ros2 run nav2_map_server map_saver_cli -f ~/maps/warehouse

# 生成两个文件：
# ~/maps/warehouse.pgm  — 占据栅格图（灰度图）
# ~/maps/warehouse.yaml — 地图元数据

# 方法2：脚本保存（自动创建目录）
bash ~/ros2_ws/src/myfirst_robot/scripts/save_map.sh warehouse
```

### 地图文件格式

**warehouse.yaml**:
```yaml
image: warehouse.pgm
mode: trinary
resolution: 0.05  # 每像素 5cm
origin: [-10.0, -10.0, 0.0]  # 地图原点（左下角）世界坐标
negate: 0
occupied_thresh: 0.65   # 占据概率 > 0.65 为障碍
free_thresh: 0.196      # 占据概率 < 0.196 为自由空间
```

**warehouse.pgm**: P5 格式灰度图
- 0 (黑色) = 占据（障碍物）
- 254 (白色) = 自由空间
- 205 (灰色) = 未知区域

## 5.7 建图质量评估

| 指标 | 合格标准 | 检查方法 |
|------|---------|---------|
| 墙壁连续性 | 无断裂 | 地图中墙壁应为连续线 |
| 货架轮廓 | 清晰可辨 | 货架边缘锐利无重影 |
| 回环闭合 | 无错位 | 走回起点时地图不错位 |
| 地图完整性 | 覆盖全部区域 | 无大块未知区域 |
| 尺寸精度 | 误差<5% | 测量已知距离对比 |

---

**下一课**：[06-Nav2导航实战](06-Nav2导航实战.md) — 配置 Nav2 实现自主导航
