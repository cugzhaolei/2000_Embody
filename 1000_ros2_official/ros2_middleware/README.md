# ROS 2 中间层 Agent（ros2_middleware）

一个**跨 ROS 版本 / 跨操作系统的中间适配层**：自动检测环境，统一配置与管理，
把"基础功能"拆成可以**自由组合的模块 + 参数**，一次性适配 foxy / humble / jazzy…

```
ros2_middleware/
├── README.md                 ← 架构与使用说明（本文件）
├── docs/
│   └── diff_matrix.md        ← 各 ROS 版本间的代码/API/包差异对照表（知识库）
├── rosagent/                 ← Python 包（纯 stdlib，Python 3.8+）
│   ├── __init__.py
│   ├── registry.py           ← Distro 注册表（适配的唯一数据源）
│   ├── detector.py           ← OS / ROS 版本 / 工作空间 / Python 检测
│   ├── env.py                ← 环境管理器（source、apt 包名翻译、域 ID）
│   ├── runtime.py            ← 运行时管理器（起停进程、健康轮询、清理）
│   ├── checks.py             ← 运行检查（环境/依赖/节点/话题）
│   ├── runner.py             ← 场景引擎（模块自由组合 + 参数）
│   ├── cli.py                ← 命令行入口 rosagent
│   ├── __main__.py
│   └── modules/
 │       ├── __init__.py       ← 模块注册表
 │       ├── base.py           ← BaseModule 基类与生命周期
 │       ├── common.py         ← 通用模块：清理 / 监视话题 / 通用 ros2 run
 │       ├── turtlesim.py      ← turtlesim 多乌龟模块
 │       ├── pubsub.py         ← 发布订阅示例模块（py/cpp）
 │       ├── service_client.py ← 服务端 + 客户端模块（第 15/16 课）
 │       ├── action_demo.py    ← Fibonacci action 模块（第 24/25 课）
 │       ├── params_demo.py    ← 参数节点模块（第 19/20 课）
 │       ├── bag_record.py     ← rosbag 录制/校验模块（第 10 课）
 │       └── launch_run.py     ← 通用 ros2 launch 模块（第 8/28 课）
 ├── scenarios/                ← 场景脚本（JSON，自由组合示例）
 │   ├── lesson2_turtlesim.json
 │   ├── pubsub_demo.json
 │   ├── service_demo.json     ← 已验证 PASS
 │   ├── action_demo.json      ← 已验证 PASS
 │   ├── params_demo.json      ← 已验证 PASS
 │   └── bag_record_demo.json  ← 已验证 PASS（录到 8 条 /chatter）
├── examples/
│   └── quickstart.sh
└── tests/
    └── test_detector.py
```

## 核心抽象（四步适配)

1. **检测**：`Detector` 识别 OS 名/版本、是否 WSL、ROS distro、默认工作空间、Python 版本。
2. **查表**：`Registry` 给出该 distro 的环境事实（setup 路径、apt 前缀、Python 要求、API 差异）。
3. **配置/管理**：`EnvironmentManager` + `RuntimeManager` 把"逻辑操作"转成对应当前 distro 的 shell 命令。
4. **组合**：模块 `BaseModule` = 一个"最小功能组件"，场景 `runner` 把模块 + 参数组合并按依赖顺序执行。

## 快速开始

```bash
source /opt/ros/foxy/setup.bash        # 任一个已安装的 distro 都行（agent 会自动识别）
cd /mnt/c/Users/admin/Desktop/dev/2000_Embody/1000_ros2_official/ros2_middleware
python3 -m rosagent detect              # 检测环境
python3 -m rosagent check               # 运行检查
python3 -m rosagent run scenarios/pubsub_demo.json         # 发布订阅
python3 -m rosagent run scenarios/service_demo.json        # 服务通信
python3 -m rosagent run scenarios/action_demo.json         # 动作通信
python3 -m rosagent run scenarios/params_demo.json         # 参数节点
python3 -m rosagent run scenarios/bag_record_demo.json     # rosbag 录制
python3 -m rosagent clean               # 清理残留进程与内存
```

## 组合场景示例

```json
{
  "name": "lesson2_turtlesim",
  "pre": ["clean"],
  "modules": [
    { "name": "turtlesim",  "params": { "n_turtles": 1, "keyboard": true } },
    { "name": "topic_view", "params": { "topics": ["/turtle1/pose"], "hz": true } }
  ],
  "watch": 30,
  "teardown": true
}
```

同一个模块换个参数就能适配：在 3 台不同机器上跑 `pubsub` 模块（py/cpp 语言不同、
topic 名不同、包来自 apt 或源码编译）都由参数 + 注册表自动处理差异。