#!/usr/bin/env bash
set -euo pipefail

package_share="$(ros2 pkg prefix robot_forki3)/share/robot_forki3"

ros2 launch robot_forki3 debug_model_sensors1.launch.py \
    robot_name:=forki3 \
    robot_params_file:="${package_share}/config/model_sensors1/default_params.yaml" \
    robot_params_file_allow_substs:=True \
    robot_xacro_args_file:="${package_share}/config/model_sensors1/default_xacro_args.yaml" \
    robot_sim_file:="${package_share}/config/model_sensors1/default_simulation.yaml" \
    robot_bridge_config_file:="${package_share}/config/model_sensors1/default_bridge.yaml" \
    rviz_enabled:=True \
    gzgui_enabled:=True \
    "$@"
