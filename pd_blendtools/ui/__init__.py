from bpy.utils import register_submodule_factory

from reload_util import import_modules
_modules_loaded = import_modules(__file__, globals())

submodules = [
    'pd_panels',
    'panels_bg',
    'panels_setup',
    'panels_tiles',
    'mtxpalette_panel',
]

register, unregister = register_submodule_factory(__name__, submodules)
