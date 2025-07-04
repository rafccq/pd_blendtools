import bpy
from bpy.types import PropertyGroup, Panel, UIList, UI_UL_list, Scene, Context
from bpy.props import StringProperty, EnumProperty

from pd_import.model_import import MeshLayer
from utils import (
    pd_utils as pdu,
    setup_utils as stu,
)
from nodes import nodeutils as ndu
from operators import pd_ops as pdops
import pd_addonprefs as pdp
import pd_blendprops as pdprops


class PDTOOLS_PT_ImportExport(Panel):
    bl_label = "Import/Export"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "PD Tools"

    def draw(self, context: Context) -> None:
        self.layout.operator_context = "INVOKE_DEFAULT"

        rompath = pdp.pref_get(pdp.PD_PREF_ROMPATH)
        rom_exists = bool(rompath)

        row = self.layout.row()
        row.operator("pdtools.import_level")

        row = self.layout.row()
        row.enabled = rom_exists
        icon = 'NONE' if rompath else 'ERROR'
        row.operator("pdtools.import_model_rom", icon=icon)

        row = self.layout.row()
        row.operator("pdtools.import_model_file")
        row.enabled = rom_exists

        self.layout.separator(type='LINE')

        obj = context.object
        row = self.layout.row()
        ismodel = obj is not None and (obj.pd_obj.type & 0xff00) == pdprops.PD_OBJTYPE_MODEL
        row.enabled = rom_exists and ismodel
        row.operator("pdtools.export_model", text = "Export Model")

        row = self.layout.row()
        row.operator("pdtools.export_level")

        # draw the progress bar
        if context.scene.level_loading and bpy.app.version >= (4, 0, 0):
            row = self.layout.row()
            row.progress(
                factor = context.window_manager.progress,
                type="BAR",
                text = context.window_manager.progress_msg
            )
            row.scale_x = 2


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
        props = context.object.pd_model

        box = layout.box()
        box.prop(props, 'name', icon='LOCKED', text='')

        if props.idx >= 0:
            box.label(text=f'Index: {props.idx:02X}', icon='LOCKED')

        if props.layer >= 0:
            txtlayer = 'opa' if props.layer == MeshLayer.OPA else 'xlu'
            box.label(text=f'Layer: {txtlayer}', icon='LOCKED')
        box.enabled = False

class PDTOOLS_PT_Scene(Panel):
    bl_label = 'Scene'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "PD Tools"

    def draw(self, context):
        togg = True

        layout = self.layout
        box = layout.box()
        box.label(text=f'Visibility')
        container = box.grid_flow(columns=3, align=True)
        for idx, name in enumerate(pdprops.PD_COLLECTIONS):
            container.prop(context.scene, 'collections_vis', index=idx, toggle=togg, text=name)

        box = layout.box()
        box.label(text=f'Selection')
        container = box.grid_flow(columns=3, align=True)
        for idx, name in enumerate(pdprops.PD_COLLECTIONS):
            container.prop(context.scene, 'collections_sel', index=idx, toggle=togg, text=name)


class PDModelListItem(PropertyGroup):
    modelname: StringProperty(name='modelname')


class PDTOOLS_UL_ListModels(UIList):
    bl_idname = "pdtools.list_models"

    #note: only in v4.2+ the filter will update as you type
    filter_name: StringProperty(name="filter_name", options={"TEXTEDIT_UPDATE"})
    filter_type: EnumProperty(
        items=[("Props", "Props", "Props", 'Props Models', 1),
               ("Guns", "Guns", "Guns", 'Guns Models', 2),
               ("Chars", "Chars", "Chars", 'Character Models', 3)],
        name="Model Type",
        description="Model Type",
        default="Guns",
    )

    def draw_item(self, _context, layout, _data, item, icon, _active_data, _active_propname):
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            text = item.name
            if item.alias: text += f' ({item.alias})'
            layout.label(text=text, translate=False, icon_value=icon)
        elif self.layout_type == 'GRID':
            layout.alignment = 'CENTER'
            layout.label(text="", icon_value=icon)

    def draw_filter(self, _context, layout):
        row = layout.row(align=True)
        row.prop(self, "filter_name", text="Filter", icon="VIEWZOOM")

        if self['dofilter']:
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
                propname="name")
        else:
            flt_flags = [self.bitflag_filter_item] * len(items)

        # annoyingly, for some reason context_pointer_set is not working here
        # so we manually set this dofilter prop to determine whether or not to show the extra filters
        self['dofilter'] = prop in ['pd_modelfiles']
        if self['dofilter']:
            for idx, item in enumerate(items):
                name = item.name
                f_type = flt_flags[idx] if name[0] == self.filter_type[0] else 0
                flt_flags[idx] &= f_type

        return flt_flags, []

classes = [
    PDTOOLS_PT_ImportExport,
    PDTOOLS_PT_Scene,
    PDTOOLS_UL_ListModels,
]

register, unregister = bpy.utils.register_classes_factory(classes)
