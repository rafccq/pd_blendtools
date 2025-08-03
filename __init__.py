bl_info = {
    "name": "Perfect Dark Blender Editor",
    "author": "Raf Ccq",
    "version": (0, 0, 1),
    "blender": (3, 6, 0),
    "description": "Blender tools for editing Perfect Dark N64 levels and models",
    "location": "View3D > UI panel > PDTools",
    "wiki_url": "https://github.com/rafccq/pd_blendtools",
    "tracker_url": "https://github.com/rafccq/pd_blendtools/issues",
    "updater_info": "https://github.com/rafccq/pd_blendtools",
    "category": "Import-Export"
}

if "bpy" in locals():
    import reload_util as rlu

    path = __path__[0]
    rlu.reload_submodules(path)
    rlu.reload_submodules(path, 'materials')
    rlu.reload_submodules(path, 'operators')
    rlu.reload_submodules(path, 'pd_data')
    rlu.reload_submodules(path, 'pd_export')
    rlu.reload_submodules(path, 'pd_import')
    rlu.reload_submodules(path, 'ui')
    rlu.reload_submodules(path, 'utils')
    rlu.reload_submodules(path, 'fast64')
    rlu.reload_submodules(path, 'fast64.f3d')
    print('--RELOAD DONE--')

import os
import sys
import inspect
cmd_subfolder = os.path.realpath(os.path.abspath(os.path.split(inspect.getfile(inspect.currentframe()))[0]))
if cmd_subfolder not in sys.path:
    sys.path.insert(0, cmd_subfolder)

import bpy
from bpy.types import PropertyGroup, Object
from bpy.props import StringProperty, IntProperty
from bpy.app.handlers import persistent
from . import addon_updater_ops

from data.typeinfo import TypeInfo
from pd_data.decl_model import model_decls
from .pd_addonprefs import PD_AddonPreferences
from . import pd_addonprefs as pdp
import pd_blendprops as pdprops

from operators import pd_ops as pdops
import operators as ops
import ui
from pd_import import (
    bg_import as bgi,
    model_import as mdi,
    tiles_import as tlimp,
    setup_import as stpi,
)
import materials as pdm

import fast64

submodules = [
    ui,
    ops,
    pdprops,
    tlimp,
    stpi,
    bgi,
    fast64,
    pdm,
]

class PDModelPropertyGroup(PropertyGroup):
    name: StringProperty(name='name', default='', options={'LIBRARY_EDITABLE'})
    idx: IntProperty(name='idx', default=0, options={'LIBRARY_EDITABLE'})
    layer: IntProperty(name='layer', default=-1, options={'LIBRARY_EDITABLE'})


def register_types():
    for name, decl in model_decls.items():
        TypeInfo.register(name, decl)

def register():
    v = bl_info['version']
    print(f'---------------------------------')
    print(f'PD Blend Tools Register v = {v[0]}.{v[1]}.{v[2]}')
    print(f'---------------------------------')

    addon_updater_ops.register(bl_info)
    bpy.utils.register_class(PD_AddonPreferences)
    bpy.utils.register_class(PDModelPropertyGroup)
    Object.pd_model = bpy.props.PointerProperty(type=PDModelPropertyGroup)
    register_types()

    # register the submodules
    for m in submodules:
        m.register()

    bpy.app.handlers.load_post.append(pd_load_handler)

def unregister():
    for m in reversed(submodules):
        m.unregister()

    bpy.utils.unregister_class(PDModelPropertyGroup)
    bpy.utils.unregister_class(PD_AddonPreferences)

    addon_updater_ops.unregister()

def clear_cache():
    bgi.bg_load.cache_clear()
    stpi.get_setupdata.cache_clear()

@persistent
def pd_load_handler(_dummy):
    clear_cache()
    from ui import mtxpalette_panel as mtxp
    context = bpy.context

    mtxp.gen_icons(context) # we need to generate the mtx icons again
    rompath = pdp.rompath()
    if rompath:
        pdops.PDTOOLS_OT_LoadRom.load_rom(context, rompath)
