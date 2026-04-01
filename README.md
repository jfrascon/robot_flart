# robot_forklift_simple_3sw

`robot_forklift_simple_3sw` models a family of forklifts with three steerable
wheels and a simple fork.

The package name identifies the robot family. Each concrete variant of that
family is identified by a robot `model`.

The current public models are:
- `m1`: the base forklift robot
- `m2`: the same base robot plus the current sensor set

The term `simple` refers to the fork geometry used in this package. The fork is
simple enough to represent a fork with two tines and a core body that links the
tines together, but it does not try to model the hydraulic system, the lifting
mechanism, or the tilting mechanism of a real forklift.

The simple fork model is imported from `robotics_description`.

## Quick Start

Launch the base robot without simulation:

```bash
ros2 launch robot_forklift_simple_3sw m1.launch.py
```

Launch the sensorized robot:

```bash
ros2 launch robot_forklift_simple_3sw m2.launch.py
```

Launch the sensorized robot in simulation mode:

```bash
ros2 launch robot_forklift_simple_3sw m2.launch.py use_sim_time:=True
```

When `use_sim_time:=True`, the package also launches the ROS-GZ bridge for that
robot model.

## Main Launch Files

The public launch entry points are:
- [launch/m1.launch.py](launch/m1.launch.py)
- [launch/m2.launch.py](launch/m2.launch.py)

These are the launch files a user is expected to start directly. Each launch
file fixes its robot model internally.

The package also contains these internal reusable launch files:
- [launch/_rsp.launch.py](launch/_rsp.launch.py)
- [launch/_bridge.launch.py](launch/_bridge.launch.py)

`launch/_rsp.launch.py` builds the `xacro` command and starts
`robot_state_publisher`.

`launch/_bridge.launch.py` starts the Gazebo bridge node.

Useful launch arguments:
- `use_sim_time`: set to `True` for simulation
- `robot_name`: robot instance name
- `namespace`: namespace prefix for the robot resources
- `params_file`: kinematics and node parameters file
- `sim_file`: simulation plugin configuration file for the selected model
- `bridge_file`: ROS <-> Gazebo bridge configuration file

To inspect the launch arguments of one public model launch file:

```bash
ros2 launch robot_forklift_simple_3sw m1.launch.py --show-args
```

`m1.launch.py --show-args` shows the launch arguments declared by
`launch/m1.launch.py`.

Because `m1.launch.py` and `m2.launch.py` fix the model internally, this output
also includes the `xacro:arg` values of that selected model.

## Launch Architecture

`m1.launch.py` and `m2.launch.py` each declare the public launch arguments of
that model launch file.

Each model launch file:
- fixes `robot_model` internally
- declares the model xargs through `robot_model_utils`
- forwards those xargs to `launch/_rsp.launch.py`
- includes `launch/_bridge.launch.py`
- includes `three_swerve_kinematics.launch.py` from
  `ground_vehicle_kinematics`

## Xacro Structure

The public Xacro models live in:
- [urdf/models/m1.xacro](urdf/models/m1.xacro)
- [urdf/models/m2.xacro](urdf/models/m2.xacro)

The shared internal Xacro file lives in:
- [urdf/includes/common.xacro](urdf/includes/common.xacro)

`common.xacro` is not a public robot model. It is an internal Xacro file used
by the public robot models.

The Xacro argument catalog is split in the same way:
- [robot_forklift_simple_3sw/xargs/common.yaml](robot_forklift_simple_3sw/xargs/common.yaml)
- [robot_forklift_simple_3sw/xargs/m2.yaml](robot_forklift_simple_3sw/xargs/m2.yaml)

`m1` uses the arguments from `common.yaml`.

`m2` uses the arguments from `common.yaml` plus the arguments from `m2.yaml`.

## Configuration Files

Example files are stored in:
- [config/example_m1.yaml](config/example_m1.yaml)
- [config/example_m2.yaml](config/example_m2.yaml)
- [config/example_m1_simulation.yaml](config/example_m1_simulation.yaml)
- [config/example_m2_simulation.yaml](config/example_m2_simulation.yaml)
- [config/example_m1_bridge.yaml](config/example_m1_bridge.yaml)
- [config/example_m2_bridge.yaml](config/example_m2_bridge.yaml)

Typical use:
- use `example_*.yaml` for robot and kinematics parameters
- use `example_*_simulation.yaml` for Gazebo plugin configuration
- use `example_*_bridge.yaml` for ROS <-> Gazebo channel configuration

If `params_file`, `sim_file`, or `bridge_file` are not provided, the selected
model launch file uses its matching example file.

## Robot Models

Currently the package exposes these robot models:
- `m1`
- `m2`

`m1` is the base forklift robot.

`m2` extends the base robot with the current sensor set.
