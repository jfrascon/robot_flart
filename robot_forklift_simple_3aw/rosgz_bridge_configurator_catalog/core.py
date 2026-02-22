from typing import Any, Dict, List, Tuple

import ros2_launch_helpers as rlh

__all__ = ['create_cfg']


def create_cfg(sim_file: str, namespace: str, robot_name: str) -> Tuple[List[Dict[str, Any]], List[str]]:
    """Create the ROS <-> GZ bridge channels configuration for the core fs3aw profile.

    - Processes the simulation configuration file and builds channel entries based on enabled sections.
    - Returns (channels, messages). On success, messages is empty. On errors, channels is empty and
      messages contains the reason.
    """

    robot_ns = rlh.create_robot_namespace(namespace, robot_name)
    underscored_robot_ns = rlh.underscorify_namespace(robot_ns)

    try:
        sim_file, sim_cfg = rlh.read_yaml_mapping(sim_file)
    except Exception as exc:
        return ([], [f'[{underscored_robot_ns}] {exc}'])

    if not sim_cfg:
        return ([], [f"[{underscored_robot_ns}] Simulation file '{sim_file}' is a YAML mapping but has no keys"])

    base_sim_cfg = sim_cfg.get('base', {})
    base_velocity_controller_sim_cfg = base_sim_cfg.get('velocity_controller', {})
    use_base_velocity_controller = base_velocity_controller_sim_cfg.get('enabled', False)

    base_pose_ground_truth_publisher_sim_cfg = base_sim_cfg.get('pose_ground_truth_publisher', {})
    use_base_pose_ground_truth_publisher = base_pose_ground_truth_publisher_sim_cfg.get('enabled', False)

    steerable_wheel_steerable_joint_controller_sim_cfg = base_sim_cfg.get(
        'steerable_wheel_steerable_joint_controller', {}
    )
    use_steerable_wheel_steerable_joint_controller = steerable_wheel_steerable_joint_controller_sim_cfg.get(
        'enabled', False
    )

    steerable_wheel_rotation_joint_controller_sim_cfg = base_sim_cfg.get(
        'steerable_wheel_rotation_joint_controller', {}
    )
    use_steerable_wheel_rotation_joint_controller = steerable_wheel_rotation_joint_controller_sim_cfg.get(
        'enabled', False
    )

    fork_sim_cfg = sim_cfg.get('fork', {})
    fork_position_controller_sim_cfg = fork_sim_cfg.get('position_controller', {})
    use_fork_position_controller = fork_position_controller_sim_cfg.get('enabled', False)

    joint_state_publisher_sim_cfg = sim_cfg.get('joint_state_publisher', {})
    use_joint_state_publisher = joint_state_publisher_sim_cfg.get('enabled', False)

    use_any_plugin = (
        use_base_velocity_controller
        or use_base_pose_ground_truth_publisher
        or use_steerable_wheel_steerable_joint_controller
        or use_steerable_wheel_rotation_joint_controller
        or use_fork_position_controller
        or use_joint_state_publisher
    )

    if not use_any_plugin:
        return (
            [],
            [
                f"[{underscored_robot_ns}] No plugins enabled in the simulation configuration for the 'base' and "
                "'fork' of the robot"
            ],
        )

    channels: List[Dict[str, Any]] = []

    if use_base_velocity_controller:
        base_velocity_controller_topic = f'{robot_ns}/cmd_vel'
        channels.append(
            {
                'ros_topic_name': base_velocity_controller_topic,
                'gz_topic_name': base_velocity_controller_topic,
                'ros_type_name': 'geometry_msgs/msg/Twist',
                'gz_type_name': 'gz.msgs.Twist',
                'direction': 'ROS_TO_GZ',
                'qos_profile': 'SENSOR_DATA',
                'lazy': True,
            }
        )

    if use_base_pose_ground_truth_publisher:
        base_pose_ground_truth_topic = f'{robot_ns}/base_pose_ground_truth'
        channels.append(
            {
                'ros_topic_name': base_pose_ground_truth_topic,
                'gz_topic_name': base_pose_ground_truth_topic,
                'ros_type_name': 'nav_msgs/msg/Odometry',
                'gz_type_name': 'gz.msgs.OdometryWithCovariance',
                'direction': 'GZ_TO_ROS',
                'qos_profile': 'SENSOR_DATA',
                'lazy': True,
            }
        )

        tf_topic_no_namespace = base_pose_ground_truth_publisher_sim_cfg.get('tf_topic', 'tf_sim_world_robot_root_fr')
        tf_topic = f'{robot_ns}/{tf_topic_no_namespace}'
        channels.append(
            {
                'ros_topic_name': tf_topic,
                'gz_topic_name': tf_topic,
                'ros_type_name': 'tf2_msgs/msg/TFMessage',
                'gz_type_name': 'gz.msgs.Pose_V',
                'direction': 'GZ_TO_ROS',
                'qos_profile': 'SENSOR_DATA',
                'lazy': False,
            }
        )

    if use_steerable_wheel_steerable_joint_controller or use_steerable_wheel_rotation_joint_controller:
        steerable_wheel_command_topic = f'{robot_ns}/joint_commands/base'
        channels.append(
            {
                'ros_topic_name': steerable_wheel_command_topic,
                'gz_topic_name': steerable_wheel_command_topic,
                'ros_type_name': 'actuator_msgs/msg/Actuators',
                'gz_type_name': 'gz.msgs.Actuators',
                'direction': 'ROS_TO_GZ',
                'qos_profile': 'SENSOR_DATA',
                'lazy': True,
            }
        )

    if use_fork_position_controller:
        fork_position_controller_topic = f'{robot_ns}/joint_commands/fork'
        channels.append(
            {
                'ros_topic_name': fork_position_controller_topic,
                'gz_topic_name': fork_position_controller_topic,
                'ros_type_name': 'std_msgs/msg/Float64',
                'gz_type_name': 'gz.msgs.Double',
                'direction': 'ROS_TO_GZ',
                'qos_profile': 'SENSOR_DATA',
                'lazy': True,
            }
        )

    if use_joint_state_publisher:
        joint_states_topic = f'{robot_ns}/joint_states'
        channels.append(
            {
                'ros_topic_name': joint_states_topic,
                'gz_topic_name': joint_states_topic,
                'ros_type_name': 'sensor_msgs/msg/JointState',
                'gz_type_name': 'gz.msgs.Model',
                'direction': 'GZ_TO_ROS',
                'qos_profile': 'SENSOR_DATA',
                'lazy': True,
            }
        )

    return (channels, [])
