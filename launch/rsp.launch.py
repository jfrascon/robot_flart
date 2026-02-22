import os
from pathlib import Path
from typing import Any, Dict, List, Tuple

import ros2_launch_helpers as rlh
from ament_index_python.packages import get_package_share_directory
from launch.actions import DeclareLaunchArgument, OpaqueFunction
from launch.substitutions import Command, FindExecutable, LaunchConfiguration
from launch.utilities.type_utils import normalize_typed_substitution, perform_typed_substitution
from launch_ros.actions import Node
from launch_ros.descriptions import ParameterFile, ParameterValue

from launch import LaunchContext, LaunchDescription, LaunchDescriptionEntity
from robot_forklift_simple_3aw import xargs_catalog_manager


def generate_launch_description() -> LaunchDescription:
    """Build the launch description for robot_state_publisher across fs3aw versions."""
    ldes: List[LaunchDescriptionEntity] = [
        DeclareLaunchArgument(
            'use_sim_time',
            default_value='False',
            choices=['True', 'true', 'False', 'false'],
            description='Use simulation clock if true',
        ),
        DeclareLaunchArgument('namespace', default_value='', description='Namespace for all resources'),
        DeclareLaunchArgument('robot_version', default_value='core', description='Robot version to launch'),
        OpaqueFunction(function=_validate_selected_robot_version),
        DeclareLaunchArgument('robot_name', default_value='fs3aw', description='The unique name for the robot'),
        DeclareLaunchArgument(
            'params_file',
            default_value='',
            description='Path to params file. If empty, use default for selected robot_version.',
        ),
        DeclareLaunchArgument(
            'publish_frequency', default_value='', description='Frequency of publication for robot_state_publisher'
        ),
        DeclareLaunchArgument(
            'ignore_timestamp',
            default_value='',
            choices=['True', 'true', 'False', 'false', ''],
            description='If True, joint_state messages are accepted, no matter their timestamp',
        ),
        OpaqueFunction(function=_declare_xargs_launch_arguments_for_selected_version),
        DeclareLaunchArgument('topic_remappings', default_value='', description=rlh.TOPIC_REMAPPINGS_DESC),
        DeclareLaunchArgument(
            'node_options', default_value=rlh.default_node_options_str(), description=rlh.NODE_OPTIONS_DESC
        ),
        DeclareLaunchArgument(
            'logging_options', default_value=rlh.default_logging_options_str(), description=rlh.LOGGING_OPTIONS_DESC
        ),
        OpaqueFunction(function=_launch_rsp),
    ]

    return LaunchDescription(ldes)


