import os
from pathlib import Path
from typing import Any, Dict, List

import ros2_launch_helpers as rlh
import yaml
from ament_index_python.packages import get_package_share_directory
from launch.actions import DeclareLaunchArgument, GroupAction, OpaqueFunction
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterFile

from launch import LaunchContext, LaunchDescription, LaunchDescriptionEntity

REQUIRED_CHANNEL_FIELDS = {
    'ros_topic_name',
    'gz_topic_name',
    'ros_type_name',
    'gz_type_name',
    'direction',
    'qos_profile',
    'lazy',
}


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
        # 'params_file' and 'subscription_heartbeat' are parameters for the bridge node.
        DeclareLaunchArgument(
            'params_file',
            default_value='',
            description='Path to params file. If empty, use default for selected robot_version.',
        ),
        DeclareLaunchArgument(
            'subscription_heartbeat', default_value='', description='Subscription heartbeat (Optional, default: "")'
        ),
        DeclareLaunchArgument(
            'sim_file',
            default_value='',
            description='Path to the simulation file. If empty, use the example file for selected robot_version.',
        ),
        DeclareLaunchArgument(
            'bridge_file',
            default_value='',
            description='Path to the bridge file. If empty, use the example file for selected robot_version.',
        ),
        DeclareLaunchArgument(
            'node_options', default_value=rlh.default_node_options_str(), description=rlh.NODE_OPTIONS_DESC
        ),
        DeclareLaunchArgument(
            'logging_options', default_value=rlh.default_logging_options_str(), description=rlh.LOGGING_OPTIONS_DESC
        ),
        GroupAction(
            condition=IfCondition(LaunchConfiguration('use_sim_time')),
            actions=[OpaqueFunction(function=_launch_bridge)],
        ),
    ]

    return LaunchDescription(ldes)


def _check_channel_fields(channel_name: str, channel_cfg: Dict[str, Any]) -> None:
    """Validate required fields and field types for one bridge channel."""
    present_fields = set(channel_cfg.keys())

    unknown_fields = present_fields.difference(REQUIRED_CHANNEL_FIELDS)

    if unknown_fields:
        raise ValueError(
            f'Channel {channel_name!r} has fields that are not allowed: {sorted(unknown_fields)}. '
            f'Allowed fields: {sorted(REQUIRED_CHANNEL_FIELDS)}.'
        )

    missing_fields = REQUIRED_CHANNEL_FIELDS.difference(present_fields)

    if missing_fields:
        raise ValueError(f'Channel {channel_name!r} is missing required fields: {sorted(missing_fields)}.')

    for field_name, field_value in channel_cfg.items():
        if field_name == 'lazy':
            if not isinstance(field_value, bool):
                raise ValueError(f'Field {field_name!r} for channel {channel_name!r} must be a boolean.')
        else:
            if not isinstance(field_value, str):
                raise ValueError(f'Field {field_name!r} for channel {channel_name!r} must be a string.')


def _get_channels(robot_version: str, bridge_file: str, sim_file: str) -> List[Dict[str, Any]]:
    """Convert the channel catalog into the list expected by the bridge node.

    The public bridge YAML stores one top-level entry per channel. The launch
    applies the policy of the selected robot version to those channels and only
    then converts the remaining channel configs to the list expected by the
    bridge node.
    """
    # No need to validate existence of the files here because the `read_yaml_file` function will
    # raise an exception if the file does not exist or if there is an error while parsing the file.
    resolved_yaml_file, channels_cfg = rlh.read_yaml_file(bridge_file)

    # The channel config must be mapping of channel name to channel config.
    if not isinstance(channels_cfg, dict):
        raise ValueError(f"File '{resolved_yaml_file}' must be a mapping. Got: '{type(channels_cfg).__name__}'")

    # Read the simulation config and check it is a mapping of plugin name to plugin config.
    resolved_sim_file, sim_cfg = rlh.read_yaml_file(sim_file)

    if not isinstance(sim_cfg, dict):
        raise ValueError(f"File '{resolved_sim_file}' must be a mapping. Got: '{type(sim_cfg).__name__}'")

    # Process the channels according to the robot version being launched.
    if robot_version == 'core':
        _process_core_channels(channels_cfg, sim_cfg)
    elif robot_version == 'v1':
        _process_v1_channels(channels_cfg, sim_cfg)
    else:
        raise ValueError(f'Robot version {robot_version!r} is not supported by bridge.launch.py')

    # Extract the channel name and leave only the channel fields, which is the format expected by the bridge node.
    return list(channels_cfg.values())


