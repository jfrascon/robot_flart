import os

import ros2_launch_helpers as rlh
from ament_index_python.packages import get_package_share_directory
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition, UnlessCondition  # noqa: F401
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import IfElseSubstitution, LaunchConfiguration, PathJoinSubstitution, TextSubstitution
from launch_ros.substitutions import FindPackageShare

from launch import LaunchDescription


def generate_launch_description():
    # ldes => (l)aunch (d)escription (e)ntitie(s)
    ldes = [
        # Common launch arguments.
        DeclareLaunchArgument(
            'use_sim_time',
            default_value='False',
            choices=['True', 'true', 'False', 'false'],
            description='Use simulation clock if true',
        ),
        DeclareLaunchArgument('namespace', default_value='', description='Namespace for all resources'),
        DeclareLaunchArgument('robot_name', default_value='flart', description='The unique name for the robot'),
        # Launch arguments for the robot description.
        DeclareLaunchArgument(
            'use_visual_meshes',
            default_value='True',
            choices=['True', 'true', 'False', 'false'],
            description='Whether to use visual meshes if True, or simple shapes if False (default: True)',
        ),
        DeclareLaunchArgument(
            'use_collision_meshes',
            default_value='False',
            choices=['True', 'true', 'False', 'false'],
            description='Whether to use collision meshes if True, or simple shapes if False (default: False)',
        ),
        DeclareLaunchArgument(
            'sim_cfg_file',
            default_value=os.path.join(get_package_share_directory('robot_flart'), 'config', 'simulation_default.yaml'),
            description='Path to the simulation configuration file (default: flart/simulation_default.yaml)',
        ),
        DeclareLaunchArgument(
            'rsp_publish_frequency',
            default_value='20.0',
            description='Frequency of publication for robot_state_publisher',
        ),
        DeclareLaunchArgument(
            'respawn_rosgz_bridge',
            default_value='False',
            choices=['True', 'true', 'False', 'false'],
            description='Whether to respawn the rosgz_bridge_node if it dies (default: False)',
        ),
        DeclareLaunchArgument(
            'log_level_rosgz_bridge',
            default_value='info',
            choices=['debug', 'info', 'warn', 'error'],
            description='Log level for the rosgz_bridge_node (default: info)',
        ),
        DeclareLaunchArgument('odom_frame', default_value='odom', description='Odometry frame name for the robot'),
        # Launch de robot description, both in simulation and real mode.
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                PathJoinSubstitution([FindPackageShare('robot_flart'), 'launch', 'rsp.launch.py'])
            ),
            launch_arguments={
                'use_sim_time': LaunchConfiguration('use_sim_time'),
                'robot_name': LaunchConfiguration('robot_name'),
                'namespace': LaunchConfiguration('namespace'),
                'odom_frame': LaunchConfiguration('odom_frame'),
                'use_visual_meshes': LaunchConfiguration('use_visual_meshes'),
                'use_collision_meshes': LaunchConfiguration('use_collision_meshes'),
                # If the robot is running in real mode, do not pass any simulation configuration file, since no sensor
                # can be simulated.
                # If the robot is running in simulation mode, pass the simulation configuration file available, which
                # can be the default if no other is provided by the user, or the one provided by the user.
                # Be aware that if the user provides an empty string as simulation configuration file, no sensor will be
                # simulated.
                'sim_cfg_file': IfElseSubstitution(
                    condition=LaunchConfiguration('use_sim_time'),
                    if_value=LaunchConfiguration('sim_cfg_file'),
                    else_value=TextSubstitution(text=''),
                ),
                'rsp_publish_frequency': LaunchConfiguration('rsp_publish_frequency'),
            }.items(),
        ),
        # Launch sensors: simulation vs real, based on 'use_sim_time'.
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                PathJoinSubstitution([FindPackageShare('robot_flart'), 'launch', 'rosgz_bridge.launch.py'])
            ),
            launch_arguments={
                'robot_name': LaunchConfiguration('robot_name'),
                'namespace': LaunchConfiguration('namespace'),
                'sim_cfg_file': LaunchConfiguration('sim_cfg_file'),
                'respawn_rosgz_bridge': LaunchConfiguration('respawn_rosgz_bridge'),
                'log_level_rosgz_bridge': LaunchConfiguration('log_level_rosgz_bridge'),
            }.items(),
            condition=IfCondition(LaunchConfiguration('use_sim_time')),
        ),
        # Launch Three Swerve Kinematics node.
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                PathJoinSubstitution(
                    [FindPackageShare('ground_vehicle_kinematics'), 'launch', 'three_swerve_bringup.launch.py']
                )
            ),
            launch_arguments={
                'use_sim_time': LaunchConfiguration('use_sim_time'),
                'namespace': LaunchConfiguration('namespace'),
                'robot_name': LaunchConfiguration('robot_name'),
                'params_file': PathJoinSubstitution(
                    [FindPackageShare('robot_flart'), 'config', 'three_swerve_kinematics.yaml']
                ),
                'remappings': TextSubstitution(text=''),
                'log_options': rlh.default_log_options_str(),
                'node_options': rlh.default_node_options_str(),
            }.items(),
        ),
    ]

    return LaunchDescription(ldes)
