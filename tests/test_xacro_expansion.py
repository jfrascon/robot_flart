from pathlib import Path

import pytest
from conftest import PACKAGE_DIR, run_bash


@pytest.mark.parametrize('robot_model', ['core', 'v1'])
def test_xacro_expands_to_valid_urdf(robot_model: str, tmp_path: Path) -> None:
    urdf_path = tmp_path / f'{robot_model}.urdf'
    xacro_path = PACKAGE_DIR / 'urdf' / f'{robot_model}.xacro'

    result = run_bash(f'xacro "{xacro_path}" > "{urdf_path}" && check_urdf "{urdf_path}"')

    output = result.stdout + result.stderr

    assert result.returncode == 0, output
    assert urdf_path.is_file(), output
    assert 'Successfully Parsed XML' in output, output


def test_launch_show_args_lists_expected_robot_models() -> None:
    result = run_bash('ros2 launch robot_forklift_simple_3sw robot.launch.py --show-args')
    output = result.stdout + result.stderr

    assert result.returncode == 0, output
    assert "'robot_model'" in output, output
    assert 'core' in output, output
    assert 'v1' in output, output
