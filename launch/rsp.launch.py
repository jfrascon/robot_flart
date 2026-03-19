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
from robot_forklift_simple_3sw import xargs


def generate_launch_description() -> LaunchDescription:
    """Build the launch description for robot_state_publisher across fs3sw versions."""
    ldes: List[LaunchDescriptionEntity] = [
        DeclareLaunchArgument(
            'use_sim_time',
            default_value='False',
            choices=['True', 'true', 'False', 'false'],
            description='Use simulation clock if true',
        ),
        DeclareLaunchArgument('namespace', default_value='', description='Namespace for all resources'),
        DeclareLaunchArgument('robot_version', default_value='core', description='Robot version to launch'),
        DeclareLaunchArgument('robot_name', default_value='fs3sw', description='The unique name for the robot'),
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
        OpaqueFunction(function=_declare_xargs),
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
    # Example: if robot_ns is /myns/my_robot, underscored_robot_ns will be myns_my_robot.
    underscored_robot_ns = rlh.underscorify_namespace(robot_ns)

    xacro_file = os.path.join(
        get_package_share_directory('robot_forklift_simple_3sw'), 'urdf', f'{robot_version}.xacro'
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

    for xarg_name in xargs.get_xargs(robot_version).keys():
        # Get the value associated to the key `xarg_name` used to declare the launch argument for
        # that xarg.
        # The value might be a user-given value or the default value from the catalog.
        value = LaunchConfiguration(xarg_name).perform(ctx).strip()

        if xarg_name == 'sim_file':
            # If the app is running in non-sim mode, plugins in the xacro file are not used, so
            # value = ''.
            if not use_sim_time:
                value = ''
            # If the app is running in sim mode but the user did not provide a value for the
            # sim_file xarg, use the default sim file for that robot version.
            elif not value:
                config_dir = Path(get_package_share_directory('robot_forklift_simple_3sw')).joinpath('config')
                value = str(config_dir.joinpath(f'example_{robot_version}_simulation.yaml'))
            # If the app is running in sim mode and the user provided a value for the sim_file xarg,
            # use it as is, after resolving it in case it is a relative path.
            else:
                value = rlh.resolve_file(value)

            # If the app is running in sim mode, there should be a sim file, either provided by the
            # user or the default one. Warn the user if the sim file does not exist, and in that
            # case do not use any sim file.
            if value and not Path(value).is_file():
                msgs.append(
                    f"[WARNING][{underscored_robot_ns}] File '{xarg_name}' not found. "
                    'No simulation plugins will be loaded for that robot part'
                )
                value = ''
        elif xarg_name == 'bridge_file':
            if not use_sim_time:
                value = ''
            elif not value:
                config_dir = Path(get_package_share_directory('robot_forklift_simple_3sw')).joinpath('config')
                value = str(config_dir.joinpath(f'example_{robot_version}_bridge.yaml'))
            else:
                value = rlh.resolve_file(value)

            if value and not Path(value).is_file():
                msgs.append(
                    f"[WARNING][{underscored_robot_ns}] File '{xarg_name}' not found. "
                    'Default Gazebo plugin topics will be used'
                )
                value = ''

        cmd.extend([' ', f'{xarg_name}:=', _quote_if_needed(value)])

    return cmd, msgs


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


def _launch_rsp(ctx: LaunchContext) -> List[LaunchDescriptionEntity]:
    """Launch robot_state_publisher for the selected fs3sw robot version."""

    robot_version = LaunchConfiguration('robot_version').perform(ctx).strip()
    namespace = LaunchConfiguration('namespace').perform(ctx).strip()
    robot_name = LaunchConfiguration('robot_name').perform(ctx).strip()
    robot_ns = rlh.create_robot_namespace(namespace, robot_name)
    # Example: if robot_ns is /myns/my_robot, underscored_robot_ns will be myns_my_robot.
    underscored_robot_ns = rlh.underscorify_namespace(robot_ns)

    ldes: List[LaunchDescriptionEntity] = []

    cmd, msgs = _build_xacro_command(ctx)
    ldes.extend(rlh.to_log_info_actions(msgs))

    # Build parameters to pass to the node.
    parameters: List[Any] = []
    input_params_file = LaunchConfiguration('params_file').perform(ctx).strip()

    if input_params_file:
        params_file = Path(input_params_file)
    else:
        config_dir = Path(get_package_share_directory('robot_forklift_simple_3sw')).joinpath('config')
        params_file = config_dir.joinpath(f'example_{robot_version}.yaml')

    if not params_file.is_file():
        raise FileNotFoundError(
            f"Params file '{params_file}' does not exist. "
            f"Please provide a valid params file via the 'params_file' launch argument."
        )

    # allow_substs=False since there are no substitutions affecting the parameters for the
    # robot_state_publisher node.
    parameters.append(ParameterFile(str(params_file), allow_substs=False))

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
