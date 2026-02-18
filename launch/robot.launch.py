import os
from typing import List

import ros2_launch_helpers as rlh
from ament_index_python.packages import get_package_share_directory
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, LogInfo, OpaqueFunction
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.substitutions import FindPackageShare

from launch import LaunchContext, LaunchDescription, LaunchDescriptionEntity
from robot_flart import xargs_catalog_manager as flart_xargs


def generate_launch_description():
    # ldes => (l)aunch (d)escription (e)ntitie(s)
    ldes: list[LaunchDescriptionEntity] = [
        DeclareLaunchArgument(
            'use_sim_time',
            default_value='False',
            choices=['True', 'true', 'False', 'false'],
            description='Use simulation clock if true',
        ),
        DeclareLaunchArgument('namespace', default_value='', description='Namespace for all resources'),
        # Core version is the 'default' robot version; i.e, body + wheels + fork.
        # Other versions (v0, v1, ...) extend the core version with additional features.
        DeclareLaunchArgument(
            'robot_version', default_value='core', description='Robot version to launch (default: core)'
        ),
        DeclareLaunchArgument('robot_name', default_value='flart_core', description='The unique name for the robot'),
        ################################################################################################################
        # Parameters
        ################################################################################################################
        DeclareLaunchArgument(
            'params_file',
            default_value=os.path.join(get_package_share_directory('robot_flart'), 'config', 'example_flart_core.yaml'),
            description='Base YAML with ros__parameters',
        ),
        # Declare launch arguments that are used to set the xacro arguments (<xacro:arg>) in the selected xacro file
        # (based on 'robot_version' launch argument).
        # These xacro arguments (<xacro:arg>) are used to generate the robot description, and they
        # used to generate the robot description. These launch arguments are generated dynamically based on the xacro
        OpaqueFunction(function=declare_launch_arguments_for_selected_version),
    ]
    ####################################################################################################################
    # Remappings, logging options and node options
    ####################################################################################################################
    ldes.extend(declare_topic_remappings())
    ldes.extend(declare_node_options())
    ldes.extend(declare_logging_options())
    ####################################################################################################################
    # Includes
    ####################################################################################################################
    ldes.extend(
        [
            # Launch de robot description. The rsp node works both in simulation and real mode.
            OpaqueFunction(function=include_rsp),
            # Launch rosgz_bridge nodes (core + extras) only in simulation.
            OpaqueFunction(function=include_rosgz_bridge, condition=IfCondition(LaunchConfiguration('use_sim_time'))),
            # Launch three swerve kinematics node to do the kinematics calculations, direct and inverse.
            OpaqueFunction(function=include_three_swerve_kinematics),
        ]
    )

    return LaunchDescription(ldes)


################################################################################
# Opaque functions
################################################################################


def include_rsp(ctx: LaunchContext) -> List[LaunchDescriptionEntity]:
    robot_version = LaunchConfiguration('robot_version').perform(ctx).strip()

    return [
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                PathJoinSubstitution([FindPackageShare('robot_flart'), 'launch', 'rsp.launch.py'])
            ),
            launch_arguments={
                'use_sim_time': LaunchConfiguration('use_sim_time'),
                'namespace': LaunchConfiguration('namespace'),
                'robot_version': LaunchConfiguration('robot_version'),
                'robot_name': LaunchConfiguration('robot_name'),
                'params_file': LaunchConfiguration('params_file'),
                # Launch arguments 'publish_frequency' and 'ignore_timestamp' are not passed directly here, they must
                # be provided in the launch configuration 'params_file'.
                **get_launch_configurations_from_resolved_xargs(robot_version),
                'topic_remappings': LaunchConfiguration('rsp_topic_remappings'),
                'node_options': LaunchConfiguration('rsp_options'),
                'logging_options': LaunchConfiguration('rsp_logging_options'),
            }.items(),
        )
    ]


