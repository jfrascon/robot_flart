from typing import Any, Dict, List, Tuple

import ros2_launch_helpers as rlh

# Public API of this module.
# Useful when a client uses the instruction 'from <module> import *', since it avoids exporting internal names that
# start with an underscore.
__all__ = ['create_cfg']


def create_cfg(core_sim_file: str, namespace: str, robot_name: str) -> Tuple[List[Dict[str, Any]], str]:
    """Create the ROS <-> GZ bridge channels configuration for the version 'core' of the 'flart' robot.

    - Processes the simulation configuration file and builds channel entries based on enabled sections.
    - Returns a tuple ([cfg], [msg]).
      On success, '[cfg]' is a list of channel configurations (dict) and '[msg]' is empty.
      On errors or special cases (e.g., no file provided) '[cfg]' is empty and '[msg]' explains the reasons.
    """

    robot_ns = rlh.create_robot_namespace(namespace, robot_name)
    underscored_robot_ns = rlh.underscorify_namespace(robot_ns)

    # Read the simulation file and return the content. If it is not possible to grab the content, return None and the
    # error message to the caller.
    try:
        core_sim_file, core_sim_cfg = rlh.read_yaml_mapping(core_sim_file)
    except Exception as e:
        return ([], f'[{underscored_robot_ns}] {e}')

    # If the core_sim_cfg is empty, no plugins are enabled, so return an appropriate message.
    if not core_sim_cfg:
        return ([], f"[{underscored_robot_ns}] Simulation file '{core_sim_file}' is a YAML mapping but has no keys")

    # When working in simulation, the topics used by GZ plugins installed in the xacro file where the 'core' version of
    # the 'flart' robot is defined are fixed, they do not admit to be passed as parameters to the plugins.
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

    base_sim_cfg = core_sim_cfg.get('base', {})
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

    fork_sim_cfg = core_sim_cfg.get('fork', {})
    fork_position_controller_sim_cfg = fork_sim_cfg.get('position_controller', {})
    use_fork_position_controller = fork_position_controller_sim_cfg.get('enabled', False)

    joint_state_publisher_sim_cfg = core_sim_cfg.get('joint_state_publisher', {})
    use_joint_state_publisher = joint_state_publisher_sim_cfg.get('enabled', False)

    use_any_plugin = (
        use_base_velocity_controller
        or use_base_pose_ground_truth_publisher
        or use_steerable_wheel_steerable_joint_controller
        or use_steerable_wheel_rotation_joint_controller
        or use_fork_position_controller
        or use_joint_state_publisher
    )

    # If no plugins are enabled, return None and a warning message.
    if not use_any_plugin:
        return (
            [],
            f"[{underscored_robot_ns}] No plugins enabled in the simulation configuration for the 'base' and "
            "'fork' of the robot",
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
                'lazy': False,  # /tf should not be lazy
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
        fork_position_controller_topic = f'{robot_ns}/joints_commands/fork'
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

    return (channels, '')
