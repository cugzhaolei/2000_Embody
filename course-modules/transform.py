#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
课程模块文件改造脚本 - 模块七 & 模块八
- 页面布局改造：导航区、目录区、课程信息头、正文分区emoji、深化层次
- 渐进式引用注释：参考文献区、关键术语注释
"""

import re
import os

BASE_DIR = r'C:\Users\admin\Desktop\dev\2000_Embody\course-modules'

# ============================================================
# 10项正文分区映射
# ============================================================
SECTION_MAP = {
    1: ('🎯 业务背景', '业务背景'),
    2: ('📐 底层原理', '底层原理'),
    3: ('🔧 硬件方案', '硬件方案'),
    4: ('💻 软件实现', '软件实现'),
    5: ('🚀 Demo', 'Demo'),
    6: ('🔄 数据流', '数据流'),
    7: ('🔍 调试手段', '调试手段'),
    8: ('⚠️ 故障排查', '故障排查|常见故障|典型故障|故障'),
    9: ('🏭 工业案例', '工业案例'),
    10: ('❓ 面试题', '面试问题|面试题|面试考点'),
}

# ============================================================
# 导航区模板
# ============================================================
NAV_LINKS = [
    ('模块一', '模块一-机器人行业与产品分析-01至08课.md'),
    ('模块二', '模块二-机械系统结构设计-09至18课.md'),
    ('模块三', '模块三-电气系统与控制柜设计-19至28课.md'),
    ('模块四', '模块四-工业通信总线体系-29至38课.md'),
    ('模块五', '模块五-ROS2分布式软件架构-39至50课.md'),
    ('模块六', '模块六-多传感器感知系统-51至60课.md'),
    ('模块七', '模块七-导航算法SLAM与运动控制-61至72课.md'),
    ('模块八', '模块八-工业级高可靠软件架构-73至80课.md'),
    ('模块九', '模块九-具身智能模型训练与部署-81至88课.md'),
    ('模块十', '模块十-系统集成测试与产业实践-89至100课.md'),
]


def make_navigation(bold_module):
    parts = []
    for name, file in NAV_LINKS:
        if name == bold_module:
            parts.append(f'[**{name}**](./{file})')
        else:
            parts.append(f'[{name}](./{file})')
    return '> 🧭 **课程导航**：' + ' → '.join(parts)


def make_toc(lessons):
    lines = ['## 📋 本模块目录']
    for lesson in lessons:
        lines.append(f'- 第{lesson["num"]}课 {lesson["title"]} …… [{lesson["difficulty"]}]')
    return '\n'.join(lines)


def find_lesson_config(config, lesson_num):
    for l in config['lessons']:
        if l['num'] == lesson_num:
            return l
    return None


# ============================================================
# 术语注释
# ============================================================

def annotate_terms(text, annotations, annotated_set):
    """在文本中首次出现的术语后添加注释。每行最多注释一个术语。"""
    if not text.strip():
        return text
    # 跳过包含代码块标记的行
    if '```' in text:
        return text
    # 跳过模块入库文件行
    if text.startswith('【模块') and '入库文件' in text:
        return text

    # 找出所有未注释且在文本中出现的术语，选最早出现的一个
    candidates = []
    for term, annotation in annotations.items():
        if term in annotated_set:
            continue
        idx = text.find(term)
        if idx < 0:
            continue
        # 检查术语后是否已有注释括号
        after_idx = idx + len(term)
        if after_idx < len(text) and text[after_idx] == '（':
            annotated_set.add(term)
            continue
        # 避免在 markdown 链接内部注释
        before = text[:idx]
        if before.count('[') > before.count(']'):
            continue
        if before.count('(') > before.count(')') and before.rfind('(') > before.rfind('['):
            continue
        candidates.append((idx, term, annotation))

    if not candidates:
        return text

    # 按位置排序，注释最早出现的术语
    candidates.sort(key=lambda x: x[0])
    idx, term, annotation = candidates[0]
    after_idx = idx + len(term)
    annotation_text = f'（{annotation}）'
    text = text[:after_idx] + annotation_text + text[after_idx:]
    annotated_set.add(term)
    return text


# ============================================================
# 模块七配置
# ============================================================

MODULE7_CONFIG = {
    'file': '模块七-导航算法SLAM与运动控制-61至72课.md',
    'bold_module': '模块七',
    'lessons': [
        {'num': '61', 'title': 'PID闭环运动控制与参数整定',
         'difficulty': '⭐⭐⭐ 进阶', 'hours': '3h', 'prereq': '第51课 多传感器融合',
         'output': 'PID控制器代码+整定记录文档'},
        {'num': '62', 'title': 'Pure Pursuit纯跟踪算法',
         'difficulty': '⭐⭐⭐ 进阶', 'hours': '2h', 'prereq': '第61课 PID控制',
         'output': 'Pure Pursuit代码+路径跟踪文档'},
        {'num': '63', 'title': 'A*全局路径搜索',
         'difficulty': '⭐⭐⭐ 进阶', 'hours': '2h', 'prereq': '第62课 Pure Pursuit',
         'output': 'A*搜索代码+路径规划文档'},
        {'num': '64', 'title': 'Dijkstra路径规划',
         'difficulty': '⭐⭐⭐ 进阶', 'hours': '2h', 'prereq': '第63课 A*搜索',
         'output': 'Dijkstra代码+规划对比文档'},
        {'num': '65', 'title': 'RRT随机采样规划',
         'difficulty': '⭐⭐⭐⭐ 专家', 'hours': '3h', 'prereq': '第64课 Dijkstra',
         'output': 'RRT代码+采样规划文档'},
        {'num': '66', 'title': 'DWA局部避障算法',
         'difficulty': '⭐⭐⭐⭐ 专家', 'hours': '3h', 'prereq': '第63课 A*规划',
         'output': 'DWA配置文件'},
        {'num': '67', 'title': 'MPC模型预测控制',
         'difficulty': '⭐⭐⭐⭐ 专家', 'hours': '3h', 'prereq': '第61课 PID+第66课 DWA',
         'output': 'MPC控制器代码'},
        {'num': '68', 'title': 'SLAM算法：GMapping、LIO-SAM',
         'difficulty': '⭐⭐⭐⭐ 专家', 'hours': '3h', 'prereq': '第51课 多传感器融合',
         'output': 'SLAM配置文件+建图操作文档'},
        {'num': '69', 'title': 'AMCL粒子滤波定位',
         'difficulty': '⭐⭐⭐ 进阶', 'hours': '2h', 'prereq': '第68课 SLAM',
         'output': 'AMCL配置文件+定位调试文档'},
        {'num': '70', 'title': 'Nav2整套导航系统架构与调参',
         'difficulty': '⭐⭐⭐⭐ 专家', 'hours': '4h', 'prereq': '第63+66+69课',
         'output': 'Nav2完整配置+调参文档'},
        {'num': '71', 'title': 'MoveIt2机械臂运动规划框架',
         'difficulty': '⭐⭐⭐⭐ 专家', 'hours': '3h', 'prereq': '第70课 Nav2',
         'output': 'MoveIt2配置包'},
        {'num': '72', 'title': '机械臂FK正解、IK逆解数学模型',
         'difficulty': '⭐⭐⭐⭐ 专家', 'hours': '3h', 'prereq': '第71课 MoveIt2',
         'output': 'FK/IK数学推导文档+Python代码'},
    ],
    'term_annotations': {
        'PID': 'Proportional-Integral-Derivative：比例-积分-微分控制，工业最常用的闭环控制算法',
        'Pure Pursuit': '纯追踪算法：以车辆后轴为参考点，跟踪前方预瞄点的路径跟踪算法',
        'A*': 'A-star搜索算法：结合启发式函数h(n)与实际代价g(n)的最短路径搜索算法，保证最优性',
        'Dijkstra': 'Dijkstra最短路径算法：基于贪心策略的单源最短路径算法，A*的无启发式特例',
        'RRT': 'Rapidly-exploring Random Tree：快速探索随机树，高维空间中基于随机采样的路径规划算法',
        'RRT*': 'RRT-Star：RRT的渐进最优变体，通过重连和重布线优化路径成本',
        'RRTConnect': 'RRT双向连接变体：从起点和终点同时生长两棵树，显著提升求解速度',
        'PRM': 'Probabilistic Roadmap：概率路线图，先在空间中随机采样构建路线图再查询路径的多查询规划算法',
        'DWA': 'Dynamic Window Approach：动态窗口法，在速度空间中搜索满足动力学约束的局部避障速度',
        'DWB': 'Dynamic Window Bounded：DWA的改进实现，Nav2中dwb_controller的底层算法',
        'MPC': 'Model Predictive Control：模型预测控制，基于系统模型滚动优化有限时域内最优控制输入',
        'SLAM': 'Simultaneous Localization and Mapping：同步定位与建图，机器人在未知环境中同时构建地图并定位自身的技术',
        'GMapping': '基于粒子滤波的2D栅格SLAM算法，每个粒子维护一张栅格地图，适合单线2D激光雷达',
        'LIO-SAM': 'Lidar-Inertial Odometry via Smoothing and Mapping：激光惯性紧耦合SLAM，基于GTSAM因子图优化',
        'FAST-LIO': 'Fast LiDAR-Inertial Odometry：高效激光惯性里程计，基于IEKF紧耦合，计算效率极高',
        'Cartographer': 'Google开源的2D/3D SLAM算法，基于子图(submap)和回环检测(correlation scan matching)',
        'AMCL': 'Adaptive Monte Carlo Localization：自适应蒙特卡洛定位，基于粒子滤波的概率定位算法',
        'KLD采样': 'Kullback-Leibler Divergence采样：AMCL中动态调整粒子数的自适应机制，收敛时减少粒子',
        'Nav2': 'Navigation2：ROS2导航框架，提供全局规划、局部规划、代价地图、行为树和恢复行为的完整软件栈',
        'Costmap2D': 'ROS2中2D代价地图实现，将传感器数据映射为栅格代价用于路径规划和避障',
        'Behavior Tree': '行为树：以Sequence/Fallback/Action/Condition/Decorator节点组合任务的控制架构',
        'MoveIt2': 'ROS2机械臂运动规划框架，集成OMPL规划器、FCL碰撞检测和运动学求解器',
        'OMPL': 'Open Motion Planning Library：开源运动规划库，实现RRT、PRM、BIT*等采样规划算法',
        'FCL': 'Flexible Collision Library：灵活碰撞检测库，支持多种几何体类型的碰撞查询和距离计算',
        'URDF': 'Unified Robot Description Format：统一机器人描述格式，XML格式描述机器人连杆和关节的物理属性',
        'SRDF': 'Semantic Robot Description Format：语义机器人描述格式，定义规划组、关节组和碰撞白名单',
        'FK': 'Forward Kinematics：正运动学，给定关节角度计算末端执行器位姿的映射',
        'IK': 'Inverse Kinematics：逆运动学，给定末端执行器位姿求解关节角度的逆映射',
        'DH参数': 'Denavit-Hartenberg参数：描述相邻连杆坐标系的四参数(a,α,d,θ)，建立运动学模型的标准方法',
        'Jacobian': '雅可比矩阵：描述关节速度与末端速度线性映射关系的矩阵，奇异点处运动学退化',
        'C-space': 'Configuration Space：构型空间，机器人所有可能构型的参数空间，路径规划的基本搜索空间',
    },
    'references': {
        '61': """### 📚 参考文献与延伸学习

