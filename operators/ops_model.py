import os
import traceback

import bpy
from bpy.types import Operator
from bpy_extras.io_utils import ImportHelper, ExportHelper
from bpy.props import IntProperty, StringProperty

from pd_blendtools import pd_addonprefs as pda
from ui.mtxpalette_panel import gen_icons
from pd_data.model_info import ModelNames
from utils import (
    pd_utils as pdu,
    setup_utils as stu,
)
from pd_import import (
    model_import as mdi,
    setup_import as stpi,
)
from pd_export import model_export as mde
from pd_data import romdata as rom
from materials import pd_materials as pdm

from fast64.f3d import f3d_material as f3dm

def load_model(_context, modelname=None, filename=None):
    rompath = pda.rompath()
    romdata = rom.Romdata(rompath)

    matlib = bpy.data.materials
    matcache = { mat.hashed:mat.name for mat in matlib }

    if modelname:
        model_obj, _ = mdi.import_model(romdata, matcache, mdi.ASSET_TYPE_MODEL, modelname=modelname)
    elif filename:
        model_obj, _ = mdi.import_model(romdata, matcache, mdi.ASSET_TYPE_MODEL, filename=filename)
    else:
        raise RuntimeError('load_model() called without modelname and filename params')

    for bl_obj in model_obj.children:
        for mat in bl_obj.data.materials:
            if not mat.is_f3d: continue

            f3dm.update_node_values_of_material(mat, _context)
            pdm.mat_presetcombine(mat)

    coll = pdu.active_collection()
    pdu.add_to_collection(model_obj, coll=coll)
    stpi.blender_align(model_obj)
    pdu.select_obj(model_obj)


class PDTOOLS_OT_ImportModelFromFile(Operator, ImportHelper):
    bl_idname = "pdtools.import_model_file"
    bl_label = "Import From File"
    bl_description = "Import a model from a file"

    filter_glob: StringProperty(default="*.*",)

    def execute(self, context):
        scn = context.scene
        # when the addon is first installed, the icons need to be generated
        # because the load_post handler won't be called
        if len(scn.color_collection) == 0:
            gen_icons(context)

        # print('import model from file', self.filepath)
        load_model(context, filename=self.filepath)
        return {'FINISHED'}


class PDTOOLS_OT_ImportModelFromROM(Operator):
    bl_idname = "pdtools.import_model_rom"
    bl_label = "Import Model From ROM"

    @classmethod
    def description(cls, context, properties):
        scn = context.scene
        if scn.rompath:
            return 'Import a model from the ROM'
        else:
            return 'ROM not loaded. Go to Preferences > Add-ons > pd_blendtools'

    def execute(self, context):
        scn = context.scene

        # when the addon is first installed, the icons need to be generated
        # because the load_post handler won't be called
        if len(scn.color_collection) == 0:
            gen_icons(context)

        item = scn.pd_modelfiles[scn.pd_modelfiles_idx]
        load_model(context, modelname=item.name)
        return {'FINISHED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=300)

    def draw(self, context):
        scn = context.scene
        layout = self.layout
        layout.template_list('pdtools.list_models', '', scn, 'pd_modelfiles', scn, 'pd_modelfiles_idx', rows=20)


class PDTOOLS_OT_SelectModel(Operator):
    bl_idname = "pdtools.select_model"
    bl_label = "Select Model"
    bl_description = "Select Model"

    type: StringProperty(name='type', options={'LIBRARY_EDITABLE', 'HIDDEN'})
    saved_idx: IntProperty(name='saved_idx', options={'LIBRARY_EDITABLE', 'HIDDEN'})

    def execute(self, context):
        scn = context.scene

        if len(scn.color_collection) == 0:
            gen_icons(context)

        if self.type == 'model':
            bl_obj = context.active_object
            pd_prop = bl_obj.pd_prop
            stu.change_model(bl_obj, scn.pd_modelnames_idx)
            scn.pd_modelnames_idx = self.saved_idx
        else:
            item = scn.pd_modelnames[scn.pd_modelnames_idx]
            scn.pd_model = item.name
        return {'FINISHED'}

    def invoke(self, context, event):
        scn = context.scene

        if self.type == 'model':
            pd_prop = context.active_object.pd_prop
            self.saved_idx = scn.pd_modelnames_idx
            scn.pd_modelnames_idx = pd_prop.modelnum
        else:
            scn.pd_modelnames_idx = ModelNames.index(scn.pd_model)

        return context.window_manager.invoke_props_dialog(self, width=400)

    def draw(self, context):
        scn = context.scene
        self.layout.template_list('pdtools.list_models', '', scn, 'pd_modelnames',
                                  scn, 'pd_modelnames_idx', rows=20)


class PDTOOLS_OT_ExportModel(Operator, ExportHelper):
    bl_idname = "pdtools.export_model"
    bl_label = "Export Model"
    bl_description = "Export the Model"

    filename_ext = ''

    def execute(self, context):
        print(f'Export model: {self.filepath}')
        model_obj = pdu.get_model_obj(context.object)
        try:
            mde.export_model(model_obj, self.filepath)
        except RuntimeError as ex:
            traceback.print_exc()
            pass

        self.report({'INFO'}, "Model Exported")
        return {'FINISHED'}

    def invoke(self, context, _event):
        obj = pdu.get_model_obj(context.object)
        props = obj.pd_model

        blend_filepath = context.blend_data.filepath
        self.filepath = os.path.join(blend_filepath, props.name)
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}


class PDTOOLS_OT_AssignMtxToVerts(Operator):
    bl_idname = "pdtools.assign_mtx_verts"
    bl_label = "Assign To Selected"
    bl_description = "Assign matrix to selected vertices"

    mtx: IntProperty()

    def execute(self, context):
        nverts = pdu.assign_mtx_to_selected_verts(self.mtx)
        s = 's' if nverts > 1 else ''
        self.report({"INFO"}, f'Matrix {self.mtx:02X} assigned to {nverts} vert{s}')
        return {'FINISHED'}


class PDTOOLS_OT_SelectVertsUnassignedMtxs(Operator):
    bl_idname = "pdtools.select_vtx_unassigned_mtxs"
    bl_label = "Select Unassigned"
    bl_description = "Select vertices with no assigned matrix"

    def execute(self, context):
        nverts = pdu.select_vtx_unassigned_mtxs()
        s = 's' if nverts > 1 else ''
        self.report({"INFO"}, f'{nverts} vert{s} selected')
        pdu.redraw_ui()
        return {'FINISHED'}


classes = [
    PDTOOLS_OT_ImportModelFromROM,
    PDTOOLS_OT_ImportModelFromFile,
    PDTOOLS_OT_SelectModel,
    PDTOOLS_OT_ExportModel,
    PDTOOLS_OT_AssignMtxToVerts,
    PDTOOLS_OT_SelectVertsUnassignedMtxs,
]

register, unregister = bpy.utils.register_classes_factory(classes)
