"""Work with the xargs used by the fs3sw package.

This package defines a base robot version called ``core``. The ``core`` version has
its own xacro file, which contains the base robot description.

Other robot versions, such as ``v1``, are created by extending that base xacro
description with more xacro content. In this way, new robot versions can add more
features on top of ``core``.

Many parts of the robot description are configurable through ``xacro:arg`` entries.
Some of those arguments belong to the base ``core`` description, and others belong to
the xacro files that add the extra content of a specific robot version.

To let the user configure how the robot description is rendered from the launch file,
the package must declare launch arguments for those xacro arguments.

The value of each launch argument, either its default value or a value given by the
user, is then passed to the ``xacro`` command so it can be used when generating the
final ``robot_description``.

To be able to declare one launch argument and one launch configuration for each
``xacro:arg`` used by each robot version, this package uses a YAML-based system.

Each robot version has one YAML file. That file lists the xargs used by that robot
version together with their default values and other metadata, such as their
description and optional choices.

This module reads those YAML files and provides the xargs that belong to one robot
version, so the launch files can declare the needed launch arguments, build the
corresponding launch configurations, and pass their values to the ``xacro`` command.
In this way, the YAML-based system makes it possible to define those launch arguments
and launch configurations dynamically for the robot version selected at launch time.
"""

from pathlib import Path
from typing import Any, Dict, List

import ros2_launch_helpers as rlh
import yaml
from ament_index_python.packages import get_package_share_directory
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration

from launch import LaunchDescriptionEntity

# The required fields for each xarg configuration. Each xarg must have these fields.
REQUIRED_XARG_FIELDS = {'default_value', 'description'}
# The allowed fields for each xarg configuration. Each xarg can have these fields, but they are not required.
OPTIONAL_XARG_FIELDS = {'choices'}


def declare_launch_arguments(robot_version: str) -> List[LaunchDescriptionEntity]:
    """Return the launch argument declarations for the xargs of one robot version."""
    ldes: List[LaunchDescriptionEntity] = []

    for xarg_name, xarg_cfg in get_xargs(robot_version).items():
        kwargs = {'default_value': xarg_cfg['default_value'], 'description': xarg_cfg['description']}

        if 'choices' in xarg_cfg:
            kwargs['choices'] = xarg_cfg['choices']

        ldes.append(DeclareLaunchArgument(xarg_name, **kwargs))

    return ldes


def get_launch_configurations(robot_version: str) -> Dict[str, LaunchConfiguration]:
    """Return launch configurations for the xargs of one robot version."""
    return {xarg_name: LaunchConfiguration(xarg_name) for xarg_name in get_xargs(robot_version).keys()}


def get_robot_versions() -> List[str]:
    """Return available robot versions from xacro files under urdf."""
    try:
        urdf_dir = _get_urdf_dir()
    except FileNotFoundError:
        return []

    return sorted(path.stem for path in urdf_dir.glob('*.xacro') if path.is_file())


def get_xargs(robot_version: str) -> Dict[str, Dict[str, Any]]:
    """Return the xargs mapping for the requested robot version."""
    robot_version = (robot_version or '').strip()

    if not robot_version:
        raise ValueError("'robot_version' must be a non-empty string.")

    # Always load the core xargs first, next load the version-specific xargs, and merge them with
    # version-specific xargs taking precedence.
    core_xargs = _load_xargs_yaml('core')

    if robot_version == 'core':
        return core_xargs

    version_xargs = _load_xargs_yaml(robot_version)

    return {**core_xargs, **version_xargs}


def get_xargs_versions() -> List[str]:
    """Return available versions from internal xargs YAML files."""
    # The robot versions are determined by the YAML file names under the internal xargs directory,
    # excluding the file extension. For example, xargs/core.yaml corresponds to the "core" robot
    # version.
    try:
        xargs_dir = _get_xargs_dir()
    except FileNotFoundError:
        return []

    return sorted(path.stem for path in xargs_dir.glob('*.yaml') if path.is_file())


