import os
import pkgutil
from importlib import import_module
from pathlib import Path
from typing import Any, Dict, List

import ros2_launch_helpers as rlh
import yaml
from ament_index_python.packages import get_package_share_directory
from launch.actions import DeclareLaunchArgument, GroupAction, LogInfo, OpaqueFunction
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterFile

from launch import LaunchContext, LaunchDescription, LaunchDescriptionEntity


def generate_launch_description() -> LaunchDescription:
    ldes: List[LaunchDescriptionEntity] = [
        DeclareLaunchArgument(
            'use_sim_time',
            default_value='False',
            choices=['True', 'true', 'False', 'false'],
            description='Use simulation clock if true',
        ),
        DeclareLaunchArgument(
            'robot_version', default_value='core', description='Robot version to launch bridge for (core, v1, ...)'
        ),
        DeclareLaunchArgument('namespace', default_value='', description='Namespace for all resources'),
        DeclareLaunchArgument('robot_name', default_value='fs3sw', description='The unique name for the robot'),
        ########################################################################
        # Parameters
        ########################################################################
        # 'params_file' and 'subscription_heartbeat' are parameters for the rosgz_bridge node.
        DeclareLaunchArgument(
            'params_file',
            default_value='',
            description='Path to params file. If empty, use default for selected robot_version.',
        ),
        DeclareLaunchArgument(
            'subscription_heartbeat', default_value='', description='Subscription heartbeat (Optional, default: "")'
        ),
        # Parameter to enable/disable channels in the rosgz_bridge node.
        DeclareLaunchArgument(
            'sim_file',
            default_value='',
            description='Path to simulation file. If empty, use default for selected robot_version.',
        ),
        DeclareLaunchArgument(
            'node_options', default_value=rlh.default_node_options_str(), description=rlh.NODE_OPTIONS_DESC
        ),
        DeclareLaunchArgument(
            'logging_options', default_value=rlh.default_logging_options_str(), description=rlh.LOGGING_OPTIONS_DESC
        ),
        GroupAction(
            condition=IfCondition(LaunchConfiguration('use_sim_time')),
            actions=[OpaqueFunction(function=_validate_robot_version), OpaqueFunction(function=_launch_rosgz_bridge)],
        ),
    ]

    return LaunchDescription(ldes)


def _get_available_rosgz_bridge_configurators() -> List[str]:
    """
    Return available rosgz_bridge configurators by listing modules in
    `robot_forklift_simple_3sw.rosgz_bridge_configurator_catalog`.
    """
    try:
        package = import_module('robot_forklift_simple_3sw.rosgz_bridge_configurator_catalog')
    except ModuleNotFoundError:
        return []

    package_paths = getattr(package, '__path__', None)

    if not package_paths:
        return []

    # List package modules and return their names as available configurators, ignoring private modules
    # (those starting with '_').
    return sorted(module.name for module in pkgutil.iter_modules(package_paths) if not module.name.startswith('_'))


def _get_default_params_file_for_robot_version(robot_version: str) -> str:
    """Return default params YAML path for a robot version using naming convention."""

    config_dir = Path(get_package_share_directory('robot_forklift_simple_3sw')).joinpath('config')
    candidate = config_dir.joinpath(f'example_{robot_version}.yaml')

    # If a version-specific params file does not exist, fall back to core params config.
    if candidate.is_file():
        return str(candidate)

    # If the specific params file for the robot version does not exist, return the default params file for the
    # 'core' version, since all robot versions should be compatible with the base bridge parameters.
    return str(config_dir.joinpath('example_core.yaml'))


def _get_default_sim_file_for_robot_version(robot_version: str) -> str:
    """Return default simulation YAML path for a robot version using naming convention."""

    config_dir = Path(get_package_share_directory('robot_forklift_simple_3sw')).joinpath('config')
    candidate = config_dir.joinpath(f'example_{robot_version}_simulation.yaml')

    # If a version-specific default does not exist, fall back to core simulation config.
    if candidate.is_file():
        return str(candidate)

    # If the specific sim file for the robot version does not exist, return the default sim file for the 'core'
    # version, since all the robot versions should be compatible with the 'core' simulation config (which only contains
    # channels for the base and fork of the robot, which are common to all versions).
    return str(config_dir.joinpath('example_core_simulation.yaml'))


def _get_parameters(ctx: LaunchContext, robot_version: str, config_file: str, underscored_robot_ns: str) -> List[Any]:
    """Build the parameter list for the rosgz_bridge node.

    The parameter file (if provided) is inserted first, and then launch-argument parameters
    are appended so they take precedence over same-name entries coming from the YAML file.
    """
    parameters: List[Any] = []
    input_params_file = LaunchConfiguration('params_file').perform(ctx).strip()
    params_file = input_params_file or _get_default_params_file_for_robot_version(robot_version)

    if params_file:
        parameters.append(ParameterFile(params_file, allow_substs=False))

    parameters_dict: Dict[str, Any] = {
        'use_sim_time': True,
        'config_file': config_file,
        # The configurator for rosgz_bridge already expands gz topic names to full names with the robot namespace,
        # so 'expand_gz_topic_names' is set to False to avoid re-expansion
        # topic names again.
        'expand_gz_topic_names': False,
        # Keep original Gazebo timestamps by setting 'override_timestamps_with_wall_time' to False.
        'override_timestamps_with_wall_time': False,
    }

    # Add the 'subscription_heartbeat' parameter only if it's provided as launch argument and it's a valid integer.
    subscription_heartbeat = LaunchConfiguration('subscription_heartbeat').perform(ctx).strip()
    if subscription_heartbeat:
        try:
            parameters_dict['subscription_heartbeat'] = int(subscription_heartbeat)
        except ValueError as exc:
            raise ValueError(
                f"[ERROR][{underscored_robot_ns}] Invalid 'subscription_heartbeat' value "
                f"'{subscription_heartbeat}'. Expected an integer."
            ) from exc

    parameters.append(parameters_dict)
    return parameters


