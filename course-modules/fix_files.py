#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修复课程模块文件中的已知问题：
1. 模块一：删除重复TOC和重复课程信息头
2. 模块二：为每节课添加深化内容，修正参考文献
"""

import re
import sys

DIR_PATH = r'C:\Users\admin\Desktop\dev\2000_Embody\course-modules'

# ============================================================
# 模块二深化内容数据（每课的📗📘📕内容）
# ============================================================

DEEPEN_CONTENT = {
    '09': {
        'green': """
#### 9.3 底盘结构方案对比图

```mermaid
graph TB
    subgraph 差速两轮
        D1[驱动轮×2<br/>同轴左右布置]
        D2[万向轮×1-2<br/>辅助支撑]
        D3[结构简单/成本低]
    end

    subgraph 四轮差速
        Q1[驱动轮×4<br/>四角布置]
        Q2[全轮驱动/载重大]
        Q3[转向原地旋转]
    end

    subgraph 麦克纳姆轮
        M1[麦轮×4<br/>辊子45°]
        M2[全向移动/横移]
        M3[地面要求高/磨损大]
    end

    subgraph 阿克曼转向
        A1[前轮转向<br/>后轮驱动]
        A2[高速稳定/载重大]
        A3[转弯半径大/无横移]
    end

    D1 --> R{选型决策}
    Q1 --> R
    M1 --> R
    A1 --> R
    R --> S1[仓储物流→差速]
    R --> S2[狭小工位→麦轮]
    R --> S3[户外巡检→阿克曼]
    R --> S4[重载/高速→阿克曼]
```

#### 9.4 底盘结构参数对照表

| 参数 | 差速两轮 | 四轮差速 | 麦克纳姆轮 | 阿克曼转向 |
|------|---------|---------|-----------|-----------|
| **驱动轮数** | 2 | 4 | 4 | 2(后驱)/4(四驱) |
| **自由度** | 2自由度 | 2自由度 | 3自由度 | 2自由度 |
| **全向移动** | 否 | 否 | 是 | 否 |
| **原地旋转** | 是 | 是 | 是 | 否 |
| **最大速度** | 1.5-2m/s | 1.5-2m/s | 1.0-1.5m/s | 5-20km/h |
| **载重能力** | 50-200kg | 100-500kg | 50-150kg | 100-1000kg |
| **爬坡能力** | ≤5° | ≤8° | ≤3° | ≤15° |
| **定位精度** | ±20-30mm | ±20-30mm | ±30-50mm | ±50-100mm |
| **地面要求** | 平整 | 平整 | 平整+干净 | 平整 |
| **典型成本** | 1-3万 | 2-5万 | 3-8万 | 5-15万 |
| **适用场景** | 仓储物流 | 重载搬运 | 狭小空间 | 户外巡检 |

#### 9.6 调试检查清单

- [ ] 底盘结构方案已根据场景需求确定（速度/载重/全向性/成本）
- [ ] 运动学模型推导完成，正逆解验证一致
- [ ] 轮距/轴距/轮径参数已确定
- [ ] 悬挂行程满足地面不平面度要求
- [ ] 驱动轮接地压力均匀性已验证
- [ ] 最小转弯半径满足场地约束
- [ ] 电池安装位已规划，CG高度校核
- [ ] 传感器安装位视野无遮挡
""",
        'blue': """
#### 9.1 底盘方案选型决策矩阵

| 评估维度 | 权重 | 差速两轮 | 四轮差速 | 麦克纳姆轮 | 阿克曼转向 |
|---------|------|---------|---------|-----------|-----------|
| 运动灵活性 | 25% | 6 | 7 | 10 | 4 |
| 载重能力 | 20% | 7 | 9 | 6 | 9 |
| 成本优势 | 20% | 9 | 7 | 5 | 4 |
| 地面适应性 | 15% | 7 | 7 | 4 | 9 |
| 控制复杂度 | 10% | 9 | 8 | 5 | 6 |
| 维护便利性 | 10% | 9 | 7 | 5 | 7 |
| **加权总分** | **100%** | **7.45** | **7.55** | **6.15** | **6.25** |

> **选型建议**：3C仓储首选差速两轮（简单可靠+低成本），狭小工位选麦轮（全向性），户外大场景选阿克曼（高速稳定）。

#### 9.2 底盘关键器件供应商对比表

| 器件 | 品牌 | 型号 | 关键参数 | 参考价(元) | 交期 |
|------|------|------|---------|-----------|------|
| 差速轮毂电机 | 汇川 | MS1H2-20B30CB | 200W/3000rpm | 1,200 | 2-3周 |
| 差速轮毂电机 | 禾川 | X6-200W-30 | 200W/3000rpm | 980 | 2-3周 |
| 麦轮电机 | 云帆 | YF-80BL80 | 80W/3000rpm | 450 | 1-2周 |
| 聚氨酯麦轮4寸 | 常州宏利 | HL-MW100 | 12辊/承载30kg | 180 | 1周 |
| 悬挂弹簧 | 力佳 | LJD-3015 | 刚度15N/mm | 35 | 现货 |
| 轴承 | NSK | 6205-2RS | 25×52×15mm | 28 | 现货 |
""",
        'red': """
#### 9.5 底盘方案成本分析表

| 成本项 | 差速两轮(元) | 麦克纳姆轮(元) | 阿克曼转向(元) |
|-------|------------|-------------|-------------|
| 驱动电机×2 | 2,400 | — | 2,400 |
| 驱动电机×4 | — | 1,800 | — |
| 转向电机×1 | — | — | 800 |
| 驱动器×2 | 3,200 | — | 3,200 |
| 驱动器×4 | — | 2,400 | — |
| 转向驱动器×1 | — | — | 600 |
| 轮组 | 600 | 720 | 800 |
| 减速器×2 | 3,600 | — | 3,600 |
| 减速器×4 | — | 2,400 | — |
| 悬挂组 | 400 | 400 | 600 |
| 转向机构 | — | — | 1,500 |
| 结构件 | 3,000 | 3,500 | 5,000 |
| **合计** | **13,200** | **11,220** | **18,500** |

> **结论**：差速两轮底盘成本最低，麦轮电机多但单轮便宜，阿克曼转向机构复杂成本最高。
""",
    },
    '10': {
        'green': """
#### 10.1 差速运动学推导过程图

