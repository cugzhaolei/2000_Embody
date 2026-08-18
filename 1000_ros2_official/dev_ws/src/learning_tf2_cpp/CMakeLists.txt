cmake_minimum_required(VERSION 3.5)
project(learning_tf2_cpp)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

find_package(ament_cmake REQUIRED)
find_package(geometry_msgs REQUIRED)
find_package(rclcpp REQUIRED)
find_package(tf2 REQUIRED)
find_package(tf2_ros REQUIRED)
find_package(turtlesim REQUIRED)

add_executable(turtle_tf2_broadcaster src/turtle_tf2_broadcaster.cpp)
ament_target_dependencies(
  turtle_tf2_broadcaster
  geometry_msgs
  rclcpp
  tf2
  tf2_ros
  turtlesim
)

add_executable(turtle_tf2_listener src/turtle_tf2_listener.cpp)
ament_target_dependencies(
  turtle_tf2_listener
  geometry_msgs
  rclcpp
  tf2
  tf2_ros
  turtlesim
)

add_executable(static_turtle_tf2_broadcaster src/static_turtle_tf2_broadcaster.cpp)
ament_target_dependencies(
  static_turtle_tf2_broadcaster
  geometry_msgs
  rclcpp
  tf2
  tf2_ros
)

add_executable(fixed_frame_tf2_broadcaster src/fixed_frame_tf2_broadcaster.cpp)
ament_target_dependencies(
  fixed_frame_tf2_broadcaster
  geometry_msgs
  rclcpp
  tf2
  tf2_ros
)

install(TARGETS
  turtle_tf2_broadcaster
  turtle_tf2_listener
  static_turtle_tf2_broadcaster
  fixed_frame_tf2_broadcaster
  DESTINATION lib/${PROJECT_NAME}
)

if(BUILD_TESTING)
  find_package(ament_lint_auto REQUIRED)
  ament_lint_auto_find_test_dependencies()
endif()

ament_package()