def _build_xacro_command(ctx: LaunchContext) -> Tuple[List[Any], List[str]]:
    """Build the xacro command list and collect textual diagnostics for the selected version.

    Raises:
        FileNotFoundError: If the selected xacro file does not exist.
    """

    robot_version = LaunchConfiguration('robot_version').perform(ctx).strip()
    namespace = LaunchConfiguration('namespace').perform(ctx).strip()
    robot_name = LaunchConfiguration('robot_name').perform(ctx).strip()
    robot_ns = rlh.create_robot_namespace(namespace, robot_name)
    underscored_robot_ns = rlh.underscorify_namespace(robot_ns)

    xacro_file = os.path.join(
        get_package_share_directory('robot_forklift_simple_3aw'), 'urdf', f'{robot_version}.xacro'
    )

    if not Path(xacro_file).is_file():
        raise FileNotFoundError(f"[ERROR][{underscored_robot_ns}] File '{xacro_file}' not found")

    use_sim_time = perform_typed_substitution(
        ctx, normalize_typed_substitution(LaunchConfiguration('use_sim_time'), bool), bool
    )

    msgs: List[str] = []

    cmd: List[Any] = [
        FindExecutable(name='xacro'),
        ' ',
        xacro_file,
        ' use_sim_mode:=',
        LaunchConfiguration('use_sim_time'),
        ' namespace:=',
        LaunchConfiguration('namespace'),
        ' robot_name:=',
        LaunchConfiguration('robot_name'),
    ]

    for xarg_name in xargs_catalog_manager.get_resolved_xargs(robot_version).keys():
        # Get the value of the LaunchConfiguration for the xarg. The value might be a user-given value or the default
        # value from the catalog.
        raw_value = LaunchConfiguration(xarg_name).perform(ctx).strip()

        # The 'sim_file' xarg needs special handling because it is only relevant when 'use_sim_time' is true, and
        # specific warnings are logged when the file is missing or invalid in that mode.
        # For the remaining xargs, the value is only quoted when it contains whitespace.
        if xarg_name == 'sim_file':
            # If 'use_sim_time' is false, the value of 'sim_file' is ignored and set to an empty string, as the
            # simulation configuration is not relevant when not using simulation time. No warning is logged in
            # this case, as it is not an error to not provide a simulation file when not using simulation time.
            if not use_sim_time:
                value = '""'
            # If 'use_sim_time' is true, the value of 'sim_file' is validated. If it is missing or not found, a warning
            # is logged and the value is set to an empty string, meaning no simulation plugins are loaded. If valid, its
            # path is used as the value.
            elif not raw_value:
                msgs.append(
                    f"[WARNING][{underscored_robot_ns}] File 'sim_file' not provided. "
                    'No simulation plugins will be loaded'
                )
                value = '""'
            # Handling the case where the file is provided but not found separately to provide a more specific warning
            # message, as it is a common mistake to provide an incorrect path to the simulation file.
            elif not Path(raw_value).is_file():
                msgs.append(
                    f"[WARNING][{underscored_robot_ns}] File 'sim_file' not found. No simulation plugins will be loaded"
                )
                value = '""'
            # If 'use_sim_time' is true and the file is provided and found, its path is used for 'sim_file'.
            # The value is quoted only when it contains whitespace to keep xacro tokenization correct.
            else:
                value = _quote_if_needed(raw_value)
        # For the remaining xargs, quote only when whitespace is present so xacro parses one token.
        else:
            value = _quote_if_needed(raw_value)

        cmd.extend([' ', f'{xarg_name}:=', value])

    return cmd, msgs


def _declare_xargs_launch_arguments_for_selected_version(ctx: LaunchContext) -> List[LaunchDescriptionEntity]:
    """Declare xargs launch arguments for the selected robot version."""
    robot_version = LaunchConfiguration('robot_version').perform(ctx).strip()
    return xargs_catalog_manager.declare_launch_arguments_for_robot_version(robot_version)


def _get_default_params_file_for_robot_version(robot_version: str) -> str:
    """Return default params YAML path for a robot version using naming convention."""

    config_dir = Path(get_package_share_directory('robot_forklift_simple_3aw')).joinpath('config')
    candidate = config_dir.joinpath(f'example_{robot_version}.yaml')

    if candidate.is_file():
        return str(candidate)

    return str(config_dir.joinpath('example_core.yaml'))


