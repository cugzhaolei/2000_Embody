#include <chrono>
#include <functional>
#include <memory>

#include "geometry_msgs/msg/transform_stamped.hpp"
#include "geometry_msgs/msg/twist.hpp"

#include "rclcpp/rclcpp.hpp"
#include "tf2/exceptions.h"
#include "tf2_ros/transform_listener.h"
#include "tf2_ros/buffer.h"
#include "turtlesim/srv/spawn.hpp"

using namespace std::chrono_literals;

class FrameListener : public rclcpp::Node
{
public:
  FrameListener()
  : Node("turtle_tf2_frame_listener")
  {
    // Declare and acquire `target_frame` parameter
    target_frame_ = this->declare_parameter<std::string>("target_frame", "turtle1");

    tf_buffer_ =
      std::make_unique<tf2_ros::Buffer>(this->get_clock());
    tf_listener_ =
      std::make_shared<tf2_ros::TransformListener>(*tf_buffer_);

    // Create turtle2 velocity publisher
    publisher_ =
      this->create_publisher<geometry_msgs::msg::Twist>("turtle2/cmd_vel", 1);

    // Call on_timer function every second
    timer_ = this->create_wall_timer(
      1s, std::bind(&FrameListener::on_timer, this));
  }

private:
  void on_timer()
  {
    // Store frame names in variables that will be used to
    // compute transformations
    std::string fromFrameRel = target_frame_.c_str();
    std::string toFrameRel = "turtle2";

    if (tf_buffer_->canTransform(toFrameRel, fromFrameRel, tf2::TimePointZero)) {
      // Look up for the transformation between target_frame and turtle2 frames
      // and send velocity commands for turtle2 to reach target_frame
      auto transformStamped = tf_buffer_->lookupTransform(
        toFrameRel, fromFrameRel,
        tf2::TimePointZero);

      // Based on the transforms from the laser frame to the base frame,
      // extract the rotation and translation information
      geometry_msgs::msg::Twist msg;

      static const double scaleRotationRate = 1.0;
      msg.angular.z = scaleRotationRate * atan2(
        transformStamped.transform.translation.y,
        transformStamped.transform.translation.x);

      static const double scaleForwardSpeed = 1.0;
      msg.linear.x = scaleForwardSpeed * sqrt(
        pow(transformStamped.transform.translation.x, 2) +
        pow(transformStamped.transform.translation.y, 2));

      publisher_->publish(msg);
    }
  }

  // Member variables
  std::unique_ptr<tf2_ros::Buffer> tf_buffer_;
  std::shared_ptr<tf2_ros::TransformListener> tf_listener_{nullptr};
  rclcpp::Publisher<geometry_msgs::msg::Twist>::SharedPtr publisher_;
  rclcpp::TimerBase::SharedPtr timer_;
  std::string target_frame_;
};

int main(int argc, char * argv[])
{
  rclcpp::init(argc, argv);
  rclcpp::spin(std::make_shared<FrameListener>());
  rclcpp::shutdown();
  return 0;
}