def _get_urdf_dir() -> Path:
    """Return the directory that stores robot xacro files."""
    urdf_dir = Path(get_package_share_directory('robot_forklift_simple_3sw')).joinpath('urdf')

    if not urdf_dir.is_dir():
        raise FileNotFoundError(f'URDF directory {urdf_dir!r} not found.')

    return urdf_dir


def _get_robot_versions() -> List[str]:
    """Return available robot versions from xacro files under urdf."""
    try:
        urdf_dir = _get_urdf_dir()
    except FileNotFoundError:
        return []

    return sorted(path.stem for path in urdf_dir.glob('*.xacro') if path.is_file())


def _process_core_channels(channels_cfg: Dict[str, Dict[str, Any]], sim_cfg: Dict[str, Any]) -> None:
    """Apply the core robot policy to the bridge channels in place."""
    required_plugins = (
        'base_velocity_controller',
        'base_pose_ground_truth_publisher',
        'base_steerable_wheel_steerable_joint_controller',
        'base_steerable_wheel_rotation_joint_controller',
        'fork_position_controller',
        'joint_state_publisher',
    )
    required_channels = (
        'base_velocity_controller',
        'base_pose_ground_truth_publisher',
        'base_pose_ground_truth_publisher_tf',
        'base_steerable_wheel_command',
        'fork_position_controller',
        'joint_state_publisher',
    )

    # Check required fields in plugins and channels are present.
    for plugin_name in required_plugins:
        if plugin_name not in sim_cfg:
            raise ValueError(f'Plugin {plugin_name!r} not found in simulation file.')
        if not isinstance(sim_cfg[plugin_name], dict):
            raise ValueError(f'Plugin {plugin_name!r} in simulation file must be a YAML mapping.')

    for channel_name in required_channels:
        if channel_name not in channels_cfg:
            raise ValueError(f'Channel {channel_name!r} not found in bridge file.')
        if not isinstance(channels_cfg[channel_name], dict):
            raise ValueError(f'Channel {channel_name!r} in bridge file must be a YAML mapping.')
        _check_channel_fields(channel_name, channels_cfg[channel_name])

    # If a plugin is disabled in the simulation config, then the corresponding channel(s) must be
    # removed from the bridge config. This is because if the plugin is disabled, the corresponding
    # topic will not be published in Gazebo and therefore the bridge will fail to start if it tries
    # to subscribe to that topic.
    if not sim_cfg['base_velocity_controller'].get('enabled', False):
        channels_cfg.pop('base_velocity_controller', None)

    if not sim_cfg['base_pose_ground_truth_publisher'].get('enabled', False):
        channels_cfg.pop('base_pose_ground_truth_publisher', None)
        channels_cfg.pop('base_pose_ground_truth_publisher_tf', None)

    steerable_joint_controller_enabled = sim_cfg['base_steerable_wheel_steerable_joint_controller'].get(
        'enabled', False
    )

    rotation_joint_controller_enabled = sim_cfg['base_steerable_wheel_rotation_joint_controller'].get('enabled', False)

    # `not xxx and not yyy` is the same as `not (xxx or yyy)`, but the former is more explicit.
    if not steerable_joint_controller_enabled and not rotation_joint_controller_enabled:
        channels_cfg.pop('base_steerable_wheel_command', None)

    if not sim_cfg['fork_position_controller'].get('enabled', False):
        channels_cfg.pop('fork_position_controller', None)

    if not sim_cfg['joint_state_publisher'].get('enabled', False):
        channels_cfg.pop('joint_state_publisher', None)