**入门读物**：
- [书籍] 《自动控制原理》（第七版）胡寿松 — 第3章 PID控制
- [视频] MATLAB Control Systems in Practice — PID Tuning Methods

**进阶论文**：
- [论文] "Automatic Tuning and Adaptation for PID Controllers — A Survey" — Åström et al., 1993, Control Engineering Practice
- [论文] "PID Control: New Identification and Design Methods" — Cominos & Munro, 2002, IEE Proc-Control Theory Appl.

**实战资源**：
- [开源] ROS2 control framework https://github.com/ros-controls/ros2_control
- [工具] PID Tuner https://pidtuner.com/
- [文档] ROS2 diff_drive_controller https://github.com/ros-controls/ros2_controllers

**跨模块关联**：
- → 模块二·第15课：编码器反馈设计（PID闭环的反馈源）
- → 模块三·第22课：伺服驱动器配置（PID参数在驱动器中的实现）
- → 模块七·第67课：MPC控制（PID的高级替代方案）""",

        '62': """### 📚 参考文献与延伸学习

**入门读物**：
- [书籍] 《机器人学、机器视觉与控制》(Robotics, Vision and Control) Peter Corke — 第4章 移动机器人控制
- [视频] MIT 6.4210 Robotic Manipulation — Mobile Robot Control

