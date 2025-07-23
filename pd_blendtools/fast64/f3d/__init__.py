from reload_util import import_modules
_modules_loaded = import_modules(__file__, globals())

def register():
    mat_register()