cmake_minimum_required(VERSION 3.5)
project(action_tutorials_cpp)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

# find dependencies
find_package(ament_cmake REQUIRED)
find_package(action_tutorials_interfaces REQUIRED)
find_package(rclcpp REQUIRED)
find_package(rclcpp_action REQUIRED)
find_package(rclcpp_components REQUIRED)

add_library(action_server SHARED
  src/fibonacci_action_server.cpp
)
target_compile_definitions(action_server PRIVATE "ACTION_TUTORIALS_CPP_BUILDING_DLL")
ament_target_dependencies(action_server
  "action_tutorials_interfaces"
  "rclcpp"
  "rclcpp_action"
  "rclcpp_components"
)
rclcpp_components_register_nodes(action_server "action_tutorials_cpp::FibonacciActionServer")
install(TARGETS
  action_server
  ARCHIVE DESTINATION lib
  LIBRARY DESTINATION lib
  RUNTIME DESTINATION bin
)

add_executable(action_server_executable
  src/fibonacci_action_server.cpp
)
ament_target_dependencies(action_server_executable
  "action_tutorials_interfaces"
  "rclcpp"
  "rclcpp_action"
)

add_executable(action_client_executable
  src/fibonacci_action_client.cpp
)
ament_target_dependencies(action_client_executable
  "action_tutorials_interfaces"
  "rclcpp"
  "rclcpp_action"
)

install(TARGETS
  action_server_executable
  action_client_executable
  DESTINATION lib/${PROJECT_NAME}
)

if(BUILD_TESTING)
  find_package(ament_lint_auto REQUIRED)
  ament_lint_auto_find_test_dependencies()
endif()

ament_package()
