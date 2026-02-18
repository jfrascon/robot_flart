"""Xargs specification for FLART v0 version."""

import os

from ament_index_python.packages import get_package_share_directory

XARGS = {
    'version': 'v0',
    'extends': 'core',
    'args': {
        'extras_sim_file': {
            'default_value': os.path.join(
                get_package_share_directory('robot_flart'), 'config', 'example_flart_v0_simulation_extras.yaml'
            ),
            'description': "Path to simulation configuration for the 'extra' elements defined in the 'v0' version of "
            "the 'flart' robot",
        },
        'top_platform_use_visual': {
            'default_value': 'True',
            'description': 'Include visual element for the top platform sensor body.',
            'choices': ['True', 'true', 'False', 'false'],
        },
        'top_platform_use_collision': {
            'default_value': 'True',
            'description': 'Include collision element for the top platform sensor body.',
            'choices': ['True', 'true', 'False', 'false'],
        },
        'top_platform_use_inertial': {
            'default_value': 'True',
            'description': 'Include inertial element for the top platform sensor body.',
            'choices': ['True', 'true', 'False', 'false'],
        },
        'top_platform_color': {
            'default_value': '',
            'description': "Optional color override 'r g b a'; empty keeps mesh color.",
        },
        'top_lidar_use_visual': {
            'default_value': 'True',
            'description': 'Include visual element for the sensor body.',
            'choices': ['True', 'true', 'False', 'false'],
        },
        'top_lidar_use_collision': {
            'default_value': 'True',
            'description': 'Include collision element for the sensor body.',
            'choices': ['True', 'true', 'False', 'false'],
        },
        'top_lidar_use_inertial': {
            'default_value': 'True',
            'description': 'Include inertial element for the sensor body.',
            'choices': ['True', 'true', 'False', 'false'],
        },
        'top_lidar_use_v_mesh': {
            'default_value': 'False',
            'description': 'Use a mesh for visual; if False, use a primitive.',
            'choices': ['True', 'true', 'False', 'false'],
        },
        'top_lidar_use_low_res_v_mesh': {
            'default_value': 'True',
            'description': 'Prefer low-resolution mesh for visual when using mesh.',
            'choices': ['True', 'true', 'False', 'false'],
        },
        'top_lidar_color': {
            'default_value': '',
            'description': "Optional color override 'r g b a'; empty keeps mesh color.",
        },
        'top_lidar_use_c_mesh': {
            'default_value': 'False',
            'description': 'Use a mesh for collision; if False, use a primitive.',
            'choices': ['True', 'true', 'False', 'false'],
        },
        'top_lidar_use_low_res_c_mesh': {
            'default_value': 'False',
            'description': 'Prefer low-resolution mesh for collision when using mesh.',
            'choices': ['True', 'true', 'False', 'false'],
        },
        'top_imu_use_visual': {
            'default_value': 'True',
            'description': 'Include visual element for the sensor.',
            'choices': ['True', 'true', 'False', 'false'],
        },
        'top_imu_use_collision': {
            'default_value': 'True',
            'description': 'Include collision element for the sensor.',
            'choices': ['True', 'true', 'False', 'false'],
        },
        'top_imu_use_inertial': {
            'default_value': 'True',
            'description': 'Include inertial element for the sensor.',
            'choices': ['True', 'true', 'False', 'false'],
        },
        'top_imu_use_v_mesh': {
            'default_value': 'True',
            'description': 'Use a mesh for visual; if False, use a primitive.',
            'choices': ['True', 'true', 'False', 'false'],
        },
        'top_imu_color': {
            'default_value': '',
            'description': "Optional color override 'r g b a'; empty keeps mesh color.",
        },
        'top_imu_use_c_mesh': {
            'default_value': 'False',
            'description': 'Use a mesh for collision; if False, use a primitive.',
            'choices': ['True', 'true', 'False', 'false'],
        },
        'rear_rgbd_use_visual': {
            'default_value': 'True',
            'description': 'Include visual element for the sensor.',
            'choices': ['True', 'true', 'False', 'false'],
        },
        'rear_rgbd_use_collision': {
            'default_value': 'True',
            'description': 'Include collision element for the sensor.',
            'choices': ['True', 'true', 'False', 'false'],
        },
        'rear_rgbd_use_inertial': {
            'default_value': 'True',
            'description': 'Include inertial element for the sensor.',
            'choices': ['True', 'true', 'False', 'false'],
        },
        'rear_rgbd_use_v_mesh': {
            'default_value': 'True',
            'description': 'Use a mesh for visual; if False, use a primitive.',
            'choices': ['True', 'true', 'False', 'false'],
        },
        'rear_rgbd_color': {
            'default_value': '0.5 0.5 0.5 1.0',
            'description': "Optional color override 'r g b a'; empty keeps mesh color.",
        },
        'rear_rgbd_use_c_mesh': {
            'default_value': 'False',
            'description': 'Use a mesh for collision; if False, use a primitive.',
            'choices': ['True', 'true', 'False', 'false'],
        },
    },
}