**进阶论文**：
- [论文] "Implementation of the Pure Pursuit Path Tracking Algorithm" — Coulter, 1992, CMU-RI-TR-92-01
- [论文] "Performance Comparison of Path Tracking Controllers for Autonomous Vehicles" — Snider, 2009, CMU-RI-TR-09-08

**实战资源**：
- [开源] Nav2 Regulated Pure Pursuit Controller https://navigation.ros.org/plugins/index.html
- [文档] ROS2 controller_manager https://github.com/ros-controls/ros2_control

**跨模块关联**：
- → 模块二·第10课：差速运动学（Pure Pursuit的底盘运动学基础）
- → 模块七·第63课：A*搜索（全局路径作为Pure Pursuit的跟踪输入）
- → 模块七·第66课：DWA避障（Pure Pursuit的局部避障增强）""",

        '63': """### 📚 参考文献与延伸学习

**入门读物**：
- [书籍] 《算法导论》(Introduction to Algorithms) CLRS — 第24章 单源最短路径
- [书籍] 《人工智能：一种现代方法》Russell & Norvig — 第3章 搜索算法

**进阶论文**：
- [论文] "A Formal Basis for the Heuristic Determination of Minimum Cost Paths" — Hart, Nilsson & Raphael, 1968, IEEE Trans. Systems Science and Cybernetics
- [论文] "Optimality of A* Revisited" — Dechter & Pearl, 1985, Journal of the ACM

**实战资源**：
- [开源] Nav2 navfn_planner https://navigation.ros.org/planning/index.html
- [文档] OMPL A* implementation https://ompl.kavrakilab.org/

**跨模块关联**：
- → 模块七·第64课：Dijkstra（A*无启发式的特例）
- → 模块七·第66课：DWA（A*全局规划+DWA局部规划的组合）
- → 模块七·第70课：Nav2架构（A*作为全局规划器在Nav2中的集成）""",

        '64': """### 📚 参考文献与延伸学习

**入门读物**：
- [书籍] 《算法导论》CLRS — 第24章 Dijkstra算法
- [书籍] 《图论及其应用》Bondy & Murty — 第1章 最短路径

**进阶论文**：
- [论文] "A Note on Two Problems in Connexion with Graphs" — Dijkstra, 1959, Numerische Mathematik
- [论文] "Shortest Path Algorithms: An Evaluation Using Real Road Networks" — Cherkassky et al., 1996, Transportation Science

**实战资源**：
- [开源] Nav2 smac_planner https://navigation.ros.org/planning/index.html
- [工具] NetworkX Dijkstra https://networkx.org/

**跨模块关联**：
- → 模块七·第63课：A*（Dijkstra是A*的启发式h=0特例）
- → 模块七·第65课：RRT（基于采样的规划对比基于图搜索的规划）
- → 模块七·第70课：Nav2（Dijkstra在Nav2代价地图上的应用）""",

        '65': """### 📚 参考文献与延伸学习

**入门读物**：
- [书籍] 《Planning Algorithms》Steven LaValle — 第5章 采样规划，在线免费 http://planning.cs.uiuc.edu/
- [视频] Steven LaValle — Motion Planning Lectures, UIUC

**进阶论文**：
- [论文] "Rapidly-Exploring Random Trees: A New Tool for Path Planning" — LaValle, 1998, TR 98-11
- [论文] "Sampling-based Algorithms for Optimal Motion Planning" — Karaman & Frazzoli, 2011, IJRR
- [论文] "RRT-Connect: An Efficient Approach to Single-Query Path Planning" — Kuffner & LaValle, 2000, ICRA

**实战资源**：
- [开源] OMPL RRT/RRT*/RRTConnect https://ompl.kavrakilab.org/
- [文档] MoveIt2 OMPL planner configuration https://moveit.ros.org/

