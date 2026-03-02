"""Xargs specification for fs3aw core version."""

import os

from ament_index_python.packages import get_package_share_directory

# Considerations for core xargs:
# The default values for the body correspond to the default mesh (mass, size, and inertia are consistent with that
# mesh). If the user changes the body mesh, they should also update the corresponding body parameters to
# maintain a consistent model. However, we cannot enforce this consistency in the xargs, so we provide the parameters
# independently and document their relationship in the description. The user is responsible for ensuring that the
# parameters are consistent with the chosen mesh.
# If the user scales the body mesh through `body_scale`, `body_size` must be set to the final scaled size.


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
        'mass': {'default_value': '500', 'description': 'Total mass represented by the internal ballast model (kg).'},
        'body_size': {
            'default_value': '1.531 0.774 1.64',
            'description': (
                "Chassis size as 'x y z' in meters. If `body_scale` is applied to `body_mesh`, "
                '`body_size` must be the scaled final size.'
            ),
        },
        'ballast_size_z': {'default_value': '0.1', 'description': 'Ballast height along Z (m).'},
        'body_ground_clearance': {'default_value': '0.06', 'description': 'Base-to-ground clearance (m).'},
        'dist_to_wheels': {
            'default_value': '0.50',
            'description': 'Distance from base origin to each wheel center in the XY plane (m).',
        },
        'alpha_deg': {
            'default_value': '154',
            'description': 'Wheel layout angle in degrees, used in xacro as radians(alpha_deg).',
        },
        'body_mesh': {
            'default_value': 'robot_forklift_simple_3aw/meshes/forklift_simple_3aw_base.stl',
            'description': 'Body mesh path within package format <pkg>/<path>.',
        },
        'body_scale': {'default_value': '1.0 1.0 1.0', 'description': "Body mesh scale as 'sx sy sz'."},
        'body_color': {'default_value': '0.0 0.0 1.0 1.0', 'description': "Body color as 'r g b a'."},
        'st_wheel_use_inertial': {
            'default_value': 'True',
            'description': 'Use inertial element for wheels. If False, a null inertia will be used',
            'choices': ['True', 'true', 'False', 'false'],
        },
        'st_wheel_mass': {'default_value': '10.0', 'description': 'Steerable wheel mass (kg).'},
        'st_wheel_radius': {'default_value': '0.127', 'description': 'Steerable wheel radius (m).'},
        'st_wheel_thickness': {'default_value': '0.082', 'description': 'Steerable wheel thickness (m).'},
        'st_wheel_color': {'default_value': '0.1 0.1 0.1 1.0', 'description': "Steerable wheel color as 'r g b a'."},
        # Note: If you want the wheel to be able to reach +-pi rad angle (+-180 degress), set limits to +-3.1416.
        # pi = 3.141592654.... < 3.1416
        'st_wheel_steerable_limits': {
            'default_value': '-3.1416 3.1416 100.0 100000.0',
            'description': "Steerable joint limits as 'lower upper velocity effort'.",
        },
        'st_wheel_rotation_joint_limits': {
            'default_value': '100.0 100000.0',
            'description': "Wheel rotation joint limits as 'velocity effort'.",
        },
        'st_wheel_max_contacts': {'default_value': '1', 'description': 'Maximum contact points for wheel collision.'},
        'st_wheel_mu': {
            'default_value': '0.05',
            'description': 'Primary friction coefficient for wheel-ground contact.',
        },
        'st_wheel_mu2': {
            'default_value': '0.5',
            'description': 'Secondary friction coefficient for wheel-ground contact.',
        },
        'st_wheel_slip1': {
            'default_value': '0.005',
            'description': 'Primary slip compliance for wheel-ground contact.',
        },
        'st_wheel_slip2': {
            'default_value': '0.0005',
            'description': 'Secondary slip compliance for wheel-ground contact.',
        },
        'fork_use_inertial': {
            'default_value': 'False',
            'description': 'Use inertial element for fork',
            'choices': ['True', 'true', 'False', 'false'],
        },
        'fork_color': {'default_value': '0.1 0.1 0.1 1.0', 'description': "Fork color as 'r g b a'."},
        'fork_lower_limit': {'default_value': '-0.01', 'description': 'Fork lower prismatic limit (m).'},
        'fork_upper_limit': {'default_value': '0.8', 'description': 'Fork upper prismatic limit (m).'},
        'fork_velocity_limit': {'default_value': '0.5', 'description': 'Fork prismatic joint velocity limit (m/s).'},
        'fork_effort_limit': {'default_value': '20000.0', 'description': 'Fork prismatic joint effort limit.'},
        'fork_tines_rest_clearance': {
            'default_value': '0.03',
            'description': 'Distance from ground to tine bottom face at rest (m).',
        },
    },
}