def include_rosgz_bridge(ctx: LaunchContext) -> List[LaunchDescriptionEntity]:
    robot_version = LaunchConfiguration('robot_version').perform(ctx).strip()
    available_robot_versions = flart_xargs.get_robot_versions()

    ns = LaunchConfiguration('namespace').perform(ctx).strip()
    robot_name = LaunchConfiguration('robot_name').perform(ctx).strip()
    robot_ns = rlh.create_robot_namespace(ns, robot_name)
    underscored_robot_ns = rlh.underscorify_namespace(robot_ns)

    if robot_version not in available_robot_versions:
        return [
            LogInfo(
                msg=f"[ERROR][{underscored_robot_ns}] Version '{robot_version}' for the 'flart' robot is not "
                f'available.  Available versions: {", ".join(available_robot_versions)}'
            )
        ]

    # Every version of the 'flart' robot uses the 'core_sim_file'.
    core_sim_file = LaunchConfiguration('core_sim_file').perform(ctx).strip()

    # If the 'core_sim_file' is an empty string, no simulation plugins will be loaded for the base and fork, so there is
    # no need to create the channels of the rosgz_bridge that communicate ROS2 with GZ for those plugins.
    # At this point, we do not know yet if the robot version uses 'extras_sim_file' or not, but we can
    # 'decide partially' if we will launch the rosgz_bridge or not based on the value of 'core_sim_file' alone.
    launch_rosgz_bridge = core_sim_file != ''

    launch_arguments = {
        'use_sim_time': LaunchConfiguration('use_sim_time'),
        'namespace': ns,
        'robot_name': robot_name,
        'params_file': LaunchConfiguration('params_file'),
        'core_sim_file': core_sim_file,
        # No remappings for rosgz_bridges.
        'node_options': LaunchConfiguration('rosgz_bridge_options'),
        'logging_options': LaunchConfiguration('rosgz_bridge_logging_options'),
    }

    # Only non-core versions MAY use 'extras_sim_file'.
    # If the robot version does not use the 'extras_sim_file' or the variable 'extras_sim_file' is an empty string,
    # no extra simulation plugins will be loaded, so there is no need to create the channels of the rosgz_bridge that
    # communicate ROS2 with GZ for those extra plugins.
    # Therefore we have the following cases:
    # 1. The robot version does not use 'extras_sim_file':
    #    1.1 'core_sim_file' is empty     => do not launch rosgz_bridge.
    #    1.2 'core_sim_file' is not empty => launch rosgz_bridge.
    # 2. The robot version uses 'extras_sim_file' and 'extras_sim_file' is empty:
    #    2.1 'core_sim_file' is empty     => do not launch rosgz_bridge.
    #    2.2 'core_sim_file' is not empty => launch rosgz_bridge.
    # 3. The robot version uses 'extras_sim_file' and 'extras_sim_file' is not empty: always launch rosgz_bridge.

    if 'extras_sim_file' in flart_xargs.get_resolved_xargs(robot_version):
        extras_sim_file = LaunchConfiguration('extras_sim_file').perform(ctx).strip()
        launch_rosgz_bridge = launch_rosgz_bridge and (extras_sim_file != '')

    if not launch_rosgz_bridge:
        return [
            LogInfo(
                msg=(
                    f'[{underscored_robot_ns}] Not launching rosgz_bridge node because no simulation '
                    'plugins are enabled.'
                )
            )
        ]

    return [
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                PathJoinSubstitution(
                    [FindPackageShare('robot_flart'), 'launch', f'rosgz_bridge_{robot_version}.launch.py']
                )
            ),
            launch_arguments=launch_arguments.items(),
        )
    ]


def include_three_swerve_kinematics(ctx: LaunchContext) -> List[LaunchDescriptionEntity]:
    return [
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
                'params_file': LaunchConfiguration('params_file'),
                'topic_remappings': LaunchConfiguration('three_swerve_kinematics_node_topic_remappings'),
                'node_options': LaunchConfiguration('three_swerve_kinematics_node_options'),
                'logging_options': LaunchConfiguration('three_swerve_kinematics_node_logging_options'),
            }.items(),
        )
    ]


def declare_launch_arguments_for_selected_version(ctx: LaunchContext) -> List[LaunchDescriptionEntity]:
    robot_version = LaunchConfiguration('robot_version').perform(ctx).strip()
    return flart_xargs.declare_launch_arguments_for_robot_version(ctx, robot_version)


def get_launch_configurations_from_resolved_xargs(robot_version: str) -> dict[str, LaunchConfiguration]:
    return {
        xarg_name: LaunchConfiguration(xarg_name) for xarg_name in flart_xargs.get_resolved_xargs(robot_version).keys()
    }


################################################################################
# Non-opaque functions
################################################################################


def declare_logging_options() -> List[LaunchDescriptionEntity]:
    # Parameter names are : <binary_name>_logging_options
    return [
        DeclareLaunchArgument(
            'rsp_logging_options', default_value=rlh.default_logging_options_str(), description=rlh.LOGGING_OPTIONS_DESC
        ),
        DeclareLaunchArgument(
            'rosgz_bridge_logging_options',
            default_value=rlh.default_logging_options_str(),
            description=rlh.LOGGING_OPTIONS_DESC,
        ),
        DeclareLaunchArgument(
            'three_swerve_kinematics_node_logging_options',
            default_value=rlh.default_logging_options_str(),
            description=rlh.LOGGING_OPTIONS_DESC,
        ),
    ]


def declare_node_options() -> List[LaunchDescriptionEntity]:
    # Parameter names are : <binary_name>_options
    return [
        DeclareLaunchArgument(
            'rsp_options', default_value=rlh.default_node_options_str(), description=rlh.NODE_OPTIONS_DESC
        ),
        DeclareLaunchArgument(
            'rosgz_bridge_options', default_value=rlh.default_node_options_str(), description=rlh.NODE_OPTIONS_DESC
        ),
        DeclareLaunchArgument(
            'three_swerve_kinematics_node_options',
            default_value=rlh.default_node_options_str(),
            description=rlh.NODE_OPTIONS_DESC,
        ),
    ]


def declare_topic_remappings() -> List[LaunchDescriptionEntity]:
    # Parameter names are: <binary_name>_topic_remappings
    return [
        DeclareLaunchArgument('rsp_topic_remappings', default_value='', description=rlh.TOPIC_REMAPPINGS_DESC),
        DeclareLaunchArgument(
            'three_swerve_kinematics_node_topic_remappings', default_value='', description=rlh.TOPIC_REMAPPINGS_DESC
        ),
    ]