def _check_xarg_fields(xarg_name: str, xarg_cfg: Dict[str, Any], xargs_file: Path) -> None:
    """Validate required fields, allowed fields and field types for one xarg."""
    allowed_fields = REQUIRED_XARG_FIELDS.union(OPTIONAL_XARG_FIELDS)
    # Get a set of the fields that are present in the xarg configuration. This will be used to check
    # for unknown fields and missing required fields.
    present_fields = set(xarg_cfg.keys())

    # Check for fields that are not part of the supported xargs schema.
    unknown_fields = present_fields.difference(allowed_fields)

    if unknown_fields:
        raise ValueError(
            f'Xarg {xarg_name!r} in file {xargs_file!r} has fields that are not allowed: '
            f'{sorted(unknown_fields)}. Allowed fields: {sorted(allowed_fields)}.'
        )

    # At this point we know that all fields in the xarg configuration are part of the supported
    # xargs schema, but some required fields may still be missing. Check for that next.

    # Check for missing required fields. If any are missing, raise an error.
    missing_fields = REQUIRED_XARG_FIELDS.difference(present_fields)

    if missing_fields:
        raise ValueError(
            f'Xarg {xarg_name!r} in file {xargs_file!r} is missing required fields: {sorted(missing_fields)}.'
        )

    # At this point we know that all required fields are present and all fields are part of the
    # supported xargs schema, but some fields may have invalid types. Check for that next.

    for field_name, field_value in xarg_cfg.items():
        if field_name == 'choices':
            if not isinstance(field_value, list) or not all(isinstance(choice, str) for choice in field_value):
                raise ValueError(
                    f"Field 'choices' for xarg {xarg_name!r} in file {xargs_file!r} must be a list of strings."
                )
        else:
            if not isinstance(field_value, str):
                raise ValueError(
                    f'Field {field_name!r} for xarg {xarg_name!r} in file {xargs_file!r} must be a string.'
                )


def _get_xargs_dir() -> Path:
    """Return the directory that stores the internal xargs YAML files."""
    xargs_dir = Path(__file__).resolve().parent.joinpath('xargs')

    if not xargs_dir.is_dir():
        raise FileNotFoundError(f'Xargs directory {xargs_dir!r} not found.')

    return xargs_dir


def _get_urdf_dir() -> Path:
    """Return the directory that stores robot xacro files."""
    urdf_dir = Path(get_package_share_directory('robot_forklift_simple_3sw')).joinpath('urdf')

    if not urdf_dir.is_dir():
        raise FileNotFoundError(f'URDF directory {urdf_dir!r} not found.')

    return urdf_dir


def _load_xargs_yaml(robot_version: str) -> Dict[str, Dict[str, Any]]:
    """Load xargs for one robot version directly from its YAML file."""
    # Each filename under the internal xargs directory corresponds to a robot version, and the file
    # content is a YAML mapping of xarg names to their configurations.
    # For example, xargs/core.yaml corresponds to the "core" robot version, and its content
    # is a mapping of xarg names to their configurations.
    xargs_file = _get_xargs_dir().joinpath(f'{robot_version}.yaml')

    if not xargs_file.is_file():
        raise FileNotFoundError(f'Xargs file {xargs_file!r} not found.')

    # Load the YAML file content as a mapping of xarg names to their configurations.
    # If the file is empty, treat it as an empty mapping.
    with xargs_file.open('r', encoding='utf-8') as file:
        loaded = yaml.safe_load(file) or {}

    if not isinstance(loaded, dict):
        raise ValueError(f'Xargs file {xargs_file!r} must contain a YAML mapping.')

    # Validate the structure of the loaded xargs.
    # Each xarg configuration must be a mapping.
    for xarg_name, xarg_cfg in loaded.items():
        if not isinstance(xarg_cfg, dict):
            raise ValueError(f'Xarg {xarg_name!r} in file {xargs_file!r} must be a YAML mapping.')

        _check_xarg_fields(xarg_name, xarg_cfg, xargs_file)

        default_value = xarg_cfg['default_value']

        if default_value.startswith('package://') or default_value.startswith('file://'):
            xarg_cfg['default_value'] = rlh.resolve_file(default_value)

    return loaded