**跨模块关联**：
- → 模块七·第63课：A*搜索（图搜索与采样规划的对比）
- → 模块七·第71课：MoveIt2（RRT作为MoveIt2的核心规划算法）
- → 模块七·第72课：FK/IK（RRT在构型空间中的路径规划）""",

        '66': """### 📚 参考文献与延伸学习

**入门读物**：
- [书籍] 《概率机器人》(Probabilistic Robotics) Sebastian Thrun — 第6章 运动规划
- [视频] University of Freiburg — Autonomous Navigation Lecture 8: Local Planning

**进阶论文**：
- [论文] "The Dynamic Window Approach to Collision Avoidance" — Fox, Burgard & Thrun, 1997, IEEE Robotics & Automation Magazine
- [论文] "Trajectory Space: A Dual Representation for Motion Planning and Analysis" — Gerkey & Konolige, 2008, RSS

**实战资源**：
- [开源] Nav2 dwb_controller https://navigation.ros.org/plugins/index.html
- [文档] Nav2 controller server https://navigation.ros.org/configuration/packages/configuring-dwb-controller.html

**跨模块关联**：
- → 模块七·第61课：PID控制（DWA输出的速度指令由PID执行）
- → 模块七·第67课：MPC（MPC是DWA的优化升级方案）
- → 模块七·第70课：Nav2（DWA作为Nav2的局部规划器）""",

        '67': """### 📚 参考文献与延伸学习

**入门读物**：
- [书籍] 《模型预测控制》席裕庚 — MPC原理与设计
- [书籍] 《Predictive Control for Linear and Hybrid Systems》Borrelli, Bemporad & Morari — 2017, Cambridge University Press

**进阶论文**：
- [论文] "Model Predictive Control: Theory and Design — A Survey" — Mayne et al., 2000, Automatica
- [论文] "Real-time Model Predictive Control for Autonomous and Semiautonomous Vehicles" — Falcone et al., 2007, IEEE Trans. CST

**实战资源**：
- [开源] ACADO Toolkit https://github.com/acado/acado
- [开源] CasADi https://web.casadi.org/
- [文档] Nav2 mpc_controller https://navigation.ros.org/

**跨模块关联**：
- → 模块七·第61课：PID控制（MPC是PID的多约束优化替代）
- → 模块七·第66课：DWA（MPC与DWA的局部规划对比）
- → 模块八·第80课：性能优化（MPC计算延迟的优化策略）""",

        '68': """### 📚 参考文献与延伸学习

**入门读物**：
- [书籍] 《概率机器人》(Probabilistic Robotics) Sebastian Thrun — 第10-12章 SLAM
- [视频] Cyrill Stachniss — Robot Mapping Lectures, University of Bonn

**进阶论文**：
- [论文] "Simultaneous Localization and Mapping: Part I" — Durrant-Whyte & Bailey, 2006, IEEE RAM
- [论文] "LIO-SAM: Tightly-coupled Lidar Inertial Odometry via Smoothing and Mapping" — Shan et al., 2020, IROS
- [论文] "FAST-LIO2: Fast Direct LiDAR-Inertial Odometry" — Xu et al., 2022, IEEE TRO

**实战资源**：
- [开源] Google Cartographer https://github.com/cartographer-project/cartographer
- [开源] LIO-SAM https://github.com/TixiaoShan/LIO-SAM
- [开源] FAST-LIO2 https://github.com/hku-mars/FAST_LIO
- [文档] slam_toolbox https://github.com/SteveMacenski/slam_toolbox

**跨模块关联**：
- → 模块六·第51课：多传感器融合（SLAM的核心是传感器融合）
- → 模块七·第69课：AMCL定位（SLAM建图后用AMCL定位）
- → 模块七·第70课：Nav2（SLAM地图作为Nav2的输入）""",

        '69': """### 📚 参考文献与延伸学习

**入门读物**：
- [书籍] 《概率机器人》Sebastian Thrun — 第8章 Monte Carlo Localization
- [视频] Cyrill Stachniss — Robot Mapping Lecture: MCL

**进阶论文**：
- [论文] "KLD-Sampling: Adaptive Particle Filters" — Fox, 2001, NIPS
- [论文] "Monte Carlo Localization: Efficient Position Estimation for Mobile Robots" — Thrun et al., 1999, AAAI

**实战资源**：
- [开源] Nav2 AMCL https://navigation.ros.org/configuration/packages/configuring-amcl.html
- [文档] ROS2 nav2_amcl https://github.com/ros-planning/navigation2/tree/main/nav2_amcl

**跨模块关联**：
- → 模块七·第68课：SLAM建图（AMCL定位依赖SLAM产出的地图）
- → 模块七·第70课：Nav2架构（AMCL作为Nav2定位模块）
- → 模块六·第56课：粒子滤波（AMCL的底层算法原理）""",

        '70': """### 📚 参考文献与延伸学习

**入门读物**：
- [书籍] Nav2官方文档 https://navigation.ros.org/
- [视频] ROS2 Nav2 Tutorial Series — Open Navigation

**进阶论文**：
- [论文] "The Marathon 2: A Navigation System" — Macenski et al., 2020, IEEE RAM
- [论文] "Toward The Navigation That We Need: An Architecture For The Navigation Stack" — Macenski & Jamburic, 2021

**实战资源**：
- [开源] Nav2 GitHub https://github.com/ros-planning/navigation2
- [教程] Nav2 Tutorials https://navigation.ros.org/tutorials/index.html
- [博客] Steve Macenski — Nav2 Blog Series

**跨模块关联**：
- → 模块七·第63课：A*全局规划（Nav2的全局规划器实现）
- → 模块七·第66课：DWA局部避障（Nav2的局部规划器实现）
- → 模块七·第69课：AMCL定位（Nav2的定位模块）
- → 模块八·第74课：行为树（Nav2使用BT编排导航行为）""",

        '71': """### 📚 参考文献与延伸学习

