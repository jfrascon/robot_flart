"""Rosgz bridge catalog entry for the FLART v0 profile."""

from robot_flart import _rosgz_bridge_v0_cfg_builder

ROSGZ_BRIDGE_CATALOG_ENTRY = {
    'version': 'v0',
    'extends': 'core',
    'builders': ({'sim_file_key': 'extras_sim_file', 'create_cfg': _rosgz_bridge_v0_cfg_builder.create_cfg},),
}