```mermaid
graph LR
    A[左轮角速度 ω_L] --> C[左轮线速度 v_L = ω_L × r]
    B[右轮角速度 ω_R] --> D[右轮线速度 v_R = ω_R × r]
    C --> E[车体线速度 v = (v_L + v_R)/2]
    D --> E
    C --> F[车体角速度 ω = (v_R - v_L)/L]
    D --> F
    E --> G[Δx = v·cos(θ)·Δt]
    E --> H[Δy = v·sin(θ)·Δt]
    F --> I[Δθ = ω·Δt]
    G --> J[里程计位姿递推]
    H --> J
    I --> J
```

#### 10.4 里程计误差来源分析表

| 误差来源 | 误差类型 | 典型量级 | 累积特性 | 修正方法 |
|---------|---------|---------|---------|---------|
| 轮径偏差 | 系统误差 | 1-3% | 线性累积 | 标定轮径 |
| 轮距偏差 | 系统误差 | 1-5mm | 线性累积 | 实测轮距 |
| 地面打滑 | 随机误差 | >10% | 跳变 | IMU融合 |
| 编码器分辨率 | 量化误差 | 0.09°/脉冲 | 随机 | 提高PPR |
| 采样不同步 | 系统误差 | <1ms | 随机 | 硬件同步 |
| 轮子变形 | 缓变误差 | 0.5-1% | 缓慢漂移 | 定期标定 |
""",
        'blue': """
#### 10.2 编码器选型与精度计算

| 参数 | 底盘轮编码器 | 机械臂关节编码器 |
|------|------------|----------------|
| 类型 | 增量式 | 绝对式 |
| 分辨率 | 1000PPR(四倍频4000) | 17bit(131072) |
| 减速比 | 1:30 | 1:100 |
| 关节分辨率 | 4000×30=120000脉冲/转 | 131072×100=13107200单位/转 |
| 角度分辨率 | 0.003° | 0.000027° |
| 线速度分辨率 | 0.0026mm(轮径100mm) | — |
| 适用标准 | IEC 61491 | IEC 61491 |

#### 10.3 里程计标定方法

| 标定方法 | 步骤 | 精度 | 耗时 | 适用场景 |
|---------|------|------|------|---------|
| 直线标定 | 机器人走直线1m，对比编码器读数 | ±1% | 10min | 轮径标定 |
| 圆弧标定 | 机器人原地旋转360°，对比IMU | ±2% | 15min | 轮距标定 |
| URG标定 | 激光雷达辅助标定 | ±0.5% | 30min | 高精度标定 |
| Kalman滤波在线标定 | 运行中持续估计轮径/轮距 | ±0.3% | 实时 | 工程部署 |
""",
        'red': """
#### 10.5 里程计与SLAM融合架构

```mermaid
graph TB
    subgraph 传感器层
        E1[编码器A/B脉冲]
        I1[IMU加速度/角速度]
        L1[激光雷达点云]
    end

    subgraph 里程计层
        O1[轮式里程计<br/>高频50Hz/漂移大]
        O2[IMU预积分<br/>高频200Hz/漂移中]
    end

    subgraph 融合层
        F1[EKF扩展卡尔曼滤波<br/>轮式+IMU融合]
        F2[AMCL定位<br/>激光匹配校正]
    end

    subgraph 输出
        P1[融合位姿<br/>/odom→/map]
    end

    E1 --> O1
    I1 --> O2
    O1 --> F1
    O2 --> F1
    L1 --> F2
    F1 --> F2
    F2 --> P1
```

> **关键**：里程计提供高频先验位姿，SLAM提供低频全局校正，EKF融合两者优势。
""",
    },
    '11': {
        'green': """
#### 11.4 麦轮运动学正逆解推导

```mermaid
graph LR
    subgraph 逆运动学
        V1[vx] --> M[逆运动学矩阵K/r]
        V2[vy] --> M
        V3[ω] --> M
        M --> W1[ω₁]
        M --> W2[ω₂]
        M --> W3[ω₃]
        M --> W4[ω₄]
    end

    subgraph 正运动学
        W1b[ω₁] --> P[正运动学矩阵K⁺·r]
        W2b[ω₂] --> P
        W3b[ω₃] --> P
        W4b[ω₄] --> P
        P --> V4[vx]
        P --> V5[vy]
        P --> V6[ω]
    end
```

#### 11.5 麦轮误差来源与修正方法

| 误差来源 | 影响方向 | 典型误差 | 修正方法 |
|---------|---------|---------|---------|
| 辊子接地面积小 | 横移 | 10-50mm/m | 增大辊子数/更换高摩擦材质 |
| 地面摩擦系数变化 | 全方向 | 5-20mm/m | 铺设防滑地面/自适应增益 |
| 安装角度偏差 | 旋转 | 1-5°/m | 精确校准安装角/在线标定 |
| 辊子磨损 | 横移 | 逐渐增大 | 定期更换辊子/磨损补偿算法 |
| 悬挂预紧力不均 | 横移 | 10-30mm/m | 调整四轮预紧力一致 |
""",
        'blue': """
#### 11.1 麦轮选型参数对比表

| 参数 | 4寸8辊 | 4寸10辊 | 4寸12辊 | 6寸10辊 | 8寸12辊 |
|------|--------|--------|--------|--------|--------|
| 轮毂直径(mm) | 100 | 100 | 100 | 152 | 200 |
| 辊子数量 | 8 | 10 | 12 | 10 | 12 |
| 辊子材质 | 橡胶 | 聚氨酯 | 聚氨酯 | 聚氨酯 | 聚氨酯 |
| 单轮承载(kg) | 15 | 25 | 30 | 50 | 80 |
| 宽度(mm) | 35 | 40 | 45 | 50 | 60 |
| 参考价(元) | 80 | 120 | 180 | 280 | 450 |
| 推荐场景 | 轻载科研 | 中载AGV | 中载AMR | 重载AGV | 重载户外 |

> **推荐**：本项目(80kg总质量)选用4寸12辊聚氨酯麦轮，单轮承载30kg，4轮总承载120kg，余量50%。

#### 11.3 麦轮底盘运动学标定方法

| 标定项 | 方法 | 工具 | 频率 |
|-------|------|------|------|
| 辊子安装角 | 激光跟踪仪测旋转轨迹 | 激光跟踪仪 | 装机时 |
| Lx/Ly参数 | 架空四轮，给定cmd_vel测实际速度 | 编码器+示波器 | 首次部署 |
| 摩擦系数 | 横移1m测实际位移偏差 | 卷尺+计时器 | 每月 |
| 接地压力 | 四轮各放地磅，调整悬挂 | 地磅×4 | 装机时 |
""",
        'red': """
