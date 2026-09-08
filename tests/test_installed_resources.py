import os
from pathlib import Path

from ament_index_python.packages import get_package_share_directory
import pytest

EXPECTED_RESOURCES = (
    'LICENSE',
    'README.md',
    'config/model_base/default_bridge.yaml',
    'config/model_base/default_params.yaml',
    'config/model_base/default_simulation.yaml',
    'config/model_base/default_xacro_args.yaml',
    'config/model_sensors1/default_bridge.yaml',
    'config/model_sensors1/default_params.yaml',
    'config/model_sensors1/default_simulation.yaml',
    'config/model_sensors1/default_xacro_args.yaml',
    'launch/_bridge.launch.py',
    'launch/_fork_control.launch.py',
    'launch/_ground_vehicle_kinematics.launch.py',
    'launch/_robot_state_publisher.launch.py',
    'launch/debug_model_base.launch.py',
    'launch/debug_model_sensors1.launch.py',
    'launch/real_model_base.launch.py',
    'launch/real_model_sensors1.launch.py',
    'meshes/forklift_chassis.stl',
    'rviz/sim_debug.rviz',
    'scripts/debug_model_base_with_defaults.sh',
    'scripts/debug_model_sensors1_with_defaults.sh',
    'urdf/includes/common.xacro',
    'urdf/models/model_base.xacro',
    'urdf/models/model_sensors1.xacro',
    'worlds/debug_world.sdf',
    'worlds/debug_world_bridge.yaml',
)

REMOVED_RESOURCES = (
    'config/model_base/example_bridge.yaml',
    'config/model_base/example_params.yaml',
    'config/model_base/example_simulation.yaml',
    'config/model_sensors1/example_bridge.yaml',
    'config/model_sensors1/example_params.yaml',
    'config/model_sensors1/example_simulation.yaml',
    'launch/_rsp.launch.py',
    'launch/model_base.launch.py',
    'launch/model_sensors1.launch.py',
)

SOURCE_ONLY_RESOURCES = (
    'meshes/forklift_chassis_stl.svg',
    'meshes/forklift_chassis_stl_generator.py',
    'meshes/forklift_chassis_stl_meshlab_data.md',
)


@pytest.fixture(scope='module')
def package_share() -> Path:
    return Path(get_package_share_directory('robot_forki3'))


@pytest.mark.parametrize('relative_path', EXPECTED_RESOURCES)
def test_required_resource_is_installed(package_share: Path, relative_path: str) -> None:
    assert package_share.joinpath(relative_path).is_file()


@pytest.mark.parametrize('relative_path', REMOVED_RESOURCES)
def test_removed_resource_is_not_installed(package_share: Path, relative_path: str) -> None:
    assert not package_share.joinpath(relative_path).exists()


@pytest.mark.parametrize('relative_path', SOURCE_ONLY_RESOURCES)
def test_development_resource_is_not_installed(package_share: Path, relative_path: str) -> None:
    assert not package_share.joinpath(relative_path).exists()


@pytest.mark.parametrize(
    'relative_path',
    ['scripts/debug_model_base_with_defaults.sh', 'scripts/debug_model_sensors1_with_defaults.sh'],
)
def test_installed_debug_script_is_executable(package_share: Path, relative_path: str) -> None:
    assert os.access(package_share / relative_path, os.X_OK)
