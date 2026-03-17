import os
from glob import glob

from setuptools import find_packages, setup

package_name = 'robot_forklift_simple_3sw'


def _glob_files(pattern):
    """Return only regular files for a glob pattern."""
    return [path for path in glob(pattern) if os.path.isfile(path)]


setup(
    name=package_name,
    version='1.0.0',
    packages=find_packages(exclude=['test', 'tests']),
    data_files=[
        ('share/ament_index/resource_index/packages', [f'resource/{package_name}']),
        (f'share/{package_name}', ['package.xml']),
        (f'share/{package_name}/config', _glob_files('config/*')),
        (f'share/{package_name}/launch', _glob_files('launch/*')),
        (f'share/{package_name}/meshes', _glob_files('meshes/*')),
        (f'share/{package_name}/urdf', _glob_files('urdf/*')),
    ],
    install_requires=['setuptools', 'PyYAML'],
    zip_safe=True,
    maintainer='Juan Francisco Rascon Crespo',
    maintainer_email='jfracon@gmail.com',
    description='Deployment package for the robot fs3sw',
    license='Apache-2.0',
    extras_require={'test': ['pytest']},
    entry_points={'console_scripts': []},
    python_requires='>=3.8',
)