#### 11.2 麦轮底盘成本分析表

| 成本项 | 推荐型号 | 单价(元) | 数量 | 小计(元) | 备注 |
|-------|---------|---------|------|---------|------|
| 麦轮电机 | 云帆YF-80BL80 | 450 | 4 | 1,800 | 80W无刷 |
| 电机驱动器 | 云帆YF-DM8048 | 380 | 4 | 1,520 | 48V/4A |
| 麦轮4寸12辊 | 常州宏利HL-MW100 | 180 | 4 | 720 | 聚氨酯 |
| 行星减速器1:30 | 新宝PG42-30 | 650 | 4 | 2,600 | 背隙<1弧分 |
| 编码器1000PPR | 汇川ZNH-IS6023S | 600 | 4 | 2,400 | 增量式 |
| 悬挂弹簧 | 力佳LJD-3015 | 35 | 4 | 140 | 15N/mm |
| 底盘框架 | 定制铝合金 | 3,500 | 1 | 3,500 | 钣金+CNC |
| **合计** | | | | **12,680** | |

> **对比**：麦轮底盘12,680元 vs 差速底盘13,200元，成本接近但全向性大幅提升。
""",
    },
    '12': {
        'green': """
#### 12.4 阿克曼转向运动学推导

```mermaid
graph TB
    subgraph 自行车模型
        A[前轮转角δ] --> B[角速度 θ̇ = v·tanδ/L]
        C[车速v] --> D[线速度 ẋ = v·cosθ<br/>ẏ = v·sinθ]
        B --> E[位姿更新<br/>x,y,θ]
        D --> E
    end

    subgraph 阿克曼几何约束
        F[cotδ_outer - cotδ_inner = W/L] --> G[所有车轮绕<br/>同一瞬时圆心]
        H[R_min = L/sinδ_max] --> I[最小转弯半径<br/>= 3.5m]
    end
```

#### 12.5 路径跟踪算法对比

| 算法 | Pure Pursuit | Stanley | MPC |
|------|-------------|---------|-----|
| **原理** | 跟踪预瞄点 | 前轴横向偏差+航向偏差 | 模型预测滚动优化 |
| **参数** | 预瞄距离L_d | 增益k | 预测步长N,权重Q/R |
| **低速性能** | 好 | 好 | 好 |
| **高速性能** | 中 | 好 | 优 |
| **参数调节** | 简单(1个) | 简单(1个) | 复杂(多参数) |
| **计算量** | 低 | 低 | 高 |
| **ROS2支持** | nav2_regulated_pure_pursuit | nav2_regulated_pure_pursuit | 自研/acado_ros2 |
| **适用速度** | <2m/s | <5m/s | 不限 |
""",
        'blue': """
#### 12.1 阿克曼底盘参数选型表

| 参数 | 符号 | 园区配送车 | 户外巡检车 | 无人驾驶物流车 |
|------|------|-----------|-----------|-------------|
| 轴距 | L | 0.8m | 1.2m | 2.0m |
| 轮距 | W | 0.6m | 0.8m | 1.4m |
| 最大转向角 | δ_max | 30° | 25° | 35° |
| 最小转弯半径 | R_min | 1.6m | 2.8m | 3.5m |
| 最大速度 | v_max | 5km/h | 10km/h | 20km/h |
| 转向驱动 | — | 舵机 | 电动助力EPS | 线控转向 |
| 轮胎 | — | 实心橡胶 | 充气轮 | 汽车轮胎 |
| 参考成本 | — | 3-5万 | 8-12万 | 15-25万 |

#### 12.3 阿克曼转向控制器参数整定

| 参数 | Pure Pursuit | Stanley | 建议初始值 |
|------|-------------|---------|-----------|
| 预瞄距离/增益 | L_d = k·v | k = 0.5 | L_d=1.0m / k=0.5 |
| 最小预瞄距离 | L_d_min | — | 0.3m |
| 速度比例系数 | k_v = 1.0 | — | 1.0-2.0 |
| 最大转向角限制 | δ_max | δ_max | 25-35° |
| 横向偏差阈值 | — | e_ya | 0.1m |
""",
        'red': """
#### 12.2 阿克曼底盘成本分析表

| 成本项 | 园区配送车(元) | 户外巡检车(元) |
|-------|-------------|-------------|
| 驱动电机+驱动器 | 3,200 | 5,600 |
| 转向电机+驱动器 | 800 | 2,000(EPS) |
| 减速器×2 | 3,600 | 4,000 |
| 转向机构 | 1,500 | 3,000 |
| 轮胎×4 | 400 | 2,000 |
| 悬挂系统 | 600 | 2,500 |
| 结构件 | 5,000 | 10,000 |
| **合计** | **15,100** | **29,100** |

> **结论**：阿克曼底盘比差速/麦轮底盘贵2-3倍，但高速稳定性和载重能力远超后者，适合户外场景。
""",
    },
    '13': {
        'green': """
#### 13.1 电机扭矩计算过程可视化

```mermaid
graph LR
    A[整车参数<br/>m=80kg, v=1.5m/s] --> B[滚动阻力矩<br/>T_roll=μ·m·g·r]
    A --> C[爬坡阻力矩<br/>T_slope=m·g·sinα·r]
    A --> D[加速阻力矩<br/>T_accel=m·a·r]
    B --> E[总扭矩<br/>T_total=T_roll+T_slope+T_accel]
    C --> E
    D --> E
    E --> F[电机功率<br/>P=T_total·v/r]
    F --> G[安全系数1.5~2.0<br/>→ 选型扭矩]
```

#### 13.4 本项目电机选型计算书

| 参数 | 符号 | 数值 | 单位 |
|------|------|------|------|
| 总质量 | m | 80 | kg |
| 目标速度 | v_max | 1.5 | m/s |
| 爬坡角度 | α | 10 | ° |
| 目标加速度 | a | 0.5 | m/s² |
| 轮半径 | r | 0.05 | m |
| 滚动阻力系数 | μ | 0.02 | — |
| 驱动轮数 | n | 2 | 个 |
| 滚动阻力矩(单轮) | T_roll | 0.39 | N·m |
| 爬坡阻力矩(单轮) | T_slope | 3.41 | N·m |
| 加速阻力矩(单轮) | T_accel | 1.00 | N·m |
| 总需求扭矩(单轮) | T_total | 4.80 | N·m |
| 电机功率需求 | P | 216 | W |
| 安全系数1.5倍 | T_sel | 7.20 | N·m |
| **选配电机额定扭矩** | **T_rated** | **≥7.2** | **N·m** |
""",
        'blue': """
