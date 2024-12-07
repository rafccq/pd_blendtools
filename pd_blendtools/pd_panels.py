import bpy
from bpy.types import PropertyGroup, Panel, UIList, UI_UL_list, Scene, Context
from bpy.props import IntProperty, StringProperty, BoolProperty, CollectionProperty

import pd_utils as pdu
from pd_import import MeshLayer


class PDTOOLS_PT_PanelModel(Panel):
    bl_idname = "PDTOOLS_PT_PanelModel"
    bl_label = "Model"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "PD Tools"

    def draw(self, context: Context) -> None:
        self.layout.operator_context = "INVOKE_DEFAULT"
        row = self.layout.row()

        addon_prefs = pdu.addon_prefs()
        rom_exists = bool(addon_prefs.rompath)
        row.enabled = rom_exists
        icon = 'NONE' if addon_prefs.rompath else 'ERROR'
        row.operator("pdtools.import_model_rom", icon=icon)
        # self.layout.operator("pdtools.import_model_file")

        obj = context.object
        row = self.layout.row()
        row.enabled = rom_exists and pdu.get_model_obj(obj) is not None
        row.operator("pdtools.export_model", text = "Export Model")


class PDTOOLS_PT_ModelProps(Panel):
    bl_label = 'PD Model'
    bl_idname = 'PDTOOLS_PT_ModelProps'
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "object"

    @classmethod
    def poll(cls, context):
        return context.object

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

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname):
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            text = item.filename
            if item.alias: text += f' ({item.alias})'
            layout.label(text=text, translate=False, icon_value=icon)
        elif self.layout_type == 'GRID':
            layout.alignment = 'CENTER'
            layout.label(text="", icon_value=icon)

    def draw_filter(self, context, layout):
        row = layout.row(align=True)
        row.prop(self, "filter_name", text="Filter", icon="VIEWZOOM")
        row = layout.row(align=True)
        row.prop(self, "filter_type", expand=True)

    def filter_items(self, context, data, prop):
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
    PDTOOLS_UL_ModelList,
    PDTOOLS_PT_ModelProps,
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
