from pathlib import Path
from typing import List

import ros2_launch_helpers as rlh
from ament_index_python.packages import get_package_share_directory
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, OpaqueFunction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.substitutions import FindPackageShare

from launch import LaunchContext, LaunchDescription, LaunchDescriptionEntity
from robot_forklift_simple_3sw import xargs_catalog_manager


def generate_launch_description() -> LaunchDescription:
    """Build the unified launch description for all fs3sw robot versions."""
    ldes: list[LaunchDescriptionEntity] = [
        DeclareLaunchArgument(
            'use_sim_time',
            default_value='False',
            choices=['True', 'true', 'False', 'false'],
            description='Use simulation clock if true',
        ),
        DeclareLaunchArgument('namespace', default_value='', description='Namespace for all resources'),
        DeclareLaunchArgument(
            'robot_version', default_value='core', description='Robot version to launch (for example: core, v1)'
        ),
        DeclareLaunchArgument('robot_name', default_value='fs3sw', description='The unique name for the robot'),
        DeclareLaunchArgument(
            'params_file',
            default_value='',
            description='Path to params file. If empty, each included launch picks default by robot_version.',
        ),
        OpaqueFunction(function=_validate_robot_version),
        OpaqueFunction(function=_declare_xargs_launch_arguments_for_selected_version),
    ]

    ldes.extend(_declare_topic_remappings())
    ldes.extend(_declare_node_options())
    ldes.extend(_declare_logging_options())
    ldes.extend(
        [
            OpaqueFunction(function=_include_rsp),
            OpaqueFunction(function=_include_rosgz_bridge),
            OpaqueFunction(function=_include_three_swerve_kinematics),
        ]
    )

    return LaunchDescription(ldes)


def _declare_logging_options() -> List[LaunchDescriptionEntity]:
    """Declare logging-option launch arguments for nodes started by this launch file."""
    return [
        DeclareLaunchArgument(
            'rsp_logging_options', default_value=rlh.default_logging_options_str(), description=rlh.LOGGING_OPTIONS_DESC
        ),
        DeclareLaunchArgument(
            'three_swerve_kinematics_node_logging_options',
            default_value=rlh.default_logging_options_str(),
            description=rlh.LOGGING_OPTIONS_DESC,
        ),
        DeclareLaunchArgument(
            'rosgz_bridge_node_logging_options',
            default_value=rlh.default_logging_options_str(),
            description=rlh.LOGGING_OPTIONS_DESC,
        ),
    ]


def _declare_node_options() -> List[LaunchDescriptionEntity]:
    """Declare node-option launch arguments for nodes started by this launch file."""
    return [
        DeclareLaunchArgument(
            'rsp_options', default_value=rlh.default_node_options_str(), description=rlh.NODE_OPTIONS_DESC
        ),
        DeclareLaunchArgument(
            'three_swerve_kinematics_node_options',
            default_value=rlh.default_node_options_str(),
            description=rlh.NODE_OPTIONS_DESC,
        ),
        DeclareLaunchArgument(
            'rosgz_bridge_node_options', default_value=rlh.default_node_options_str(), description=rlh.NODE_OPTIONS_DESC
        ),
    ]


def _declare_topic_remappings() -> List[LaunchDescriptionEntity]:
    """Declare topic-remapping launch arguments for included nodes."""
    return [
        DeclareLaunchArgument('rsp_topic_remappings', default_value='', description=rlh.TOPIC_REMAPPINGS_DESC),
        DeclareLaunchArgument(
            'three_swerve_kinematics_node_topic_remappings', default_value='', description=rlh.TOPIC_REMAPPINGS_DESC
        ),
    ]


