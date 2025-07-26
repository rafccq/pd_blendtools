# Thanks to pyCod3R from blender.stackexchange for this solution

import bpy
import bpy.utils.previews

from . import mtxpalette as mtxp
import pd_blendprops as pdprops
from utils import pd_utils as pdu


class PDTOOLS_PT_MtxPalettePanel(bpy.types.Panel):
    bl_label = 'Matrices'
    bl_idname = "PDTOOLS_PT_MtxPalettePanel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Tool'

    def draw(self, context):
        scn = context.scene

        layout = self.layout
        col = layout.column(align=True)

        col.prop(scn, 'show_all_mtxs', text='Show All')
        show_all = scn.show_all_mtxs

        obj = context.object
        model_mtxs = []

        # check if the object exists and has matrices
        if not obj or 'matrices' not in obj.data:
            show_all = True
            col.enabled = False
        else:
            model_mtxs = obj.data['matrices']
            col.enabled = True

        box = col.box()
        container = box.grid_flow(row_major=True, even_columns=True, align=True)

        selected = None
        for idx in range(64):
            if idx not in model_mtxs and not show_all: continue

            item = scn.color_collection[idx]

            if item.active: selected = item

            col = container.column()
            col.prop(item, "active", icon_value=item.icon, icon_only=True, text=item.name)

        if obj and context.mode == 'EDIT_MESH':
            row = box.row()
            selection = selected is not None
            # enable this button only when the vertx selection mode is set
            row.enabled = selection and context.tool_settings.mesh_select_mode[0]
            mtx = mtxp.color2mtx(selected.color) if selection else 0
            row.operator("pdtools.assign_mtx_verts", text = "Assign To Selected").mtx = mtx
            row = box.row()
            row.operator("pdtools.select_vtx_unassigned_mtxs")

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        ismodel = obj and pdu.pdtype(obj.parent) == pdprops.PD_OBJTYPE_MODEL
        return ismodel and context.mode in ['PAINT_VERTEX', 'EDIT_MESH']


def on_update_mtx(self, _context):
    if self.active:
        for c in self.id_data.color_collection:
            if c.name != self.name: c.active = False
    bpy.data.brushes['Draw'].color = self.color[:3]

class ColorCollection(bpy.types.PropertyGroup):
    name: bpy.props.StringProperty
    active: bpy.props.BoolProperty(default=False, update=on_update_mtx)
    icon: bpy.props.IntProperty()
    color: bpy.props.FloatVectorProperty(
         name = "Color",
         subtype = "COLOR",
         default = (1.0,1.0,1.0,1.0),
         size = 4)


# custom icons for the mtx colors
preview_collections = {}

def gen_icons(context):
    # clear the collection
    scene = context.scene
    if hasattr(scene, "color_collection"):
        scene.color_collection.clear()

    # generate colors and icons
    pcoll = bpy.utils.previews.new()

    size = 32, 32
    for i, hexcol in enumerate(mtxp.mtxpalette):
        color_name = f'{i:02X}'
        color = mtxp.hex2col(hexcol)
        pixels = [*color] * size[0] * size[1]
        icon = pcoll.new(color_name) # name has to be unique!
        icon.icon_size = size
        icon.is_icon_custom = True
        icon.icon_pixels_float = pixels

        # add the item to the collection
        color_item = scene.color_collection.add()
        color_item.name = color_name
        color_item.color = color
        color_item.icon = pcoll[color_name].icon_id

    preview_collections["main"] = pcoll

def register():
    bpy.utils.register_class(PDTOOLS_PT_MtxPalettePanel)
    bpy.utils.register_class(ColorCollection)
    bpy.types.Scene.color_collection = bpy.props.CollectionProperty(type=ColorCollection)
    bpy.types.Scene.show_all_mtxs = bpy.props.BoolProperty(default=False)

def unregister():
    for pcoll in preview_collections.values():
        bpy.utils.previews.remove(pcoll)
    preview_collections.clear()

    bpy.utils.unregister_class(ColorCollection)
    bpy.utils.unregister_class(PDTOOLS_PT_MtxPalettePanel)
    
    del bpy.types.Scene.color_collection

if __name__ == "__main__":
    register()
