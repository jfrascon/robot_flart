import copy
from typing import Any, Dict, List

from launch.actions import DeclareLaunchArgument, LogInfo
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.substitutions import FindPackageShare

from launch import LaunchContext, LaunchDescriptionEntity

# Public API of this module.
# Useful when a client uses the instruction 'from <module> import *', since it avoids exporting internal names that
# start with an underscore.
__all__ = [
    'get_launch_configurations',
    'get_robot_versions',
    'get_xargs',
    'get_xarg',
    'get_xarg_names',
    'has_xarg',
    'declare_launch_arguments',
]

# Registry of robot versions and their '<xacro:arg>' elements (dict-of-dicts).
# Keys are version names; values map arg name -> arg metadata.
_robot_versions_xargs: Dict[str, Dict[str, Any]] = {}

# Core args (base for all versions)
_robot_versions_xargs['core'] = {
    'core_sim_file': {
        'default_value': PathJoinSubstitution(
            [FindPackageShare('robot_flart'), 'config', 'example_flart_core_simulation.yaml']
        ),
        'description': 'Path to simulation configuration for base+fork (default: example_flart_core_simulation.yaml)',
    },
    'body_use_visual': {
        'default_value': 'True',
        'description': 'Use visual element for the robot body (default: True)',
        'choices': ['True', 'true', 'False', 'false'],
    },
    'body_use_collision': {
        'default_value': 'True',
        'description': 'Use collision element for the robot body (default: True)',
        'choices': ['True', 'true', 'False', 'false'],
    },
    'body_use_inertial': {
        'default_value': 'True',
        'description': 'Use inertial element for the robot body. If False, a null inertia will be used (default: True)',
        'choices': ['True', 'true', 'False', 'false'],
    },
    'body_use_v_mesh': {
        'default_value': 'True',
        'description': 'Use mesh for body visual; otherwise primitives (default: True)',
        'choices': ['True', 'true', 'False', 'false'],
    },
    'body_use_c_mesh': {
        'default_value': 'False',
        'description': 'Use mesh for body collision; otherwise primitives (default: False)',
        'choices': ['True', 'true', 'False', 'false'],
    },
    'st_wheel_use_visual': {
        'default_value': 'True',
        'description': 'Use visual element for wheels (default: True)',
        'choices': ['True', 'true', 'False', 'false'],
    },
    'st_wheel_use_inertial': {
        'default_value': 'True',
        'description': 'Use inertial element for wheels. If False, a null inertia will be used (default: True)',
        'choices': ['True', 'true', 'False', 'false'],
    },
    'st_wheel_use_v_mesh': {
        'default_value': 'True',
        'description': 'Use mesh for wheel visual; otherwise primitives (default: True)',
        'choices': ['True', 'true', 'False', 'false'],
    },
    'fork_use_visual': {
        'default_value': 'True',
        'description': 'Use visual element for fork (default: True)',
        'choices': ['True', 'true', 'False', 'false'],
    },
    'fork_use_collision': {
        'default_value': 'True',
        'description': 'Use collision element for fork (default: True)',
        'choices': ['True', 'true', 'False', 'false'],
    },
    'fork_use_inertial': {
        'default_value': 'False',
        'description': 'Use inertial element for fork (default: False)',
        'choices': ['True', 'true', 'False', 'false'],
    },
    'fork_use_v_mesh': {
        'default_value': 'True',
        'description': 'Use mesh for fork visual; otherwise primitives (default: True)',
        'choices': ['True', 'true', 'False', 'false'],
    },
    'fork_use_c_mesh': {
        'default_value': 'False',
        'description': 'Use mesh for fork collision; otherwise primitives (default: False)',
        'choices': ['True', 'true', 'False', 'false'],
    },
}

