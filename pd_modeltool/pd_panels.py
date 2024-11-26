import bpy
from bpy.types import PropertyGroup
from bpy.props import IntProperty, StringProperty, BoolProperty, CollectionProperty

class PDTOOLS_PT_MainPanel(bpy.types.Panel):
    bl_idnaame = "PDTOOLS_PT_MainPanel"
    bl_label = "Setup"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "PD Tools"

    def draw(self, context: bpy.types.Context) -> None:
        row = self.layout.row()

        self.layout.operator_context = "INVOKE_DEFAULT"
        op = row.operator("pdtools.load_rom")


class PDTOOLS_PT_PanelModel(bpy.types.Panel):
    bl_idname = "PDTOOLS_PT_PanelModel"
    bl_label = "Model"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "PD Tools"

    def draw(self, context: bpy.types.Context) -> None:
        scn = context.scene
        self.layout.operator_context = "INVOKE_DEFAULT"
        row = self.layout.row()
        row.enabled = bool(scn.rompath)
        icon = 'NONE' if scn.rompath else 'ERROR'
        row.operator("pdtools.import_model_rom", text = "Import From ROM", icon=icon)
        self.layout.operator("pdtools.import_model_file")


class PDModelListItem(PropertyGroup):
    filename: StringProperty(name='filename')
    alias: StringProperty(name='alias')

class PDTOOLS_UL_ModelList(bpy.types.UIList):
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
            flt_flags = bpy.types.UI_UL_list.filter_items_by_name(
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
    PDTOOLS_PT_MainPanel,
    PDTOOLS_PT_PanelModel,
    PDTOOLS_UL_ModelList,
    PDModelListItem
]

def register():
    for cl in classes:
        bpy.utils.register_class(cl)

    bpy.types.Scene.pdmodel_list = CollectionProperty(type=PDModelListItem)
    bpy.types.Scene.pdmodel_listindex = IntProperty(name="ModelList item index", default=0)
    bpy.types.Scene.rompath = StringProperty(name="ROM file path", default='')

def unregister():
    for cl in classes:
        bpy.utils.unregister_class(cl)

    del bpy.types.Scene.pdmodel_list
    del bpy.types.Scene.pdmodel_listindex
    del bpy.types.Scene.rompath

if __name__ == '__main__':
    register()
