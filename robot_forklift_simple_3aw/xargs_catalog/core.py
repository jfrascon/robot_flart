"""Xargs specification for fs3aw core version."""

import os

from ament_index_python.packages import get_package_share_directory

XARGS = {
    'version': 'core',
    'extends': None,
    'args': {
        'sim_file': {
            'default_value': os.path.join(
                get_package_share_directory('robot_forklift_simple_3aw'), 'config', 'example_core_simulation.yaml'
            ),
            'description': 'Path to simulation configuration for base+fork',
        },
        'body_use_inertial': {
            'default_value': 'True',
            'description': 'Use inertial element for the robot body. If False, a null inertia will be used',
            'choices': ['True', 'true', 'False', 'false'],
        },
        'st_wheel_use_visual': {
            'default_value': 'True',
            'description': 'Use visual element for wheels',
            'choices': ['True', 'true', 'False', 'false'],
        },
        'st_wheel_use_inertial': {
            'default_value': 'True',
            'description': 'Use inertial element for wheels. If False, a null inertia will be used',
            'choices': ['True', 'true', 'False', 'false'],
        },
        'st_wheel_use_v_mesh': {
            'default_value': 'False',
            'description': 'Use mesh for wheel visual; otherwise primitives',
            'choices': ['True', 'true', 'False', 'false'],
        },
        'fork_use_inertial': {
            'default_value': 'False',
            'description': 'Use inertial element for fork',
            'choices': ['True', 'true', 'False', 'false'],
        },
    },
}
