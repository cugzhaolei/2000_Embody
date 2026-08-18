# 第 21 课 · 开始使用 ros2doctor (Getting Started with ros2doctor)

> 对应鱼香ROS官方教程：[开始使用ros2doctor](http://dev.ros2.fishros.com/doc/Tutorials/Getting-Started-With-Ros2doctor.html)

## 目标
用 `ros2doctor` 自动诊断 ROS 2 环境的常见问题（环境、网络、依赖、接口等）。

## 操作

```bash
source /opt/ros/foxy/setup.bash

# 检查整个环境
ros2 doctor

# 只检查网络与接口（不阻塞）
ros2 doctor --report
```

## 输出解读
- 每项前面有 `✓` / `✗` / `!`。
- `✗` 表示存在问题，后面会有建议。
- `!` 表示警告。

## 常见问题示例
- `Environment variable: ROS_DOMAIN_ID is not defined` → 无害，可忽略（或 export ROS_DOMAIN_ID=42 统一）。
- Python 版本不符 → 检查是否用对了 WSL distro（Foxy 需要 Ubuntu 20.04 的 Python 3.8）。

## 小结
`ros2 doctor` 是排查「装好了但跑不起来」的第一工具，优先于上网搜索。