def _get_parameters(ctx: LaunchContext) -> Tuple[List[Any], List[str]]:
    """Build the parameter list for robot_state_publisher.

    The function also builds the xacro command and returns textual diagnostics generated while
    validating simulation inputs.

    The parameter file (if provided) is inserted first, and then launch-argument parameters
    are appended so they take precedence over same-name entries coming from the YAML file.

    Raises:
        FileNotFoundError: Propagated if the selected xacro file does not exist.
        ValueError: If `publish_frequency` is provided but is not a real number.
    """
    robot_version = LaunchConfiguration('robot_version').perform(ctx).strip()
    namespace = LaunchConfiguration('namespace').perform(ctx).strip()
    robot_name = LaunchConfiguration('robot_name').perform(ctx).strip()
    robot_ns = rlh.create_robot_namespace(namespace, robot_name)
    underscored_robot_ns = rlh.underscorify_namespace(robot_ns)

    cmd, msgs = _build_xacro_command(ctx=ctx)

    parameters: List[Any] = []
    input_params_file = LaunchConfiguration('params_file').perform(ctx).strip()
    params_file = input_params_file or _get_default_params_file_for_robot_version(robot_version)

    if params_file:
        parameters.append(ParameterFile(params_file, allow_substs=False))

    use_sim_time = perform_typed_substitution(
        ctx, normalize_typed_substitution(LaunchConfiguration('use_sim_time'), bool), bool
    )

    parameters_dict: Dict[str, Any] = {
        'use_sim_time': use_sim_time,
        'robot_description': ParameterValue(Command(cmd), value_type=str),
        # This field is intentionally kept empty.
        # Frame prefixes are generated directly inside the xacro using namespace and robot_name.
        'frame_prefix': '',
        # Robot description is obtained by processing the xacro file for the selected robot version with the
        # appropriate xargs.
        'use_robot_description_topic': False,
    }

    publish_frequency = LaunchConfiguration('publish_frequency').perform(ctx).strip()

    if publish_frequency:
        try:
            parameters_dict['publish_frequency'] = float(publish_frequency)
        except ValueError as exc:
            raise ValueError(
                f"[ERROR][{underscored_robot_ns}] Invalid 'publish_frequency' value "
                f"'{publish_frequency}'. Expected a real number."
            ) from exc

    ignore_timestamp = LaunchConfiguration('ignore_timestamp').perform(ctx).strip()

    if ignore_timestamp:
        # Transform to bool. The parameter `ignore_timestamp` can only have the values 'True', 'true', 'False', 'false'
        # or '', so if it is not empty, it can be treated as a valid boolean value.
        ignore_timestamp = perform_typed_substitution(
            ctx, normalize_typed_substitution(LaunchConfiguration('ignore_timestamp'), bool), bool
        )
        parameters_dict['ignore_timestamp'] = ignore_timestamp

    parameters.append(parameters_dict)

    return parameters, msgs


def _launch_rsp(ctx: LaunchContext) -> List[LaunchDescriptionEntity]:
    """Launch robot_state_publisher for the selected fs3aw robot version."""

    namespace = LaunchConfiguration('namespace').perform(ctx).strip()
    robot_name = LaunchConfiguration('robot_name').perform(ctx).strip()
    robot_ns = rlh.create_robot_namespace(namespace, robot_name)

    ldes: List[LaunchDescriptionEntity] = []

    parameters, msgs = _get_parameters(ctx=ctx)
    ldes.extend(rlh.to_log_info_entities(msgs))

    node_options = rlh.process_node_options(LaunchConfiguration('node_options').perform(ctx))
    node_name = str(node_options['name']) or 'robot_state_publisher'

    ldes.append(
        Node(
            package='robot_state_publisher',
            executable='robot_state_publisher',
            name=node_name,
            namespace=robot_ns,
            parameters=parameters,
            remappings=rlh.process_topic_remappings(LaunchConfiguration('topic_remappings').perform(ctx)),
            ros_arguments=rlh.process_logging_options(LaunchConfiguration('logging_options').perform(ctx)),
            output=node_options['output'],
            emulate_tty=node_options['emulate_tty'],
            respawn=node_options['respawn'],
            respawn_delay=node_options['respawn_delay'],
        )
    )

    return ldes


def _quote_if_needed(raw_value: str) -> str:
    """Quote values containing whitespace so xacro parses them as one token."""
    return f'"{raw_value}"' if any(ch.isspace() for ch in raw_value) else raw_value


def _validate_selected_robot_version(ctx: LaunchContext) -> List[LaunchDescriptionEntity]:
    """Fail fast if selected robot version is not supported by the xargs catalog."""
    robot_version = LaunchConfiguration('robot_version').perform(ctx).strip()
    available_robot_versions = xargs_catalog_manager.get_robot_versions()

    if robot_version in available_robot_versions:
        return []

    raise ValueError(
        f"Version '{robot_version}' for the 'fs3aw' robot is not available. "
        f'Available versions: {", ".join(available_robot_versions)}'
    )
