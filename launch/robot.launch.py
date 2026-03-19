from pathlib import Path
from typing import List

import ros2_launch_helpers as rlh
from ament_index_python.packages import get_package_share_directory
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, OpaqueFunction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.substitutions import FindPackageShare

from launch import LaunchContext, LaunchDescription, LaunchDescriptionEntity
from robot_forklift_simple_3sw import xargs


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
        OpaqueFunction(function=_declare_xargs),
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


def _declare_xargs(ctx: LaunchContext) -> List[LaunchDescriptionEntity]:
    """Declare xargs launch arguments for the selected robot version."""
    robot_version = LaunchConfiguration('robot_version').perform(ctx).strip()
    available_robot_versions = xargs.get_robot_versions()

    if robot_version not in available_robot_versions:
        raise ValueError(
            f"Version '{robot_version}' for the 'fs3sw' robot is not available. "
            f'Available robot versions: {", ".join(available_robot_versions)}'
        )

    available_xargs_versions = xargs.get_xargs_versions()

    if robot_version not in available_xargs_versions:
        raise ValueError(
            f"Version '{robot_version}' for the 'fs3sw' robot has no xargs configuration. "
            f'Available xargs versions: {", ".join(available_xargs_versions)}'
        )

    return xargs.declare_launch_arguments(robot_version)


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
                # Keys `sim_file` and `rosgz_bridge_file` are declared dynamically from xargs.
                # Both belong to the shared core xargs catalog, so every robot version provides them.
                'sim_file': LaunchConfiguration('sim_file'),
                'rosgz_bridge_file': LaunchConfiguration('rosgz_bridge_file'),
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
                **xargs.get_launch_configurations(robot_version),
            }.items(),
        )
    ]


def _include_three_swerve_kinematics(ctx: LaunchContext) -> List[LaunchDescriptionEntity]:
    """Include the three-swerve kinematics launch for this robot instance."""
    robot_version = LaunchConfiguration('robot_version').perform(ctx).strip()
    input_params_file = LaunchConfiguration('params_file').perform(ctx).strip()

    # If the user provided a params file via the 'params_file' launch argument, use it for the
    # kinematics node. Otherwise, look for a default params file based on the robot version under
    # the config directory. For example, if the robot version is "v1", look for
    # "config/example_v1.yaml".

    if input_params_file:
        params_file = Path(input_params_file)
    else:
        config_dir = Path(get_package_share_directory('robot_forklift_simple_3sw')).joinpath('config')
        params_file = config_dir.joinpath(f'example_{robot_version}.yaml')

    if not params_file.is_file():
        raise FileNotFoundError(
            f"Params file '{params_file}' does not exist for robot version '{robot_version}'. "
            f"Please provide a valid params file via the 'params_file' launch argument."
        )

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
                'params_file': str(params_file),
                'topic_remappings': LaunchConfiguration('three_swerve_kinematics_node_topic_remappings'),
                'node_options': LaunchConfiguration('three_swerve_kinematics_node_options'),
                'logging_options': LaunchConfiguration('three_swerve_kinematics_node_logging_options'),
            }.items(),
        )
    ]