def _get_rosgz_bridge_configurator(robot_version: str):
    """
    Resolve the function to create the rosgz_bridge config for the selected robot version from the configurator catalog.
    """

    if not robot_version:
        return None

    module_name = f'robot_forklift_simple_3sw.rosgz_bridge_configurator_catalog.{robot_version}'

    try:
        module = import_module(module_name)
    except ModuleNotFoundError as exc:
        # There are two different situations:
        # 1) The requested configurator module does not exist (version not supported): return None.
        # 2) The configurator module exists, but one of its internal imports is missing: re-raise.
        #    This is a real error that should not be masked as "version not available".
        if exc.name == module_name:
            return None
        raise

    # The contract of each configurator module is to expose a callable named `create_cfg`.
    create_cfg = getattr(module, 'create_cfg', None)

    return create_cfg if callable(create_cfg) else None


def _launch_rosgz_bridge(ctx: LaunchContext) -> List[LaunchDescriptionEntity]:
    """Create and launch the rosgz bridge node for the selected fs3sw profile."""

    robot_version = LaunchConfiguration('robot_version').perform(ctx).strip()
    namespace = LaunchConfiguration('namespace').perform(ctx).strip()
    robot_name = LaunchConfiguration('robot_name').perform(ctx).strip()
    robot_ns = rlh.create_robot_namespace(namespace, robot_name)
    underscored_robot_ns = rlh.underscorify_namespace(robot_ns)

    # Get the configurator function for the selected robot version from the catalog of configurators.
    # Each configurator is responsible for creating the rosgz_bridge config based on the selected robot version and the
    # provided simulation file, and returning any messages to log during the process (e.g. warnings about missing
    # channels or general info about which channels are being bridged).
    configurator = _get_rosgz_bridge_configurator(robot_version)

    if configurator is None:
        # If the configurator for the selected version is not found, log an error with the available configurators.
        available_configurators = ', '.join(_get_available_rosgz_bridge_configurators())

        return [
            LogInfo(
                msg=f"[ERROR][{underscored_robot_ns}] No rosgz_bridge configurator found for version '{robot_version}'."
                f' Available configurators: {available_configurators if available_configurators else "None"}'
            )
        ]

    input_sim_file = LaunchConfiguration('sim_file').perform(ctx).strip()
    sim_file = input_sim_file or _get_default_sim_file_for_robot_version(robot_version)

    cfg, msgs = configurator(sim_file, namespace, robot_name)

    ldes: List[LaunchDescriptionEntity] = rlh.to_log_info_entities(msgs)

    # If there is no config to launch the function must end.
    # If there are messages, those messages are in `ldes`, to return those messages.
    # If there are no messages, return a default message about no channels being enabled.
    if not cfg:
        if not msgs:
            return [
                LogInfo(
                    msg=f'[{underscored_robot_ns}] Not launching rosgz_bridge node because no channels are enabled.'
                )
            ]

        return ldes

    # The configuration for the rosgz_bridge node must be passed to the rosgz_bridge node via a YAML file up to
    # ROS2-Humble (starting in ROS2-Jazzy the configuration for the bridge can be passed via parameter).
    # Write the config to a YAML file in the ROS_HOME directory with the name
    # '<underscored_robot_ns>_rosgz_bridge.yaml' and then that file is passed to the rosgz_bridge node via the
    # 'config_file' parameter.
    ros_home = Path(os.environ.get('ROS_HOME', os.path.expanduser('~/.ros')))
    abs_path = ros_home.joinpath(f'{underscored_robot_ns}_rosgz_bridge.yaml')
    abs_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        with abs_path.open('w', encoding='utf-8') as stream:
            yaml.safe_dump(cfg, stream=stream, sort_keys=False, default_flow_style=False, allow_unicode=True, width=120)
    except Exception as exc:
        raise Exception(f"[{underscored_robot_ns}] Could not write rosgz_bridge config to '{abs_path}': {exc}") from exc

    parameters = _get_parameters(
        ctx=ctx, robot_version=robot_version, config_file=str(abs_path), underscored_robot_ns=underscored_robot_ns
    )

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


def _validate_robot_version(ctx: LaunchContext) -> List[LaunchDescriptionEntity]:
    """Fail fast if selected robot version has no rosgz bridge configurator."""
    robot_version = LaunchConfiguration('robot_version').perform(ctx).strip()
    available_configurators = _get_available_rosgz_bridge_configurators()

    if robot_version in available_configurators:
        return []

    raise ValueError(
        f"No rosgz_bridge configurator found for version '{robot_version}'. "
        f'Available configurators: {", ".join(available_configurators) if available_configurators else "None"}'
    )
