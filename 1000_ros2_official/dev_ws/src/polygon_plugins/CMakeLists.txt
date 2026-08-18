cmake_minimum_required(VERSION 3.5)
project(polygon_plugins)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

find_package(ament_cmake REQUIRED)
find_package(pluginlib REQUIRED)
find_package(polygon_base REQUIRED)

add_library(polygon_plugins src/polygon_plugins.cpp)
target_compile_definitions(polygon_plugins PRIVATE POLYGON_PLUGINS_BUILDING_DLL)
ament_target_dependencies(polygon_plugins pluginlib polygon_base)

pluginlib_export_plugin_description_file(polygon_base polygon_plugins.xml)

install(TARGETS polygon_plugins
  ARCHIVE DESTINATION lib
  LIBRARY DESTINATION lib
  RUNTIME DESTINATION bin
)

if(BUILD_TESTING)
  find_package(ament_lint_auto REQUIRED)
  ament_lint_auto_find_test_dependencies()
endif()

ament_package()
