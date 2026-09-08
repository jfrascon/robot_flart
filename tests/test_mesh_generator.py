from pathlib import Path
import struct
import subprocess

import pytest

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
GENERATOR = PACKAGE_ROOT / 'meshes' / 'forklift_chassis_stl_generator.py'


def test_generator_writes_a_binary_stl_when_executed_directly(tmp_path: Path) -> None:
    output_path = tmp_path / 'forklift_chassis.stl'

    result = subprocess.run(
        [str(GENERATOR), '--output', str(output_path), '--thickness-mm', '2.0'],
        capture_output=True,
        check=False,
        text=True,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    data = output_path.read_bytes()
    triangle_count = struct.unpack('<I', data[80:84])[0]
    assert triangle_count > 0
    assert len(data) == 84 + triangle_count * 50


@pytest.mark.parametrize('thickness', ['0', '-1', 'nan', 'inf', '-inf'])
def test_generator_rejects_non_positive_or_non_finite_thickness(thickness: str) -> None:
    result = subprocess.run(
        [str(GENERATOR), f'--thickness-mm={thickness}'],
        capture_output=True,
        check=False,
        text=True,
    )

    assert result.returncode != 0
    assert 'must be a positive finite number' in result.stderr
