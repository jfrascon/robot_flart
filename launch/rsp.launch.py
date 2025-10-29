import os
from pathlib import Path

import ros2_launch_helpers as rlh
from ament_index_python.packages import get_package_share_directory
from launch.actions import DeclareLaunchArgument, OpaqueFunction
from launch.substitutions import Command, FindExecutable, LaunchConfiguration
from launch.utilities.type_utils import normalize_typed_substitution, perform_typed_substitution
from launch_ros.actions import Node
from launch_ros.descriptions import ParameterValue

from launch import LaunchContext, LaunchDescription, LaunchDescriptionEntity


def generate_launch_description():
    # ldes => (l)aunch (d)escription (e)ntitie(s)

    ldes = [
        DeclareLaunchArgument(
            'use_sim_time',
            default_value='False',
            choices=['True', 'true', 'False', 'false'],
            description='Use simulation clock if true',
        ),
        DeclareLaunchArgument('namespace', default_value='', description='namespace (optional, default: "")'),
        DeclareLaunchArgument('robot_name', default_value='flart', description='The unique name for the robot'),
        # <parameters>
        DeclareLaunchArgument(
            'odom_frame',
            default_value='odom',
            description="Odometry frame name of the robot. The 'robot_prefix' will be appended",
        ),
        DeclareLaunchArgument(
            'use_visual_meshes',
            default_value='True',
            description='Whether to use visual meshes if True, or simple shapes if False (default: True)',
        ),
        DeclareLaunchArgument(
            'use_collision_meshes',
            default_value='False',
            description='Whether to use collision meshes if True, or simple shapes if False (default: False)',
        ),
        DeclareLaunchArgument(
            'publish_frequency',
            default_value='20.0',
            description='Frequency of publication for robot_state_publisher (default: 20.0)',
        ),
        DeclareLaunchArgument(
            'sim_cfg_file',
            default_value=os.path.join(get_package_share_directory('robot_flart'), 'config', 'simulation_default.yaml'),
            description='Path to the simulation configuration file (default: simulation_default.yaml)',
        ),
        # </parametes>
        DeclareLaunchArgument('remappings', default_value='', description=rlh.REMAPPINGS_DESC),
        DeclareLaunchArgument(
            'log_options', default_value=rlh.default_log_options_str(), description=rlh.LOG_OPTIONS_DESC
        ),
        DeclareLaunchArgument(
            'node_options', default_value=rlh.default_node_options_str(), description=rlh.NODE_OPTIONS_DESC
        ),
        OpaqueFunction(function=rlh.set_robot_namespace, args=['namespace', 'robot_name']),
        OpaqueFunction(function=launch_rsp),
    ]

    return LaunchDescription(ldes)


# ----------------------------------------------------------------------------------------------------------------------

# Opaque functions.


def launch_rsp(ctx: LaunchContext) -> list[LaunchDescriptionEntity]:
    use_sim_time = perform_typed_substitution(
        ctx, normalize_typed_substitution(LaunchConfiguration('use_sim_time'), bool), bool
    )

    robot_namespace = LaunchConfiguration('robot_namespace').perform(ctx)
    sim_cfg_file = LaunchConfiguration('sim_cfg_file').perform(ctx)

    # If we are not in simulation mode, do not use any simulation configuration file; it is no needed.
    if not use_sim_time:
        sim_cfg_file = ''
    # If we are in simulation mode but no simulation configuration file is provided, no plugins will be loaded.
    elif sim_cfg_file:
        # If the user provided a simulation configuration file, check it exists.
        if not Path(sim_cfg_file).is_file():
            raise FileNotFoundError(f"File '{sim_cfg_file}' not found")

    robot_description_param = ParameterValue(
        Command(
            [
                FindExecutable(name='xacro'),
                ' ',
                os.path.join(get_package_share_directory('robot_flart'), 'urdf', 'description.xacro'),
                ' robot_name:=',
                LaunchConfiguration('robot_name'),
                ' namespace:=',
                LaunchConfiguration('namespace'),
                ' odom_frame:=',
                LaunchConfiguration('odom_frame'),
                # User can disable the use of visual or collision meshes, for example to improve performance when
                # simulating the robot in Gazebo.
                ' use_visual_meshes:=',
                LaunchConfiguration('use_visual_meshes'),
                ' use_collision_meshes:=',
                LaunchConfiguration('use_collision_meshes'),
                # Depending on whether the robot is running in simulation mode or in real mode, some xacro sections
                # will be included or excluded.
                ' use_sim_mode:=',
                LaunchConfiguration('use_sim_time'),
                ' sim_cfg_file:=',
                sim_cfg_file,
            ]
        ),
        value_type=str,
    )

    node_options = rlh.parse_cli_node_opts(LaunchConfiguration('node_options').perform(ctx))

    return [
        Node(
            package='robot_state_publisher',
            executable='robot_state_publisher',
            name=str(node_options['name']) or 'robot_state_publisher',
            namespace=robot_namespace,
            # Both methods of passing parameters are allowed:
            # Method 1: Using a list of dictionaries, where each dictionary contains a key-value pair.
            # parameters = [
            #     {'key1': value1},
            #     {'key2': value2},
            #     ...
            # ]
            # Method 2: Using a single dictionary with all key-value pairs.
            # parameters = [
            #     {
            #         'key1': value1,
            #         'key2': value2,
            #         ...
            #     }
            # ]
            parameters=[
                {
                    'use_sim_time': use_sim_time,
                    'robot_description': robot_description_param,
                    #'frame_prefix': "DO NOT USE IT, ROBOT_PREFIX IS COMPUTED AND USED IN THE XACRO FILE"
                    'publish_frequency': ParameterValue(LaunchConfiguration('publish_frequency'), value_type=float),
                }
            ],
            remappings=rlh.parse_cli_remappings(LaunchConfiguration('remappings').perform(ctx)),
            ros_arguments=rlh.parse_cli_log_opts(LaunchConfiguration('log_options').perform(ctx)),
            output=node_options['output'],
            emulate_tty=node_options['emulate_tty'],
            respawn=node_options['respawn'],
            respawn_delay=node_options['respawn_delay'],
        )
    ]
