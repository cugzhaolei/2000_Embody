# 第 11 课 · 创建工作空间 (Creating a Workspace)

> 对应鱼香ROS官方教程：[创建工作空间](http://dev.ros2.fishros.com/doc/Tutorials/Workspace/Creating-A-Workspace.html)

## 目标
建立标准的 colcon 工作空间结构：`dev_ws/src/`，把所有教程包放进 `src` 统一编译。

## 操作

```bash
source /opt/ros/foxy/setup.bash

# 本仓库已经内置了一个 dev_ws，直接复制到 WSL 家目录（推荐）
cp -r /mnt/c/Users/admin/Desktop/dev/2000_Embody/1000_ros2_official/dev_ws ~/dev_ws

# 或者手动创建空工作空间
# mkdir -p ~/dev_ws/src
# cd ~/dev_ws

# 编译全部包（需要先装 colcon）
sudo apt install -y python3-colcon-common-extensions
cd ~/dev_ws
colcon build --symlink-install

# 加载新编译出来的环境（之后的新终端要 source 一次）
source install/setup.bash

# 验证
ros2 pkg list | grep examples
```

## 本工作空间里包含的官方包
| 包 | 用途 |
|----|------|
| `examples/` | ros2/examples foxy 全部 Python/C++ 最小示例（发布订阅/服务/动作/组合） |
| `tutorial_interfaces` | 自定义 msg/srv（第 17-18 课） |
| `action_tutorials_*` | 自定义 action 接口与实现（第 23-25 课） |
| `py_parameters` / `cpp_parameters` | 参数节点（第 19-20 课） |
| `learning_tf2_py` / `learning_tf2_cpp` | tf2 广播器/监听器（第 29 课） |
| `polygon_base` / `polygon_plugins` | pluginlib 插件（第 22 课） |
| `launch_tutorial` | launch 文件（第 9/28 课） |
| `urdf_tutorial` | URDF 模型（第 30 课） |

## 说明
- 之后所有 `ros2 run examples_...` 等命令都依赖 `source install/setup.bash`。
- 想只编译某个包：`colcon build --packages-select <包名>`。