# An OF is needed to have access to the launch context, resolve the selected robot version and pass it to the
# xargs catalog manager which returns the appropriate DeclareLaunchArgument entities based on the catalog of xargs that
# robot version declares.
# This allows us to only declare the launch arguments relevant to the selected robot version and keep the launch file
# clean and scalable as new versions are added.
def _declare_xargs_launch_arguments_for_selected_version(ctx: LaunchContext) -> List[LaunchDescriptionEntity]:
    """Declare xargs launch arguments for the selected robot version."""
    robot_version = LaunchConfiguration('robot_version').perform(ctx).strip()
    return xargs_catalog_manager.declare_launch_arguments_for_robot_version(robot_version)


def _include_rosgz_bridge(ctx: LaunchContext) -> List[LaunchDescriptionEntity]:
    """Include the shared ROS-GZ bridge launch for the selected version."""
    return [
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                PathJoinSubstitution(
                    [FindPackageShare('robot_forklift_simple_3sw'), 'launch', 'rosgz_bridge.launch.py']
                )
            ),
            launch_arguments={
                'use_sim_time': LaunchConfiguration('use_sim_time'),
                'namespace': LaunchConfiguration('namespace'),
                'robot_version': LaunchConfiguration('robot_version'),
                'robot_name': LaunchConfiguration('robot_name'),
                'params_file': LaunchConfiguration('params_file'),
                'sim_file': LaunchConfiguration('sim_file'),
                'node_options': LaunchConfiguration('rosgz_bridge_node_options'),
                'logging_options': LaunchConfiguration('rosgz_bridge_node_logging_options'),
            }.items(),
        )
    ]


def _include_rsp(ctx: LaunchContext) -> List[LaunchDescriptionEntity]:
    """Include the shared RSP launch with xargs resolved for the selected version."""
    robot_version = LaunchConfiguration('robot_version').perform(ctx).strip()

    return [
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                PathJoinSubstitution([FindPackageShare('robot_forklift_simple_3sw'), 'launch', 'rsp.launch.py'])
            ),
            launch_arguments={
                'use_sim_time': LaunchConfiguration('use_sim_time'),
                'namespace': LaunchConfiguration('namespace'),
                'robot_version': LaunchConfiguration('robot_version'),
                'robot_name': LaunchConfiguration('robot_name'),
                'params_file': LaunchConfiguration('params_file'),
                'topic_remappings': LaunchConfiguration('rsp_topic_remappings'),
                'node_options': LaunchConfiguration('rsp_options'),
                'logging_options': LaunchConfiguration('rsp_logging_options'),
                **xargs_catalog_manager.get_launch_configurations_for_robot_version(robot_version),
            }.items(),
        )
    ]


def _include_three_swerve_kinematics(ctx: LaunchContext) -> List[LaunchDescriptionEntity]:
    """Include the three-swerve kinematics launch for this robot instance."""
    robot_version = LaunchConfiguration('robot_version').perform(ctx).strip()
    input_params_file = LaunchConfiguration('params_file').perform(ctx).strip()

    if input_params_file:
        params_file = input_params_file
    else:
        config_dir = Path(get_package_share_directory('robot_forklift_simple_3sw')).joinpath('config')
        candidate = config_dir.joinpath(f'example_{robot_version}.yaml')
        params_file = str(candidate if candidate.is_file() else config_dir.joinpath('example_core.yaml'))

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
                'params_file': params_file,
                'topic_remappings': LaunchConfiguration('three_swerve_kinematics_node_topic_remappings'),
                'node_options': LaunchConfiguration('three_swerve_kinematics_node_options'),
                'logging_options': LaunchConfiguration('three_swerve_kinematics_node_logging_options'),
            }.items(),
        )
    ]


def _validate_robot_version(ctx: LaunchContext) -> List[LaunchDescriptionEntity]:
    """Fail if the selected robot version is not recognized."""

    robot_version = LaunchConfiguration('robot_version').perform(ctx).strip()
    available_robot_versions = xargs_catalog_manager.get_robot_versions()

    if robot_version in available_robot_versions:
        return []

    raise ValueError(
        f"Version '{robot_version}' for the 'fs3sw' robot is not available. "
        f'Available versions: {", ".join(available_robot_versions)}'
    )
