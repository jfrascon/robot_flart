import os
from pathlib import Path
from typing import Any, Dict, List

import ros2_launch_helpers as rlh
import yaml
from ament_index_python.packages import get_package_share_directory
from launch.actions import DeclareLaunchArgument, LogInfo, OpaqueFunction
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterFile

from launch import LaunchContext, LaunchDescription, LaunchDescriptionEntity
from robot_flart import rosgz_bridge_catalog_manager

_ROBOT_VERSION = 'v0'


def generate_launch_description() -> LaunchDescription:
    """Build the rosgz bridge launch description for the FLART v0 profile."""
    ldes: List[LaunchDescriptionEntity] = [
        DeclareLaunchArgument(
            'use_sim_time',
            default_value='False',
            choices=['True', 'true', 'False', 'false'],
            description='Use simulation clock if true',
        ),
        DeclareLaunchArgument(
            'namespace',
            default_value='',
            description='Namespace for all resources',
            condition=IfCondition(LaunchConfiguration('use_sim_time')),
        ),
        DeclareLaunchArgument(
            'robot_name',
            default_value='flart',
            description='The unique name for the robot',
            condition=IfCondition(LaunchConfiguration('use_sim_time')),
        ),
        DeclareLaunchArgument(
            'params_file',
            default_value=os.path.join(get_package_share_directory('robot_flart'), 'config', 'example_flart_v0.yaml'),
            description='Base YAML with ros__parameters (Default: example_flart_v0.yaml)',
            condition=IfCondition(LaunchConfiguration('use_sim_time')),
        ),
        DeclareLaunchArgument(
            'subscription_heartbeat',
            default_value='',
            description='Subscription heartbeat (Optional, default: "")',
            condition=IfCondition(LaunchConfiguration('use_sim_time')),
        ),
        DeclareLaunchArgument(
            'core_sim_file',
            default_value=os.path.join(
                get_package_share_directory('robot_flart'), 'config', 'example_flart_core_simulation.yaml'
            ),
            description='Path to core simulation plugins YAML (Default: example_flart_core_simulation.yaml)',
            condition=IfCondition(LaunchConfiguration('use_sim_time')),
        ),
        DeclareLaunchArgument(
            'extras_sim_file',
            default_value=os.path.join(
                get_package_share_directory('robot_flart'), 'config', 'example_flart_v0_simulation_extras.yaml'
            ),
            description='Path to v0 extras simulation plugins YAML (Default: example_flart_v0_simulation_extras.yaml)',
            condition=IfCondition(LaunchConfiguration('use_sim_time')),
        ),
        DeclareLaunchArgument(
            'node_options',
            default_value=rlh.default_node_options_str(),
            description=rlh.NODE_OPTIONS_DESC,
            condition=IfCondition(LaunchConfiguration('use_sim_time')),
        ),
        DeclareLaunchArgument(
            'logging_options',
            default_value=rlh.default_logging_options_str(),
            description=rlh.LOGGING_OPTIONS_DESC,
            condition=IfCondition(LaunchConfiguration('use_sim_time')),
        ),
        OpaqueFunction(function=launch_rosgz_bridge, condition=IfCondition(LaunchConfiguration('use_sim_time'))),
    ]

    return LaunchDescription(ldes)


def launch_rosgz_bridge(ctx: LaunchContext) -> List[LaunchDescriptionEntity]:
    """Create and launch the rosgz bridge node for the v0 profile."""
    ldes: List[LaunchDescriptionEntity] = []

    namespace = LaunchConfiguration('namespace').perform(ctx).strip()
    robot_name = LaunchConfiguration('robot_name').perform(ctx).strip()
    robot_ns = rlh.create_robot_namespace(namespace, robot_name)
    underscored_robot_ns = rlh.underscorify_namespace(robot_ns)

    rosgz_bridge_cfg, bridge_messages = rosgz_bridge_catalog_manager.build_bridge_config_for_robot_version(
        _ROBOT_VERSION,
        namespace,
        robot_name,
        {
            'core_sim_file': LaunchConfiguration('core_sim_file').perform(ctx).strip(),
            'extras_sim_file': LaunchConfiguration('extras_sim_file').perform(ctx).strip(),
        },
    )

    if not rosgz_bridge_cfg:
        if bridge_messages:
            return [LogInfo(msg=msg) for msg in bridge_messages]
        no_channels_msg = f'[{underscored_robot_ns}] Not launching rosgz_bridge node because no channels are enabled.'
        return [LogInfo(msg=no_channels_msg)]

    for bridge_msg in bridge_messages:
        ldes.append(LogInfo(msg=bridge_msg))

    ros_home = Path(os.environ.get('ROS_HOME', os.path.expanduser('~/.ros')))
    abs_path = ros_home.joinpath(f'{underscored_robot_ns}_rosgz_bridge.yaml')
    abs_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        with abs_path.open('w', encoding='utf-8') as stream:
            yaml.safe_dump(
                rosgz_bridge_cfg,
                stream=stream,
                sort_keys=False,
                default_flow_style=False,
                allow_unicode=True,
                width=120,
            )
    except Exception as exc:
        raise Exception(f"[{underscored_robot_ns}] Could not write rosgz_bridge config to '{abs_path}': {exc}") from exc

    parameters = []
    params_file = LaunchConfiguration('params_file').perform(ctx).strip()
    if params_file:
        parameters.append(ParameterFile(params_file, allow_substs=True))

    parameters_dict: Dict[str, Any] = {
        'use_sim_time': True,
        'config_file': str(abs_path),
        'expand_gz_topic_names': False,
        'override_timestamps_with_wall_time': False,
    }

    subscription_heartbeat = LaunchConfiguration('subscription_heartbeat').perform(ctx).strip()
    if subscription_heartbeat:
        parameters_dict['subscription_heartbeat'] = int(subscription_heartbeat)

    parameters.append(parameters_dict)

    node_options = rlh.process_node_options(LaunchConfiguration('node_options').perform(ctx))
    node_name = str(node_options['name']) or 'rosgz_bridge'

    ldes.append(
        Node(
            package='ros_gz_bridge',
            executable='bridge_node',
            name=node_name,
            namespace=robot_ns,
            parameters=parameters,
            ros_arguments=rlh.process_logging_options(LaunchConfiguration('logging_options').perform(ctx)),
            output=node_options['output'],
            emulate_tty=node_options['emulate_tty'],
            respawn=node_options['respawn'],
            respawn_delay=node_options['respawn_delay'],
        )
    )

    return ldes
