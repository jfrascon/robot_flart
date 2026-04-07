from pathlib import Path

import pytest
from conftest import PACKAGE_DIR, run_bash


@pytest.mark.parametrize('robot_model', ['base', 'sensors1'])
def test_xacro_expands_to_valid_urdf(robot_model: str, tmp_path: Path) -> None:
    urdf_path = tmp_path / f'{robot_model}.urdf'
    xacro_path = PACKAGE_DIR / 'urdf' / 'models' / f'model_{robot_model}.xacro'

    result = run_bash(f'xacro "{xacro_path}" > "{urdf_path}" && check_urdf "{urdf_path}"')

    output = result.stdout + result.stderr

    assert result.returncode == 0, output
    assert urdf_path.is_file(), output
    assert 'Successfully Parsed XML' in output, output


@pytest.mark.parametrize(
    ('launch_file', 'model_specific_xarg'),
    [('model_base.launch.py', 'body_use_inertial'), ('model_sensors1.launch.py', 'top_platform_use_visual')],
)
def test_launch_show_args_lists_expected_static_launch_arguments(launch_file: str, model_specific_xarg: str) -> None:
    result = run_bash(f'ros2 launch robot_forki3 {launch_file} --show-args')
    output = result.stdout + result.stderr

    assert result.returncode == 0, output
    assert "'use_sim_time'" in output, output
    assert "'robot_name'" in output, output
    assert "'robot_model'" in output, output
    assert "'params_file'" in output, output
    assert "'bridge_file'" in output, output
    assert f"'{model_specific_xarg}'" in output, output
