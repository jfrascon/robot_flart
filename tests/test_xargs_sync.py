import re
from pathlib import Path

from conftest import PACKAGE_DIR

from robot_forklift_simple_3sw import robot_model_utils

RESERVED_LAUNCH_ARGS = {'use_sim_mode', 'namespace', 'robot_name'}


def _xacro_arg_names(xacro_file: Path) -> set[str]:
    pattern = re.compile(r'<xacro:arg\s+name="([^"]+)"')
    return set(pattern.findall(xacro_file.read_text(encoding='utf-8')))


def test_xargs_models_match_available_robot_models() -> None:
    assert robot_model_utils.get_robot_models() == ['core', 'v1']
    assert robot_model_utils.get_robot_models_with_xargs() == ['core', 'v1']


def test_robot_model_exists_matches_available_robot_models() -> None:
    assert robot_model_utils.robot_model_exists('core')
    assert robot_model_utils.robot_model_exists('v1')
    assert not robot_model_utils.robot_model_exists('')
    assert not robot_model_utils.robot_model_exists('v2')


def test_core_xargs_match_core_xacro_args() -> None:
    core_arg_names = _xacro_arg_names(PACKAGE_DIR / 'urdf' / 'core.xacro') - RESERVED_LAUNCH_ARGS

    assert set(robot_model_utils.get_xargs('core')) == core_arg_names


def test_v1_xargs_match_core_and_v1_xacro_args() -> None:
    merged_arg_names = (
        _xacro_arg_names(PACKAGE_DIR / 'urdf' / 'core.xacro') | _xacro_arg_names(PACKAGE_DIR / 'urdf' / 'v1.xacro')
    ) - RESERVED_LAUNCH_ARGS

    assert set(robot_model_utils.get_xargs('v1')) == merged_arg_names