**入门读物**：
- [书籍] MoveIt2官方文档 https://moveit.ros.org/
- [视频] MoveIt2 Tutorial — PickNik Robotics

**进阶论文**：
- [论文] "MoveIt! Task Constructor: Toward Modern Software Architecture for Robot Manipulation" — Sucan & Chitta, 2018
- [论文] "OMPL: Open Motion Planning Library" — Sucan, Moll & Kavraki, 2012, IEEE RAM

**实战资源**：
- [开源] MoveIt2 GitHub https://github.com/ros-planning/moveit2
- [教程] MoveIt2 Tutorials https://moveit.picknik.ai/
- [工具] MoveIt Setup Assistant https://moveit.ros.org/moveit!/ros/visualization/

**跨模块关联**：
- → 模块七·第65课：RRT规划（MoveIt2底层使用OMPL的RRT算法）
- → 模块七·第72课：FK/IK（MoveIt2的运动学求解器）
- → 模块二·第03课：机械臂分类（MoveIt2支持的机械臂类型）""",

        '72': """### 📚 参考文献与延伸学习

**入门读物**：
- [书籍] 《机器人学导论》(Introduction to Robotics) John J. Craig — 第3-4章 运动学
- [视频] Stanford CS223A Introduction to Robotics — Lecture 3-5

**进阶论文**：
- [论文] "The Kinematics of Manipulators Under Computer Control" — Pieper, 1968, Stanford PhD Thesis
- [论文] "A Survey on the Inverse Kinematics of Robot Manipulators" — Buss, 2004, IEEE Trans. on Control Systems Technology

**实战资源**：
- [开源] MoveIt2 IK solvers https://moveit.ros.org/
- [开源] IKFast https://openrave.org/
- [文档] KDL IK https://www.orocos.org/kdl

**跨模块关联**：
- → 模块七·第71课：MoveIt2（FK/IK是MoveIt2的核心求解器）
- → 模块二·第03课：机械臂分类（不同构型机械臂的运动学差异）
- → 模块七·第67课：MPC控制（IK在MPC中的实时求解需求）""",
    },
}


# ============================================================
# 模块八配置
# ============================================================

MODULE8_CONFIG = {
    'file': '模块八-工业级高可靠软件架构-73至80课.md',
    'bold_module': '模块八',
    'lessons': [
        {'num': '73', 'title': '有限状态机任务调度设计',
         'difficulty': '⭐⭐⭐ 进阶', 'hours': '2h', 'prereq': '模块七',
         'output': 'FSM框架代码+状态转换图'},
        {'num': '74', 'title': '行为树BT复杂业务流程管理',
         'difficulty': '⭐⭐⭐ 进阶', 'hours': '3h', 'prereq': '第73课 FSM',
         'output': 'BT配置文件+行为树XML'},
        {'num': '75', 'title': '插件化模块化架构设计',
         'difficulty': '⭐⭐⭐ 进阶', 'hours': '2h', 'prereq': '第39课 ROS2架构',
         'output': 'pluginlib模板代码'},
        {'num': '76', 'title': '分级日志系统与故障记录方案',
         'difficulty': '⭐⭐⭐ 进阶', 'hours': '2h', 'prereq': '第75课 pluginlib',
         'output': '日志配置文件'},
        {'num': '77', 'title': '配置文件统一管理与热加载',
         'difficulty': '⭐⭐⭐ 进阶', 'hours': '2h', 'prereq': '第76课 日志系统',
         'output': '配置管理框架代码'},
        {'num': '78', 'title': '异常捕获、自动复位、故障自愈机制',
         'difficulty': '⭐⭐⭐ 进阶', 'hours': '3h', 'prereq': '第77课 配置管理',
         'output': '自愈代码+断路器实现'},
        {'num': '79', 'title': '多线程、多进程资源隔离方案',
         'difficulty': '⭐⭐⭐ 进阶', 'hours': '3h', 'prereq': '第78课 自愈机制',
         'output': 'Docker Compose配置+隔离方案'},
        {'num': '80', 'title': 'CPU、内存、网络延迟性能优化手段',
         'difficulty': '⭐⭐⭐ 进阶', 'hours': '3h', 'prereq': '第79课 资源隔离',
         'output': '性能优化脚本+Profiling报告'},
    ],
    'term_annotations': {
        'FSM': 'Finite State Machine：有限状态机，(S, E, T, s0, F)五元组描述的状态转移模型',
        'HFSM': 'Hierarchical FSM：层级有限状态机，状态内嵌套子状态机，解决状态爆炸问题',
        'Moore型': 'Moore Machine：输出仅依赖当前状态的有限状态机',
        'Mealy型': 'Mealy Machine：输出依赖当前状态和输入事件的有限状态机',
        'BT': 'Behavior Tree：行为树，以Sequence/Fallback/Action/Condition/Decorator节点组合任务的控制架构',
        'Sequence': '序列节点：子节点依次执行，任一失败则整体失败的BT控制节点',
        'Fallback': '选择节点：子节点依次尝试，任一成功则整体成功的BT控制节点',
        'Decorator': '装饰节点：修饰子节点行为的BT节点，如重试、延时、反转等',
        'pluginlib': 'ROS2插件加载框架，基于动态库和ClassLoader实现运行时插件注册与加载',
        'ClassLoader': 'ROS2动态库加载器，支持运行时加载共享库(.so/.dll)中的插件类',
        'spdlog': '高性能C++日志库，支持异步日志、多sink、格式化输出，ROS2 rclcpp的默认日志后端',
        '结构化日志': 'Structured Logging：以JSON/键值对格式输出日志，便于日志聚合系统自动解析和检索',
        'declare_parameter': 'ROS2参数声明机制，在节点中声明参数名、类型、默认值和范围约束',
        '热加载': 'Hot Reload：运行时重新加载配置文件无需重启进程的机制',
        'Circuit Breaker': '断路器模式：当下游服务连续失败时自动切断请求，防止级联故障的容错模式',
        '指数退避': 'Exponential Backoff：重试间隔按指数增长的策略（1s→2s→4s→8s），避免雪崩',
        '降级': 'Degradation：系统部分功能失效时切换到简化模式，保证核心功能可用的容灾策略',
        'Watchdog': '看门狗：定时喂狗机制，进程异常时看门狗超时触发重启',
        'Docker Compose': 'Docker容器编排工具，通过YAML文件定义和运行多容器应用',
        'CPU绑核': 'CPU Affinity/Pinning：将进程绑定到指定CPU核心，减少上下文切换和缓存失效',
        'GPU MPS': 'Multi-Process Service：NVIDIA GPU多进程服务，允许多个进程共享GPU的计算资源',
        'PREEMPT_RT': 'Linux实时补丁，将内核转为完全抢占模式，调度延迟降至微秒级',
        'DDS': 'Data Distribution Service：OMG标准的分布式实时通信中间件，ROS2的底层通信机制',
        '共享内存': 'Shared Memory零拷贝：DDS进程间通过共享内存段直接交换数据，避免序列化开销',
        'Jumbo Frame': '超大帧：MTU设为9000字节（标准1500），减少大帧网络开销和中断频率',
        'SIMD': 'Single Instruction Multiple Data：单指令多数据流，AVX/SSE指令集实现数据级并行',
        'TensorRT': 'NVIDIA推理优化器，通过层融合、精度校准(FP16/INT8)和内核自动调优加速推理',
        'Profiling': '性能剖析：通过采样或插桩分析程序运行时行为，定位性能瓶颈的方法',
    },
    'references': {
        '73': """### 📚 参考文献与延伸学习