#### 13.2 电机选型对比表

| 参数 | 汇川MS1H2-20B30CB | 禾川X6-200W-30 | 步科iDM4-200W | 安川SGM7J-02AFC6S |
|------|------------------|---------------|--------------|------------------|
| 额定功率 | 200W | 200W | 200W | 200W |
| 额定扭矩 | 0.637N·m | 0.64N·m | 0.64N·m | 0.637N·m |
| 额定转速 | 3000rpm | 3000rpm | 3000rpm | 3000rpm |
| 配减速器1:30后 | 19.1N·m | 19.2N·m | 19.2N·m | 19.1N·m |
| 满足选型需求 | ✓(7.2N·m) | ✓ | ✓ | ✓ |
| 价格(含驱动器) | 2,800元 | 1,980元 | 2,200元 | 6,000元 |
| 交期 | 2-3周 | 2-3周 | 3-4周 | 6-8周 |
| ROS2驱动 | 汇川协议 | 禾川SDK | 步科SDK | 安川SDK |

> **推荐**：本项目选汇川MS1H2+IS620P(性价比+国内售后)或禾川(更低成本)。
""",
        'red': """
#### 13.3 电机选型决策矩阵

| 评估维度 | 权重 | 汇川MS1H2 | 禾川X6 | 步科iDM4 | 安川SGM7J |
|---------|------|----------|--------|---------|----------|
| 扭矩余量(额定×i/需求) | 20% | 9 | 9 | 9 | 9 |
| 成本竞争力 | 25% | 8 | 9 | 8 | 4 |
| 供货交期 | 20% | 9 | 9 | 7 | 5 |
| ROS2生态 | 15% | 7 | 5 | 5 | 6 |
| 售后技术支持 | 10% | 9 | 7 | 7 | 7 |
| 功率密度 | 10% | 7 | 7 | 7 | 9 |
| **加权总分** | **100%** | **8.30** | **8.00** | **7.35** | **6.30** |
""",
    },
    '14': {
        'green': """
#### 14.4 减速器类型对比表

| 特性 | 行星减速器 | 谐波减速器 | RV减速器 |
|------|-----------|-----------|---------|
| 结构 | 太阳轮+行星轮+齿圈 | 柔轮+波发生器+刚轮 | 摆线针轮+行星架 |
| 减速比范围 | 3-100 | 50-160 | 40-200 |
| 扭矩密度 | 中 | 高 | 高 |
| 背隙 | 1-5弧分 | <30弧秒 | <1弧分 |
| 效率 | 95-98% | 70-85% | 90-95% |
| 同轴输入输出 | 是 | 是 | 是 |
| 成本(同规格) | 低 | 中 | 高 |
| 适用场景 | 底盘轮驱动 | 机械臂关节 | 工业臂关节 |

#### 14.1 本项目减速器选型计算

| 参数 | 符号 | 数值 | 说明 |
|------|------|------|------|
| 电机额定扭矩 | T_motor | 0.637N·m | 汇川MS1H2 |
| 电机最高转速 | N_motor | 3000rpm | — |
| 减速比 | i | 1:30 | 行星减速器 |
| 传动效率 | η | 0.95 | 行星减速器 |
| 输出扭矩 | T_out | 18.1N·m | T_motor×i×η |
| 输出转速 | N_out | 100rpm | N_motor/i |
| 轮径100mm线速度 | v | 0.52m/s | π×0.1×100/60 |
| 需求轮扭矩 | T_req | 7.2N·m | 第13课计算结果 |
| 扭矩裕度 | T_out/T_req | 2.51 | >1.3 ✓ |
""",
        'blue': """
#### 14.3 行星减速器供应商对比表

| 品牌 | 型号 | 减速比 | 额定输出扭矩 | 背隙 | 价格(元) | 交期 |
|------|------|--------|------------|------|---------|------|
| 新宝 | PG42-030 | 1:30 | 22N·m | ≤1弧分 | 650 | 2-3周 |
| 来福 | LPL-042-030 | 1:30 | 20N·m | ≤2弧分 | 480 | 2-3周 |
| 精锐 | PRS042-030 | 1:30 | 21N·m | ≤1.5弧分 | 550 | 3-4周 |
| Neugart | PLE-042-030 | 1:30 | 25N·m | ≤1弧分 | 1,800 | 4-6周 |
| 威腾 | WTP042-030 | 1:30 | 20N·m | ≤2弧分 | 420 | 1-2周 |

> **推荐**：选新宝PG42(背隙最优)或威腾(交期最快+成本最低)。
""",
        'red': """
#### 14.2 减速器寿命校核

| 校核项 | 公式 | 本项目计算 | 结果 |
|-------|------|-----------|------|
| 等效载荷 | T_eq = T_rated × (t1/t_total)^1/3 | 0.637×0.8^1/3 = 0.58N·m | — |
| 疲劳寿命 | L10 = (T_rated×i×η/T_eq)^3 × 10^6转 | (18.1/7.2)^3 × 10^6 = 15.8×10^6转 | — |
| 工作小时数 | H = L10/(60×N_out) | 15.8×10^6/(60×100) = 2633h | >5000h × |
| 考虑工况系数 | f_w=1.2修正 | 2633/1.2 = 2194h | 需选更大型号 |
| **升级PG60** | T_rated=50N·m | L10=365×10^6转 → H=60833h | >5000h ✓ |

> **结论**：PG42寿命不满足MTBF≥5000h要求，需升级为PG60(额定50N·m)或降低负载率。
""",
    },
    '15': {
        'green': """
#### 15.2 编码器类型与工作原理

```mermaid
graph TB
    subgraph 增量式编码器
        I1[A/B两路正交脉冲] --> I2[四倍频计数<br/>分辨率=PPR×4]
        I2 --> I3[脉冲计数→位置<br/>脉冲频率→速度]
        I3 --> I4[断电丢位<br/>需回零]
    end

    subgraph 绝对式编码器
        A1[码盘位置编码] --> A2[数字接口输出<br/>SSI/BiSS/EnDat]
        A2 --> A3[断电保持<br/>上电即走]
        A3 --> A4[成本较高<br/>线数更高]
    end
```

