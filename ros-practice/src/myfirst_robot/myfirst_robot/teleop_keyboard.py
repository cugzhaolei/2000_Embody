#!/usr/bin/env python3
"""
键盘遥控节点：控制差速驱动机器人移动
按键映射：
    w: 前进    x: 后退
    a: 左转    d: 右转
    s: 停止
    1-9: 设置线速度 (0.1~0.9 m/s)
    q/z: 增大/减小角速度
"""
import sys
import termios
import tty
import select
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist


class TeleopKeyboard(Node):
    def __init__(self):
        super().__init__('teleop_keyboard')
        self.publisher_ = self.create_publisher(Twist, '/cmd_vel', 10)
        self.timer = self.create_timer(0.1, self.timer_callback)

        self.linear_speed = 0.3
        self.angular_speed = 0.5
        self.target_linear = 0.0
        self.target_angular = 0.0

        self.get_logger().info('=== 键盘遥控已启动 ===')
        self.get_logger().info('w:前进 x:后退 a:左转 d:右转 s:停止')
        self.get_logger().info(f'当前线速度: {self.linear_speed} m/s')
        self.get_logger().info(f'当前角速度: {self.angular_speed} rad/s')

    def get_key(self):
        """非阻塞读取键盘输入"""
        if select.select([sys.stdin], [], [], 0) == ([sys.stdin], [], []):
            return sys.stdin.read(1)
        return ''

    def timer_callback(self):
        key = self.get_key()
        if key:
            if key == 'w':
                self.target_linear = self.linear_speed
                self.target_angular = 0.0
            elif key == 'x':
                self.target_linear = -self.linear_speed
                self.target_angular = 0.0
            elif key == 'a':
                self.target_linear = 0.0
                self.target_angular = self.angular_speed
            elif key == 'd':
                self.target_linear = 0.0
                self.target_angular = -self.angular_speed
            elif key == 's':
                self.target_linear = 0.0
                self.target_angular = 0.0
            elif key in '123456789':
                self.linear_speed = int(key) * 0.1
                self.get_logger().info(f'线速度设为: {self.linear_speed} m/s')
            elif key == 'q':
                self.angular_speed = min(1.0, self.angular_speed + 0.1)
                self.get_logger().info(f'角速度: {self.angular_speed} rad/s')
            elif key == 'z':
                self.angular_speed = max(0.1, self.angular_speed - 0.1)
                self.get_logger().info(f'角速度: {self.angular_speed} rad/s')
            elif key == '\x03':  # Ctrl+C
                rclpy.shutdown()

        msg = Twist()
        msg.linear.x = self.target_linear
        msg.angular.z = self.target_angular
        self.publisher_.publish(msg)


def main(args=None):
    rclpy.init(args=args)
    node = TeleopKeyboard()

    # 设置终端为原始模式
    old_settings = termios.tcgetattr(sys.stdin)
    try:
        tty.setraw(sys.stdin.fileno())
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
        # 停止机器人
        stop_msg = Twist()
        node.publisher_.publish(stop_msg)
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
