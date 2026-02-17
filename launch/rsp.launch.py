import os
from pathlib import Path
from typing import Any, Dict, List

import ros2_launch_helpers as rlh
from ament_index_python.packages import get_package_share_directory
from launch.actions import DeclareLaunchArgument, LogInfo, OpaqueFunction
from launch.substitutions import Command, FindExecutable, LaunchConfiguration
from launch.utilities.type_utils import normalize_typed_substitution, perform_typed_substitution
from launch_ros.actions import Node
from launch_ros.descriptions import ParameterFile, ParameterValue

from launch import LaunchContext, LaunchDescription, LaunchDescriptionEntity
from robot_flart import xacro_args as flart_xacro_args


def generate_launch_description():
    # ldes => (l)aunch (d)escription (e)ntitie(s)

    ldes = [
        DeclareLaunchArgument(
            'use_sim_time',
            default_value='False',
            choices=['True', 'true', 'False', 'false'],
            description='Use simulation clock if true',
        ),
        DeclareLaunchArgument('namespace', default_value='', description='namespace (Optional, default: "")'),
        DeclareLaunchArgument(
            'robot_version', default_value='core', description='Robot version to launch (default: core)'
        ),
        DeclareLaunchArgument('robot_name', default_value='flart_core', description='The unique name for the robot'),
        ########################################################################
        # Parameters
        ########################################################################
        DeclareLaunchArgument(
            'params_file',
            default_value=os.path.join(get_package_share_directory('robot_flart'), 'config', 'example_flart_core.yaml'),
            description='Base YAML with ros__parameters (Default: robot_flart/config/example_flart_core.yaml)',
        ),
        # Parameters 'publish_frequency' and 'ignore_timestamp' passed to the launch file override those set
        # in the parameter file.
        DeclareLaunchArgument(
            'publish_frequency',
            default_value='',
            description='Frequency of publication for robot_state_publisher (Optional, default: "")',
        ),
        DeclareLaunchArgument(
            'ignore_timestamp',
            default_value='',
            choices=['True', 'true', 'False', 'false', ''],
            description='If True, joint_state messages are accepted, no matter their timestamp '
            '(Optional, default: "" )',
        ),
        # Declare description arguments to pass to the xacro file.
        OpaqueFunction(function=flart_xacro_args.declare_launch_arguments),
        ########################################################################
        # Remappings, node options and logging options
        ########################################################################
        DeclareLaunchArgument('topic_remappings', default_value='', description=rlh.TOPIC_REMAPPINGS_DESC),
        DeclareLaunchArgument(
            'node_options', default_value=rlh.default_node_options_str(), description=rlh.NODE_OPTIONS_DESC
        ),
        DeclareLaunchArgument(
            'logging_options', default_value=rlh.default_logging_options_str(), description=rlh.LOGGING_OPTIONS_DESC
        ),
        #########################################################################
        # Others
        ########################################################################
        OpaqueFunction(function=launch_rsp),
    ]

    return LaunchDescription(ldes)


################################################################################
# Non-opaque functions
################################################################################

################################################################################
# Opaque functions
################################################################################


