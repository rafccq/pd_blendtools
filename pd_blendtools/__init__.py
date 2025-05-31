bl_info = {
    "name": "pd_blendtools",
    "author": "Raf Ccq",
    "version": (0, 0, 1),
    "blender": (4, 0, 0),
    # "blender": (3, 5, 0),
    "description": "A tool to help import/edit/export PD models in Blender",
    "location": "View3D > UI panel > PDTools",
    "wiki_url": "https://github.com/rafccq/pd_blendtools",
    "tracker_url": "https://github.com/rafccq/pd_blendtools/issues",
    "updater_info": "https://github.com/rafccq/pd_blendtools",
    "category": "Import-Export"
}

import os
import sys
import inspect
cmd_subfolder = os.path.realpath(os.path.abspath(os.path.split(inspect.getfile(inspect.currentframe()))[0]))
if cmd_subfolder not in sys.path:
    sys.path.insert(0, cmd_subfolder)

import bpy
from bpy.types import PropertyGroup, Object, Panel
from bpy.props import StringProperty, IntProperty, PointerProperty
from bpy.app.handlers import persistent

from typeinfo import TypeInfo
from decl_model import model_decls
from pd_addonprefs import PD_AddonPreferences
import pd_blendprops as pdprops

import pd_shadernodes as pdn
# import nodes.pd_shadernodes as pdn
import pd_panels
import pd_ops as pdops
import mtxpalette_panel as mtxp
import pd_addonprefs as pdp

submodules = [
    pdn,
    pd_panels,
    pdops,
    mtxp,
    pdprops,
]


class PDModelPropertyGroup(PropertyGroup):
    name: StringProperty(name='name', default='', options={'LIBRARY_EDITABLE'})
    idx: IntProperty(name='idx', default=0, options={'LIBRARY_EDITABLE'})
    layer: IntProperty(name='layer', default=-1, options={'LIBRARY_EDITABLE'})


def register_types():
    for name, decl in model_decls.items():
        TypeInfo.register(name, decl)

def register():
    try:
        bpy.utils.register_class(PD_AddonPreferences)
    except RuntimeError as err:
        print('unregister error:', err)
        pass

    print(f'---------------------------------')
    print(f'PD Blend Tools Register')
    print(f'---------------------------------')
    bpy.utils.register_class(PDModelPropertyGroup)
    Object.pd_model = bpy.props.PointerProperty(type=PDModelPropertyGroup)
    register_types()

    # register the submodules
    for m in submodules:
        m.register()

    bpy.app.handlers.load_post.append(pd_load_handler)

def unregister_nodes():
    pdn.unregister()

def unregister():
    for m in reversed(submodules):
        m.unregister()

    bpy.utils.unregister_class(PDModelPropertyGroup)
    bpy.utils.unregister_class(PD_AddonPreferences)


@persistent
def pd_load_handler(_dummy):
    context = bpy.context

    mtxp.gen_icons(context) # we need to generate the mtx icons again
    rompath = pdp.pref_get(pdp.PD_PREF_ROMPATH)
    if rompath:
        pdops.PDTOOLS_OT_LoadRom.load_rom(context, rompath)

if __name__ == "__main__":
    register()