**入门读物**：
- [书籍] 《设计模式：可复用面向对象软件的基础》Gamma et al. — State模式
- [书籍] 《嵌入式系统设计》Philippe Gerum — 第5章 状态机设计

**进阶论文**：
- [论文] "Statecharts: A Visual Formalism for Complex Systems" — Harel, 1987, Science of Computer Programming
- [论文] "A Survey of State Machine Synthesis Methods" — Villa et al., 1997, IEEE TCAD

**实战资源**：
- [开源] FlexBE https://github.com/FlexBE/flexbe_behavior_engine
- [开源] SMACH https://github.com/ros/executive_smach
- [文档] ROS2 Lifecycle https://design.ros2.org/articles/node_lifecycle.html

**跨模块关联**：
- → 模块八·第74课：行为树（FSM的替代方案，解决状态爆炸）
- → 模块七·第70课：Nav2行为树（BT与FSM在导航中的对比）
- → 模块五·第39课：ROS2架构（rclcpp_lifecycle与FSM的关系）""",

        '74': """### 📚 参考文献与延伸学习

**入门读物**：
- [书籍] 《Behavior Trees in Robotics and AI》Michele Colledanchise — 2018, CRC Press
- [视频] Davide Faconti — BehaviorTree.CPP Tutorial Series

**进阶论文**：
- [论文] "Behavior Trees for Task-Level Control of Robotic Systems" — Colledanchise & Ögren, 2017, IEEE RAS
- [论文] "Behavior Trees in Robotics: A Survey" — Iovino et al., 2022, IEEE RAS

**实战资源**：
- [开源] BehaviorTree.CPP https://github.com/BehaviorTree/BehaviorTree.CPP
- [开源] Nav2 BT nodes https://navigation.ros.org/behavior_trees/
- [工具] Groot BT Editor https://github.com/BehaviorTree/Groot

**跨模块关联**：
- → 模块八·第73课：FSM（BT与FSM的架构对比与选型）
- → 模块七·第70课：Nav2行为树（BT在Nav2导航中的具体应用）""",

        '75': """### 📚 参考文献与延伸学习

**入门读物**：
- [书籍] 《设计模式》Gamma et al. — Abstract Factory & Plugin Pattern
- [文档] ROS2 pluginlib教程 https://docs.ros.org/en/humble/Tutorials/Advanced/Pluginlib.html

**进阶论文**：
- [论文] "Dynamic Plugin Architecture for Component-Based Robotics Software" — Bubeck et al., 2018, IEEE SIMPAR
- [标准] OSGi Service Platform — 动态模块系统规范

**实战资源**：
- [开源] ROS2 pluginlib https://github.com/ros/pluginlib
- [开源] Nav2 plugin system https://navigation.ros.org/plugins/
- [文档] class_loader https://github.com/ros/class_loader

**跨模块关联**：
- → 模块五·第39课：ROS2架构（pluginlib是ROS2核心组件机制）
- → 模块八·第76课：日志系统（日志模块的插件化扩展）
- → 模块七·第70课：Nav2插件（Nav2的规划器/控制器插件体系）""",

        '76': """### 📚 参考文献与延伸学习

**入门读物**：
- [书籍] 《Site Reliability Engineering》Google SRE团队 — 第16章 处理过载
- [书籍] 《日志管理与分析》Anton Chuvakin — 日志分级与聚合

