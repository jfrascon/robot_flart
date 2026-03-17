"""Catalog manager for building xarg-based launch argument declarations based on robot version."""

import copy
from functools import lru_cache
from typing import Any, Dict, List

from launch.actions import DeclareLaunchArgument, LogInfo
from launch.substitutions import LaunchConfiguration

from launch import LaunchDescriptionEntity
from robot_forklift_simple_3sw.xargs_catalog.core import XARGS as CORE_XARGS
from robot_forklift_simple_3sw.xargs_catalog.v1 import XARGS as V1_XARGS

# Single source of truth for xarg catalog entries, keyed by robot version.
XARGS_CATALOG: Dict[str, Dict[str, Any]] = {CORE_XARGS['version']: CORE_XARGS, V1_XARGS['version']: V1_XARGS}


def declare_launch_arguments_for_robot_version(robot_version: str) -> List[LaunchDescriptionEntity]:
    """
    Declare launch arguments for a specific robot version.
    """
    ldes: List[LaunchDescriptionEntity] = []
    selected_robot_version = (robot_version or '').strip()

    if not selected_robot_version:
        return ldes

    available_robot_versions = get_robot_versions()

    if selected_robot_version not in available_robot_versions:
        ldes.append(
            LogInfo(
                msg=f"Version '{selected_robot_version}' for the 'fs3sw' robot is not available. "
                f'Available versions: {", ".join(available_robot_versions)}'
            )
        )

        return ldes

    # Retrive the xargs for the specified robot version.
    xargs = get_resolved_xargs(selected_robot_version)

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
    """Return xargs for a given robot version"""

    if not robot_version:
        return {}

    # Return a defensive copy so callers can mutate the result without corrupting the cached data.
    return copy.deepcopy(_resolve_xargs_cached(robot_version))


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


# The function _resolve_xargs_cached returns the resolved xargs for a version using a cache to optimize repeated calls
# with the same robot_version. To use the cache effectively, the function is decorated with @lru_cache, which allows it
# to store previously computed results for each robot_version.
# This means that if the function is called again with the same robot_version, it can return the cached result instead
# of recomputing it, improving performance.
# The maxsize=None argument indicates that the cache can grow without bound, which is suitable in this case since the
# number of robot versions is likely small and static.
#
# Why a cache is used here (lru_cache):
#
# Resolving xargs for a version may require following an inheritance chain (e.g., v2 -> v1 -> core), merging parent
# entries first and then overriding with child entries. This operation is deterministic for a given version and,
# during one launch execution, it is often called multiple times by different helpers (get_resolved_xargs,
# get_xarg_catalog_entry, declare_launch_arguments_for_robot_version, etc.).
#
# Decorating the resolver with @lru_cache avoids recomputing the same merge repeatedly for the same robot_version,
# reducing overhead and keeping call sites simple.
#
# maxsize=None means the cache is unbounded:
# - Pros: no eviction, always O(1)-like lookup after first computation.
# - Cons: entries stay for the process lifetime.
#
# In this module the set of versions is small and static (core, v1, ...), so unbounded cache is acceptable in practice.
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

    # `visit_order` is built while traversing child -> parent, for example:
    # - requested version `v2`
    # - chain: v2 -> v1 -> core
    # - visit_order: ['v2', 'v1', 'core']
    # To merge correctly, parent defaults are applied first and then child overrides,
    # by iterating `reversed(visit_order)`:
    # core, v1, v2.
    # If parent and child define the same xarg key, the child value wins.
    for version in reversed(visit_order):
        resolved.update(XARGS_CATALOG[version].get('args', {}))

    return resolved