def _process_v1_channels(channels_cfg: Dict[str, Dict[str, Any]], sim_cfg: Dict[str, Any]) -> None:
    """Apply the v1 robot policy to the bridge channels in place."""
    _process_core_channels(channels_cfg, sim_cfg)

    # In the v1 simulation file, each sensor config can map to one or more Gazebo plugins:
    # - `top_lidar` sensor config is used to configure 1 plugin.
    # - `top_imu` sensor config is used to configure 1 plugin.
    # - `rear_camera` sensor config is used to configure 3 plugins (`rgbd_camera`, `infrared_camera`
    # for infra1, and `infrared_camera` for infra2).
    required_sensor_cfgs = ('top_lidar', 'top_imu', 'rear_camera')

    # Check required sensor configs are present in the simulation config and have the correct type.
    for sensor_cfg_name in required_sensor_cfgs:
        if sensor_cfg_name not in sim_cfg:
            raise ValueError(f'Sensor config {sensor_cfg_name!r} not found in simulation file.')
        if not isinstance(sim_cfg[sensor_cfg_name], dict):
            raise ValueError(f'Sensor config {sensor_cfg_name!r} in simulation file must be a YAML mapping.')

    # 3 plugins were indicated for the rear camera sensor, but the config for the infra1 and infra2
    # plugins is the same, except for the Gazebo topic names.
    required_rear_camera_module_cfgs = ('rgbd_camera', 'infrared_camera')

    rear_camera_cfg = sim_cfg['rear_camera']

    for rear_camera_module_cfg_name in required_rear_camera_module_cfgs:
        if rear_camera_module_cfg_name not in rear_camera_cfg:
            raise ValueError(f"Plugin {rear_camera_module_cfg_name!r} not found in 'rear_camera' simulation config.")
        if not isinstance(rear_camera_cfg[rear_camera_module_cfg_name], dict):
            raise ValueError(
                f"Plugin {rear_camera_module_cfg_name!r} in 'rear_camera' simulation config must be a YAML mapping."
            )

    # The bridge channels for the rgbd plugin.
    # The trigger channel is used to trigger the camera in Gazebo when the camera is configured to
    # be triggered.
    # If the camera is not configured to be triggered, then the trigger channel will be removed
    # from the bridge config.
    # For these reason the trigger channel is defined separately from the other channels to make it
    # easier to apply the policy for triggered vs non-triggered camera.
    rgbd_camera_trigger_channel = 'rear_camera_rgbd_trigger'
    rgbd_camera_channels = (
        'rear_camera_rgbd_image',
        'rear_camera_rgbd_camera_info',
        'rear_camera_rgbd_depth_image',
        'rear_camera_rgbd_points',
        rgbd_camera_trigger_channel,
    )

    # Same explanation applies to the infrared cameras as for the rgbd camera regarding the trigger channel.
    infrared1_trigger_channel = 'rear_camera_infra1_trigger'
    infrared1_channels = ('rear_camera_infra1_image', 'rear_camera_infra1_camera_info', infrared1_trigger_channel)

    infrared2_trigger_channel = 'rear_camera_infra2_trigger'
    infrared2_channels = ('rear_camera_infra2_image', 'rear_camera_infra2_camera_info', infrared2_trigger_channel)

    rgbd_camera_cfg = rear_camera_cfg['rgbd_camera']
    infrared_camera_cfg = rear_camera_cfg['infrared_camera']

    required_channels = ('top_lidar', 'top_imu', *rgbd_camera_channels, *infrared1_channels, *infrared2_channels)

    # Check required channels are present in the bridge config and have the correct type.
    # Also check each channel has the required fields and field types using the
    # `_check_channel_fields` function.
    for channel_name in required_channels:
        if channel_name not in channels_cfg:
            raise ValueError(f'Channel {channel_name!r} not found in bridge file.')
        if not isinstance(channels_cfg[channel_name], dict):
            raise ValueError(f'Channel {channel_name!r} in bridge file must be a YAML mapping.')
        _check_channel_fields(channel_name, channels_cfg[channel_name])

    # If a sensor is disabled in the simulation config, then the corresponding channel(s) must be
    # removed from the bridge config. This is because if the sensor is disabled, the corresponding
    # topic will not be published in Gazebo.
    if not sim_cfg['top_lidar'].get('enabled', False):
        channels_cfg.pop('top_lidar', None)

    if not sim_cfg['top_imu'].get('enabled', False):
        channels_cfg.pop('top_imu', None)

    # If the rgbd configuration indicates `enabled: False`, then all the channels for the rgbd
    # camera must be removed from the bridge config.
    # If the rgbd configuration indicates `enabled: True` but `triggered: False`, then only the
    # trigger channel for the rgbd camera must be removed from the bridge config.
    # The same applies to the infrared camera channels and configuration.
    if not rgbd_camera_cfg.get('enabled', False):
        for channel_name in (*rgbd_camera_channels, rgbd_camera_trigger_channel):
            channels_cfg.pop(channel_name, None)
    elif not rgbd_camera_cfg.get('triggered', False):
        channels_cfg.pop(rgbd_camera_trigger_channel, None)

    if not infrared_camera_cfg.get('enabled', False):
        for channel_name in (
            *infrared1_channels,
            infrared1_trigger_channel,
            *infrared2_channels,
            infrared2_trigger_channel,
        ):
            channels_cfg.pop(channel_name, None)
    elif not infrared_camera_cfg.get('triggered', False):
        channels_cfg.pop(infrared1_trigger_channel, None)
        channels_cfg.pop(infrared2_trigger_channel, None)