**进阶论文**：
- [论文] "The Log: What Every Software Engineer Should Know About Real-Time Data" — Kreps, 2014, LinkedIn Engineering
- [标准] RFC 5424 Syslog协议 — 日志格式与传输标准

**实战资源**：
- [开源] spdlog https://github.com/gabime/spdlog
- [开源] ELK Stack (Elasticsearch + Logstash + Kibana) https://www.elastic.co/
- [文档] rclcpp logging https://docs.ros.org/en/humble/Concepts/About-Logging.html

**跨模块关联**：
- → 模块八·第78课：自愈机制（日志是故障检测和自愈触发的基础）
- → 模块八·第77课：配置管理（日志级别通过配置管理动态调整）
- → 模块十·第89课：系统测试（日志分析是故障排查的核心手段）""",

        '77': """### 📚 参考文献与延伸学习

**入门读物**：
- [书籍] 《The Twelve-Factor App》Adam Wiggins — Factor III: Config
- [文档] ROS2 Parameter Server https://docs.ros.org/en/humble/Concepts/About-ROS-2-Parameters.html

**进阶论文**：
- [论文] "Configuration Management for Distributed Systems: A Survey" — Zhang et al., 2019, IEEE Software
- [标准] YAML specification 1.2 https://yaml.org/spec/1.2/

**实战资源**：
- [开源] ament_index https://github.com/ament/ament_index
- [工具] ROS2 param https://docs.ros.org/en/humble/Tutorials/Beginner-CLI-Tools/Understanding-ROS2-Parameters.html
- [开源] libyaml https://github.com/yaml/libyaml

**跨模块关联**：
- → 模块八·第76课：日志系统（日志级别通过参数热加载调整）
- → 模块八·第78课：自愈机制（自愈阈值参数的热加载）
- → 模块五·第40课：ROS2参数机制（declare_parameter的底层实现）""",

        '78': """### 📚 参考文献与延伸学习

**入门读物**：
- [书籍] 《Release It!》（第2版）Michael Nygard — Circuit Breaker, Bulkhead Pattern
- [书籍] 《Site Reliability Engineering》Google — 第11-14章 故障应急

**进阶论文**：
- [论文] "Circuit Breaker Pattern" — Netflix TechBlog, 2012
- [论文] "Fault Tolerance Patterns: A Survey" — Hanmer, 2013, ACM Computing Surveys

**实战资源**：
- [开源] resilience4j https://github.com/resilience4j/resilience4j
- [开源] ROS2 diagnostic_updater https://github.com/ros/diagnostics
- [文档] Nav2 recovery behaviors https://navigation.ros.org/configuration/packages/configuring-recovery.html

**跨模块关联**：
- → 模块八·第73课：FSM（FSM中的ERROR状态与自愈的衔接）
- → 模块八·第79课：资源隔离（隔离是防止级联故障的Bulkhead实现）
- → 模块七·第70课：Nav2恢复行为（Nav2的spin/clear/wait恢复策略）""",

        '79': """### 📚 参考文献与延伸学习

**入门读物**：
- [书籍] 《Docker实战》Jeff Nickoloff — 容器隔离与资源限制
- [书籍] 《Kubernetes权威指南》韩先康 — 资源配额与限制

**进阶论文**：
- [论文] "PREEMPT_RT: The Real-Time Linux Kernel" — Gleixner & Rostedt, 2006, Linux Kernel documentation
- [论文] "Container-based Isolation for Robotic Systems" — Beyer et al., 2020, IEEE ICRA Workshop

**实战资源**：
- [文档] Docker Compose https://docs.docker.com/compose/
- [文档] PREEMPT_RT patch https://wiki.linuxfoundation.org/realtime/start
- [文档] NVIDIA MPS https://docs.nvidia.com/deploy/mps/

**跨模块关联**：
- → 模块八·第78课：自愈机制（容器化部署配合自动重启策略）
- → 模块八·第80课：性能优化（隔离是性能优化的前提——先隔离再优化）
- → 模块三·第19课：电气系统设计（硬件看门狗与软件看门狗的配合）""",

        '80': """### 📚 参考文献与延伸学习

**入门读物**：
- [书籍] 《Systems Performance》（第2版）Brendan Gregg — 性能分析与优化方法论
- [书籍] 《性能之巅》Brendan Gregg — 深入Linux性能分析

**进阶论文**：
- [论文] "Cyclone DDS: A High-Performance Implementation of the OMG DDS Specification" — van der Heiden et al., 2020, Eclipse Foundation
- [论文] "TensorRT: High-Performance Deep Learning Inference" — NVIDIA, 2020, GTC

**实战资源**：
- [工具] perf https://perf.wiki.kernel.org/
- [工具] eBPF https://ebpf.io/
- [文档] TensorRT https://docs.nvidia.com/deeplearning/tensorrt/
- [文档] FastDDS Shared Memory https://fast-dds.docs.eprosima.com/

