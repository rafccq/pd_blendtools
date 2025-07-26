from .f3d_material import mat_register, mat_unregister

from reload_util import import_modules
_modules_loaded = import_modules(__file__, globals())


def register():
    mat_register()

def unregister():
    mat_unregister()

