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

import nodes.pd_shadernodes as pdn
import pd_panels
import pd_ops as pdo
import pd_utils as pdu
import mtxpalette_panel as mtxp

submodules = [
    pdn,
    pd_panels,
    pdo,
    mtxp
]


class PDModelPropertyGroup(PropertyGroup):
    name: StringProperty(name='name', default='', options={'LIBRARY_EDITABLE'})
    idx: IntProperty(name='idx', default=0, options={'LIBRARY_EDITABLE'})
    layer: IntProperty(name='layer', default=0, options={'LIBRARY_EDITABLE'})


def register_types():
    for name, decl in model_decls.items():
        TypeInfo.register(name, decl)

def register():
    bpy.utils.register_class(PD_AddonPreferences)
    bpy.utils.register_class(PDModelPropertyGroup)
    Object.pdmodel_props = bpy.props.PointerProperty(type=PDModelPropertyGroup)
    register_types()

    for m in submodules:
        m.register()

    bpy.app.handlers.load_post.append(pd_load_handler)

def unregister():
    for m in reversed(submodules):
        m.unregister()

    del Object.pdmodel_props
    bpy.utils.unregister_class(PDModelPropertyGroup)
    bpy.utils.unregister_class(PD_AddonPreferences)


if __name__ == "__main__":
    register()

@persistent
def pd_load_handler(_dummy):
    context = bpy.context

    mtxp.gen_icons(context) # we need to generate the mtx icons again
    rompath = pdu.addon_prefs().rompath
    if rompath:
        pdo.PDTOOLS_OT_LoadRom.load_rom(context, rompath)