#### 15.4 编码器分辨率计算示例

| 应用场景 | 定位精度δ | 减速比i | 轮/臂端半径r | 所需线数N | 选配方案 |
|---------|---------|--------|------------|----------|---------|
| 底盘轮定位 | ±5mm | 30 | 50mm | N≥2π×50/(5×30)=2.09→3 | 1000PPR(×4=4000)>3 ✓ |
| 机械臂关节定位 | ±0.02mm | 100 | 臂展400mm | N≥2π×400/(0.02×100)=1257 | 17bit(131072)>1257 ✓ |
| 高精度云台 | ±0.01° | 50 | — | N≥360/(0.01×50)=720 | 20bit(1048576)>720 ✓ |
""",
        'blue': """
#### 15.1 编码器选型参数对比表

| 参数 | 增量式1000PPR | 绝对式17bit | 绝对式23bit |
|------|-------------|-----------|-----------|
| 分辨率 | 4000(四倍频) | 131072 | 8388608 |
| 角度分辨率 | 0.09° | 0.0027° | 0.000043° |
| 断电保持 | 否 | 是 | 是 |
| 接口 | A/B/Z脉冲 | SSI/BiSS | BiSS/EnDat |
| 最高转速 | 12000rpm | 6000rpm | 6000rpm |
| 工作温度 | -20~85°C | -20~85°C | -20~85°C |
| 防护等级 | IP54 | IP65 | IP65 |
| 价格(元) | 100-600 | 600-2000 | 1500-5000 |
| 适用场景 | 底盘轮 | 机械臂关节 | 高精度关节 |
""",
        'red': """
#### 15.3 编码器EMC设计与信号链优化

| 干扰类型 | 表现 | 根因 | 解决方案 |
|---------|------|------|---------|
| 脉冲计数跳变 | 位置突变 | 电机PWM干扰 | 双绞屏蔽线+磁环 |
| A/B相偏移 | 速度计算错误 | 线缆长度>5m | RS422差分传输 |
| 丢脉冲 | 累积误差 | 采样频率不够 | DMA+硬件定时器 |
| 零点漂移 | 原点偏移 | 温度变化 | 温度补偿/定期校准 |
| 共模干扰 | 信号失真 | 地线回路 | 单点接地+光耦隔离 |

> **设计原则**：编码器信号线必须使用双绞屏蔽线，屏蔽层单端接地，远离电机动力线>10cm，使用RS422差分传输提高抗干扰能力。
""",
    },
    '16': {
        'green': """
#### 16.1 重心计算方法图解

```mermaid
graph TB
    A[各部件质量m_i] --> B[各部件质心坐标<br/>x_i, y_i, z_i]
    B --> C[CG_x = Σm_i·x_i / Σm_i]
    B --> D[CG_y = Σm_i·y_i / Σm_i]
    B --> E[CG_z = Σm_i·z_i / Σm_i]
    C --> F[重心位置<br/>CG_x, CG_y, CG_z]
    D --> F
    E --> F
    F --> G[CG投影到地面<br/>是否在支撑多边形内？]
    G -->|是| H[静态稳定 ✓]
    G -->|否| I[静态不稳定 ✗<br/>需调整布局]
```

#### 16.4 稳定性校核公式汇总

| 校核项 | 公式 | 本项目参数 | 计算结果 | 判定 |
|-------|------|-----------|---------|------|
| 静态稳定裕度 | d_min = min(CG到各边距离) | CG=(0,0,250) | d_min=65mm | >50mm ✓ |
| 侧翻临界速度 | v_tip = √(g×d×R/h_CG) | d=175mm, R=0.5m, h=250mm | v_tip=1.85m/s | >1.5m/s ✓ |
| 急停前倾校核 | a_tip = g×L_front/h_CG | L_front=180mm | a_tip=7.06m/s² | >1.0m/s² ✓ |
| 爬坡稳定 | tan(α_max) = d_min/h_CG | d_min=65mm, h=250mm | α_max=14.6° | >10° ✓ |
""",
        'blue': """
#### 16.2 本项目整车质量分布

| 部件 | 质量(kg) | x(mm) | y(mm) | z(mm) | m×x | m×y | m×z |
|------|---------|-------|-------|-------|-----|-----|-----|
| 底盘框架 | 15 | 0 | 0 | 50 | 0 | 0 | 750 |
| 驱动轮组×2 | 4 | 0 | ±175 | 50 | 0 | 0 | 200 |
| 电机+减速器×2 | 6 | 0 | ±175 | 80 | 0 | 0 | 480 |
| 锂电池 | 12 | 0 | 0 | 120 | 0 | 0 | 1440 |
| 工控机 | 2 | 100 | 0 | 150 | 200 | 0 | 300 |
| 激光雷达 | 0.7 | 0 | 0 | 280 | 0 | 0 | 196 |
| 协作臂 | 22 | -50 | 0 | 350 | -1100 | 0 | 7700 |
| IMU | 0.05 | 0 | 0 | 200 | 0 | 0 | 10 |
| 其他(线缆等) | 3 | 0 | 0 | 150 | 0 | 0 | 450 |
| **合计** | **64.75** | | | | **-900** | **0** | **11526** |
| **重心位置** | | **-13.9** | **0** | **178** | | | |

#### 16.3 SolidWorks质量属性提取步骤

| 步骤 | 操作 | 输出 |
|------|------|------|
| 1 | 打开装配体，确认材料属性正确 | 各零件密度已设置 |
| 2 | 工具→质量属性 | 总质量、CG坐标、惯性矩 |
| 3 | 设置坐标系原点为底盘几何中心 | CG坐标相对于底盘中心 |
| 4 | 导出质量属性报告 | .txt/.csv格式 |
| 5 | 导入Excel汇总 | 各部件m_i和CG_i |
""",
        'red': '',
    },
    '17': {
        'green': """
#### 17.3 SolidWorks装配配合类型汇总

