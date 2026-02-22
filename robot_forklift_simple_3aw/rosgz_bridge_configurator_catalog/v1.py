from typing import Any, Dict, List, Tuple

import ros2_launch_helpers as rlh

from robot_forklift_simple_3aw.rosgz_bridge_configurator_catalog import core

__all__ = ['create_cfg']


def create_cfg(sim_file: str, namespace: str, robot_name: str) -> Tuple[List[Dict[str, Any]], List[str]]:
    """Create the ROS <-> GZ bridge channels configuration for the v1 fs3aw profile.

    This builder composes the core profile channels and adds the v1-specific sensor channels.
    """

    core_channels, core_messages = core.create_cfg(sim_file, namespace, robot_name)

    robot_ns = rlh.create_robot_namespace(namespace, robot_name)
    underscored_robot_ns = rlh.underscorify_namespace(robot_ns)

    try:
        sim_file, sim_cfg = rlh.read_yaml_mapping(sim_file)
    except Exception as exc:
        return ([], [f'[{underscored_robot_ns}] {exc}'])

    if not sim_cfg:
        return ([], [f"[{underscored_robot_ns}] Simulation file '{sim_file}' is a YAML mapping but has no keys"])

    top_lidar_sim_cfg = sim_cfg.get('top_lidar', {})
    use_top_lidar = top_lidar_sim_cfg.get('enabled', False)

    top_imu_sim_cfg = sim_cfg.get('top_imu', {})
    use_top_imu = top_imu_sim_cfg.get('enabled', False)

    rear_camera_cfg = sim_cfg.get('rear_camera', {})
    rear_camera_color_cfg = rear_camera_cfg.get('color_camera', {})
    rear_camera_infrared_cfg = rear_camera_cfg.get('infrared_camera', {})
    rear_camera_depth_cfg = rear_camera_cfg.get('depth_camera', {})
    use_rear_camera = (
        rear_camera_color_cfg.get('enabled', False)
        or rear_camera_infrared_cfg.get('enabled', False)
        or rear_camera_depth_cfg.get('enabled', False)
    )

    use_any_plugin = use_top_lidar or use_top_imu or use_rear_camera

    if not use_any_plugin:
        return (
            core_channels,
            core_messages
            + [
                f'[{underscored_robot_ns}] No plugins enabled in the simulation configuration for the extra elements '
                "of the 'v1' version of the 'fs3aw' robot."
            ],
        )

    channels: List[Dict[str, Any]] = []

    if use_top_lidar:
        top_lidar_topic = f'{robot_ns}/top_lidar/scan/points'
        channels.append(
            {
                'ros_topic_name': top_lidar_topic,
                'gz_topic_name': top_lidar_topic,
                'ros_type_name': 'sensor_msgs/msg/PointCloud2',
                'gz_type_name': 'gz.msgs.PointCloudPacked',
                'direction': 'GZ_TO_ROS',
                'qos_profile': 'SENSOR_DATA',
                'lazy': True,
            }
        )

    if use_top_imu:
        top_imu_topic = f'{robot_ns}/top_imu/data'
        channels.append(
            {
                'ros_topic_name': top_imu_topic,
                'gz_topic_name': top_imu_topic,
                'ros_type_name': 'sensor_msgs/msg/Imu',
                'gz_type_name': 'gz.msgs.IMU',
                'direction': 'GZ_TO_ROS',
                'qos_profile': 'SENSOR_DATA',
                'lazy': True,
            }
        )

    if use_rear_camera:
        camera_namespace = f'{robot_ns}/rear_camera'

        if rear_camera_color_cfg.get('enabled', False):
            rear_camera_color_topic = f'{camera_namespace}/color/image_raw'
            channels.append(
                {
                    'ros_topic_name': rear_camera_color_topic,
                    'gz_topic_name': rear_camera_color_topic,
                    'ros_type_name': 'sensor_msgs/msg/Image',
                    'gz_type_name': 'gz.msgs.Image',
                    'direction': 'GZ_TO_ROS',
                    'qos_profile': 'SENSOR_DATA',
                    'lazy': True,
                }
            )

            rear_camera_color_info_topic = f'{camera_namespace}/color/camera_info'

            channels.append(
                {
                    'ros_topic_name': rear_camera_color_info_topic,
                    'gz_topic_name': rear_camera_color_info_topic,
                    'ros_type_name': 'sensor_msgs/msg/CameraInfo',
                    'gz_type_name': 'gz.msgs.CameraInfo',
                    'direction': 'GZ_TO_ROS',
                    'qos_profile': 'SENSOR_DATA',
                    'lazy': True,
                }
            )

        if rear_camera_infrared_cfg.get('enabled', False):
            rear_camera_infra1_topic = f'{camera_namespace}/infra1/image_raw'
            channels.append(
                {
                    'ros_topic_name': rear_camera_infra1_topic,
                    'gz_topic_name': rear_camera_infra1_topic,
                    'ros_type_name': 'sensor_msgs/msg/Image',
                    'gz_type_name': 'gz.msgs.Image',
                    'direction': 'GZ_TO_ROS',
                    'qos_profile': 'SENSOR_DATA',
                    'lazy': True,
                }
            )

            rear_camera_infra2_topic = f'{camera_namespace}/infra2/image_raw'
            channels.append(
                {
                    'ros_topic_name': rear_camera_infra2_topic,
                    'gz_topic_name': rear_camera_infra2_topic,
                    'ros_type_name': 'sensor_msgs/msg/Image',
                    'gz_type_name': 'gz.msgs.Image',
                    'direction': 'GZ_TO_ROS',
                    'qos_profile': 'SENSOR_DATA',
                    'lazy': True,
                }
            )

            rear_camera_infra1_info_topic = f'{camera_namespace}/infra1/camera_info'

            channels.append(
                {
                    'ros_topic_name': rear_camera_infra1_info_topic,
                    'gz_topic_name': rear_camera_infra1_info_topic,
                    'ros_type_name': 'sensor_msgs/msg/CameraInfo',
                    'gz_type_name': 'gz.msgs.CameraInfo',
                    'direction': 'GZ_TO_ROS',
                    'qos_profile': 'SENSOR_DATA',
                    'lazy': True,
                }
            )

            rear_camera_infra2_info_topic = f'{camera_namespace}/infra2/camera_info'

            channels.append(
                {
                    'ros_topic_name': rear_camera_infra2_info_topic,
                    'gz_topic_name': rear_camera_infra2_info_topic,
                    'ros_type_name': 'sensor_msgs/msg/CameraInfo',
                    'gz_type_name': 'gz.msgs.CameraInfo',
                    'direction': 'GZ_TO_ROS',
                    'qos_profile': 'SENSOR_DATA',
                    'lazy': True,
                }
            )

        if rear_camera_depth_cfg.get('enabled', False):
            rear_camera_depth_topic = f'{camera_namespace}/depth/image_raw'
            channels.append(
                {
                    'ros_topic_name': rear_camera_depth_topic,
                    'gz_topic_name': rear_camera_depth_topic,
                    'ros_type_name': 'sensor_msgs/msg/Image',
                    'gz_type_name': 'gz.msgs.Image',
                    'direction': 'GZ_TO_ROS',
                    'qos_profile': 'SENSOR_DATA',
                    'lazy': True,
                }
            )

            channels.append(
                {
                    'ros_topic_name': f'{rear_camera_depth_topic}/points',
                    'gz_topic_name': f'{rear_camera_depth_topic}/points',
                    'ros_type_name': 'sensor_msgs/msg/PointCloud2',
                    'gz_type_name': 'gz.msgs.PointCloudPacked',
                    'direction': 'GZ_TO_ROS',
                    'qos_profile': 'SENSOR_DATA',
                    'lazy': True,
                }
            )

            rear_camera_depth_info_topic = f'{camera_namespace}/depth/camera_info'

            channels.append(
                {
                    'ros_topic_name': rear_camera_depth_info_topic,
                    'gz_topic_name': rear_camera_depth_info_topic,
                    'ros_type_name': 'sensor_msgs/msg/CameraInfo',
                    'gz_type_name': 'gz.msgs.CameraInfo',
                    'direction': 'GZ_TO_ROS',
                    'qos_profile': 'SENSOR_DATA',
                    'lazy': True,
                }
            )

    all_channels = core_channels + channels
    all_messages = core_messages

    return (all_channels, all_messages)
