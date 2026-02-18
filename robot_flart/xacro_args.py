"""Backward-compatible facade over the xargs catalog manager."""

import copy
from typing import Any, Dict, List

from launch.substitutions import LaunchConfiguration

from launch import LaunchContext, LaunchDescriptionEntity
from robot_flart import xargs_catalog_manager as flart_xargs

__all__ = [
    'get_launch_configurations',
    'get_robot_versions',
    'get_xargs',
    'get_xarg',
    'get_xarg_names',
    'has_xarg',
    'declare_launch_arguments',
]


def declare_launch_arguments(ctx: LaunchContext) -> List[LaunchDescriptionEntity]:
    """Declare xarg launch arguments using the selected `robot_version` from launch context."""
    robot_version = LaunchConfiguration('robot_version').perform(ctx).strip()
    return flart_xargs.declare_launch_arguments_for_robot_version(ctx, robot_version)


def get_launch_configurations(robot_version: str) -> Dict[str, LaunchConfiguration]:
    """Return LaunchConfiguration objects for all resolved xargs of a robot version."""
    xargs = flart_xargs.get_resolved_xargs(robot_version)
    return {xarg_name: LaunchConfiguration(xarg_name) for xarg_name in xargs.keys()}


def get_robot_versions() -> List[str]:
    """Return the list of robot versions available in the xargs catalog."""
    return flart_xargs.get_robot_versions()


def get_xarg(robot_version: str, xarg_name: str) -> Any:
    """Return a deep-copied xarg entry for a given robot version and xarg name."""
    if not xarg_name:
        return {}

    xargs = flart_xargs.get_resolved_xargs(robot_version)
    if xarg_name not in xargs:
        return {}

    return copy.deepcopy(xargs[xarg_name])


def get_xarg_names(robot_version: str) -> List[str]:
    """Return all resolved xarg names for a robot version."""
    xargs = flart_xargs.get_resolved_xargs(robot_version)
    return list(xargs.keys())


def get_xargs(robot_version: str) -> Dict[str, Any]:
    """Return all resolved xargs for a robot version."""
    return flart_xargs.get_resolved_xargs(robot_version)


def has_xarg(robot_version: str, xarg_name: str) -> bool:
    """Return whether a resolved xarg exists for the given robot version."""
    if not xarg_name:
        return False

    xargs = flart_xargs.get_resolved_xargs(robot_version)
    return xarg_name in xargs
