import bpy
from nodeitems_utils import NodeItem
import nodeitems_utils as ndu
from nodeitems_builtins import ShaderNodeCategory
from bpy.types import Menu
from bl_ui import node_add_menu
from bpy.utils import register_class, unregister_class

from nodes.shadernode_base import PD_ShaderNodeBase
from nodes.shadernode_othermode_h import PD_ShaderNodeSetOtherModeH
from nodes.shadernode_othermode_l import PD_ShaderNodeSetOtherModeL
from nodes.shadernode_geomode import PD_ShaderNodeSetGeoMode, PD_ShaderNodeClearGeoMode
from nodes.shadernode_setcombine import PD_ShaderNodeSetCombine
from nodes.shadernode_tex import PD_ShaderNodeTexConfig, PD_ShaderNodeTexLoad


class PD_ShaderNodeMaterialSetup(PD_ShaderNodeBase):
    bl_idname = 'pd.nodes.materialsetup'
    bl_label = "Material Setup"
    bl_icon = 'NODE_MATERIAL'

    def init(self, context):
        self.pd_init(False, (.353, .233, .233))

classes = [
    PD_ShaderNodeBase,
    PD_ShaderNodeMaterialSetup,
    PD_ShaderNodeClearGeoMode,
    PD_ShaderNodeSetGeoMode,
    PD_ShaderNodeSetOtherModeL,
    PD_ShaderNodeSetOtherModeH,
    PD_ShaderNodeTexConfig,
    PD_ShaderNodeTexLoad,
    PD_ShaderNodeSetCombine,
    PD_ShaderNodeSetTImage,
]

node_categories = [
    ShaderNodeCategory('PD', "PD Material CMD", items=[
        NodeItem(c.bl_idname) for c in classes
    ]),
]

class NODE_MT_category_pd_material(Menu):
    bl_idname = "NODE_MT_category_pd_material"
    bl_label = "PD Material CMD"

    def draw(self, context):
        layout = self.layout

        for clsid in classes:
            node_add_menu.add_node_type(layout, clsid.bl_idname)

        node_add_menu.draw_assets_for_catalog(layout, self.bl_label)

classes += [NODE_MT_category_pd_material]

def pd_materials_draw(self, context):
    layout = self.layout
    layout.menu("NODE_MT_category_pd_material")

def register():
    for cls in classes:
        register_class(cls)

    if bpy.app.version >= (4, 0, 0):
        bpy.types.NODE_MT_shader_node_add_all.append(pd_materials_draw)
    else:
        ndu.register_node_categories('PDNODES', node_categories)


def unregister():
    for cls in reversed(classes):
        unregister_class(cls)

    if bpy.app.version < (4, 0, 0):
        ndu.unregister_node_categories('PDNODES')

