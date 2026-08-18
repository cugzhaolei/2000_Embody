# 第 18 课 · 在 ROS 2 接口上扩展 (Expanding on ROS 2 Interfaces)

> 对应鱼香ROS官方教程：[在ROS 2接口上扩展](http://dev.ros2.fishros.com/doc/Tutorials/Single-Package-Define-And-Use-Interface.html)

## 目标
在**同一个包**里既定义接口，又写节点使用它（省去跨包依赖的麻烦）。

## 概念
| 接口 | 场景 |
|------|------|
| 独立接口包 | 接口被很多包共用（推荐生产做法，如第 17 课） |
| 同包定义+使用 | 学习/原型阶段，图省事 |

## 操作（把 tutorial_interfaces 扩展出可用接口）

在 `tutorial_interfaces` 里新增一个含数组的 msg：

```bash
cd ~/dev_ws/src/tutorial_interfaces/msg
# 新建 NumList.msg，内容：
#   int64[] data
```

```bash
# 在 CMakeLists.txt 的 set(msg_files ...) 中加一行 msg/NumList.msg
cd ~/dev_ws
colcon build --packages-select tutorial_interfaces
source install/setup.bash
ros2 interface show tutorial_interfaces/msg/NumList
```

## 更多接口类型速查
```text
bool, byte, char, float32, float64, int8..int64, uint8..uint64, string
以及可变长数组：int32[] / string[]，固定长数组：int32[4]
```

## 说明
Foxy 中 msg 字段支持**默认值**（如 `int64 num 42`）。srv 的注释用 `#`。