| 配合类型 | 图标 | 自由度限制 | 典型应用 |
|---------|------|-----------|---------|
| 同轴配合 | ⌀ | 4(2移动+2旋转) | 轴与孔、电机与安装孔 |
| 重合配合 | — | 3(1移动+2旋转) | 面贴合、板与板 |
| 平行配合 | // | 2(2旋转) | 两个平面平行 |
| 距离配合 | ↔ | 1(1移动) | 零件间距固定 |
| 角度配合 | ∠ | 1(1旋转) | 两个面角度关系 |
| 相切配合 | ⊙ | 1-2 | 圆柱面与平面 |
| 齿轮配合 | ⚙ | 1 | 齿轮传动比 |
| 凸轮配合 | ○ | 1 | 凸轮从动件 |

#### 17.4 干涉检查流程

```mermaid
graph LR
    A[完成装配体] --> B[工具→干涉检查]
    B --> C[选择全部零件]
    C --> D[运行检查]
    D --> E{有干涉？}
    E -->|否| F[通过 ✓]
    E -->|是| G[查看干涉对]
    G --> H[修改零件尺寸<br/>或调整配合]
    H --> B
```
""",
        'blue': """
#### 17.1 SolidWorks建模规范

| 规范项 | 要求 | 示例 |
|-------|------|------|
| 文件命名 | 项目号_部件号_零件名 | AMR200_D01_底盘框架 |
| 零件材料 | 必须指定材料属性 | AL6061-T6 / SUS304 |
| 草图 | 完全定义，无欠约束 | 所有尺寸标注完整 |
| 特征顺序 | 先基体→后辅助→最后倒角 | 拉伸→切除→圆角 |
| 配合关系 | 最简配合，避免过约束 | 同轴+重合即可 |
| 图层管理 | 按部件分组 | 底盘层/轮组层/电气层 |
| 导出格式 | STEP AP214 | 供CAE/CAM使用 |
| 版本管理 | 文件名含版本号 | AMR200_D01_底盘框架_V2 |

#### 17.2 STEP文件导出与交换规范

| 格式 | 协议 | 适用场景 | 文件大小 |
|------|------|---------|---------|
| STEP AP203 | 配置控制设计 | 简单零件交换 | 小 |
| STEP AP214 | 汽车设计(通用) | 机械装配体 | 中 |
| STEP AP242 | 模型Based设计 | 复杂装配+PMI | 大 |
| IGES | 曲面交换 | 曲面造型 | 中 |
| STL | 三角网格 | 3D打印 | 大 |
| Parasolid | SolidWorks原生 | SW内部交换 | 小 |
""",
        'red': """
#### 17.2 常见装配问题与解决方案

| 问题 | 表现 | 根因 | 解决方案 |
|------|------|------|---------|
| 过约束 | 零件无法移动/报错 | 多余配合冲突 | 删除冲突配合，保留最少自由度 |
| 干涉 | 红色高亮区域 | 零件几何重叠 | 修改零件尺寸或调整位置 |
| 配合丢失 | 零件自由浮动 | 参考面被删除 | 重新选择参考面建立配合 |
| 性能慢 | 旋转卡顿 | 零件数过多/细节过多 | 轻量化简化/使用子装配 |
| 螺旋配合 | 螺栓不跟随孔移动 | 螺栓未与孔同轴配合 | 添加同轴配合+重合配合 |
""",
    },
}

# ============================================================
# 模块一修复函数
# ============================================================

def fix_module1():
    filepath = f'{DIR_PATH}\\模块一-机器人行业与产品分析-01至08课.md'
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    lines = content.split('\n')
    result = []
    i = 0

    while i < len(lines):
        line = lines[i]

        # Fix 1: Remove duplicate TOC (lines 19-27 in original: "## 本模块目录" appearing second time)
        if line.strip() == '## 本模块目录':
            # Check if we already have a TOC in result
            toc_count = sum(1 for r in result if r.strip() == '## 本模块目录')
            if toc_count >= 1:
                # Skip this duplicate TOC block
                i += 1
                while i < len(lines) and not (lines[i].startswith('---') or lines[i].startswith('## ')):
                    i += 1
                continue

        # Fix 2: Remove duplicate course info header (> 📌 **难度**...)
        if line.strip().startswith('> 📌 **难度**'):
            # Check if previous line is also a course info header or blank
            info_count = sum(1 for r in result if r.strip().startswith('> 📌 **难度**'))
            # Find the current lesson
            current_lesson = None
            for r in reversed(result):
                m = re.match(r'^## 第(\d+)课', r)
                if m:
                    current_lesson = m.group(1)
                    break

            # Count how many info headers we've seen for this lesson
            lesson_info_count = 0
            in_current_lesson = False
            for r in result:
                if re.match(r'^## 第\d+课', r):
                    if current_lesson and f'第{current_lesson}课' in r:
                        in_current_lesson = True
                    else:
                        in_current_lesson = False
                if in_current_lesson and r.strip().startswith('> 📌 **难度**'):
                    lesson_info_count += 1

            if lesson_info_count >= 1:
                # Skip this duplicate info header and any blank line after
                i += 1
                if i < len(lines) and lines[i].strip() == '':
                    i += 1
                continue

        # Fix 3: Remove double --- separator (replace with single)
        if line.strip() == '---':
            # Check if next non-blank line is also ---
            j = i + 1
            while j < len(lines) and lines[j].strip() == '':
                j += 1
            if j < len(lines) and lines[j].strip() == '---':
                result.append(line)
                i = j + 1  # Skip the second ---
                continue

        result.append(line)
        i += 1

    output = '\n'.join(result)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(output)
    print(f'Fixed Module 1. Output size: {len(output)} bytes')


# ============================================================
# 模块二修复函数
# ============================================================

def fix_module2():
    filepath = f'{DIR_PATH}\\模块二-机械系统结构设计-09至18课.md'
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Fix 1: Replace all references with correct per-lesson references
    # The references from the transform.py config
    references = {
        '09': """### 📚 参考文献与延伸学习

**入门读物**：
- [书籍] 《移动机器人学基础》Roland Siegwart — 第2章 运动学与动力学
- [视频] MIT 2.12 Introduction to Robotics — Lecture 3: Mobile Robot Kinematics

**进阶论文**：
- [论文] "Kinematic Models of Mobile Robots" — Campion et al., 1996, IEEE Trans. on Robotics and Automation
- [标准] ISO 3691-4 工业车辆安全—无人驾驶车辆

**实战资源**：
- [开源] ROS2 diff_drive_controller https://github.com/ros-controls/ros2_controllers
- [标准] GB/T 20721-2021 自动导引车通用技术条件
- [标准] ISO 13849-1 机械安全 控制系统安全相关部分

