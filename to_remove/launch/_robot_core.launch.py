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
from robot_forklift_simple_3aw import xargs_catalog_manager

_ROBOT_VERSION = 'core'


def generate_launch_description():
    """Build the launch description for the FLART core robot profile."""
    ldes: list[LaunchDescriptionEntity] = [
        DeclareLaunchArgument(
            'use_sim_time',
            default_value='False',
            choices=['True', 'true', 'False', 'false'],
            description='Use simulation clock if true',
        ),
        DeclareLaunchArgument('namespace', default_value='', description='Namespace for all resources'),
        DeclareLaunchArgument('robot_name', default_value='fs3aw_core', description='The unique name for the robot'),
        DeclareLaunchArgument(
            'params_file',
            default_value=os.path.join(
                get_package_share_directory('robot_forklift_simple_3aw'), 'config', 'example_fs3aw_core.yaml'
            ),
            description='Base YAML with ros__parameters for the nodes launched by this file',
        ),
    ]

    ldes.extend(xargs_catalog_manager.declare_launch_arguments_for_robot_version(_ROBOT_VERSION))
    ldes.extend(declare_topic_remappings())
    ldes.extend(declare_node_options())
    ldes.extend(declare_logging_options())
    # Include robot subsystems: RSP and kinematics are always launched, while rosgz_bridge is only
    # launched in simulation mode (`use_sim_time=True`).
    ldes.extend(
        [
            OpaqueFunction(function=include_rsp),
            OpaqueFunction(function=include_rosgz_bridge, condition=IfCondition(LaunchConfiguration('use_sim_time'))),
            OpaqueFunction(function=include_three_swerve_kinematics),
        ]
    )

    return LaunchDescription(ldes)


def include_rsp(_ctx: LaunchContext) -> List[LaunchDescriptionEntity]:
    """Include the core-specific RSP launch file."""
    return [
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                PathJoinSubstitution([FindPackageShare('robot_forklift_simple_3aw'), 'launch', 'rsp_core.launch.py'])
            ),
            launch_arguments={
                'use_sim_time': LaunchConfiguration('use_sim_time'),
                'namespace': LaunchConfiguration('namespace'),
                'robot_name': LaunchConfiguration('robot_name'),
                'params_file': LaunchConfiguration('params_file'),
                'topic_remappings': LaunchConfiguration('rsp_topic_remappings'),
                'node_options': LaunchConfiguration('rsp_options'),
                'logging_options': LaunchConfiguration('rsp_logging_options'),
                **xargs_catalog_manager.get_launch_configurations_for_robot_version(_ROBOT_VERSION),
            }.items(),
        )
    ]


def include_rosgz_bridge(ctx: LaunchContext) -> List[LaunchDescriptionEntity]:
    """Include the core rosgz bridge launch when core simulation plugins are enabled."""
    ns = LaunchConfiguration('namespace').perform(ctx).strip()
    robot_name = LaunchConfiguration('robot_name').perform(ctx).strip()
    robot_ns = rlh.create_robot_namespace(ns, robot_name)
    underscored_robot_ns = rlh.underscorify_namespace(robot_ns)

    # The core profile uses only `core_sim_file` to decide whether simulation bridges are needed.
    core_sim_file = LaunchConfiguration('core_sim_file').perform(ctx).strip()

    if not core_sim_file:
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
                    [FindPackageShare('robot_forklift_simple_3aw'), 'launch', 'rosgz_bridge_core.launch.py']
                )
            ),
            launch_arguments={
                'use_sim_time': LaunchConfiguration('use_sim_time'),
                'namespace': ns,
                'robot_name': robot_name,
                'params_file': LaunchConfiguration('params_file'),
                'core_sim_file': core_sim_file,
                'node_options': LaunchConfiguration('rosgz_bridge_options'),
                'logging_options': LaunchConfiguration('rosgz_bridge_logging_options'),
            }.items(),
        )
    ]


def include_three_swerve_kinematics(_ctx: LaunchContext) -> List[LaunchDescriptionEntity]:
    """Include the three-swerve kinematics launch for this robot instance."""
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


def declare_logging_options() -> List[LaunchDescriptionEntity]:
    """Declare logging-option launch arguments for nodes started by this launch file."""
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
    """Declare node-option launch arguments for nodes started by this launch file."""
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
    """Declare topic-remapping launch arguments for included nodes."""
    return [
        DeclareLaunchArgument('rsp_topic_remappings', default_value='', description=rlh.TOPIC_REMAPPINGS_DESC),
        DeclareLaunchArgument(
            'three_swerve_kinematics_node_topic_remappings', default_value='', description=rlh.TOPIC_REMAPPINGS_DESC
        ),
    ]
