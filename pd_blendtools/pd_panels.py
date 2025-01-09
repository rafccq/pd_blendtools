import bpy
from bpy.types import PropertyGroup, Panel, UIList, UI_UL_list, Scene, Context
from bpy.props import IntProperty, StringProperty, BoolProperty, CollectionProperty, BoolVectorProperty

from pd_blendprops import TILE_FLAGS
from pd_import import MeshLayer
import pd_addonprefs as pdp
import pd_blendprops as pdprops
import pd_utils as pdu
import pd_ops as pdo


class PDTOOLS_PT_PanelModel(Panel):
    bl_label = "Model"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "PD Tools"

    @classmethod
    def poll(cls, context):
        return context.object

    def draw(self, context: Context) -> None:
        self.layout.operator_context = "INVOKE_DEFAULT"
        row = self.layout.row()

        rompath = pdp.pref_get(pdp.PD_PREF_ROMPATH)
        rom_exists = bool(rompath)
        row.enabled = rom_exists
        icon = 'NONE' if rompath else 'ERROR'
        row.operator("pdtools.import_model_rom", icon=icon)

        obj = context.object
        row = self.layout.row()
        ismodel = (obj.pd_obj.type & 0xff00) == pdprops.PD_OBJTYPE_MODEL
        row.enabled = rom_exists and ismodel
        row.operator("pdtools.export_model", text = "Export Model")


class PDTOOLS_PT_ModelProps(Panel):
    bl_label = 'PD Model'
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "object"

    @classmethod
    def poll(cls, context):
        obj = context.object
        return obj and (obj.pd_obj.type & 0xff00) == pdprops.PD_OBJTYPE_MODEL

    def draw(self, context):
        layout = self.layout
        props = context.object.pdmodel_props

        box = layout.box()
        box.prop(props, 'name', icon='LOCKED', text='')

        if props.idx >= 0:
            box.label(text=f'Index: {props.idx:02X}', icon='LOCKED')

        if props.layer >= 0:
            txtlayer = 'opa' if props.layer == MeshLayer.OPA else 'xlu'
            box.label(text=f'Layer: {txtlayer}', icon='LOCKED')
        box.enabled = False

class PDTOOLS_PT_RoomProps(Panel):
    bl_label = 'PD Room'
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "object"


    def draw(self, context):
        obj = context.object
        layout = self.layout
        isroom = pdu.pdtype(obj) == pdprops.PD_OBJTYPE_ROOM

        props_room = obj.pd_room

        box = layout.box()
        name = 'Room' if isroom else 'Block'
        num = props_room.roomnum if isroom else props_room.blocknum

        if isroom:
            box.label(text=f'{name} {num:02X}', icon='LOCKED')
        else:
            box.label(text=f'{name} {num}', icon='LOCKED')
            box.label(text=f'Type: {props_room.blocktype}', icon='LOCKED')
            box.label(text=f'Layer: {props_room.layer}')

        box.enabled = False

class PDTOOLS_PT_Portal(Panel):
    bl_label = 'PD Portal'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "PD Tools"

    @classmethod
    def poll(cls, context):
        obj = context.object
        return obj and (obj.pd_obj.type & 0xff00) == pdprops.PD_OBJTYPE_PORTAL

    def draw(self, context):
        obj = context.object
        layout = self.layout

        props_portal = obj.pd_portal

        box = layout.box()
        box.label(text=f'{obj.pd_obj.name}', icon='OBJECT_DATA')
        box.prop(props_portal, 'room1', text='room 1')
        box.prop(props_portal, 'room2', text='room 2')
        box.operator("pdtools.portal_find_rooms", text = "Auto Find")


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
        column.separator(type='LINE')

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