# Version 'v0' extends core with extra args.
_robot_versions_xargs['v0'] = {
    **_robot_versions_xargs['core'],
    # Redefinition of the simulation file.
    'extras_sim_file': {
        'default_value': PathJoinSubstitution(
            [FindPackageShare('robot_flart'), 'config', 'example_flart_v0_simulation_extras.yaml']
        ),
        'description': "Path to simulation configuration for the 'extra' elements defined in the 'v0' version of the"
        "'flart' robot (default: example_flart_v0_simulation_extras.yaml)",
    },
    'top_platform_use_visual': {
        'default_value': 'True',
        'description': 'Include visual element for the top platform sensor body.',
        'choices': ['True', 'true', 'False', 'false'],
    },
    'top_platform_use_collision': {
        'default_value': 'True',
        'description': 'Include collision element for the top platform sensor body.',
        'choices': ['True', 'true', 'False', 'false'],
    },
    'top_platform_use_inertial': {
        'default_value': 'True',
        'description': 'Include inertial element for the top platform sensor body.',
        'choices': ['True', 'true', 'False', 'false'],
    },
    'top_platform_color': {
        'default_value': '',
        'description': "Optional color override 'r g b a'; empty keeps mesh color.",
    },
    'top_lidar_use_visual': {
        'default_value': 'True',
        'description': 'Include visual element for the sensor body.',
        'choices': ['True', 'true', 'False', 'false'],
    },
    'top_lidar_use_collision': {
        'default_value': 'True',
        'description': 'Include collision element for the sensor body.',
        'choices': ['True', 'true', 'False', 'false'],
    },
    'top_lidar_use_inertial': {
        'default_value': 'True',
        'description': 'Include inertial element for the sensor body.',
        'choices': ['True', 'true', 'False', 'false'],
    },
    'top_lidar_use_v_mesh': {
        'default_value': 'False',
        'description': 'Use a mesh for visual; if False, use a primitive.',
        'choices': ['True', 'true', 'False', 'false'],
    },
    'top_lidar_use_low_res_v_mesh': {
        'default_value': 'True',
        'description': 'Prefer low-resolution mesh for visual when using mesh.',
        'choices': ['True', 'true', 'False', 'false'],
    },
    # The low_res_v_mesh has its own color, so if color is set to empty the color of the low_res_v_mesh is used.
    'top_lidar_color': {
        'default_value': '',
        'description': "Optional color override 'r g b a'; empty keeps mesh color.",
    },
    'top_lidar_use_c_mesh': {
        'default_value': 'False',
        'description': 'Use a mesh for collision; if False, use a primitive.',
        'choices': ['True', 'true', 'False', 'false'],
    },
    'top_lidar_use_low_res_c_mesh': {
        'default_value': 'False',
        'description': 'Prefer low-resolution mesh for collision when using mesh.',
        'choices': ['True', 'true', 'False', 'false'],
    },
    'top_imu_use_visual': {
        'default_value': 'True',
        'description': 'Include visual element for the sensor.',
        'choices': ['True', 'true', 'False', 'false'],
    },
    'top_imu_use_collision': {
        'default_value': 'True',
        'description': 'Include collision element for the sensor.',
        'choices': ['True', 'true', 'False', 'false'],
    },
    'top_imu_use_inertial': {
        'default_value': 'True',
        'description': 'Include inertial element for the sensor.',
        'choices': ['True', 'true', 'False', 'false'],
    },
    'top_imu_use_v_mesh': {
        'default_value': 'True',
        'description': 'Use a mesh for visual; if False, use a primitive.',
        'choices': ['True', 'true', 'False', 'false'],
    },
    # The v_mesh has its own color, so if color is set to empty the color of the v_mesh is used.
    'top_imu_color': {'default_value': '', 'description': "Optional color override 'r g b a'; empty keeps mesh color."},
    'top_imu_use_c_mesh': {
        'default_value': 'False',
        'description': 'Use a mesh for collision; if False, use a primitive.',
        'choices': ['True', 'true', 'False', 'false'],
    },
    'rear_rgbd_use_visual': {
        'default_value': 'True',
        'description': 'Include visual element for the sensor.',
        'choices': ['True', 'true', 'False', 'false'],
    },
    'rear_rgbd_use_collision': {
        'default_value': 'True',
        'description': 'Include collision element for the sensor.',
        'choices': ['True', 'true', 'False', 'false'],
    },
    'rear_rgbd_use_inertial': {
        'default_value': 'True',
        'description': 'Include inertial element for the sensor.',
        'choices': ['True', 'true', 'False', 'false'],
    },
    'rear_rgbd_use_v_mesh': {
        'default_value': 'True',
        'description': 'Use a mesh for visual; if False, use a primitive.',
        'choices': ['True', 'true', 'False', 'false'],
    },
    # The v_mesh has its own color, so if color is set to empty the color of the v_mesh is used.
    'rear_rgbd_color': {
        'default_value': '0.5 0.5 0.5 1.0',
        'description': "Optional color override 'r g b a'; empty keeps mesh color.",
    },
    'rear_rgbd_use_c_mesh': {
        'default_value': 'False',
        'description': 'Use a mesh for collision; if False, use a primitive.',
        'choices': ['True', 'true', 'False', 'false'],
    },
}

