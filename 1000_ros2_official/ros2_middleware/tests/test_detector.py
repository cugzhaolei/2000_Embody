# 轻量单元测试：不需要 ROS 环境即可跑（覆盖注册表 / 检测 / 包名翻译逻辑）。
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rosagent import registry as reg  # noqa: E402


class TestRegistry(unittest.TestCase):
    def setUp(self):
        self.r = reg.Registry(reg.DISTROS)

    def test_known_distros(self):
        for d in ("foxy", "humble", "jazzy"):
            self.assertTrue(self.r.has(d))

    def test_apt_pkg_translation(self):
        self.assertEqual(self.r.apt_pkg("foxy", "turtlesim"), "ros-foxy-turtlesim")
        self.assertEqual(self.r.apt_pkg("jazzy", "turtlesim"), "ros-jazzy-turtlesim")

    def test_python_ok(self):
        self.assertTrue(self.r.python_ok("foxy", (3, 8)))
        self.assertFalse(self.r.python_ok("foxy", (3, 6)))

    def test_setup_path_by_distro(self):
        for d, path in (("foxy", "/opt/ros/foxy/setup.bash"),
                        ("humble", "/opt/ros/humble/setup.bash"),
                        ("jazzy", "/opt/ros/jazzy/setup.bash")):
            self.assertEqual(self.r.config(d, "setup"), path)


if __name__ == "__main__":
    unittest.main()