def _launch_bridge(ctx: LaunchContext) -> List[LaunchDescriptionEntity]:
    """Create and launch the bridge node for the selected fs3sw profile."""

    robot_version = LaunchConfiguration('robot_version').perform(ctx).strip()
    namespace = LaunchConfiguration('namespace').perform(ctx).strip()
    robot_name = LaunchConfiguration('robot_name').perform(ctx).strip()
    robot_ns = rlh.create_robot_namespace(namespace, robot_name)
    underscored_robot_ns = rlh.underscorify_namespace(robot_ns)
    available_robot_versions = _get_robot_versions()

    if robot_version not in available_robot_versions:
        raise ValueError(
            f"Version '{robot_version}' for the 'forklift_simple_3sw' robot is not available. "
            f'Available robot versions: {", ".join(available_robot_versions)}'
        )

    sim_file = LaunchConfiguration('sim_file').perform(ctx).strip()

    if not sim_file:
        sim_file = str(
            Path(get_package_share_directory('robot_forklift_simple_3sw')).joinpath(
                'config', f'example_{robot_version}_simulation.yaml'
            )
        )

    if not Path(sim_file).is_file():
        raise FileNotFoundError(f"[{underscored_robot_ns}] Simulation file '{sim_file}' not found.")

    bridge_file = LaunchConfiguration('bridge_file').perform(ctx).strip()

    if not bridge_file:
        bridge_file = str(
            Path(get_package_share_directory('robot_forklift_simple_3sw')).joinpath(
                'config', f'example_{robot_version}_bridge.yaml'
            )
        )

    if not Path(bridge_file).is_file():
        raise FileNotFoundError(f"[{underscored_robot_ns}] Bridge file '{bridge_file}' not found.")

    channels = _get_channels(robot_version, bridge_file, sim_file)

    # The configuration for the bridge node must be passed to the bridge node via a YAML file up to
    # ROS2-Humble (starting in ROS2-Jazzy the configuration for the bridge can be passed via parameter).
    # Write the config to a YAML file in the ROS_HOME directory with the name
    # '<underscored_robot_ns>_bridge.yaml' and then that file is passed to the bridge node via the
    # 'config_file' parameter.
    ros_home = Path(os.environ.get('ROS_HOME', os.path.expanduser('~/.ros')))
    abs_path = ros_home.joinpath(f'{underscored_robot_ns}_bridge.yaml')
    abs_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        with abs_path.open('w', encoding='utf-8') as stream:
            yaml.safe_dump(
                channels, stream=stream, sort_keys=False, default_flow_style=False, allow_unicode=True, width=120
            )
    except Exception as exc:
        raise Exception(f"[{underscored_robot_ns}] Could not write bridge config to '{abs_path}': {exc}") from exc

    parameters: List[Any] = []

    config_dir = Path(get_package_share_directory('robot_forklift_simple_3sw')).joinpath('config')
    default_params_file = config_dir.joinpath(f'example_{robot_version}.yaml')
    params_file = (LaunchConfiguration('params_file').perform(ctx).strip()) or str(default_params_file)

    if not Path(params_file).is_file():
        raise FileNotFoundError(f"[{underscored_robot_ns}] Params file '{params_file}' not found.")

    if params_file:
        parameters.append(ParameterFile(params_file, allow_substs=False))

    parameters_dict: Dict[str, Any] = {
        'use_sim_time': True,
        'config_file': str(abs_path),
        # The bridge config already stores the intended GZ topic names, so the node must not expand them again.
        'expand_gz_topic_names': False,
        # Keep original Gazebo timestamps instead of replacing them with wall time.
        'override_timestamps_with_wall_time': False,
    }

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

    node_options = rlh.process_node_options(LaunchConfiguration('node_options').perform(ctx))
    node_name = str(node_options['name']) or 'bridge'

    ldes: List[LaunchDescriptionEntity] = []
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
