import os  # noqa: F401

import ros2_launch_helpers as rlh
import yaml  # noqa: F401
from ament_index_python.packages import get_package_share_directory
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.substitutions import FindPackageShare

from launch import LaunchDescription


def generate_launch_description():
    # ldes => (l)aunch (d)escription (e)ntitie(s)
    ldes = [
        DeclareLaunchArgument(
            'use_sim_time',
            default_value='False',
            choices=['True', 'true', 'False', 'false'],
            description='Use simulation clock if true',
        ),
        DeclareLaunchArgument('namespace', default_value='', description='Namespace for all resources'),
        DeclareLaunchArgument('robot_name', default_value='flart', description='The unique name for the robot'),
        # <parameters>
        # Parameters for robot_state_publisher (rsp)
        DeclareLaunchArgument('odom_frame', default_value='odom', description='Odometry frame name of the robot'),
        DeclareLaunchArgument(
            'rsp_use_visual_meshes',
            default_value='True',
            description='Whether to use visual meshes if True, or simple shapes if False (default: True)',
        ),
        DeclareLaunchArgument(
            'rsp_use_collision_meshes',
            default_value='False',
            description='Whether to use collision meshes if True, or simple shapes if False (default: False)',
        ),
        DeclareLaunchArgument(
            'rsp_publish_frequency',
            default_value='20.0',
            description='Frequency of publication for robot_state_publisher (default: 20.0)',
        ),
        DeclareLaunchArgument(
            'sim_cfg_file',
            default_value=os.path.join(get_package_share_directory('robot_flart'), 'config', 'simulation_default.yaml'),
            description='Path to the simulation configuration file (default: simulation_default.yaml)',
        ),
        # Parameters for rosgz_bridge
        DeclareLaunchArgument(
            'rosgz_bridge_subscription_heartbeat',
            default_value='1000',
            description='Subscription heartbeat (default: 1000)',
        ),
        DeclareLaunchArgument(
            'three_swerve_kinematics_params_file',
            default_value=os.path.join(
                get_package_share_directory('robot_flart'), 'config', 'three_swerve_kinematics.yaml'
            ),
            description=('Path to the three swerve kinematics parameters file (default: three_swerve_kinematics.yaml)'),
        ),
        # </parameters>
        # <remappings>NOT USED</remappings>
        # <log_options>
        DeclareLaunchArgument(
            'rsp_log_options', default_value=rlh.default_log_options_str(), description=rlh.LOG_OPTIONS_DESC
        ),
        DeclareLaunchArgument(
            'rosgz_bridge_log_options', default_value=rlh.default_log_options_str(), description=rlh.LOG_OPTIONS_DESC
        ),
        DeclareLaunchArgument(
            'three_swerve_kinematics_log_options',
            default_value=rlh.default_log_options_str(),
            description=rlh.LOG_OPTIONS_DESC,
        ),
        # </log_options>
        # <node_options>
        DeclareLaunchArgument(
            'rsp_node_options', default_value=rlh.default_node_options_str(), description=rlh.NODE_OPTIONS_DESC
        ),
        DeclareLaunchArgument(
            'rosgz_bridge_node_options', default_value=rlh.default_node_options_str(), description=rlh.NODE_OPTIONS_DESC
        ),
        DeclareLaunchArgument(
            'three_swerve_kinematics_node_options',
            default_value=rlh.default_node_options_str(),
            description=rlh.NODE_OPTIONS_DESC,
        ),
        # </node_options>
        # Launch de robot description. The rsp node works both in simulation and real mode.
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                PathJoinSubstitution([FindPackageShare('robot_flart'), 'launch', 'rsp.launch.py'])
            ),
            launch_arguments={
                'use_sim_time': LaunchConfiguration('use_sim_time'),
                'namespace': LaunchConfiguration('namespace'),
                'robot_name': LaunchConfiguration('robot_name'),
                'odom_frame': LaunchConfiguration('odom_frame'),
                'use_visual_meshes': LaunchConfiguration('rsp_use_visual_meshes'),
                'use_collision_meshes': LaunchConfiguration('rsp_use_collision_meshes'),
                'publish_frequency': LaunchConfiguration('rsp_publish_frequency'),
                'sim_cfg_file': LaunchConfiguration('sim_cfg_file'),
                'log_options': LaunchConfiguration('rsp_log_options'),
                'node_options': LaunchConfiguration('rsp_node_options'),
            }.items(),
        ),
        # Launch rosgz_bridge only in simulation, with all channels configured.
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                PathJoinSubstitution([FindPackageShare('robot_flart'), 'launch', 'rosgz_bridge.launch.py'])
            ),
            launch_arguments={
                'use_sim_time': LaunchConfiguration('use_sim_time'),
                'namespace': LaunchConfiguration('namespace'),
                'robot_name': LaunchConfiguration('robot_name'),
                'sim_cfg_file': LaunchConfiguration('sim_cfg_file'),
                'subscription_heartbeat': LaunchConfiguration('rosgz_bridge_subscription_heartbeat'),
                'log_options': LaunchConfiguration('rosgz_bridge_log_options'),
                'node_options': LaunchConfiguration('rosgz_bridge_node_options'),
            }.items(),
            condition=IfCondition(LaunchConfiguration('use_sim_time')),
        ),
        # Launch three swerve kinematics node to do the kinematics calculations, direct and inverse.
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                PathJoinSubstitution(
                    [FindPackageShare('ground_vehicle_kinematics'), 'launch', 'three_swerve_kinematics.launch.py']
                )
            ),
            launch_arguments={
                'use_sim_time': LaunchConfiguration('use_sim_time'),
                'namespace': LaunchConfiguration('namespace'),
                'robot_name': LaunchConfiguration('robot_name'),
                'params_file': LaunchConfiguration('three_swerve_kinematics_params_file'),
                'log_options': LaunchConfiguration('three_swerve_kinematics_log_options'),
                'node_options': LaunchConfiguration('three_swerve_kinematics_node_options'),
            }.items(),
        ),
    ]

    return LaunchDescription(ldes)
