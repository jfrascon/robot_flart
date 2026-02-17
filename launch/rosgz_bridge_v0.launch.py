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
from robot_flart import rosgz_bridge_core_cfg_builder, rosgz_bridge_v0_cfg_builder  # noqa: F401


def generate_launch_description():
    # ldes -> (l)aunch (d)escription (e)ntitie(s)
    ldes = [
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
        ########################################################################
        # Parameters
        ########################################################################
        # 'params_file' and 'subscription_heartbeat' are parameters for the rosgz_bridge node.
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
        # Parameter to enable/disable channels in the rosgz_bridge node.
        DeclareLaunchArgument(
            'core_sim_file',
            default_value=os.path.join(
                get_package_share_directory('robot_flart'), 'config', 'example_flart_core_simulation.yaml'
            ),
            description=(
                'Path to the simulation file for the base and fork of the flart robot '
                '(Default: example_flart_core_simulation.yaml)'
            ),
            condition=IfCondition(LaunchConfiguration('use_sim_time')),
        ),
        DeclareLaunchArgument(
            'extras_sim_file',
            default_value=os.path.join(
                get_package_share_directory('robot_flart'), 'config', 'example_flart_v0_simulation_extras.yaml'
            ),
            description=(
                "Path to the simulation file for the extra elements in the 'v0' version of the flart robot "
                '(Default: example_flart_v0_simulation_extras.yaml)'
            ),
            condition=IfCondition(LaunchConfiguration('use_sim_time')),
        ),
        ########################################################################
        # Node and logging options
        ########################################################################
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
        #########################################################################
        # Others
        ########################################################################
        # rosgz_bridge node is only launched if 'use_sim_time' is true, otherwise it is not needed.
        OpaqueFunction(function=launch_rosgz_bridge, condition=IfCondition(LaunchConfiguration('use_sim_time'))),
    ]

    return LaunchDescription(ldes)


################################################################################
# Opaque functions.
################################################################################


def launch_rosgz_bridge(ctx: LaunchContext) -> list[LaunchDescriptionEntity]:
    # ldes := (l)aunch (d)escription (e)ntitie(s) to return.
    ldes: List[LaunchDescriptionEntity] = []

    namespace = LaunchConfiguration('namespace').perform(ctx).strip()
    robot_name = LaunchConfiguration('robot_name').perform(ctx).strip()
    robot_ns = rlh.create_robot_namespace(namespace, robot_name)
    underscored_robot_ns = rlh.underscorify_namespace(robot_ns)

    # Create the configuration for the rosgz_bridge_core for this robot.
    rosgz_bridge_core_cfg, core_msg = rosgz_bridge_core_cfg_builder.create_cfg(
        LaunchConfiguration('core_sim_file').perform(ctx).strip(), namespace, robot_name
    )
    rosgz_bridge_extras_cfg, extras_msg = rosgz_bridge_v0_cfg_builder.create_cfg(
        LaunchConfiguration('extras_sim_file').perform(ctx).strip(), namespace, robot_name
    )

    if not rosgz_bridge_core_cfg and not rosgz_bridge_extras_cfg:
        # If both configurations are empty, log both messages and do not launch the bridge.
        return [
            LogInfo(msg=f'[{underscored_robot_ns}] {core_msg}'),
            LogInfo(msg=f'[{underscored_robot_ns}] {extras_msg}'),
        ]
    elif not rosgz_bridge_core_cfg:
        # If only the core configuration is empty, log its message.
        # The extras configuration is not empty, so we can proceed.
        ldes.append(LogInfo(msg=f'[{underscored_robot_ns}] {core_msg}'))
        rosgz_bridge_cfg = rosgz_bridge_extras_cfg
    elif not rosgz_bridge_extras_cfg:
        # If only the extras configuration is empty, log its message.
        # The core configuration is not empty, so we can proceed.
        ldes.append(LogInfo(msg=f'[{underscored_robot_ns}] {extras_msg}'))
        rosgz_bridge_cfg = rosgz_bridge_core_cfg
    else:
        # Both configurations are not empty, combine them.
        rosgz_bridge_cfg = rosgz_bridge_core_cfg + rosgz_bridge_extras_cfg

    # In ROS2-Humble, the only way to pass to the 'bridge_node' the channels is by using the parameter 'config_file'
    # that points to a YAML file with the channels definition.
    # Write the configuration for the rosgz_bridge for this robot into a file, so we can pass it to the
    # 'bridge_node' binary in the 'config_file' parameter.
    ros_home = Path(os.environ.get('ROS_HOME', os.path.expanduser('~/.ros')))
    abs_path = ros_home.joinpath(underscored_robot_ns + '_rosgz_bridge.yaml')
    abs_path.parent.mkdir(parents=True, exist_ok=True)  # Ensure the directory exists.

    try:
        with abs_path.open('w', encoding='utf-8') as f:
            yaml.safe_dump(
                rosgz_bridge_cfg, stream=f, sort_keys=False, default_flow_style=False, allow_unicode=True, width=120
            )
    except Exception as e:
        raise Exception(
            f"[{underscored_robot_ns}] Could not write rosgz_bridge config to file '{abs_path}': {e}"
        ) from e

    parameters = []
    params_file = LaunchConfiguration('params_file').perform(ctx).strip()

    # Add parameter file only if it's not empty.
    if params_file:
        parameters.append(ParameterFile(params_file, allow_substs=True))

    # This parameter dictionary will be added to the parameters list after the parameter file, so its values
    # override any duplicated ones in the parameter file.
    parameters_dict: Dict[str, Any] = {
        'use_sim_time': True,  # If here we are in simulation mode.
        'config_file': str(abs_path),
        # We are building the full topics, with namespace and all, so we do not want the bridge
        # to expand them.
        'expand_gz_topic_names': False,
        # The parameter `override_timestamps_with_wall_time` controls how the `header.stamp` field is set
        # in messages bridged from Gazebo to ROS 2.
        # - If set to 'true', the bridge will overwrite the original timestamp with the current system wall
        #   time, meaning the actual time according to the operating system clock (e.g., what you get with
        #   'date' in a terminal), at the moment the message is forwarded.
        #   This means the message will reflect the real-world time of the host machine, not the simulation
        #   time from Gazebo.
        # - If set to 'false', the bridge will preserve the original timestamp from the source message
        #   (e.g., Gazebo simulation time).
        #   This is recommended when you are also bridging the '/clock' topic from Gazebo to ROS 2 and
        #   using 'use_sim_time: true' in your ROS 2 nodes, so that all messages and nodes are synchronized
        #   to the same simulation time reference.
        'override_timestamps_with_wall_time': False,
    }

    # If 'subscription_heartbeat' is set in the launch file, it has priority over the one that could be set in
    # the parameter file.
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
            # remappings not needed here.
            ros_arguments=rlh.process_logging_options(LaunchConfiguration('logging_options').perform(ctx)),
            output=node_options['output'],
            emulate_tty=node_options['emulate_tty'],
            respawn=node_options['respawn'],
            respawn_delay=node_options['respawn_delay'],
        )
    )

    return ldes
