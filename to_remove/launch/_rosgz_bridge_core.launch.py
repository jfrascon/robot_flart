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
from launch_ros.descriptions import ParameterFile

from launch import LaunchContext, LaunchDescription, LaunchDescriptionEntity
from robot_forklift_simple_3aw import _rosgz_bridge_core_cfg_builder


def generate_launch_description():
    # ldes -> (l)aunch (d)escription (e)ntitie(s)
    # Once the use_sim_time argument is added, the rest of the Actions are only added if use_sim_time is true.
    ldes = [
        DeclareLaunchArgument(
            'use_sim_time',
            default_value='False',
            choices=['True', 'true', 'False', 'false'],
            description='use simulation clock if true',
        ),
        DeclareLaunchArgument(
            'namespace',
            default_value='',
            description='Namespace for all resources',
            condition=IfCondition(LaunchConfiguration('use_sim_time')),
        ),
        DeclareLaunchArgument(
            'robot_name',
            default_value='fs3aw',
            description='The unique name for the robot',
            condition=IfCondition(LaunchConfiguration('use_sim_time')),
        ),
        ########################################################################
        # Parameters
        ########################################################################
        # 'params_file' and 'subscription_heartbeat' are parameters for the rosgz_bridge node.
        DeclareLaunchArgument(
            'params_file',
            default_value=os.path.join(
                get_package_share_directory('robot_forklift_simple_3aw'), 'config', 'example_fs3aw_core.yaml'
            ),
            description='Base YAML with ros__parameters (Default: example_fs3aw_core.yaml)',
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
                get_package_share_directory('robot_forklift_simple_3aw'), 'config', 'example_fs3aw_core_simulation.yaml'
            ),
            description=(
                "Path to the simulation file for the 'core' version of the fs3aw robot "
                '(Default: example_fs3aw_core_simulation.yaml)'
            ),
            condition=IfCondition(LaunchConfiguration('use_sim_time')),
        ),
        ################################################################################
        # Node and logging options
        ################################################################################
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
        ################################################################################
        # Others
        ################################################################################
        # rosgz_bridge node is only launched if 'use_sim_time' is true, otherwise it is not needed.
        OpaqueFunction(function=launch_rosgz_bridge, condition=IfCondition(LaunchConfiguration('use_sim_time'))),
    ]

    return LaunchDescription(ldes)


################################################################################
# Opaque functions
################################################################################


def launch_rosgz_bridge(ctx: LaunchContext) -> List[LaunchDescriptionEntity]:
    # ldes := (l)aunch (d)escription (e)ntitie(s) to return.
    ldes: List[LaunchDescriptionEntity] = []

    namespace = LaunchConfiguration('namespace').perform(ctx).strip()
    robot_name = LaunchConfiguration('robot_name').perform(ctx).strip()
    robot_ns = rlh.create_robot_namespace(namespace, robot_name)
    underscored_robot_ns = rlh.underscorify_namespace(robot_ns)

    # Create the configuration for the rosgz_bridge_core for this robot.
    rosgz_bridge_cfg, msg = _rosgz_bridge_core_cfg_builder.create_cfg(
        LaunchConfiguration('core_sim_file').perform(ctx).strip(), namespace, robot_name
    )

    if not rosgz_bridge_cfg:
        return [LogInfo(msg=msg)]

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
        'use_sim_time': True,  # if here we are in simulation mode.
        'config_file': str(abs_path),
        # We are building the full topics, including namespace, so we do not need the bridge to expand the topic names.
        'expand_gz_topic_names': False,
        # The parameter 'override_timestamps_with_wall_time' controls how the 'header.stamp' field is set in messages
        # bridged from gazebo to ros 2.
        # - If set to 'true', the bridge will overwrite the original timestamp with the current system wall time,
        #   i.e., the time according to the operating system clock (e.g., what you get with `date` in a terminal),
        #   at the moment the message is forwarded.
        #   This means the message will reflect the real-world time of the host machine, not the simulation time from
        #   Gazebo.
        # - If set to 'False', the bridge will preserve the original timestamp from the source message
        #   (e.g., Gazebo simulation time).
        #   This is recommendation when you are also bridging the '/clock' topic from gazebo to ROS2 and using
        #   'use_sim_time: True' in your ROS2 nodes, so that all messages and nodes are synchronized to the same
        #   simulation time reference.
        'override_timestamps_with_wall_time': False,
    }

    # If 'subscription_heartbeat' is set in the launch file, it has priority over the one that could be set in
    # the parameter file.
    subscription_heartbeat = LaunchConfiguration('subscription_heartbeat').perform(ctx).strip()

    if subscription_heartbeat:
        parameters_dict['subscription_heartbeat'] = int(subscription_heartbeat)

    parameters.append(parameters_dict)

    # node_options include 'name', 'output', 'emulate_tty', 'respawn', 'respawn_delay',
    node_options = rlh.process_node_options(LaunchConfiguration('node_options').perform(ctx))
    node_name = str(node_options['name']) or 'rosgz_bridge'

    ldes.append(
        Node(
            package='ros_gz_bridge',
            executable='bridge_node',
            name=node_name,
            # Insert the node into the robot_ns.
            namespace=robot_ns,
            parameters=parameters,
            # Topics remappings not needed here.
            ros_arguments=rlh.process_logging_options(LaunchConfiguration('logging_options').perform(ctx)),
            output=node_options['output'],
            emulate_tty=node_options['emulate_tty'],
            respawn=node_options['respawn'],
            respawn_delay=node_options['respawn_delay'],
        )
    )

    return ldes
