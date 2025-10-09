cmake_minimum_required(VERSION 3.5)
project(xut_robot_flart)

find_package(ament_cmake REQUIRED)
find_package(ament_cmake_python REQUIRED)
ament_package_xml()

install(
    DIRECTORY config launch meshes urdf
    DESTINATION share/${PROJECT_NAME})

#ament_environment_hooks("${CMAKE_CURRENT_SOURCE_DIR}/hooks/${PROJECT_NAME}.dsv.in")

# if(BUILD_TESTING)
#   find_package(ament_cmake_pytest REQUIRED)
#   ament_add_pytest_test(xacro_test <file_to_test>)
# endif()

ament_package()
