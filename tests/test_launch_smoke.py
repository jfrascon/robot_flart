import pytest

from conftest import run_bash


@pytest.mark.parametrize(
    ('launch_file', 'launch_args', 'expected_text'),
    [
        ('real_model_base.launch.py', '', 'ThreeSwerveKinematicsSolverRos node initialized.'),
        ('real_model_sensors1.launch.py', '', 'ThreeSwerveKinematicsSolverRos node initialized.'),
        (
            'debug_model_base.launch.py',
            'rviz_enabled:=False gzgui_enabled:=False',
            'Creating ROS->GZ Bridge: [cmd_vel',
        ),
        (
            'debug_model_base.launch.py',
            'robot_description_topic:=rdesc rviz_enabled:=False gzgui_enabled:=False',
            'Creating ROS->GZ Bridge: [cmd_vel',
        ),
        (
            'debug_model_sensors1.launch.py',
            'rviz_enabled:=False gzgui_enabled:=False',
            'JointPositionControllerServer node initialized.',
        ),
    ],
)
def test_robot_launch_smoke(launch_file: str, launch_args: str, expected_text: str) -> None:
    result = run_bash(
        f'timeout --signal=INT 8s ros2 launch robot_forki3 {launch_file} {launch_args}'
    )

    output = result.stdout + result.stderr

    # timeout returns 124 when the launch keeps running as expected until interrupted.
    assert result.returncode in {0, 124}, output
    assert 'process started with pid' in output, output
    assert expected_text in output, output


@pytest.mark.parametrize(
    ('script_name', 'expected_text'),
    [
        ('debug_model_base_with_defaults.sh', 'Creating ROS->GZ Bridge: [cmd_vel'),
        (
            'debug_model_sensors1_with_defaults.sh',
            'JointPositionControllerServer node initialized.',
        ),
    ],
)
def test_installed_debug_script_smoke(script_name: str, expected_text: str) -> None:
    package_share = run_bash('ros2 pkg prefix robot_forki3').stdout.strip()
    script = f'{package_share}/share/robot_forki3/scripts/{script_name}'
    result = run_bash(
        f'timeout --signal=INT 8s "{script}" rviz_enabled:=False gzgui_enabled:=False'
    )
    output = result.stdout + result.stderr

    assert result.returncode in {0, 124}, output
    assert expected_text in output, output
