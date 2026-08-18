import math

from geometry_msgs.msg import Twist

import rclpy
from rclpy.node import Node

from tf2_ros import TransformException
from tf2_ros.buffer import Buffer
from tf2_ros.transform_listener import TransformListener

from turtlesim.srv import Spawn


class FrameListener(Node):

    def __init__(self):
        super().__init__('turtle_tf2_frame_listener')

        # Declare and acquire `target_frame` parameter
        self.target_frame = self.declare_parameter(
            'target_frame', 'turtle1').get_parameter_value().string_value

        self.tf_buffer = Buffer()
        self.tf_listener = TransformListener(self.tf_buffer, self)

        # Create turtle2 velocity publisher
        self.publisher = self.create_publisher(Twist, 'turtle2/cmd_vel', 1)

        # Call on_timer function every second
        self.timer = self.create_timer(1.0, self.on_timer)

        # Create turtle2 spawn service client
        self.spawner = self.create_client(Spawn, 'spawn')

        # Wait for spawn service to be available
        self.spawner.wait_for_service()

        # Spawn turtle2
        self.spawn_turtle2()

    def on_timer(self):
        # Store frame names in variables that will be used to
        # compute transformations
        from_frame_rel = self.target_frame
        to_frame_rel = 'turtle2'

        # Look up for the transformation between target_frame and turtle2 frames
        # and send velocity commands for turtle2 to reach target_frame
        try:
            t = self.tf_buffer.lookup_transform(
                to_frame_rel,
                from_frame_rel,
                rclpy.time.Time())
        except TransformException as ex:
            self.get_logger().info(
                f'Could not transform {to_frame_rel} to {from_frame_rel}: {ex}')
            return

        msg = Twist()
        scale_rotation_rate = 1.0
        msg.angular.z = scale_rotation_rate * math.atan2(
            t.transform.translation.y,
            t.transform.translation.x)

        scale_forward_speed = 1.0
        msg.linear.x = scale_forward_speed * math.sqrt(
            t.transform.translation.x ** 2 +
            t.transform.translation.y ** 2)

        self.publisher.publish(msg)

    def spawn_turtle2(self):
        spawn_request = Spawn.Request()
        spawn_request.x = 4.0
        spawn_request.y = 2.0
        spawn_request.theta = 0.0
        spawn_request.name = 'turtle2'
        self.spawner.call_async(spawn_request)


def main():
    rclpy.init()
    node = FrameListener()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass

    rclpy.shutdown()


if __name__ == '__main__':
    main()
