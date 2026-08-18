cmake_minimum_required(VERSION 3.5)
project(polygon_base)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

find_package(ament_cmake REQUIRED)

add_library(polygon_base INTERFACE)
target_include_directories(polygon_base INTERFACE include)
ament_export_interfaces(export_polygon_base HAS_LIBRARY_TARGET)
ament_export_include_directories(include)

ament_package()
