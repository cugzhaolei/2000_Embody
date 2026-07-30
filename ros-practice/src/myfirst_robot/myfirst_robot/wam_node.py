"""
WAM ROS2 节点 — World Action Model 交互节点
订阅: /scan, /odom, /cmd_vel_raw
发布: /cmd_vel (安全过滤), /wam/predicted_scan, /wam/collision_risk
"""
import os
import numpy as np
import torch
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import LaserScan
from nav_msgs.msg import Odometry, Path
from geometry_msgs.msg import Twist, PoseStamped
from std_msgs.msg import Float32
from visualization_msgs.msg import Marker, MarkerArray


class WAMNode(Node):
    def __init__(self):
        super().__init__('wam_node')

        # --- 参数 ---
        self.declare_parameter('model_path', os.path.expanduser('~/wam_model.pt'))
        self.declare_parameter('horizon', 20)
        self.declare_parameter('collision_threshold', 0.3)
        self.declare_parameter('use_safety_filter', True)
        self.declare_parameter('prediction_rate', 10.0)
        self.declare_parameter('scan_dim', 360)

        model_path = self.get_parameter('model_path').value
        self.horizon = self.get_parameter('horizon').value
        self.collision_threshold = self.get_parameter('collision_threshold').value
        self.use_safety_filter = self.get_parameter('use_safety_filter').value
        self.scan_dim = self.get_parameter('scan_dim').value

        # --- 加载世界模型 ---
        from myfirst_robot.wam.world_model import WorldModel
        from myfirst_robot.wam.planner import CEMPlanner

        self.world_model = WorldModel(scan_dim=self.scan_dim, action_dim=2)

        if os.path.exists(model_path):
            state = torch.load(model_path, map_location='cpu')
            self.world_model.load_state_dict(state)
            self.get_logger().info(f'加载世界模型: {model_path}')
        else:
            self.get_logger().warn(
                f'模型文件不存在: {model_path}，使用随机初始化（仅用于演示）')

        self.world_model.eval()
        self.planner = CEMPlanner(self.world_model, horizon=self.horizon)

        # --- 状态 ---
        self.current_scan = None
        self.current_odom = None

        # --- ROS2 接口 ---
        self.scan_sub = self.create_subscription(
            LaserScan, '/scan', self._scan_cb, 10)
        self.odom_sub = self.create_subscription(
            Odometry, '/odom', self._odom_cb, 10)
        self.cmd_sub = self.create_subscription(
            Twist, '/cmd_vel_raw', self._cmd_cb, 10)

        self.safe_vel_pub = self.create_publisher(Twist, '/cmd_vel', 10)
        self.risk_pub = self.create_publisher(Float32, '/wam/collision_risk', 10)
        self.pred_scan_pub = self.create_publisher(
            LaserScan, '/wam/predicted_scan', 10)
        self.viz_pub = self.create_publisher(
            MarkerArray, '/wam/imagination_viz', 10)

        rate = self.get_parameter('prediction_rate').value
        self.timer = self.create_timer(1.0 / rate, self._loop)
        self.get_logger().info(
            f'WAM节点已启动 horizon={self.horizon} safety={self.use_safety_filter}')

    def _scan_cb(self, msg: LaserScan):
        scan = np.array(msg.ranges, dtype=np.float32)
        if len(scan) != self.scan_dim:
            idx = np.linspace(0, len(scan) - 1, self.scan_dim, dtype=int)
            scan = scan[idx]
        scan = np.nan_to_num(scan, nan=20.0, posinf=20.0, neginf=0.0)
        scan = np.clip(scan, 0, 20)
        self.current_scan = torch.FloatTensor(scan)

    def _odom_cb(self, msg: Odometry):
        self.current_odom = msg

    def _cmd_cb(self, msg: Twist):
        """拦截 Nav2 输出的速度，安全过滤后发布"""
        if not self.use_safety_filter or self.current_scan is None:
            self.safe_vel_pub.publish(msg)
            return

        with torch.no_grad():
            safe_action, risk = self.planner.safe_action(
                self.current_scan, msg.linear.x, msg.angular.z)

        out = Twist()
        out.linear.x = float(safe_action[0])
        out.angular.z = float(safe_action[1])
        self.safe_vel_pub.publish(out)

        risk_msg = Float32()
        risk_msg.data = float(risk)
        self.risk_pub.publish(risk_msg)

        if risk > 0.3:
            self.get_logger().warn(
                f'碰撞风险 {risk:.2f} > 阈值，已减速: '
                f'{msg.linear.x:.2f}→{out.linear.x:.2f}')

    def _loop(self):
        """预测循环：想象未来并发布可视化"""
        if self.current_scan is None:
            return

        # 用零动作序列想象未来
        with torch.no_grad():
            actions = torch.zeros(1, self.horizon, 2)
            result = self.world_model.predict_future(self.current_scan, actions)

        # 发布预测的第5步LiDAR
        pred = result['future_scans'][0, min(4, self.horizon - 1)]
        self._pub_pred_scan(pred)

        # 发布碰撞风险
        risk = result['collision_probs'][0].max().item()
        risk_msg = Float32()
        risk_msg.data = risk
        self.risk_pub.publish(risk_msg)

        # 发布RViz可视化
        self._pub_viz(result)

    def _pub_pred_scan(self, pred: torch.Tensor):
        msg = LaserScan()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = 'laser_link'
        msg.angle_min = 0.0
        msg.angle_max = 6.2831853
        msg.angle_increment = 6.2831853 / self.scan_dim
        msg.range_min = 0.01
        msg.range_max = 20.0
        msg.ranges = pred.cpu().numpy().astype(np.float32).tolist()
        self.pred_scan_pub.publish(msg)

    def _pub_viz(self, result):
        markers = MarkerArray()
        for t in range(self.horizon):
            m = Marker()
            m.header.frame_id = 'base_link'
            m.header.stamp = self.get_clock().now().to_msg()
            m.ns = 'wam_prediction'
            m.id = t
            m.type = Marker.SPHERE
            m.action = Marker.ADD

            # 颜色由碰撞概率决定
            p = result['collision_probs'][0, t].item()
            if p < 0.3:
                m.color.r, m.color.g = 0.0, 1.0
            elif p < 0.7:
                m.color.r, m.color.g = 1.0, 1.0
            else:
                m.color.r, m.color.g = 1.0, 0.0
            m.color.b = 0.0
            m.color.a = 0.6

            m.scale.x = m.scale.y = m.scale.z = 0.1 + p * 0.2
            m.pose.position.x = float(t * 0.1)
            markers.markers.append(m)

        self.viz_pub.publish(markers)


def main(args=None):
    rclpy.init(args=args)
    node = WAMNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
