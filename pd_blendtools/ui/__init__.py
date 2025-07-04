from bpy.utils import register_submodule_factory

submodules = [
    'pd_panels',
    'panels_bg',
    'panels_setup',
    'panels_tiles',
]

register, unregister = register_submodule_factory(__name__, submodules)
