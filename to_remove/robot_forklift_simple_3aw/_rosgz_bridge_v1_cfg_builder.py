from typing import Any, Dict, List, Tuple

import ros2_launch_helpers as rlh

# Public API of this module.
# Useful when a client uses the instruction 'from <module> import *', since it avoids exporting internal names that
# start with an underscore.
__all__ = ['create_cfg']


def create_cfg(sim_file: str, namespace: str, robot_name: str) -> Tuple[List[Dict[str, Any]], str]:
    """Create the ROS <-> GZ bridge channels configuration for the extra elements defined in the version 'v1' of the
      'fs3aw' robot.

    - Processes the simulation configuration file and builds channel entries based on enabled sections.
    - Returns a tuple (cfg_list, msg).
      On success, 'cfg_list' is a list of channel configurations (dict) and 'msg' is empty.
      On errors or special cases (e.g., no file provided) 'cfg_list' is empty and 'msg' explains the reason.
    """

    robot_ns = rlh.create_robot_namespace(namespace, robot_name)
    underscored_robot_ns = rlh.underscorify_namespace(robot_ns)

    # Read the simulation file and return the content. If it is not possible to grab the content, return None and the
    # error message to the caller.
    try:
        sim_file, extra_sim_cfg = rlh.read_yaml_mapping(sim_file)
    except Exception as e:
        return ([], f'[{underscored_robot_ns}] {e}')

    # If the extra_sim_cfg is empty, no plugins are enabled, so return an appropriate message.
    if not extra_sim_cfg:
        return ([], f"[{underscored_robot_ns}] Simulation file '{sim_file}' is a YAML mapping but has no keys")

    # When working in simulation, the topics used by GZ plugins installed in the xacro file where the 'v1' version of
    # the 'fs3aw' robot is defined are fixed, they do not admit to be passed as parameters to the plugins.
    # Consequently, the topics used in this rosgz bridge to transfer messages to/from GZ and ROS must match those used
    # in the robot description.
    # This is a convention adopted that has several advanteges:
    # 1. Reduce the mental burden of deciding where a topic must be defined, the rule is simple: if the topic is
    #    robot-related it must be defined in the xacro file where the robot is described.
    # 2. Other launch files that need to use those topics should use the same topics, so consistency is enforced.
    #    This is specially important when working with multiple robots, since the topics are automatically
    #    namespaced under the robot namespace.
    # 3. Avoids the need to pass many parameters around to configure topics, since they are fixed.
    # 4. If for some reason the topics must be changed, do the changes in the xacro file where the robot is described
    #    and in those launch files that use those topics.
    # These topics do really make sense since they have the form:
    # <robot_ns>/<sensor_or_controller_or_plugin>/<topic_base_name>

    top_lidar_sim_cfg = extra_sim_cfg.get('top_lidar', {})
    use_top_lidar = top_lidar_sim_cfg.get('enabled', False)

    top_imu_sim_cfg = extra_sim_cfg.get('top_imu', {})
    use_top_imu = top_imu_sim_cfg.get('enabled', False)

    rear_camera_cfg = extra_sim_cfg.get('rear_camera', {})
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
            [],
            f'[{underscored_robot_ns}] No plugins enabled in the simulation configuration for the extra elements '
            "of the 'v1' version of the 'fs3aw' robot.",
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
    return (channels, '')
