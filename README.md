# robot_forklift_simple_3sw

`robot_forklift_simple_3sw` provides the robot description and launch files for the `fs3sw` forklift robot.

For a user of the package, the important pieces are:
- the robot launch file
- the example parameter files
- the example simulation and bridge files

## Quick Start

Launch the robot without simulation:

```bash
ros2 launch robot_forklift_simple_3sw robot.launch.py robot_version:=core
```

Launch the `v1` robot:

```bash
ros2 launch robot_forklift_simple_3sw robot.launch.py robot_version:=v1
```

Launch the robot in simulation mode:

```bash
ros2 launch robot_forklift_simple_3sw robot.launch.py robot_version:=v1 use_sim_time:=True
```

When `use_sim_time:=True`, the package also launches the Gazebo bridge automatically.

## Main Launch File

The entry point most users want is:
- [launch/robot.launch.py](launch/robot.launch.py)

Useful launch arguments:
- `robot_version`: robot variant to launch, for example `core` or `v1`
- `use_sim_time`: set to `True` for simulation
- `robot_name`: robot instance name
- `namespace`: namespace prefix for the robot resources
- `params_file`: kinematics / node parameters file
- `sim_file`: simulation plugin configuration file
- `bridge_file`: Gazebo bridge channel configuration file

To inspect all launch arguments:

```bash
ros2 launch robot_forklift_simple_3sw robot.launch.py --show-args
```

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

If `params_file`, `sim_file`, or `bridge_file` are not provided, the package picks the matching example file for the selected `robot_version`.

## Robot Versions

Currently the package exposes at least these robot versions:
- `core`
- `v1`

`core` is the base robot.

`v1` extends the base robot with the currently integrated sensor set.

## Advanced Use

If needed, the package also exposes the lower-level launches:
- [launch/rsp.launch.py](launch/rsp.launch.py) for `robot_state_publisher`
- [launch/bridge.launch.py](launch/bridge.launch.py) for the Gazebo bridge

Most users should still prefer [launch/robot.launch.py](launch/robot.launch.py), because it keeps the robot description, kinematics, and bridge aligned.
