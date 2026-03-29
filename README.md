# robot_forklift_simple_3sw

`robot_forklift_simple_3sw` is a package that models a family of forklifts with three steerable wheels.

The description above uses the term `family` because the package is designed to support multiple robot variants. In
this package, the family is identified by the package name and each concrete variant is identified by a robot
`model`. The `core` model is the base robot with a fork and motion capabilities, and the `v1` model extends the
`core` model with a specific sensor set. In the future, more robot models can be added, `v2`, `v3`, etc., each with
their own set of capabilities and sensors, but all sharing the same base robot description and kinematics.

The term `simple` refers to the fact that the fork used in this family of robots is a basic fork; simple enough to model a fork, with two tines and a core body that links the tines together, but without the extra details of a real fork, such as the hydraulic system, the lifting mechanism, or the tilting mechanism. The `simple` fork is sufficient for simulation and testing purposes, but it is not intended to be a detailed model of a real forklift fork.
The fork model used in this packages is imported from the `robotics_description` package, which provides simple fork models. Specifically, the `simple` fork model used in this package is the `fork_simple` model, which is derived from a reference fork mesh and can be geometrically scaled.

Thefore, the `robotics_description` package is a dependency of this package, and it is provided in the file [./deps.repos](./deps.repos)

For a user of the package, the important pieces are:
- the robot launch file
- the example parameter files
- the example simulation and bridge files

## Quick Start

Launch the robot without simulation:

```bash
ros2 launch robot_forklift_simple_3sw robot.launch.py robot_model:=core
```

Launch the `v1` robot:

```bash
ros2 launch robot_forklift_simple_3sw robot.launch.py robot_model:=v1
```

Launch the robot in simulation mode:

```bash
ros2 launch robot_forklift_simple_3sw robot.launch.py robot_model:=v1 use_sim_time:=True
```

When `use_sim_time:=True`, the package also launches the Gazebo bridge automatically.

## Main Launch File

The entry point most users want is:
- [launch/robot.launch.py](launch/robot.launch.py)

Useful launch arguments:
- `robot_model`: robot model to launch, for example `core` or `v1`
- `use_sim_time`: set to `True` for simulation
- `robot_name`: robot instance name
- `namespace`: namespace prefix for the robot resources
- `params_file`: kinematics / node parameters file
- `sim_file`: simulation plugin configuration file for the selected robot model
- `bridge_file`: Gazebo bridge channel configuration file used by `robot.launch.py`

To inspect all launch arguments:

```bash
ros2 launch robot_forklift_simple_3sw robot.launch.py --show-args
```

`robot.launch.py --show-args` shows the launch arguments that are declared statically in
`launch/robot.launch.py`.

This output does not include the xargs that are declared dynamically after `robot_model`
is read. Those xargs are created from the YAML file that corresponds to the selected robot
model. For example:
- `core` uses `robot_forklift_simple_3sw/xargs/core.yaml`
- `v1` uses `robot_forklift_simple_3sw/xargs/core.yaml` plus
  `robot_forklift_simple_3sw/xargs/v1.yaml`

This means that `--show-args` is useful to inspect the static launch arguments, but it is
not a complete listing of the xargs that the selected robot model accepts.

## Configuration Files

Example files are stored in:
- [config/example_core.yaml](config/example_core.yaml)
- [config/example_v1.yaml](config/example_v1.yaml)
- [config/example_core_simulation.yaml](config/example_core_simulation.yaml)
- [config/example_v1_simulation.yaml](config/example_v1_simulation.yaml)
- [config/example_core_bridge.yaml](config/example_core_bridge.yaml)
- [config/example_v1_bridge.yaml](config/example_v1_bridge.yaml)

Typical use:
- use `example_*.yaml` for robot and kinematics parameters
- use `example_*_simulation.yaml` for Gazebo plugin configuration
- use `example_*_bridge.yaml` for ROS <-> Gazebo channel configuration

If `params_file` or `sim_file` are not provided, the package picks the matching
example file for the selected `robot_model`. If `bridge_file` is not
provided, `robot.launch.py` picks the matching example bridge file for the
selected `robot_model`.

`sim_file` belongs to the xargs set of the selected robot model, so it is part of the
dynamic xargs mechanism described above. That is why `sim_file` can be accepted by the
launch file even though `ros2 launch ... --show-args` does not list it.

## Robot Models

Currently the package exposes at least these robot models:
- `core`
- `v1`

`core` is the base robot.

`v1` extends the base robot with the currently integrated sensor set.

## Advanced Use

Most users should prefer [launch/robot.launch.py](launch/robot.launch.py),
which now launches `robot_state_publisher` directly and keeps the robot
description, kinematics, and bridge aligned.

`robot.launch.py` is now the single launch entry point for the robot, including
the Gazebo bridge.
