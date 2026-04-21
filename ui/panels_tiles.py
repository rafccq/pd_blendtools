import bpy
from bpy.types import Panel

from utils import pd_utils as pdu
import pd_blendprops as pdprops


TILE_FLAGS = pdprops.TILE_FLAGS


class PDTOOLS_PT_TileTools(Panel):
    bl_label = 'Tile Tools'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "PD Tools"

    def draw(self, context):
        scn = context.scene
        layout = self.layout
        box = layout.box()
        box.label(text='Highlight')
        box.prop(scn, 'pd_tile_hilightmode', text='Mode')

        if scn.pd_tile_hilightmode == 'flags':
            container = box.grid_flow(columns=2, align=True)
            for idx, flag in enumerate(TILE_FLAGS):
                container.prop(scn.pd_tile_hilight, 'flags', index=idx, text=flag, toggle=True)
        elif scn.pd_tile_hilightmode == 'room':
            container = box.row()
            container.prop(scn.pd_tile_hilight, 'room', text='Room')

        row = layout.row()
        row.operator('pdtools.op_tiles_select_room', text='Select All In The Same Room')

        bl_tile = context.active_object
        nsel = len(context.selected_objects)
        row.enabled = bool(bl_tile) and pdu.pdtype(bl_tile) == pdprops.PD_OBJTYPE_TILE and nsel == 1


def draw_row(pd_tile, label, name, layout, factor, multiple, multiple_prop):
    container = layout.split(factor=.91) if multiple else layout

    container_L = container.split(factor=factor)
    container_L.label(text=label)
    container_L.prop(pd_tile, name, text='')

    if multiple:
        container.context_pointer_set(name='pd_tile', data=pd_tile)
        op = container.operator('pdtools.tile_apply_props', text='', icon='CHECKMARK')
        op.prop = multiple_prop


class PDTOOLS_PT_Tile(Panel):
    bl_label = 'Tile'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "PD Tools"

    @classmethod
    def poll(cls, context):
        obj = context.object
        return obj and (obj.pd_obj.type & 0xff00) == pdprops.PD_OBJTYPE_TILE

    def draw(self, context):
        # if multiple selected, choose the first object selected (always the first to last in the list)
        multiple = len(context.selected_objects) > 1
        obj = context.selected_objects[-2] if multiple else context.active_object

        if not obj: return

        scn = context.scene
        layout = self.layout

        column = layout.column()

        pd_tile = obj.pd_tile
        txt = 'Multiple Selected' if multiple else f'{obj.name}'
        column.label(text=txt, icon='OBJECT_DATA')
        pdu.ui_separator(column, type='LINE')

        factor = .35
        draw_row(pd_tile, 'Room', 'room', column, factor, multiple, pdprops.TILEPROP_ROOM)
        draw_row(pd_tile, 'Floor Color', 'floorcol', column, factor, multiple, pdprops.TILEPROP_FLOORCOL)
        draw_row(pd_tile, 'Floor Type', 'floortype', column, factor, multiple, pdprops.TILEPROP_FLOORTYPE)

        box = column.box()
        row = box.row().split(factor=.85)
        row.label(text=f'Flags')
        row.prop(scn, 'pd_tile_flag_presets', text='', icon='COLLAPSEMENU')
        container = box.grid_flow(columns=2, align=True)

        for idx, flag in enumerate(TILE_FLAGS):
            container.prop(pd_tile, 'flags', index=idx, text=flag)

        if multiple:
            container = column
            container.context_pointer_set(name='pd_tile', data=pd_tile)
            op = container.operator("pdtools.tile_apply_props", text="Apply Flags To Selection", icon='GREASEPENCIL')
            op.prop = pdprops.TILEPROP_FLAGS
            pdu.ui_separator(container, type='LINE')
            container.context_pointer_set(name='pd_tile', data=pd_tile)
            op = container.operator('pdtools.tile_apply_props', text = 'Apply All To Selection')
            op.prop = pdprops.TILEPROP_ALL


classes = [
    PDTOOLS_PT_Tile,
    PDTOOLS_PT_TileTools,
]

register, unregister = bpy.utils.register_classes_factory(classes)
