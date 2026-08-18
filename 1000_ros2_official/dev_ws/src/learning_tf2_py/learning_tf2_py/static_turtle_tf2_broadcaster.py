from geometry_msgs.msg import TransformStamped

import rclpy
from rclpy.node import Node

from tf2_ros.static_transform_broadcaster import StaticTransformBroadcaster

from tf_transformations import quaternion_from_euler


class StaticFramePublisher(Node):
    def __init__(self, transformation):
        super().__init__('static_turtle_tf2_broadcaster')
        self._tf_publisher = StaticTransformBroadcaster(self)
        self._make_transforms(transformation)

    def _make_transforms(self, transformation):
        static_transform_stamped = TransformStamped()

        static_transform_stamped.header.stamp = self.get_clock().now().to_msg()
        static_transform_stamped.header.frame_id = 'world'
        static_transform_stamped.child_frame_id = transformation[0]

        static_transform_stamped.transform.translation.x = float(transformation[1])
        static_transform_stamped.transform.translation.y = float(transformation[2])
        static_transform_stamped.transform.translation.z = float(transformation[3])

        quat = quaternion_from_euler(
            float(transformation[4]),
            float(transformation[5]),
            float(transformation[6]))
        static_transform_stamped.transform.rotation.x = quat[0]
        static_transform_stamped.transform.rotation.y = quat[1]
        static_transform_stamped.transform.rotation.z = quat[2]
        static_transform_stamped.transform.rotation.w = quat[3]

        self._tf_publisher.sendTransform(static_transform_stamped)


def main():
    logger = rclpy.logging.get_logger('logger')

    import sys
    # obtain parameters from command line arguments
    if len(sys.argv) < 8:
        logger.info('Invalid number of parameters. Usage: \n'
                    '$ ros2 run learning_tf2_py static_turtle_tf2_broadcaster '
                    'child_frame_name x y z roll pitch yaw')
        sys.exit(1)

    if sys.argv[1] == 'world':
        logger.info('Your static turtle name cannot be "world"')
        sys.exit(2)

    # pass parameters and initialize node
    rclpy.init()
    node = StaticFramePublisher(sys.argv[1:])
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass

    rclpy.shutdown()


if __name__ == '__main__':
    main()