def launch_rsp(ctx: LaunchContext) -> List[LaunchDescriptionEntity]:
    namespace = LaunchConfiguration('namespace').perform(ctx).strip()
    robot_version = LaunchConfiguration('robot_version').perform(ctx).strip()
    robot_name = LaunchConfiguration('robot_name').perform(ctx).strip()
    robot_ns = rlh.create_robot_namespace(namespace, robot_name)
    underscored_robot_ns = rlh.underscorify_namespace(robot_ns)
    available_robot_versions = flart_xacro_args.get_robot_versions()

    if robot_version not in available_robot_versions:
        return [
            LogInfo(
                msg=f"[ERROR][{underscored_robot_ns}] Version '{robot_version}' for the 'flart' robot is not "
                f'available.  Available versions: {", ".join(available_robot_versions)}'
            )
        ]

    xacro_file = os.path.join(get_package_share_directory('robot_flart'), 'urdf', f'{robot_version}.xacro')

    if not Path(xacro_file).is_file():
        return [LogInfo(msg=f"[ERROR][{underscored_robot_ns}] File '{xacro_file}' not found")]

    # ldes => (l)aunch (d)escription (e)ntitie(s)
    ldes: List[LaunchDescriptionEntity] = []

    use_sim_time = perform_typed_substitution(
        ctx, normalize_typed_substitution(LaunchConfiguration('use_sim_time'), bool), bool
    )

    # If the application is running in real mode (use_sim_time = False), do not use simulation files.
    if not use_sim_time:
        # Propery way to pass empty string to xacro command in a programmatic way is '""', in CLI we would use "".
        core_sim_file = '""'
        extras_sim_file = '""'
    else:
        # The <xacro:arg> 'core_sim_file' is part of the 'core' version of the flart robot.
        # Every version of the flart robot beyond 'core' (v0, v1, ...) includes the core version and adds additional
        # features, like sensors, etc., therefore, the <xacro:arg> 'core_sim_file' is also part of those versions.
        core_sim_file = LaunchConfiguration('core_sim_file').perform(ctx).strip()

        if not core_sim_file:
            ldes.append(
                LogInfo(
                    msg=f"[WARNING][{underscored_robot_ns}] File 'core_sim_file' not provided. "
                    'No simulation plugins will be loaded for the base and fork'
                )
            )

            core_sim_file = '""'  # This is the proper way to pass empty string to xacro command in a programmatic way.
        elif not Path(core_sim_file).is_file():
            ldes.append(
                LogInfo(
                    msg=f"[WARNING][{underscored_robot_ns}] File 'core_sim_file' not found. "
                    'No simulation plugins will be loaded for the base and fork'
                )
            )

            core_sim_file = '""'  # This is the proper way to pass empty string to xacro command in a programmatic way.

        # If the robot version simulate extra devices apart from base and fork (like sensors, etc.), a field called
        # 'extras_sim_file' must be defined for that robot version in the 'xacro_args' module.
        # If the robot version does not define the 'extras_sim_file' argument, or the value passed to that argument is
        # empty, then no extra elements are simulated.
        if flart_xacro_args.has_xarg(robot_version, 'extras_sim_file'):
            extras_sim_file = LaunchConfiguration('extras_sim_file').perform(ctx).strip()

            if not extras_sim_file:
                ldes.append(
                    LogInfo(
                        msg=f"[WARNING][{underscored_robot_ns}] File 'extras_sim_file' not provided "
                        f'No extra simulation plugins will be loaded'
                    )
                )

                extras_sim_file = '""'  # This is the proper way to pass empty str to xacro cmd in a programmatic way.
            elif not Path(extras_sim_file).is_file():
                ldes.append(
                    LogInfo(
                        msg=f"[WARNING][{underscored_robot_ns}] File 'extras_sim_file' not found. "
                        'No simulation plugins will be loaded for the extra devices'
                    )
                )

                extras_sim_file = '""'  # This is the proper way to pass empty str to xacro cmd in a programmatic way.
        else:
            ldes.append(
                LogInfo(
                    msg=f"[WARNING][{underscored_robot_ns}] Version '{robot_version}' of the 'flart' robot does not "
                    'define extra simulation file'
                )
            )

            extras_sim_file = '""'  # This is the proper way to pass empty str to xacro cmd in a programmatic way.

    # Build xacro command to expand the xacro file of the robot with the given arguments.
    cmd = [
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

    # Add to 'cmd' the value for the '<xacro:args>' items the given robot version uses.
    for xarg_name in flart_xacro_args.get_xarg_names(robot_version):
        # Every version of the 'flart' robot uses the 'core_sim_file', so the variable 'core_sim_file' is always added
        # to 'cmd'.
        # The variable 'core_sim_file' may or may not be an empty string.
        # If the variable 'core_sim_file' is an empty string, no simulation plugins will be loaded for the base and
        # fork.
        if xarg_name == 'core_sim_file':
            value = core_sim_file
        # If the robot version does not use the 'extras_sim_file', the variable 'extras_sim_file' is not added to 'cmd'.
        # If the robot version uses extras_sim_file, the variable 'extras_sim_file' may or may not be an empty string.
        # If the variable 'extras_sim_file' is an empty string, no extra simulation plugins will be loaded.
        elif xarg_name == 'extras_sim_file':
            value = extras_sim_file
        else:
            raw_value = LaunchConfiguration(xarg_name).perform(ctx).strip()
            # If raw_value contains spaces or tabs, we need to quote it to avoid errors when the command xacro
            # is parsing the value.
            # ispace() checks for spaces, tabs, new lines, etc.
            value = f'"{raw_value}"' if any(ch.isspace() for ch in raw_value) else raw_value

        cmd.extend([' ', f'{xarg_name}:=', value])

    parameters = []

    params_file = LaunchConfiguration('params_file').perform(ctx).strip()

    # Add parameter file only if it's not empty.
    if params_file:
        parameters.append(ParameterFile(params_file, allow_substs=True))

    # Create a dictionary of parameters to be passed after the parameter file, so thay have precedence over
    # those defined in the parameter file.
    parameters_dict: Dict[str, Any] = {
        'use_sim_time': use_sim_time,
        'robot_description': ParameterValue(Command(cmd), value_type=str),
        # "DO NOT CHANGE THE VALUE OF 'frame_prefix', LEAVE IT AS AN EMPTY STRING. THE 'namespace' AND 'robot_name'
        # ARE PASSED TO THE XACRO FILE, AND THE XACRO FILE USES THEM TO CREATE THE PROPER FRAME PREFIXES.
        'frame_prefix': '',
        'use_robot_description_topic': False,  # We directly pass the robot_description parameter.
    }

    # If parameters 'publish_frequency' and 'ignore_timestamp' are set through the launch file, they override those set
    # in the parameter file.
    publish_frequency = LaunchConfiguration('publish_frequency').perform(ctx).strip()

    if publish_frequency:
        parameters_dict['publish_frequency'] = float(publish_frequency)

    ignore_timestamp = LaunchConfiguration('ignore_timestamp').perform(ctx).strip()

    if ignore_timestamp:
        parameters_dict['ignore_timestamp'] = bool(ignore_timestamp)

    parameters.append(parameters_dict)

    node_options = rlh.process_node_options(LaunchConfiguration('node_options').perform(ctx))
    node_name = str(node_options['name']) or 'robot_state_publisher'

    return [
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
    ]
