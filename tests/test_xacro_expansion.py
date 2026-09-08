from pathlib import Path

import pytest
import yaml

from conftest import PACKAGE_DIR
from conftest import run_bash

ENABLED_SIMULATION_TOPIC_CASES = (
    ('base', 'base_velocity_controller', ('topic',), 'base_velocity_controller'),
    ('base', 'pose_publisher', ('topic', 'topic_with_covariance', 'tf_topic'), 'pose_publisher'),
    (
        'base',
        'base_steerable_wheel_0_steering_joint_controller',
        ('topic',),
        'base_steerable_wheel_0_steering_joint_controller',
    ),
    (
        'base',
        'base_steerable_wheel_1_steering_joint_controller',
        ('topic',),
        'base_steerable_wheel_1_steering_joint_controller',
    ),
    (
        'base',
        'base_steerable_wheel_2_steering_joint_controller',
        ('topic',),
        'base_steerable_wheel_2_steering_joint_controller',
    ),
    (
        'base',
        'base_steerable_wheel_0_rotation_joint_controller',
        ('topic',),
        'base_steerable_wheel_0_rotation_joint_controller',
    ),
    (
        'base',
        'base_steerable_wheel_1_rotation_joint_controller',
        ('topic',),
        'base_steerable_wheel_1_rotation_joint_controller',
    ),
    (
        'base',
        'base_steerable_wheel_2_rotation_joint_controller',
        ('topic',),
        'base_steerable_wheel_2_rotation_joint_controller',
    ),
    ('base', 'fork_controller', ('topic',), 'fork_controller'),
    ('base', 'joint_state_publisher', ('topic',), 'joint_state_publisher'),
    ('sensors1', 'fork_camera_rgbd', ('base_topic',), 'realsense_d435_rgbd'),
    ('sensors1', 'front_top_lidar', ('base_topic',), 'robosense_airy'),
    ('sensors1', 'front_top_lidar_imu', ('topic',), 'robosense_airy'),
    ('sensors1', 'back_top_lidar', ('base_topic',), 'robosense_airy'),
    ('sensors1', 'back_top_lidar_imu', ('topic',), 'robosense_airy'),
    ('sensors1', 'back_bottom_lidar', ('topic',), 'sick_s300'),
    ('sensors1', 'joint_state_publisher', ('topic',), 'joint_state_publisher'),
)


@pytest.mark.parametrize('robot_model', ['base', 'sensors1'])
def test_xacro_expands_to_valid_urdf(robot_model: str, tmp_path: Path) -> None:
    urdf_path = tmp_path / f'{robot_model}.urdf'
    xacro_path = PACKAGE_DIR / 'urdf' / 'models' / f'model_{robot_model}.xacro'

    result = run_bash(f'xacro "{xacro_path}" > "{urdf_path}" && check_urdf "{urdf_path}"')

    output = result.stdout + result.stderr

    assert result.returncode == 0, output
    assert urdf_path.is_file(), output
    assert 'Successfully Parsed XML' in output, output


@pytest.mark.parametrize('robot_model', ['base', 'sensors1'])
def test_simulation_xacro_expands_to_valid_urdf(robot_model: str, tmp_path: Path) -> None:
    urdf_path = tmp_path / f'{robot_model}_simulation.urdf'
    xacro_path = PACKAGE_DIR / 'urdf' / 'models' / f'model_{robot_model}.xacro'
    sim_path = PACKAGE_DIR / 'config' / f'model_{robot_model}' / 'default_simulation.yaml'

    result = run_bash(
        f'xacro "{xacro_path}" sim_file:="{sim_path}" > "{urdf_path}" && check_urdf "{urdf_path}"'
    )
    output = result.stdout + result.stderr

    assert result.returncode == 0, output
    assert 'Successfully Parsed XML' in output, output
    assert 'gz::sim::systems::OdometryPublisher' in urdf_path.read_text(encoding='utf-8')


