from glob import glob

from setuptools import find_packages, setup

package_name = 'robot_flart'

setup(
    name=package_name,
    version='1.0.0',
    packages=find_packages(exclude=['test', 'tests']),
    data_files=[
        ('share/ament_index/resource_index/packages', [f'resource/{package_name}']),
        (f'share/{package_name}', ['package.xml']),
        (f'share/{package_name}/config', glob('config/*')),
        (f'share/{package_name}/launch', glob('launch/*')),
        (f'share/{package_name}/meshes', glob('meshes/*')),
        (f'share/{package_name}/urdf', glob('urdf/*')),
    ],
    install_requires=['setuptools', 'PyYAML'],
    zip_safe=True,
    maintainer='Juan Francisco Rascon Crespo',
    maintainer_email='jfracon@gmail.com',
    description='Deployment package for the robot flart',
    license='Apache-2.0',
    extras_require={'test': ['pytest']},
    entry_points={'console_scripts': []},
    python_requires='>=3.8',
)
