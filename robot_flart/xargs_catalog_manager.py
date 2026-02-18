import copy
from functools import lru_cache
from typing import Any, Dict, List

from launch.actions import DeclareLaunchArgument, LogInfo
from launch.substitutions import LaunchConfiguration

from launch import LaunchContext, LaunchDescriptionEntity
from robot_flart.xargs_catalog.core import XARGS as CORE_XARGS
from robot_flart.xargs_catalog.v0 import XARGS as V0_XARGS

# Single source of truth for xarg catalog entries, keyed by robot version.
XARGS_CATALOG: Dict[str, Dict[str, Any]] = {CORE_XARGS['version']: CORE_XARGS, V0_XARGS['version']: V0_XARGS}


def declare_launch_arguments_for_robot_version(_: LaunchContext, robot_version: str) -> List[LaunchDescriptionEntity]:
    """Declare launch arguments for a specific robot version."""
    # Keep `robot_version` as an explicit argument: putting it in LaunchContext (e.g. SetLaunchConfiguration)
    # introduces mutable global state and order-dependent behavior.
    ldes: List[LaunchDescriptionEntity] = []
    robot_version = (robot_version or '').strip()

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

    xargs = get_resolved_xargs(robot_version)

    for xarg_name, xarg_dict in xargs.items():
        kwargs = {'default_value': xarg_dict['default_value'], 'description': xarg_dict['description']}
        if 'choices' in xarg_dict:
            kwargs['choices'] = xarg_dict['choices']

        ldes.append(DeclareLaunchArgument(xarg_name, **kwargs))

    return ldes


def get_launch_configurations_for_robot_version(robot_version: str) -> Dict[str, LaunchConfiguration]:
    """Build LaunchConfiguration objects for all resolved xargs of a robot version."""
    return {xarg_name: LaunchConfiguration(xarg_name) for xarg_name in get_resolved_xargs(robot_version).keys()}


def get_resolved_xargs(robot_version: str) -> Dict[str, Any]:
    """Return xargs for a version after resolving inheritance."""
    return _resolve_xargs(robot_version)


def get_robot_versions() -> List[str]:
    """Return all robot versions available in the catalog."""
    return list(XARGS_CATALOG.keys())


def get_xarg_catalog() -> Dict[str, Dict[str, Any]]:
    """Return the raw xargs catalog."""
    return copy.deepcopy(XARGS_CATALOG)


def get_xarg_catalog_entry(robot_version: str) -> Dict[str, Any]:
    """
    Return the xarg catalog entry as declared in the catalog, without resolving inheritance.
    The returned mapping keeps the original structure for that version, including
    its local ``args`` and optional ``extends`` reference.
    """
    if not robot_version:
        return {}

    xarg_catalog_entry = XARGS_CATALOG.get(robot_version)

    if not xarg_catalog_entry:
        return {}

    return copy.deepcopy(xarg_catalog_entry)


# ------------------
# Internal helpers (private API)


def _resolve_xargs(robot_version: str) -> Dict[str, Any]:
    """Resolve xargs for a robot version, including inherited args through 'extends'."""
    if not robot_version:
        return {}

    # Return a defensive copy so callers can mutate the result without corrupting the cached data.
    return copy.deepcopy(_resolve_xargs_cached(robot_version))


#
# Why we use lru_cache here:
#
# Resolving xargs for a version may require following an inheritance chain
# (e.g., v1 -> v0 -> core), merging parent entries first and then overriding
# with child entries. This operation is deterministic for a given version and,
# during one launch execution, it is often called multiple times by different
# helpers (get_resolved_xargs, get_xarg_catalog_entry, declare_launch_arguments_for_robot_version, etc.).
#
# Decorating the resolver with @lru_cache avoids recomputing the same merge
# repeatedly for the same robot_version, reducing overhead and keeping call
# sites simple.
#
# maxsize=None means the cache is unbounded:
# - Pros: no eviction, always O(1)-like lookup after first computation.
# - Cons: entries stay for the process lifetime.
#
# In this module the set of versions is small and static (core, v0, ...), so
# unbounded cache is acceptable in practice.
#
# Important caveat:
# If XARGS_CATALOG is mutated at runtime (not expected in normal usage),
# cached results may become stale. In that uncommon case, clear the cache with:
# _resolve_xargs_cached.cache_clear()
#
@lru_cache(maxsize=None)
def _resolve_xargs_cached(robot_version: str) -> Dict[str, Any]:
    """
    Return resolved xargs for a version using cached inheritance resolution.

    Resolution walks the `extends` chain from child to ancestors, detects inheritance cycles,
    and then merges args from ancestor to child so child keys override parent keys.
    """
    if not robot_version:
        return {}

    resolved: Dict[str, Any] = {}
    # Keep both:
    # - `visit_order` for deterministic cycle path reporting and ordered merge.
    # - `visited_set` for O(1) repeated-version detection.
    visit_order: List[str] = []
    visited_set = set()
    current_version = robot_version

    # Traverse the inheritance chain: version -> parent -> grandparent -> ...
    while current_version:
        if current_version in visited_set:
            cycle_start_idx = visit_order.index(current_version)
            cycle_path = visit_order[cycle_start_idx:] + [current_version]
            raise ValueError(f'Circular xarg inheritance detected: {" -> ".join(cycle_path)}')

        xarg_catalog_entry = XARGS_CATALOG.get(current_version)

        if not xarg_catalog_entry:
            # Keep previous behavior: unknown root returns {}, unknown parent is ignored.
            if current_version == robot_version:
                return {}
            break

        visit_order.append(current_version)
        visited_set.add(current_version)
        current_version = xarg_catalog_entry.get('extends')

    # Merge from ancestor to child so child definitions override parent definitions.
    # Example: if v0 extends core and both define the same key, v0 wins.
    for version in reversed(visit_order):
        resolved.update(XARGS_CATALOG[version].get('args', {}))

    return resolved


# ------------------
# Backward-compatible API surface (legacy)
# OBSOLETE / TO DELETE:
# Legacy wrappers have been moved to `robot_flart/xacro_args.py`.
# Keep this section commented as a migration marker until full cleanup.
#
# def declare_launch_arguments(ctx: LaunchContext) -> List[LaunchDescriptionEntity]:
#     robot_version = LaunchConfiguration('robot_version').perform(ctx).strip()
#     return declare_launch_arguments_for_robot_version(ctx, robot_version)
#
# def get_launch_configurations(robot_version: str) -> Dict[str, LaunchConfiguration]:
#     xargs = get_resolved_xargs(robot_version)
#     return {xarg_name: LaunchConfiguration(xarg_name) for xarg_name in xargs.keys()}
#
# def get_xarg(robot_version: str, xarg_name: str) -> Any:
#     if not xarg_name:
#         return {}
#     xargs = get_resolved_xargs(robot_version)
#     if xarg_name not in xargs:
#         return {}
#     return copy.deepcopy(xargs[xarg_name])
#
# def get_xarg_names(robot_version: str) -> List[str]:
#     xargs = get_resolved_xargs(robot_version)
#     return list(xargs.keys())
#
# def get_xargs(robot_version: str) -> Dict[str, Any]:
#     return get_resolved_xargs(robot_version)
#
# def has_xarg(robot_version: str, xarg_name: str) -> bool:
#     if not xarg_name:
#         return False
#     xargs = get_resolved_xargs(robot_version)
#     return xarg_name in xargs
