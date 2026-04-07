# robot_forki3

`robot_forki3` models a family of forklifts with three steerable wheels and a
simple fork.

The package name identifies the robot family. Each concrete variant of that
family is identified by a short robot model name.

The current public models are:
- `base`: the base forklift robot
- `sensors1`: the same base robot plus the current sensor set

The term `simple` refers to the fork geometry used in this package. The fork is
simple enough to represent a fork with two tines and a core body that links the
tines together, but it does not try to model the hydraulic system, the lifting
mechanism, or the tilting mechanism of a real forklift.

The simple fork model is imported from `robotics_description`.

## Quick Start

Launch the base robot without simulation:

```bash
ros2 launch robot_forki3 model_base.launch.py
```

Launch the sensorized robot:

```bash
ros2 launch robot_forki3 model_sensors1.launch.py
```

Launch the sensorized robot in simulation mode:

```bash
ros2 launch robot_forki3 model_sensors1.launch.py use_sim_time:=True
```

When `use_sim_time:=True`, the package also launches the ROS-GZ bridge for that
robot model.

## Main Launch Files

The public launch entry points are:
- [launch/model_base.launch.py](launch/model_base.launch.py)
- [launch/model_sensors1.launch.py](launch/model_sensors1.launch.py)

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
- `project_namespace`: namespace prefix shared by all robot instances in one project
- `robot_name`: robot instance name
- `params_file`: kinematics and node parameters file
- `sim_file`: simulation plugin configuration file for the selected model
- `bridge_file`: ROS <-> Gazebo bridge configuration file

To inspect the launch arguments of one public model launch file:

```bash
ros2 launch robot_forki3 model_base.launch.py --show-args
```

`model_base.launch.py --show-args` shows the launch arguments declared by
`launch/model_base.launch.py`.

Because `model_base.launch.py` and `model_sensors1.launch.py` fix the model
internally, this output also includes the `xacro:arg` values of that selected
model.

## Launch Architecture

`model_base.launch.py` and `model_sensors1.launch.py` each declare the public
launch arguments of that model launch file.

Each model launch file:
- fixes `robot_model` internally
- declares the model xargs through `model_utils`
- forwards those xargs to `launch/_rsp.launch.py`
- includes `launch/_bridge.launch.py`
- includes `three_swerve_kinematics.launch.py` from
  `ground_vehicle_kinematics`

## Xacro Structure

The public Xacro models live in:
- [urdf/models/model_base.xacro](urdf/models/model_base.xacro)
- [urdf/models/model_sensors1.xacro](urdf/models/model_sensors1.xacro)

The shared internal Xacro file lives in:
- [urdf/includes/common.xacro](urdf/includes/common.xacro)

`common.xacro` is not a public robot model. It is an internal Xacro file used
by the public robot models.

The Xacro argument catalog is split in the same way:
- [robot_forki3/xargs/common.yaml](robot_forki3/xargs/common.yaml)
- [robot_forki3/xargs/model_sensors1.yaml](robot_forki3/xargs/model_sensors1.yaml)

`base` uses the arguments from `common.yaml`.

`sensors1` uses the arguments from `common.yaml` plus the arguments from
`model_sensors1.yaml`.

## Configuration Files

Example files are stored in:
- [config/model_base/example_params.yaml](config/model_base/example_params.yaml)
- [config/model_sensors1/example_params.yaml](config/model_sensors1/example_params.yaml)
- [config/model_base/example_simulation.yaml](config/model_base/example_simulation.yaml)
- [config/model_sensors1/example_simulation.yaml](config/model_sensors1/example_simulation.yaml)
- [config/model_base/example_bridge.yaml](config/model_base/example_bridge.yaml)
- [config/model_sensors1/example_bridge.yaml](config/model_sensors1/example_bridge.yaml)

Typical use:
- use `config/model_*/example_params.yaml` for robot and kinematics parameters
- use `config/model_*/example_simulation.yaml` for Gazebo plugin configuration
- use `config/model_*/example_bridge.yaml` for ROS <-> Gazebo channel configuration

If `params_file` or `bridge_file` are not provided, the selected model launch
file uses its matching example file. If one of those arguments is explicitly set
to an empty string, the corresponding external file is not loaded.

If `sim_file` is not provided and `use_sim_time:=True`, `_rsp.launch.py` falls
back to the matching `config/model_*/example_simulation.yaml` file for the
selected model.

## Robot Models

Currently the package exposes these robot models:
- `base`
- `sensors1`

`base` is the base forklift robot.

`sensors1` extends the base robot with the current sensor set.
