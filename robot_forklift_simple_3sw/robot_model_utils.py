"""Helpers to work with the robot models provided by this package.

This package defines a base robot model called ``core``. The ``core`` model has
its own xacro file, which contains the base robot description.

Other robot models, such as ``v1``, are created by extending that base xacro
description with more xacro content. In this way, new robot models can add more
features on top of ``core``.

Many parts of the robot description are configurable through ``xacro:arg``
entries. Some of those arguments belong to the base ``core`` description, and
others belong to the xacro files that add the extra content of a specific robot
model.

To let the user configure how the robot description is rendered from the launch
file, the package must declare launch arguments for those xacro arguments.

The value of each launch argument, either its default value or a value given by
the user, is then passed to the ``xacro`` command so it can be used when
generating the final ``robot_description``.

To be able to declare one launch argument and one launch configuration for each
``xacro:arg`` used by each robot model, this package uses a YAML-based system.

Each robot model has one YAML file. That file lists the xargs used by that
robot model together with their default values and other metadata, such as
their description and optional choices.

This module provides two groups of helpers:
- helpers that work with the robot models provided by the package xacro files
- helpers that read the xargs YAML files for one robot model
"""

from pathlib import Path
from typing import Any, Dict, List

import ros2_launch_helpers as rlh
import yaml
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration

from launch import LaunchDescriptionEntity


def declare_launch_arguments(robot_model: str) -> List[LaunchDescriptionEntity]:
    """Return the launch argument declarations for the xargs of one robot model."""
    ldes: List[LaunchDescriptionEntity] = []

    for xarg_name, xarg_cfg in get_xargs(robot_model).items():
        kwargs = {'default_value': xarg_cfg['default_value'], 'description': xarg_cfg['description']}

        if 'choices' in xarg_cfg:
            kwargs['choices'] = xarg_cfg['choices']

        ldes.append(DeclareLaunchArgument(xarg_name, **kwargs))

    return ldes


def get_launch_configurations(robot_model: str) -> Dict[str, LaunchConfiguration]:
    """Return launch configurations for the xargs of one robot model."""
    return {xarg_name: LaunchConfiguration(xarg_name) for xarg_name in get_xargs(robot_model).keys()}


def get_robot_models() -> List[str]:
    """Return the robot models provided by the package xacro files."""
    try:
        urdf_dir = _get_urdf_dir()
    except FileNotFoundError:
        return []

    return sorted(path.stem for path in urdf_dir.glob('*.xacro') if path.is_file())


def get_robot_models_with_xargs() -> List[str]:
    """Return the robot models that provide an internal xargs YAML file."""
    try:
        xargs_dir = _get_xargs_dir()
    except FileNotFoundError:
        return []

    return sorted(path.stem for path in xargs_dir.glob('*.yaml') if path.is_file())


def get_xargs(robot_model: str) -> Dict[str, Dict[str, Any]]:
    """Return the xargs mapping for the requested robot model."""
    robot_model = (robot_model or '').strip()

    if not robot_model:
        raise ValueError("'robot_model' must be a non-empty string.")

    # Always load the core xargs first, next load the model-specific xargs, and
    # merge them with model-specific xargs taking precedence.
    core_xargs = _load_xargs_yaml('core')

    if robot_model == 'core':
        return core_xargs

    model_xargs = _load_xargs_yaml(robot_model)

    return {**core_xargs, **model_xargs}


def robot_model_exists(robot_model: str) -> bool:
    """Return whether one robot model is provided by the package xacro files."""
    robot_model = (robot_model or '').strip()

    if not robot_model:
        return False

    return robot_model in get_robot_models()


def _check_xarg_fields(xarg_name: str, xarg_cfg: Dict[str, Any], xargs_file: Path) -> None:
    """Validate required fields, allowed fields and field types for one xarg."""
    # Each xarg must define these fields. Additional fields are only accepted
    # when they are part of the supported xargs schema.
    required_xarg_fields = {'default_value', 'description'}
    optional_xarg_fields = {'choices'}
    allowed_fields = required_xarg_fields.union(optional_xarg_fields)
    # Get a set of the fields that are present in the xarg configuration. This
    # will be used to check for unknown fields and missing required fields.
    present_fields = set(xarg_cfg.keys())

    # Check for fields that are not part of the supported xargs schema.
    unknown_fields = present_fields.difference(allowed_fields)

    if unknown_fields:
        raise ValueError(
            f'Xarg {xarg_name!r} in file {xargs_file!r} has fields that are not allowed: '
            f'{sorted(unknown_fields)}. Allowed fields: {sorted(allowed_fields)}.'
        )

    # At this point we know that all fields in the xarg configuration are part
    # of the supported xargs schema, but some required fields may still be
    # missing. Check for that next.
    missing_fields = required_xarg_fields.difference(present_fields)

    if missing_fields:
        raise ValueError(
            f'Xarg {xarg_name!r} in file {xargs_file!r} is missing required fields: {sorted(missing_fields)}.'
        )

    # At this point we know that all required fields are present and all fields
    # are part of the supported xargs schema, but some fields may have invalid
    # types. Check for that next.
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


def _get_urdf_dir() -> Path:
    """Return the directory that stores robot xacro files."""
    urdf_dir = Path(__file__).resolve().parent.parent.joinpath('urdf')

    if not urdf_dir.is_dir():
        raise FileNotFoundError(f'URDF directory {urdf_dir!r} not found.')

    return urdf_dir


def _get_xargs_dir() -> Path:
    """Return the directory that stores the internal xargs YAML files."""
    xargs_dir = Path(__file__).resolve().parent.joinpath('xargs')

    if not xargs_dir.is_dir():
        raise FileNotFoundError(f'Xargs directory {xargs_dir!r} not found.')

    return xargs_dir


def _load_xargs_yaml(robot_model: str) -> Dict[str, Dict[str, Any]]:
    """Load xargs for one robot model directly from its YAML file."""
    # Each filename under the internal xargs directory corresponds to a robot
    # model, and the file content is a YAML mapping of xarg names to their
    # configurations. For example, xargs/core.yaml corresponds to the "core"
    # robot model, and its content is a mapping of xarg names to their
    # configurations.
    xargs_file = _get_xargs_dir().joinpath(f'{robot_model}.yaml')

    if not xargs_file.is_file():
        raise FileNotFoundError(f'Xargs file {xargs_file!r} not found.')

    # Load the YAML file content as a mapping of xarg names to their
    # configurations. If the file is empty, treat it as an empty mapping.
    with xargs_file.open('r', encoding='utf-8') as file:
        loaded = yaml.safe_load(file) or {}

    if not isinstance(loaded, dict):
        raise ValueError(f'Xargs file {xargs_file!r} must contain a YAML mapping.')

    # Validate the structure of the loaded xargs. Each xarg configuration must
    # be a mapping.
    for xarg_name, xarg_cfg in loaded.items():
        if not isinstance(xarg_cfg, dict):
            raise ValueError(f'Xarg {xarg_name!r} in file {xargs_file!r} must be a YAML mapping.')

        _check_xarg_fields(xarg_name, xarg_cfg, xargs_file)

        default_value = xarg_cfg['default_value']

        if default_value.startswith('package://') or default_value.startswith('file://'):
            xarg_cfg['default_value'] = rlh.resolve_file(default_value)

    return loaded
