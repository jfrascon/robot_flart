"""Catalog manager for building rosgz bridge channel configurations by robot version."""

import copy
from functools import lru_cache
from typing import Any, Callable, Dict, List, Tuple

from robot_flart.rosgz_bridge_catalog.core import ROSGZ_BRIDGE_CATALOG_ENTRY as CORE_ROSGZ_BRIDGE_CATALOG_ENTRY
from robot_flart.rosgz_bridge_catalog.v0 import ROSGZ_BRIDGE_CATALOG_ENTRY as V0_ROSGZ_BRIDGE_CATALOG_ENTRY

ROSGZ_BRIDGE_CATALOG: Dict[str, Dict[str, Any]] = {
    CORE_ROSGZ_BRIDGE_CATALOG_ENTRY['version']: CORE_ROSGZ_BRIDGE_CATALOG_ENTRY,
    V0_ROSGZ_BRIDGE_CATALOG_ENTRY['version']: V0_ROSGZ_BRIDGE_CATALOG_ENTRY,
}


def build_bridge_config_for_robot_version(
    robot_version: str, namespace: str, robot_name: str, sim_files: Dict[str, str]
) -> Tuple[List[Dict[str, Any]], List[str]]:
    """Build the full rosgz bridge config for a robot version by resolving profile inheritance."""
    robot_version = (robot_version or '').strip()

    if not robot_version:
        return ([], ['Bridge profile cannot be empty'])

    available_versions = get_bridge_catalog_versions()
    if robot_version not in available_versions:
        return (
            [],
            [f"Bridge profile '{robot_version}' is not available. Available profiles: {', '.join(available_versions)}"],
        )

    channels: List[Dict[str, Any]] = []
    messages: List[str] = []

    for builder_spec in get_bridge_builders_for_robot_version(robot_version):
        sim_file_key = builder_spec['sim_file_key']
        create_cfg: Callable[[str, str, str], Tuple[List[Dict[str, Any]], str]] = builder_spec['create_cfg']
        sim_file = (sim_files.get(sim_file_key, '') or '').strip()

        cfg, msg = create_cfg(sim_file, namespace, robot_name)

        if cfg:
            channels.extend(cfg)
        if msg:
            messages.append(msg)

    return (channels, messages)


def get_bridge_builders_for_robot_version(robot_version: str) -> List[Dict[str, Any]]:
    """Return resolved builder specs for a bridge profile after resolving inheritance."""
    return _resolve_bridge_builders(robot_version)


def get_bridge_catalog() -> Dict[str, Dict[str, Any]]:
    """Return a deep copy of the raw rosgz bridge catalog."""
    return copy.deepcopy(ROSGZ_BRIDGE_CATALOG)


def get_bridge_catalog_entry(robot_version: str) -> Dict[str, Any]:
    """Return one bridge catalog entry as declared in the catalog (without resolving inheritance)."""
    if not robot_version:
        return {}

    bridge_catalog_entry = ROSGZ_BRIDGE_CATALOG.get(robot_version)

    if not bridge_catalog_entry:
        return {}

    return copy.deepcopy(bridge_catalog_entry)


def get_bridge_catalog_versions() -> List[str]:
    """Return all bridge profile versions available in the rosgz bridge catalog."""
    return list(ROSGZ_BRIDGE_CATALOG.keys())


# ------------------
# Internal helpers (private API)


def _resolve_bridge_builders(robot_version: str) -> List[Dict[str, Any]]:
    """Resolve bridge builders for a robot version, including inherited profile builders."""
    if not robot_version:
        return []

    # Return a defensive copy so callers can mutate the result safely.
    return copy.deepcopy(_resolve_bridge_builders_cached(robot_version))


@lru_cache(maxsize=None)
def _resolve_bridge_builders_cached(robot_version: str) -> Tuple[Dict[str, Any], ...]:
    """Return resolved bridge builders for a version using cached inheritance resolution."""
    if not robot_version:
        return ()

    visit_order: List[str] = []
    visited_set = set()
    current_version = robot_version

    while current_version:
        if current_version in visited_set:
            cycle_start_idx = visit_order.index(current_version)
            cycle_path = visit_order[cycle_start_idx:] + [current_version]
            raise ValueError(f'Circular bridge profile inheritance detected: {" -> ".join(cycle_path)}')

        bridge_catalog_entry = ROSGZ_BRIDGE_CATALOG.get(current_version)

        if not bridge_catalog_entry:
            if current_version == robot_version:
                return ()
            break

        visit_order.append(current_version)
        visited_set.add(current_version)
        current_version = bridge_catalog_entry.get('extends')

    resolved_builders: List[Dict[str, Any]] = []
    for version in reversed(visit_order):
        resolved_builders.extend(ROSGZ_BRIDGE_CATALOG[version].get('builders', ()))

    # Use tuple for cached immutability.
    return tuple(dict(spec) for spec in resolved_builders)
