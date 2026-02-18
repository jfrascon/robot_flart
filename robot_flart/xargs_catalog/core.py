"""Xargs specification for FLART core version."""

import os

from ament_index_python.packages import get_package_share_directory

XARGS = {
    'version': 'core',
    'extends': None,
    'args': {
        'core_sim_file': {
            'default_value': os.path.join(
                get_package_share_directory('robot_flart'), 'config', 'example_flart_core_simulation.yaml'
            ),
            'description': 'Path to simulation configuration for base+fork',
        },
        'body_use_visual': {
            'default_value': 'True',
            'description': 'Use visual element for the robot body',
            'choices': ['True', 'true', 'False', 'false'],
        },
        'body_use_collision': {
            'default_value': 'True',
            'description': 'Use collision element for the robot body',
            'choices': ['True', 'true', 'False', 'false'],
        },
        'body_use_inertial': {
            'default_value': 'True',
            'description': 'Use inertial element for the robot body. If False, a null inertia will be used',
            'choices': ['True', 'true', 'False', 'false'],
        },
        'body_use_v_mesh': {
            'default_value': 'True',
            'description': 'Use mesh for body visual; otherwise primitives',
            'choices': ['True', 'true', 'False', 'false'],
        },
        'body_use_c_mesh': {
            'default_value': 'False',
            'description': 'Use mesh for body collision; otherwise primitives',
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
            'default_value': 'True',
            'description': 'Use mesh for wheel visual; otherwise primitives',
            'choices': ['True', 'true', 'False', 'false'],
        },
        'fork_use_visual': {
            'default_value': 'True',
            'description': 'Use visual element for fork',
            'choices': ['True', 'true', 'False', 'false'],
        },
        'fork_use_collision': {
            'default_value': 'True',
            'description': 'Use collision element for fork',
            'choices': ['True', 'true', 'False', 'false'],
        },
        'fork_use_inertial': {
            'default_value': 'False',
            'description': 'Use inertial element for fork',
            'choices': ['True', 'true', 'False', 'false'],
        },
        'fork_use_v_mesh': {
            'default_value': 'True',
            'description': 'Use mesh for fork visual; otherwise primitives',
            'choices': ['True', 'true', 'False', 'false'],
        },
        'fork_use_c_mesh': {
            'default_value': 'False',
            'description': 'Use mesh for fork collision; otherwise primitives',
            'choices': ['True', 'true', 'False', 'false'],
        },
    },
}
