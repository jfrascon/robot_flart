import os
from pathlib import Path
from typing import Any, Dict, List, Tuple

import ros2_launch_helpers as rlh
from ament_index_python.packages import get_package_share_directory
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, OpaqueFunction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import Command, FindExecutable, LaunchConfiguration, PathJoinSubstitution
from launch.utilities.type_utils import normalize_typed_substitution, perform_typed_substitution
from launch_ros.actions import Node
from launch_ros.descriptions import ParameterFile, ParameterValue
from launch_ros.substitutions import FindPackageShare

from launch import LaunchContext, LaunchDescription, LaunchDescriptionEntity
from robot_forklift_simple_3sw import robot_model_utils


def generate_launch_description() -> LaunchDescription:
    """Build the unified launch description for all fs3sw robot models."""
    ldes: list[LaunchDescriptionEntity] = [
        DeclareLaunchArgument(
            'use_sim_time',
            default_value='False',
            choices=['True', 'true', 'False', 'false'],
            description='Use simulation clock if true',
        ),
        DeclareLaunchArgument('namespace', default_value='', description='Namespace for all resources'),
        DeclareLaunchArgument(
            'robot_model', default_value='core', description='Robot model to launch (for example: core, v1)'
        ),
        DeclareLaunchArgument('robot_name', default_value='fs3sw', description='The unique name for the robot'),
        DeclareLaunchArgument(
            'params_file',
            default_value='',
            description='Path to params file. If empty, each included launch picks default by robot_model.',
        ),
        DeclareLaunchArgument(
            'bridge_file',
            default_value='',
            description='Path to bridge file. If empty, the bridge launch picks default by robot_model.',
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
        DeclareLaunchArgument(
            'subscription_heartbeat',
            default_value='',
            description='Subscription heartbeat for the bridge node (optional).',
        ),
        OpaqueFunction(function=_declare_model_launch_arguments),
    ]

    ldes.extend(_declare_topic_remappings())
    ldes.extend(_declare_node_options())
    ldes.extend(_declare_logging_options())
    ldes.extend(
        [
            OpaqueFunction(function=_launch_rsp),
            OpaqueFunction(function=_launch_bridge),
            OpaqueFunction(function=_include_three_swerve_kinematics),
        ]
    )

    return LaunchDescription(ldes)


def _build_xacro_command(ctx: LaunchContext) -> Tuple[List[Any], List[str]]:
    """Build the xacro command list and collect diagnostics for the selected model."""
    robot_model = LaunchConfiguration('robot_model').perform(ctx).strip()
    namespace = LaunchConfiguration('namespace').perform(ctx).strip()
    robot_name = LaunchConfiguration('robot_name').perform(ctx).strip()
    robot_ns = rlh.create_robot_namespace(namespace, robot_name)

    xacro_file = os.path.join(get_package_share_directory('robot_forklift_simple_3sw'), 'urdf', f'{robot_model}.xacro')

    if not Path(xacro_file).is_file():
        raise FileNotFoundError(_tagged_msg(robot_ns, 'ERROR', f"File '{xacro_file}' not found"))

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

    # Iterate through the model launch arguments defined by the selected robot
    # model and append them to the xacro command. Collect any diagnostic
    # messages along the way.
    for xarg_name in robot_model_utils.get_xargs(robot_model).keys():
        value = LaunchConfiguration(xarg_name).perform(ctx).strip()

        if xarg_name == 'sim_file':
            # The xacro only needs a simulation file when simulation is enabled.
            # If use_sim_time is false, force sim_file to '' so no simulation
            # plugins are loaded.
            # If use_sim_time is true and the user did not provide a sim_file,
            # use the example simulation file for the selected robot model.
            # If the user did provide a sim_file, resolve it to an absolute path.
            # If the final path does not exist, warn and fall back to '' so the
            # robot can still be expanded without simulation plugins.
            if not use_sim_time:
                value = ''
            elif not value:
                config_dir = Path(get_package_share_directory('robot_forklift_simple_3sw')).joinpath('config')
                value = str(config_dir.joinpath(f'example_{robot_model}_simulation.yaml'))
            else:
                value = rlh.resolve_file(value)

            if value and not Path(value).is_file():
                msgs.append(
                    _tagged_msg(
                        robot_ns,
                        'WARNING',
                        f"File '{xarg_name}' not found. No simulation plugins will be loaded for that robot part",
                    )
                )
                value = ''

        cmd.extend([' ', f'{xarg_name}:=', _quote_xarg_value_if_needed(value)])

    return cmd, msgs


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
            'bridge_logging_options',
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
            'bridge_options', default_value=rlh.default_node_options_str(), description=rlh.NODE_OPTIONS_DESC
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


def _declare_model_launch_arguments(ctx: LaunchContext) -> List[LaunchDescriptionEntity]:
    """Declare the model launch arguments for the selected robot model."""
    robot_model = LaunchConfiguration('robot_model').perform(ctx).strip()
    available_robot_models = robot_model_utils.get_robot_models()

    if robot_model not in available_robot_models:
        raise ValueError(
            f"Model '{robot_model}' for the 'forklift_simple_3sw' robot is not available. "
            f'Available robot models: {", ".join(available_robot_models)}'
        )

    available_xargs_models = robot_model_utils.get_robot_models_with_xargs()

    if robot_model not in available_xargs_models:
        raise ValueError(
            f"Model '{robot_model}' for the 'fs3sw' robot has no model argument configuration. "
            'Available robot models with model arguments: '
            f'{", ".join(available_xargs_models)}'
        )

    return robot_model_utils.declare_launch_arguments(robot_model)


def _include_three_swerve_kinematics(ctx: LaunchContext) -> List[LaunchDescriptionEntity]:
    """Include the three-swerve kinematics launch for this robot instance."""
    robot_model = LaunchConfiguration('robot_model').perform(ctx).strip()
    input_params_file = LaunchConfiguration('params_file').perform(ctx).strip()

    # If the user provided a params file via the 'params_file' launch argument, use it for the
    # kinematics node. Otherwise, look for a default params file based on the robot model under
    # the config directory. For example, if the robot model is "v1", look for
    # "config/example_v1.yaml".

    if input_params_file:
        params_file = Path(input_params_file)
    else:
        config_dir = Path(get_package_share_directory('robot_forklift_simple_3sw')).joinpath('config')
        params_file = config_dir.joinpath(f'example_{robot_model}.yaml')

    if not params_file.is_file():
        raise FileNotFoundError(
            f"Params file '{params_file}' does not exist for robot model '{robot_model}'. "
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


def _launch_rsp(ctx: LaunchContext) -> List[LaunchDescriptionEntity]:
    """Launch robot_state_publisher for the selected fs3sw robot model."""
    robot_model = LaunchConfiguration('robot_model').perform(ctx).strip()
    namespace = LaunchConfiguration('namespace').perform(ctx).strip()
    robot_name = LaunchConfiguration('robot_name').perform(ctx).strip()
    robot_ns = rlh.create_robot_namespace(namespace, robot_name)
    ldes: List[LaunchDescriptionEntity] = []

    cmd, msgs = _build_xacro_command(ctx)
    # Log messages collected during xacro command construction, if any.
    ldes.extend(rlh.to_log_info_actions(msgs))

    parameters: List[Any] = []
    input_params_file = LaunchConfiguration('params_file').perform(ctx).strip()

    if input_params_file:
        params_file = Path(input_params_file)
    else:
        config_dir = Path(get_package_share_directory('robot_forklift_simple_3sw')).joinpath('config')
        params_file = config_dir.joinpath(f'example_{robot_model}.yaml')

    if not params_file.is_file():
        raise FileNotFoundError(
            f"Params file '{params_file}' does not exist. "
            f"Please provide a valid params file via the 'params_file' launch argument."
        )

    parameters.append(ParameterFile(str(params_file), allow_substs=False))

    use_sim_time = perform_typed_substitution(
        ctx, normalize_typed_substitution(LaunchConfiguration('use_sim_time'), bool), bool
    )

    parameters_dict: Dict[str, Any] = {
        'use_sim_time': use_sim_time,
        'robot_description': ParameterValue(Command(cmd), value_type=str),
        'frame_prefix': '',
        'use_robot_description_topic': False,
    }

    publish_frequency = LaunchConfiguration('publish_frequency').perform(ctx).strip()

    if publish_frequency:
        try:
            parameters_dict['publish_frequency'] = float(publish_frequency)
        except ValueError as exc:
            raise ValueError(
                _tagged_msg(
                    robot_ns,
                    'ERROR',
                    f"Invalid 'publish_frequency' value '{publish_frequency}'. Expected a real number.",
                )
            ) from exc

    ignore_timestamp = LaunchConfiguration('ignore_timestamp').perform(ctx).strip()

    if ignore_timestamp:
        ignore_timestamp = perform_typed_substitution(
            ctx, normalize_typed_substitution(LaunchConfiguration('ignore_timestamp'), bool), bool
        )
        parameters_dict['ignore_timestamp'] = ignore_timestamp

    parameters.append(parameters_dict)

    node_options = rlh.process_node_options(LaunchConfiguration('rsp_options').perform(ctx))
    node_name = str(node_options['name']) or 'robot_state_publisher'

    ldes.append(
        Node(
            package='robot_state_publisher',
            executable='robot_state_publisher',
            name=node_name,
            namespace=robot_ns,
            parameters=parameters,
            remappings=rlh.process_topic_remappings(LaunchConfiguration('rsp_topic_remappings').perform(ctx)),
            ros_arguments=rlh.process_logging_options(LaunchConfiguration('rsp_logging_options').perform(ctx)),
            output=node_options['output'],
            emulate_tty=node_options['emulate_tty'],
            respawn=node_options['respawn'],
            respawn_delay=node_options['respawn_delay'],
        )
    )

    return ldes


def _launch_bridge(ctx: LaunchContext) -> List[LaunchDescriptionEntity]:
    """Launch the Gazebo bridge for the selected fs3sw robot model."""
    use_sim_time = perform_typed_substitution(
        ctx, normalize_typed_substitution(LaunchConfiguration('use_sim_time'), bool), bool
    )

    if not use_sim_time:
        return []

    robot_model = LaunchConfiguration('robot_model').perform(ctx).strip()
    namespace = LaunchConfiguration('namespace').perform(ctx).strip()
    robot_name = LaunchConfiguration('robot_name').perform(ctx).strip()
    robot_ns = rlh.create_robot_namespace(namespace, robot_name)
    available_robot_models = robot_model_utils.get_robot_models()

    if robot_model not in available_robot_models:
        raise ValueError(
            f"Model '{robot_model}' for the 'forklift_simple_3sw' robot is not available. "
            f'Available robot models: {", ".join(available_robot_models)}'
        )

    bridge_file = LaunchConfiguration('bridge_file').perform(ctx).strip()

    if not bridge_file:
        bridge_file = str(
            Path(get_package_share_directory('robot_forklift_simple_3sw')).joinpath(
                'config', f'example_{robot_model}_bridge.yaml'
            )
        )

    if not Path(bridge_file).is_file():
        raise FileNotFoundError(_tagged_msg(robot_ns, 'ERROR', f"Bridge file '{bridge_file}' not found."))

    parameters: List[Any] = []
    input_params_file = LaunchConfiguration('params_file').perform(ctx).strip()

    if input_params_file:
        params_file = Path(input_params_file)
    else:
        config_dir = Path(get_package_share_directory('robot_forklift_simple_3sw')).joinpath('config')
        params_file = config_dir.joinpath(f'example_{robot_model}.yaml')

    if not params_file.is_file():
        raise FileNotFoundError(_tagged_msg(robot_ns, 'ERROR', f"Params file '{params_file}' not found."))

    parameters.append(ParameterFile(str(params_file), allow_substs=False))

    parameters_dict: Dict[str, Any] = {
        'use_sim_time': True,
        'config_file': str(bridge_file),
        'expand_gz_topic_names': True,
        # Keep original Gazebo timestamps instead of replacing them with wall time.
        'override_timestamps_with_wall_time': False,
    }

    subscription_heartbeat = LaunchConfiguration('subscription_heartbeat').perform(ctx).strip()

    if subscription_heartbeat:
        try:
            parameters_dict['subscription_heartbeat'] = int(subscription_heartbeat)
        except ValueError as exc:
            raise ValueError(
                _tagged_msg(
                    robot_ns,
                    'ERROR',
                    f"Invalid 'subscription_heartbeat' value '{subscription_heartbeat}'. Expected an integer.",
                )
            ) from exc

    parameters.append(parameters_dict)

    node_options = rlh.process_node_options(LaunchConfiguration('bridge_options').perform(ctx))
    node_name = str(node_options['name']) or 'bridge'

    return [
        Node(
            package='ros_gz_bridge',
            executable='bridge_node',
            name=node_name,
            namespace=robot_ns,
            parameters=parameters,
            ros_arguments=rlh.process_logging_options(LaunchConfiguration('bridge_logging_options').perform(ctx)),
            output=node_options['output'],
            emulate_tty=node_options['emulate_tty'],
            respawn=node_options['respawn'],
            respawn_delay=node_options['respawn_delay'],
        )
    ]


def _tagged_msg(robot_ns: str, level: str, message: str) -> str:
    """Build one message tagged with the log level and the robot namespace."""
    return f'[{level}][{robot_ns}] {message}'


def _quote_xarg_value_if_needed(raw_value: str) -> str:
    """Quote xarg values containing whitespace so xacro parses them as one token."""
    return f'"{raw_value}"' if any(ch.isspace() for ch in raw_value) else raw_value
