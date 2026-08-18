# ROS 各版本基础代码 / 函数 / 包差异对照表
> 供中间层 Agent（registry）维护者更新；也是迁移代码时的手册。

## 环境事实

| 项 | foxy | humble | jazzy |
|----|------|--------|-------|
| 发行日期 | 2020.06 | 2022.05 | 2024.05 |
| 支持 Ubuntu | 20.04 (focal) | 22.04 (jammy) | 24.04 (noble) |
| Python | 3.8 | 3.10 | 3.12 |
| setup 路径 | `/opt/ros/foxy/setup.bash` | `/opt/ros/humble/setup.bash` | `/opt/ros/jazzy/setup.bash` |
| apt 前缀 | `ros-foxy` | `ros-humble` | `ros-jazzy` |
| 默认 DDS | Fast RTPS | Fast DDS | Fast DDS |
| EOL 状态 | 已 EOL(2023) | 维护中 | 活跃 LTS |

## 代码 / API 差异（常见坑）

### Python (rclpy)
| 场景 | foxy | humble/jazzy |
|------|------|--------------|
| tf2 lookup_transform 时间参数 | `rclpy.time.Time()` | `rclpy.time.Time()`（jazzy 要求 `Tolerance` 显式传给 `Buffer.lookup_transform` 或在 kwargs） |
| tf2 C++ Time 类型 | `tf2::TimePointZero` | `tf2::TimePoint(0)` / `tf2::TimePointZero` |
| 参数 YAML（Pararmeters yaml 加载） | `ros2 param load` 支持 | 行为一致；jazzy 新增 `--ros-args -p` 解析更严格 |
| `py::get_parameter_value()` | 需 `.get_parameter_value().string_value` | 3.8 起支持 `.value`（humble 也可用 `.value`） |

### C++ (rclcpp)
| 场景 | foxy | humble/jazzy |
|------|------|--------------|
| `create_wall_timer` chrono | `500ms` | 一致 |
| QOS 深度参数 | 均可 | jazzy 强制 `qos_profile` 更严格 |
| `TimerBase::SharedPtr` | 可用 | 一致 |
| `rclcpp::spin` | 一致 | 一致 |

### 包名 / 提供方（apt 与源码）
| 逻辑功能 | foxy | humble | jazzy |
|----------|------|--------|-------|
| 发布订阅示例 | `examples_rclpy_minimal_publisher` 等 | 同左 | 同左（现代版名同） |
| tf2 乌龟教程 | `turtle-tf2-py` / `turtle-tf2-cpp` | `turtle-tf2-py` | `turtle_tf2_py`(msgs 包名一致) |
| tf_transformations | `ros-foxy-tf-transformations` | `ros-humble-tf-transformations` | `ros-jazzy-tf-transformations` |
| pluginlib 教程 | `polygon_base`/`polygon_plugins` | 同左 | 同左 |
| URDF 教程 | `urdf_tutorial` | 同左 | 同左 |

### 行为差异
- **foxy**: `ros2 param set` 数字参数以 `int` 传递；jazzy 自动类型推导更宽松。
- **humble→jazzy**: 非默认 QoS 的 topic 用老 `depth` int 会告警，建议用 `rclpy.qos.QoSProfile`。
- **action**: 三方库 `rclpy.action` 在 foxy 起支持；foxy/jazzy 接口保持一致但错误信息不同。

> 维护方式：以上条目对应 `registry.py` 中每个 distro 的 `api_notes` 字典；
> 新增版本时只在注册表加一项即可，代码无需改动。