@pytest.mark.parametrize('robot_model', ['base', 'sensors1'])
def test_whitespace_only_sim_file_builds_real_description(
    robot_model: str, tmp_path: Path
) -> None:
    urdf_path = tmp_path / f'{robot_model}_whitespace_sim_file.urdf'
    xacro_path = PACKAGE_DIR / 'urdf' / 'models' / f'model_{robot_model}.xacro'

    result = run_bash(
        f'xacro "{xacro_path}" sim_file:="   " > "{urdf_path}" && check_urdf "{urdf_path}"'
    )
    output = result.stdout + result.stderr

    assert result.returncode == 0, output
    assert '<plugin ' not in urdf_path.read_text(encoding='utf-8')


@pytest.mark.parametrize('robot_model', ['base', 'sensors1'])
def test_nonexistent_sim_file_is_rejected(robot_model: str, tmp_path: Path) -> None:
    missing_sim_path = tmp_path / 'missing_simulation.yaml'
    xacro_path = PACKAGE_DIR / 'urdf' / 'models' / f'model_{robot_model}.xacro'

    result = run_bash(f'xacro "{xacro_path}" sim_file:="{missing_sim_path}"')
    output = result.stdout + result.stderr

    assert result.returncode != 0
    assert str(missing_sim_path) in output


@pytest.mark.parametrize(
    ('robot_model', 'component_name', 'topic_keys', 'expected_error'),
    ENABLED_SIMULATION_TOPIC_CASES,
)
def test_enabled_simulation_component_requires_a_topic(
    robot_model: str,
    component_name: str,
    topic_keys: tuple[str, ...],
    expected_error: str,
    tmp_path: Path,
) -> None:
    source_path = PACKAGE_DIR / 'config' / f'model_{robot_model}' / 'default_simulation.yaml'
    simulation_config = yaml.safe_load(source_path.read_text(encoding='utf-8'))

    assert simulation_config[component_name]['enabled'] is True
    for topic_key in topic_keys:
        simulation_config[component_name][topic_key] = ''

    invalid_sim_path = tmp_path / f'{component_name}.yaml'
    invalid_sim_path.write_text(yaml.safe_dump(simulation_config), encoding='utf-8')
    xacro_path = PACKAGE_DIR / 'urdf' / 'models' / f'model_{robot_model}.xacro'

    result = run_bash(f'xacro "{xacro_path}" sim_file:="{invalid_sim_path}"')
    output = result.stdout + result.stderr

    assert result.returncode != 0
    assert expected_error in output


def test_disabled_simulation_component_allows_an_empty_topic(tmp_path: Path) -> None:
    source_path = PACKAGE_DIR / 'config' / 'model_base' / 'default_simulation.yaml'
    simulation_config = yaml.safe_load(source_path.read_text(encoding='utf-8'))
    simulation_config['base_velocity_controller'].update(enabled=False, topic='')

    sim_path = tmp_path / 'disabled_base_velocity_controller.yaml'
    sim_path.write_text(yaml.safe_dump(simulation_config), encoding='utf-8')
    xacro_path = PACKAGE_DIR / 'urdf' / 'models' / 'model_base.xacro'

    result = run_bash(f'xacro "{xacro_path}" sim_file:="{sim_path}"')

    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize(
    'launch_file',
    [
        'real_model_base.launch.py',
        'real_model_sensors1.launch.py',
        'debug_model_base.launch.py',
        'debug_model_sensors1.launch.py',
    ],
)
def test_launch_show_args_lists_file_based_model_arguments(launch_file: str) -> None:
    result = run_bash(f'ros2 launch robot_forki3 {launch_file} --show-args')
    output = result.stdout + result.stderr

    assert result.returncode == 0, output
    assert "'robot_name'" in output, output
    assert "'robot_params_file'" in output, output
    assert "'robot_params_file_allow_substs'" in output, output
    assert "'robot_xacro_args_file'" in output, output

    if launch_file.startswith('debug_'):
        assert "'robot_sim_file'" in output, output
        assert "'robot_bridge_config_file'" in output, output
