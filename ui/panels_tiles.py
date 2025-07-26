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


def draw_row(props, label, name, layout, factor):
    container = layout.split(factor=factor)
    container.label(text=label)
    container.prop(props, name, text='')


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

        layout = self.layout

        column = layout.column()

        props_tile = obj.pd_tile
        txt = 'Multiple Selected' if multiple else f'{obj.name}'
        column.label(text=txt, icon='OBJECT_DATA')
        pdu.ui_separator(column, type='LINE')

        draw_row(props_tile, 'Room', 'room', column, .35)
        draw_row(props_tile, 'Floor Color', 'floorcol', column, .35)
        draw_row(props_tile, 'Floor Type', 'floortype', column, .35)

        box = column.box()
        box.label(text=f'Flags')
        container = box.grid_flow(columns=2, align=True)

        for idx, flag in enumerate(TILE_FLAGS):
            container.prop(props_tile, 'flags', index=idx, text=flag)

        if multiple:
            column.context_pointer_set(name='pd_tile', data=obj.pd_tile)
            column.operator("pdtools.tile_apply_props", text = "Apply To Selection")


classes = [
    PDTOOLS_PT_Tile,
    PDTOOLS_PT_TileTools,
]

register, unregister = bpy.utils.register_classes_factory(classes)
