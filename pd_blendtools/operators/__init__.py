import bpy.types
from bpy.utils import register_submodule_factory

from . import ops_bg, ops_model, ops_setup, ops_tiles, pd_ops
from .ops_bg import PDTOOLS_OT_PortalFromFace
from .ops_tiles import PDTOOLS_OT_TilesFromFaces

modules = [
    ops_bg,
    ops_model,
    ops_setup,
    ops_tiles,
    pd_ops,
]

submodules = [
    'ops_bg',
    'ops_model',
    'ops_setup',
    'ops_tiles',
    'pd_ops'
]

register_mod, unregister_mod = register_submodule_factory(__name__, submodules)

def pd_editmode_menu(self, _context):
    self.layout.separator(factor=1.0)
    self.layout.operator(PDTOOLS_OT_PortalFromFace.bl_idname)
    self.layout.operator(PDTOOLS_OT_TilesFromFaces.bl_idname)

def pd_editmode_ctxmenu(self, _context):
    if bpy.context.tool_settings.mesh_select_mode[2]:
        self.layout.separator(factor=1.0)
        self.layout.operator(PDTOOLS_OT_PortalFromFace.bl_idname)
        self.layout.operator(PDTOOLS_OT_TilesFromFaces.bl_idname)

def register():
    register_mod()

    bpy.types.VIEW3D_MT_edit_mesh_faces.append(pd_editmode_menu)  # for top menu
    bpy.types.VIEW3D_MT_edit_mesh_context_menu.append(pd_editmode_ctxmenu)  # for context menu
