from bpy.utils import register_submodule_factory

from reload_util import import_modules
_modules_loaded = import_modules(__file__, globals())


submodules = [
    'f3d',
]

register, unregister = register_submodule_factory(__name__, submodules)