################################################################################
# Non-opaque functions
################################################################################


def get_launch_configurations(robot_version: str) -> Dict[str, LaunchConfiguration]:
    """
    Return a dict of LaunchConfiguration objects for the given robot_version.
    Args:
        robot_version: Name of the robot version (str).
    Returns:
        Dict mapping arg name (str) to LaunchConfiguration object.
    """

    xargs = _robot_versions_xargs.get(robot_version, {})

    return {xarg_name: LaunchConfiguration(xarg_name) for xarg_name in xargs.keys()}


def get_robot_versions() -> List[str]:
    """
    Return the list of available robot versions.
    Returns:
        List of robot version names (str).
    """

    return list(_robot_versions_xargs.keys())


def get_xargs(robot_version: str) -> Dict[str, Any]:
    """
    Return the dict of xacro:arg metadata for a given robot_version.
    Args:
        robot_version: Name of the robot version (str).
    Returns:
        Dict mapping arg name (str) to arg metadata (dict).
    """

    if not robot_version or robot_version not in _robot_versions_xargs:
        return {}

    return copy.deepcopy(_robot_versions_xargs[robot_version])


def get_xarg(robot_version: str, xarg_name: str) -> Any:
    """
    Return the xacro:arg metadata for a given robot_version and xarg_name.
    Args:
        robot_version: Name of the robot version (str).
        xarg_name: Name of the xacro:arg (str).
    Returns:
        Arg metadata (dict) or None if not found.
    """
    if (
        not robot_version
        or not xarg_name
        or robot_version not in _robot_versions_xargs
        or xarg_name not in _robot_versions_xargs[robot_version]
    ):
        return {}

    return copy.deepcopy(_robot_versions_xargs[robot_version][xarg_name])


def get_xarg_names(robot_version: str) -> List[str]:
    """
    Return the list of xacro:arg names for a given robot_version.
    Args:
        robot_version: Name of the robot version (str).
    Returns:
        List of arg names (str).
    """
    if not robot_version or robot_version not in _robot_versions_xargs:
        return []

    return list(_robot_versions_xargs[robot_version].keys())


def has_xarg(robot_version: str, xarg_name: str) -> bool:
    """
    Check if a given robot_version defines the provided xarg_name.
    """
    if not robot_version or robot_version not in _robot_versions_xargs:
        return False

    return xarg_name in _robot_versions_xargs[robot_version]


################################################################################
# Opaque functions
################################################################################


def declare_launch_arguments(ctx: LaunchContext) -> List[LaunchDescriptionEntity]:
    """
    OpaqueFunction to declare description args based on robot_version.
    Args:
        ctx: LaunchContext passed to OpaqueFunction.
    Returns:
        List of DeclareLaunchArgument entities.
    """
    # ldes => (l)aunch (d)escription (e)ntitie(s)
    ldes: List[LaunchDescriptionEntity] = []

    # Get available versions for the flart robot and check that the requested one is among them.
    robot_version = LaunchConfiguration('robot_version').perform(ctx).strip()

    # If no robot_version is specified, return an empty list (no args to declare).
    if not robot_version:
        return ldes

    available_robot_versions = get_robot_versions()

    if robot_version not in available_robot_versions:
        ldes.append(
            LogInfo(
                msg=f"Version '{robot_version}' for the 'flart' robot is not available. "
                f'Available versions: {", ".join(available_robot_versions)}'
            )
        )

        return ldes

    # Use the '_robot_versions_xargs' directly here, no need to copy since we are not mutating anything and are inside
    # the module.

    for xarg_name, xarg_dict in _robot_versions_xargs[robot_version].items():
        kwargs = {'default_value': xarg_dict['default_value'], 'description': xarg_dict['description']}

        if 'choices' in xarg_dict:
            kwargs['choices'] = xarg_dict['choices']

        ldes.append(DeclareLaunchArgument(xarg_name, **kwargs))

    return ldes
