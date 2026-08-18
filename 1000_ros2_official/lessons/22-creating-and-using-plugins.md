# 第 22 课 · 创建和使用插件 (C++) — Creating and Using Plugins (C++ / pluginlib)

> 对应鱼香ROS官方教程：[创建和使用插件(C++)](http://dev.ros2.fishros.com/doc/Tutorials/Pluginlib.html)

## 目标
用 pluginlib 实现「插件架构」：定义基类，再实现多个可动态加载的插件类。

## 代码位置
```
dev_ws/src/polygon_base/      基类 RegularPolygon（纯虚接口）
dev_ws/src/polygon_plugins/   Triangle / Square 两个插件
```

## 操作

```bash
source /opt/ros/foxy/setup.bash
cd ~/dev_ws
colcon build --packages-select polygon_base polygon_plugins
source install/setup.bash

# 查看已注册的插件
ros2 pkg prefix polygon_plugins
ros2 plugin list | grep polygon
```

### 用一行 Python 验证插件可被加载
```bash
python3 -c "
from pluginlib import Plugin
plugins = Plugin('polygon_base', 'polygon_base/RegularPolygon')
print([p for p in plugins])
"
```

## 关键点
1. **基类**（纯虚接口）：`initialize(double)` / `area()`
2. **插件实现**：继承基类，最后用宏注册：
   ```cpp
   PLUGINLIB_EXPORT_CLASS(polygon_plugins::Triangle, polygon_base::RegularPolygon)
   ```
3. **插件描述文件** `polygon_plugins.xml`：声明插件名与所在库路径
4. **CMake**：`pluginlib_export_plugin_description_file(polygon_base polygon_plugins.xml)` 把描述打进包的索引

## 为什么用插件？
增加新形状（如 Circle）时，只新增一个类 + 注册宏，**无需改主程序**，符合开闭原则。
