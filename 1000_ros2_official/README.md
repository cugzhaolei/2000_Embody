# 1000_ros2_official · ROS 2 官方教程代码（Foxy 版，适配你的 WSL）

本目录根据鱼香ROS中文官方教程（http://dev.ros2.fishros.com/doc/Tutorials/ ）整理，
代码取自 **ROS 2 官方源仓库**（`ros2/examples`、`ros/ros_tutorials` 的 **foxy** 分支），
并按**你的 WSL 环境（Ubuntu 20.04 + ROS 2 Foxy）**定制了安装与运行命令。

```
1000_ros2_official/
├── README.md              ← 你现在看的这个（总入口）
├── scripts/
│   ├── setup_foxy_wsl.sh  ← 一键安装 ROS 2 Foxy（适配你的 Ubuntu 20.04 WSL）
│   └── check_env.sh       ← 环境自检脚本
├── lessons/               ← 30 课学习指南（每课：命令 + 代码位置 + 讲解）
│   ├── 01-configuring-environment.md
│   ├── 02-turtlesim-and-rqt.md
│   └── ...（01~30）
└── dev_ws/                ← colcon 工作空间（复制到 WSL 家目录后编译）
    └── src/
        ├── examples/              官方 ros2/examples (foxy)：发布订阅/服务/动作/组合
        ├── tutorial_interfaces    自定义 msg/srv（第 17-18 课）
        ├── action_tutorials_*     action 接口 + C++/Python 服务器客户端（第 23-25 课）
        ├── py_parameters / cpp_parameters   参数节点（第 19-20 课）
        ├── learning_tf2_py / learning_tf2_cpp  tf2 广播/监听（第 29 课）
        ├── polygon_base / polygon_plugins     pluginlib 插件（第 22 课）
        ├── launch_tutorial        launch 文件（第 9/28 课）
        └── urdf_tutorial          URDF 模型（第 30 课）
```

---

## 第一步 · 在 WSL 里安装 ROS 2 Foxy

你的 WSL 默认发行版是 **Ubuntu 20.04**，对应 ROS 2 **Foxy**（EOL，但仍可安装使用）。

```bash
# 从 Windows 终端进入你的 WSL（默认 distro）
wsl

# 在 WSL 里执行一键安装脚本
bash /mnt/c/Users/admin/Desktop/dev/2000_Embody/1000_ros2_official/scripts/setup_foxy_wsl.sh
```

脚本会自动：添加 ROS 软件源 → 安装 `ros-foxy-desktop` → 安装教程依赖（turtlesim/rqt/rosbag/URDF/tf2 等）→ 配置 `~/.bashrc`。

安装完成后，**新开一个终端**（自动 source）或手动执行：

```bash
source /opt/ros/foxy/setup.bash
ros2 --version
ros2 run turtlesim turtlesim_node     # 能看到小乌龟窗口即成功
```

> 说明：`turtlesim` 是 GUI 程序，WSL2 需要 **WSLg**（Win10 21H2+ / Win11，`wsl --update` 可升级）。

## 第二步 · 复制工作空间并编译

```bash
cp -r /mnt/c/Users/admin/Desktop/dev/2000_Embody/1000_ros2_official/dev_ws ~/dev_ws
cd ~/dev_ws
colcon build --symlink-install
echo "source ~/dev_ws/install/setup.bash" >> ~/.bashrc
source install/setup.bash
```

> 编译较慢属正常（会编译官方 examples 的所有 C++/Python 包）。只编译需要的包：
> `colcon build --packages-select examples_rclpy_minimal_publisher learning_tf2_py`

## 第三步 · 开始上课

按 `lessons/` 里的数字顺序学习（01 → 30），每个文件里都有可直接粘贴的 WSL 命令。

| 阶段 | 课程 |
|------|------|
| CLI 工具 | 01-10（环境、turtlesim/rqt、节点、话题、服务、参数、动作、日志、launch、rosbag） |
| 客户端库 | 11-22（工作空间、建包、C++/Python 发布订阅、C++/Python 服务、自定义接口、参数、doctor、插件） |
| 中级 | 23-30（action、组合、colcon、launch、tf2、URDF） |

## 常用排查

```bash
bash /mnt/c/Users/admin/Desktop/dev/2000_Embody/1000_ros2_official/scripts/check_env.sh
ros2 doctor
```

| 现象 | 处理 |
|------|------|
| `command not found: ros2` | `source /opt/ros/foxy/setup.bash` 或重开终端 |
| `Package 'examples_...' not found` | `cd ~/dev_ws && colcon build && source install/setup.bash` |
| 乌龟窗口黑屏/打不开 | WSLg 未启用：`wsl --update`；或 `sudo apt install -y x11-apps` |
| GUI 相关 rqt/rviz 卡顿 | WSL 默认 vGPU，可接受；严重时把 `export LIBGL_ALWAYS_SOFTWARE=1` 加入 ~/.bashrc |

## 代码来源（官方 foxy 分支）
- `ros2/examples`  →  https://github.com/ros2/examples/tree/foxy
- `ros/ros_tutorials`（turtlesim 自带 draw_square/mimic/teleop） →  https://github.com/ros/ros_tutorials/tree/foxy-devel
- 教程正文代码（interfaces/action/parameters/tf2/URDF/pluginlib）按 docs.ros.org/en/foxy 官方教程编写