**跨模块关联**：
- → 模块一·第02课：AGV与AMR技术路线（底盘选型的上游决策）
- → 模块二·第10课：差速运动学（本课底盘的详细运动学推导）
- → 模块七·第61课：PID控制（底盘运动控制算法）""",
        '10': """### 📚 参考文献与延伸学习

**入门读物**：
- [书籍] 《概率机器人》(Probabilistic Robotics) Sebastian Thrun — 第5章 运动模型
- [视频] University of Freiburg Autonomous Navigation — Lecture 4: Odometry

**进阶论文**：
- [论文] "Dead Reckoning for Mobile Robots: The Odometry Error Model" — Borenstein & Feng, 1996
- [论文] "Visual Odometry: A Review" — Scaramuzza & Fraundorfer, 2011, IEEE RAM

**实战资源**：
- [开源] ROS2 diff_drive_controller https://github.com/ros-controls/ros2_controllers
- [标准] IEC 61131-6 可编程控制器功能安全
- [标准] ISO 23570-3 机床电气—伺服驱动接口

**跨模块关联**：
- → 模块二·第09课：底盘结构方案（差速运动学的物理基础）
- → 模块六·第51课：多传感器融合（里程计与IMU/LiDAR融合）
- → 模块七·第61课：SLAM定位（里程计作为先验输入）""",
        '11': """### 📚 参考文献与延伸学习

**入门读物**：
- [书籍] 《机器人学基础》蔡自兴 — 第3章 移动机器人运动学
- [视频] FRC Team 1640 Mecanum Wheel Training — YouTube

**进阶论文**：
- [论文] "Kinematic Analysis and Control of Mecanum Wheeled Mobile Platform" — Tlale & de Villiers, 2008
- [论文] "Mecanum Wheel Systematic Error Compensation" — Kuo et al., 2015, IEEE ISIE

**实战资源**：
- [开源] mecanum_robot https://github.com/linorobot/mecanum_robot
- [标准] ISO 9409-1 机器人机械接口—第1部分
- [标准] GB/T 12642-2013 工业机器人性能规范

**跨模块关联**：
- → 模块二·第09课：底盘结构方案（麦轮方案的运动学基础）
- → 模块二·第10课：差速运动学（对比参考）
- → 模块七·第61课：运动控制（麦轮底盘控制器设计）""",
        '12': """### 📚 参考文献与延伸学习

**入门读物**：
- [书籍] 《车辆动力学基础》Reza N. Jazar — 第3章 转向系统
- [视频] MATLAB Vehicle Dynamics Blockset — Ackermann Steering Demo

**进阶论文**：
- [论文] "Autonomous Vehicle Steering Control: Pure Pursuit vs Stanley" — Snider, 2009, CMU-RI-TR-09-08
- [论文] "Ackermann Steering Geometry and Vehicle Dynamics" — Rajamani, 2012

**实战资源**：
- [开源] Ackermann Steering ROS2 Controller https://github.com/ros-controls/ros2_controllers
- [标准] ISO 8855 道路车辆—车辆动力学与方向控制
- [标准] GB/T 26781-2020 无人驾驶车辆转向系统

**跨模块关联**：
- → 模块二·第09课：底盘结构方案（阿克曼方案的运动学约束）
- → 模块七·第63课：路径跟踪控制（Pure Pursuit与Stanley算法实现）
- → 模块十·第95课：户外场景测试（阿克曼底盘实地验证）""",
        '13': """### 📚 参考文献与延伸学习

**入门读物**：
- [书籍] 《电机与拖动基础》李发海 — 第4章 电机选型
- [视频] Texas Instruments Motor Drive Training Series — Module 3: Motor Selection

**进阶论文**：
- [论文] "Electric Motor Selection for Mobile Robot Applications" — Hughes & Drury, 2019, IEEE IA
- [标准] IEC 60034-1 旋转电机—第1部分：额定值和性能

**实战资源**：
- [工具] 汇川电机选型软件 https://www.inovance.com/
- [标准] GB/T 755-2019 旋转电机 定额和性能
- [标准] IEC 61800-5-1 变频器安全要求

**跨模块关联**：
- → 模块一·第07课：BOM成本分析（电机选型直接影响BOM成本）
- → 模块二·第14课：减速器选型（电机选型后需匹配减速器）
- → 模块三·第19课：电气系统设计（电机驱动器选型与电路设计）""",
        '14': """### 📚 参考文献与延伸学习

**入门读物**：
- [书籍] 《机械设计手册》第3卷 齿轮传动 — 减速器选型章节
- [视频] Nabtesco RV Reducer Technical Introduction — YouTube

**进阶论文**：
- [标准] ISO 6336 渐开线圆柱齿轮承载能力计算
- [论文] "Design and Analysis of Planetary Gearbox for Robot Joint" — UIUC, 2020

**实战资源**：
- [工具] Neugart减速器选型工具 https://www.neugart.com/
- [标准] GB/T 3480-1997 渐开线圆柱齿轮承载能力计算方法
- [标准] ISO 281 滚动轴承额定动载荷与寿命

**跨模块关联**：
- → 模块二·第13课：电机选型（减速器匹配电机输出特性）
- → 模块二·第15课：编码器设计（减速器输出端编码器安装方案）
- → 模块三·第22课：伺服驱动配置（减速器背隙对伺服参数整定的影响）""",
        '15': """### 📚 参考文献与延伸学习

**入门读物**：
- [书籍] 《传感器与检测技术》周杏鹏 — 第6章 编码器
- [视频] HEIDENHAIN Encoder Technology Training — YouTube

**进阶论文**：
- [论文] "Encoder Selection for High-Performance Servo Systems" — JEITA, 2018
- [标准] IEC 61491 伺服驱动器串行接口

**实战资源**：
- [开源] AMS AS5048A Arduino Library https://github.com/SimpleHacks/AS5048A
- [标准] IEC 61158 工业通信网络
- [标准] GB/T 39560.1 旋转编码器通用技术条件

**跨模块关联**：
- → 模块二·第14课：减速器选型（编码器安装在减速器输出端或电机端）
- → 模块三·第22课：伺服驱动器（编码器反馈构成闭环控制）
- → 模块七·第61课：PID控制（编码器反馈是PID闭环的基础）""",
        '16': """### 📚 参考文献与延伸学习

