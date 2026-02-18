"""Rosgz bridge catalog entry for the FLART core profile."""

from robot_flart import _rosgz_bridge_core_cfg_builder

ROSGZ_BRIDGE_CATALOG_ENTRY = {
    'version': 'core',
    'extends': None,
    'builders': ({'sim_file_key': 'core_sim_file', 'create_cfg': _rosgz_bridge_core_cfg_builder.create_cfg},),
}