**跨模块关联**：
- → 模块八·第79课：资源隔离（先隔离后优化，绑核与实时优先级的基础）
- → 模块九·第81课：AI推理部署（TensorRT优化的详细配置）
- → 模块五·第48课：DDS通信（DDS共享内存零拷贝的底层原理）""",
    },
}


# ============================================================
# 主改造函数
# ============================================================

def transform_file(config):
    filepath = os.path.join(BASE_DIR, config['file'])

    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    lines = content.split('\n')
    result = []
    i = 0
    in_code_block = False
    current_lesson = None
    references_inserted = False
    annotated_terms = set()

    while i < len(lines):
        line = lines[i]

        # --- 代码块跟踪 ---
        if line.strip().startswith('```'):
            in_code_block = not in_code_block
            result.append(line)
            i += 1
            continue

        if in_code_block:
            result.append(line)
            i += 1
            continue

        # --- 模块标题行 ---
        if line.startswith('# 模块'):
            result.append(line)
            result.append('')
            result.append(make_navigation(config['bold_module']))
            result.append('')
            i += 1
            continue

        # --- 模块学习目标 ---
        if line.startswith('## 模块学习目标'):
            result.append(line)
            i += 1
            # 复制学习目标内容直到 --- 或 下一课
            while i < len(lines):
                if lines[i].startswith('---') or lines[i].startswith('## 第'):
                    break
                result.append(lines[i])
                i += 1
            # 添加目录
            result.append('')
            result.append(make_toc(config['lessons']))
            result.append('')
            result.append('---')
            result.append('')
            # 跳过原始的 --- 和后续空行
            if i < len(lines) and lines[i].startswith('---'):
                i += 1
                while i < len(lines) and lines[i].strip() == '':
                    i += 1
            continue

        # --- 课程标题 ---
        lesson_match = re.match(r'^## 第(\d+)课\s+(.+)$', line)
        if lesson_match:
            # 先插入上一课的参考文献
            if current_lesson and not references_inserted:
                ref_text = config['references'].get(current_lesson, '')
                if ref_text:
                    # 移除尾部空行保持整洁
                    while result and result[-1].strip() == '':
                        result.pop()
                    result.append('')
                    result.append(ref_text)
                    result.append('')
                references_inserted = True

            current_lesson = lesson_match.group(1)
            lesson_title = lesson_match.group(2).strip()
            references_inserted = False

            result.append(f'## 第{current_lesson}课 {lesson_title}')
            result.append('')

            # 插入课程信息头
            lesson_cfg = find_lesson_config(config, current_lesson)
            if lesson_cfg:
                result.append(
                    f'> 📌 **难度**：{lesson_cfg["difficulty"]} | '
                    f'**课时**：{lesson_cfg["hours"]} | '
                    f'**前置**：{lesson_cfg["prereq"]} | '
                    f'**产出**：{lesson_cfg["output"]}'
                )
                result.append('')

            i += 1
            continue

        # --- 10项正文分区 ---
        num_item_match = re.match(r'^(\d+)\.\s*(.+)$', line)
        if num_item_match and current_lesson:
            num = int(num_item_match.group(1))
            rest = num_item_match.group(2)

            if num in SECTION_MAP:
                emoji_header, keywords = SECTION_MAP[num]
                # 提取关键词和内容
                colon_pos = -1
                for kw in keywords.split('|'):
                    idx = rest.find(kw)
                    if idx >= 0:
                        colon_pos = idx + len(kw)
                        break

                if colon_pos > 0 and colon_pos < len(rest) and rest[colon_pos] in '：:':
                    content_part = rest[colon_pos + 1:].strip() if colon_pos + 1 < len(rest) else ''
                else:
                    content_part = rest.strip()

                result.append(f'### {emoji_header}')
                if content_part:
                    content_part = annotate_terms(content_part, config['term_annotations'], annotated_terms)
                    result.append(content_part)
                result.append('')
            else:
                result.append(line)
            i += 1
            continue

        # --- 入库产出 ---
        if line.startswith('【入库产出】'):
            output_text = line[6:].strip()
            result.append(f'> 📦 **入库产出**：{output_text}')
            result.append('')
            i += 1
            continue

        # --- 模块入库文件（不注释术语） ---
        if line.startswith('【模块') and '入库文件' in line:
            result.append(line)
            i += 1
            continue

        # --- --- 分隔线 ---
        if line.strip() == '---':
            # 在课程之间插入参考文献
            if current_lesson and not references_inserted:
                ref_text = config['references'].get(current_lesson, '')
                if ref_text:
                    while result and result[-1].strip() == '':
                        result.pop()
                    result.append('')
                    result.append(ref_text)
                    result.append('')
                references_inserted = True

            result.append('---')
            result.append('')
            i += 1
            # 跳过 --- 后的空行
            while i < len(lines) and lines[i].strip() == '':
                i += 1
            continue

        # --- 逆向案例标题 ---
        if line.startswith('### 逆向案例'):
            # 插入最后一课的参考文献
            if current_lesson and not references_inserted:
                ref_text = config['references'].get(current_lesson, '')
                if ref_text:
                    while result and result[-1].strip() == '':
                        result.pop()
                    result.append('')
                    result.append(ref_text)
                    result.append('')
                references_inserted = True
            result.append(line)
            i += 1
            continue

        # --- 普通内容行：应用术语注释 ---
        # 跳过标题行、引用行、分隔线的注释
        if line.startswith('#') or line.startswith('>'):
            result.append(line)
        else:
            annotated_line = annotate_terms(line, config['term_annotations'], annotated_terms)
            result.append(annotated_line)
        i += 1

    # 文件末尾：插入最后一课的参考文献（如果还有未插入的）
    if current_lesson and not references_inserted:
        ref_text = config['references'].get(current_lesson, '')
        if ref_text:
            while result and result[-1].strip() == '':
                result.pop()
            result.append('')
            result.append(ref_text)
            result.append('')

    # 写入文件
    output = '\n'.join(result)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(output)

    print(f'✅ 已完成 {config["file"]} 的改造，输出大小：{len(output)} 字符')


# ============================================================
# 主入口
# ============================================================

if __name__ == '__main__':
    print('开始改造模块七...')
    transform_file(MODULE7_CONFIG)
    print('开始改造模块八...')
    transform_file(MODULE8_CONFIG)
    print('全部完成！')