**入门读物**：
- [书籍] 《理论力学》哈工大 — 静力学与动力学基础
- [视频] Engineering Mechanics: Statics — Lesson on Center of Gravity

**进阶论文**：
- [标准] EN 1525 工业车辆安全—无人驾驶车辆
- [论文] "Stability Analysis of Mobile Manipulators" — Papadopoulos & Ghasemi, 1999, IEEE ICRA

**实战资源**：
- [工具] SolidWorks质量属性分析 — 自动计算重心
- [标准] ISO 13849-1 机械安全—控制系统安全相关部分
- [标准] GB/T 20721-2021 自动导引车通用技术条件

**跨模块关联**：
- → 模块二·第17课：SolidWorks装配（重心分析依赖三维模型质量属性）
- → 模块一·第06课：PRD需求文档（稳定性指标定义在PRD中）
- → 模块十·第89课：系统测试（稳定性实测验证）""",
        '17': """### 📚 参考文献与延伸学习

**入门读物**：
- [书籍] 《SolidWorks入门与实战》詹友刚 — 装配体与工程图章节
- [视频] SolidWorks官方装配体教程 https://my.solidworks.com/

**进阶论文**：
- [标准] ISO 10303-214 STEP应用协议AP214
- [标准] GB/T 4457.4-2002 机械制图 图样画法

**实战资源**：
- [工具] SolidWorks干涉检查 https://www.solidworks.com/
- [标准] GB/T 18784-2002 CAD/CAM数据交换格式
- [开源] FreeCAD https://www.freecad.org/

**跨模块关联**：
- → 模块二·第18课：机械设计实战（本课技能的综合应用）
- → 模块三·第19课：电气系统设计（装配中电气件的安装空间校核）
- → 模块十·第89课：系统集成测试（干涉检查是联调前的关键验证）""",
        '18': """### 📚 参考文献与延伸学习

**入门读物**：
- [书籍] 《机械设计课程设计》濮良贵 — 完整设计流程
- [书籍] 《公差配合与技术测量》廖念钊 — 公差标注方法

**进阶论文**：
- [标准] ISO 9409-1 机器人机械接口法兰
- [标准] GB/T 1800.1-2020 产品几何技术规范 极限与配合

**实战资源**：
- [标准] GB/T 1182-2018 产品几何技术规范 几何公差
- [标准] GB/T 131-2006 产品几何技术规范 表面结构
- [标准] ISO 2768-1 一般公差—第1部分：未注公差

**跨模块关联**：
- → 模块一·第08课：四层架构设计（机械层设计完成后交付电气层）
- → 模块三·第19课：电气系统设计（机械设计约束电气件安装）
- → 模块十·第89课：系统集成测试（机械装配后的整机组装与测试）""",
    }

    lines = content.split('\n')
    result = []
    i = 0

    while i < len(lines):
        line = lines[i]

        # Fix double --- separator
        if line.strip() == '---':
            j = i + 1
            while j < len(lines) and lines[j].strip() == '':
                j += 1
            if j < len(lines) and lines[j].strip() == '---':
                result.append(line)
                i = j + 1
                continue

        # Detect empty deepen sections (📗📘📕 with no content)
        # Pattern: ### 📗/📘/📕 followed immediately by ### 📗/📘/📕 or ### 📚 or ---
        if re.match(r'^### [📗📘📕]', line):
            result.append(line)
            i += 1

            # Collect content until next ### level header
            content_lines = []
            while i < len(lines) and not lines[i].startswith('### '):
                content_lines.append(lines[i])
                i += 1

            # Separate out --- separators from real content
            # --- lines between sections should not count as "real content"
            trailing_separators = []  # --- lines and blank lines after them
            real_content_lines = []
            # Scan from the end to find trailing --- and surrounding blanks
            found_sep = False
            for cl in reversed(content_lines):
                if not found_sep and cl.strip() == '---':
                    found_sep = True
                    trailing_separators.insert(0, cl)
                elif found_sep and cl.strip() == '':
                    trailing_separators.insert(0, cl)
                else:
                    found_sep = False  # stop collecting once we hit non-blank non-sep
                    real_content_lines.insert(0, cl)
            # Re-split: real_content_lines has content before trailing ---, trailing_separators has the rest

            # Check if real content is just description line and blanks
            has_real_content = False
            for cl in real_content_lines:
                stripped = cl.strip()
                if stripped and not stripped.startswith('> ') and stripped != '---':
                    has_real_content = True
                    break

            # Determine which lesson we're in
            current_lesson = None
            for r in reversed(result):
                m = re.match(r'^## 第(\d+)课', r)
                if m:
                    current_lesson = m.group(1)
                    break

            # Determine which layer this is
            layer = None
            if '📗' in line:
                layer = 'green'
            elif '📘' in line:
                layer = 'blue'
            elif '📕' in line:
                layer = 'red'

            if not has_real_content and current_lesson and layer:
                deepen_data = DEEPEN_CONTENT.get(current_lesson, {})
                layer_content = deepen_data.get(layer, '')
                if layer_content:
                    result.append(layer_content)
                else:
                    # No content for this layer, just output the description
                    for cl in real_content_lines:
                        result.append(cl)
                # Always output trailing separators (---) after the section
                for cl in trailing_separators:
                    result.append(cl)
            else:
                # Has real content, output as-is (including trailing separators)
                for cl in content_lines:
                    result.append(cl)
            continue

        # Detect and replace wrong references
        if line.strip() == '### 📚 参考文献与延伸学习':
            # Determine which lesson we're in
            current_lesson = None
            for r in reversed(result):
                m = re.match(r'^## 第(\d+)课', r)
                if m:
                    current_lesson = m.group(1)
                    break

            if current_lesson and current_lesson in references:
                # Skip old reference content and replace with correct one
                i += 1
                # Skip until next lesson header or end
                while i < len(lines) and not lines[i].startswith('## 第') and not lines[i].startswith('### 逆向案例'):
                    i += 1
                # Insert correct reference
                result.append('')
                result.append(references[current_lesson])
                result.append('')
                continue

        result.append(line)
        i += 1

    output = '\n'.join(result)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(output)
    print(f'Fixed Module 2. Output size: {len(output)} bytes')


if __name__ == '__main__':
    print('Fixing Module 1...')
    fix_module1()
    print('Fixing Module 2...')
    fix_module2()
    print('All done!')