class PDTOOLS_PT_RoomTools(Panel):
    bl_label = 'Room Tools'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "PD Tools"

    def draw(self, context):
        scn = context.scene
        layout = self.layout

        col = layout.column()
        container = col.split(factor=.5)
        container.label(text=f'Go To Room')
        container.prop(scn, 'pd_room_goto', text='')

        sel = context.selected_objects
        nsel = len(sel)
        isroom = lambda o: pdu.pdtype(o) == pdprops.PD_OBJTYPE_ROOMBLOCK

        row = col.row()
        row = row.split(factor=0.5)
        col = row.column()
        col.operator(pdo.PDTOOLS_OT_RoomSplitByPortal.bl_idname, text='Split By Portal')
        portalselected = context.scene.pd_portal is not None
        col.enabled = isroom(context.active_object) and portalselected
        row.prop(scn, 'pd_portal', text='')

        row = layout.column()
        row.operator(pdo.PDTOOLS_OT_RoomSelectAllBlocks.bl_idname, text='Select All Blocks In Room')
        row.enabled = nsel == 1 and isroom(context.active_object)


class PDTOOLS_PT_Scene(Panel):
    bl_label = 'Scene'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "PD Tools"

    def draw(self, context):
        togg = False

        layout = self.layout
        box = layout.box()
        box.label(text=f'Visibility')
        container = box.grid_flow(columns=3, align=True)
        for idx, name in enumerate(pdprops.PD_COLLECTIONS):
            container.prop(context.scene, 'collections_vis', index=idx, toggle=togg, text=name)

        layout.separator(type='LINE')

        box = layout.box()
        box.label(text=f'Selection')
        container = box.grid_flow(columns=3, align=True)
        for idx, name in enumerate(pdprops.PD_COLLECTIONS):
            container.prop(context.scene, 'collections_sel', index=idx, toggle=togg, text=name)

class PDModelListItem(PropertyGroup):
    filename: StringProperty(name='filename')
    alias: StringProperty(name='alias')


class PDTOOLS_UL_ModelList(UIList):
    #note: only in v4.2+ the filter will update as you type
    filter_name: StringProperty(name="filter_name", options={"TEXTEDIT_UPDATE"})
    filter_type: bpy.props.EnumProperty(
        items=[("Props", "Props", "Props", 'Props Models', 1),
               ("Guns", "Guns", "Guns", 'Guns Models', 2),
               ("Chars", "Chars", "Chars", 'Character Models', 3)],
        name="Model Type",
        description="Model Type",
        default="Guns",
    )

    def draw_item(self, _context, layout, _data, item, icon, _active_data, _active_propname):
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            text = item.filename
            if item.alias: text += f' ({item.alias})'
            layout.label(text=text, translate=False, icon_value=icon)
        elif self.layout_type == 'GRID':
            layout.alignment = 'CENTER'
            layout.label(text="", icon_value=icon)

    def draw_filter(self, _context, layout):
        row = layout.row(align=True)
        row.prop(self, "filter_name", text="Filter", icon="VIEWZOOM")
        row = layout.row(align=True)
        row.prop(self, "filter_type", expand=True)

    def filter_items(self, _context, data, prop):
        items = getattr(data, prop)
        if not len(items):
            return [], []

        if self.filter_name:
            flt_flags = UI_UL_list.filter_items_by_name(
                self.filter_name,
                self.bitflag_filter_item,
                items,
                propname="filename")
        else:
            flt_flags = [self.bitflag_filter_item] * len(items)

        for idx, item in enumerate(items):
            name = item.filename
            f_type = flt_flags[idx] if name[0] == self.filter_type[0] else 0
            flt_flags[idx] &= f_type

        return flt_flags, []

classes = [
    PDTOOLS_PT_PanelModel,
    PDTOOLS_PT_Scene,
    PDTOOLS_PT_TileTools,
    PDTOOLS_PT_RoomTools,
    PDTOOLS_UL_ModelList,
    PDTOOLS_PT_RoomProps,
    PDTOOLS_PT_Portal,
    PDTOOLS_PT_Tile,
    PDModelListItem
]

def register():
    for cl in classes:
        bpy.utils.register_class(cl)

    Scene.pdmodel_list = CollectionProperty(type=PDModelListItem)
    Scene.pdmodel_listindex = IntProperty(name="ModelList item index", default=0)
    Scene.rompath = StringProperty(name="ROM file path", default='')

def unregister():
    for cl in reversed(classes):
        bpy.utils.unregister_class(cl)

    del Scene.pdmodel_list
    del Scene.pdmodel_listindex
    del Scene.rompath

if __name__ == '__main__':
    register()
