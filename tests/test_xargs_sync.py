import re
from pathlib import Path

from conftest import PACKAGE_DIR

from robot_forklift_simple_3sw import xargs

RESERVED_LAUNCH_ARGS = {'use_sim_mode', 'namespace', 'robot_name'}


def _xacro_arg_names(xacro_file: Path) -> set[str]:
    pattern = re.compile(r'<xacro:arg\s+name="([^"]+)"')
    return set(pattern.findall(xacro_file.read_text(encoding='utf-8')))


def test_xargs_versions_match_available_robot_versions() -> None:
    assert xargs.get_xargs_versions() == ['core', 'v1']


def test_core_xargs_match_core_xacro_args() -> None:
    core_arg_names = _xacro_arg_names(PACKAGE_DIR / 'urdf' / 'core.xacro') - RESERVED_LAUNCH_ARGS

    assert set(xargs.get_xargs('core')) == core_arg_names


def test_v1_xargs_match_core_and_v1_xacro_args() -> None:
    merged_arg_names = (
        _xacro_arg_names(PACKAGE_DIR / 'urdf' / 'core.xacro') | _xacro_arg_names(PACKAGE_DIR / 'urdf' / 'v1.xacro')
    ) - RESERVED_LAUNCH_ARGS

    assert set(xargs.get_xargs('v1')) == merged_arg_names
