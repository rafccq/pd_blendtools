import bpy
from bpy_extras.io_utils import ImportHelper
from bpy.props import IntProperty

import romdata as rom
import pd_import as pdi
import pd_utils as pdu

class PDTOOLS_OT_LoadRom(bpy.types.Operator, ImportHelper):
    bl_idname = "pdtools.load_rom"
    bl_label = "Load Rom"
    bl_description = "Load a PD rom, accepted versions: NTSC"

    filter_glob: bpy.props.StringProperty(
        default="*.z64",
    )

    def execute(self, context):
        PDTOOLS_OT_LoadRom.load_rom(context, self.filepath)
        return {'FINISHED'}

    @staticmethod
    def load_rom(context, filepath):
        scn = context.scene

        romdata = rom.Romdata(filepath)

        # fill the scene's list of models
        scn.rompath = filepath
        scn.pdmodel_list.clear()
        for filename in romdata.fileoffsets.keys():
            if filename[0] not in ['P', 'G', 'C']: continue

            item = scn.pdmodel_list.add()
            item.filename = filename
            # if item.alias: # TODO


class PDTOOLS_OT_ImportModelFromFile(bpy.types.Operator, ImportHelper):
    bl_idname = "pdtools.import_model_file"
    bl_label = "Import From File"
    bl_description = "Import a model from a file"

    filter_glob: bpy.props.StringProperty(
        default="*.*",
        # options={'HIDDEN'},
    )

    def execute(self, context):
        print('import model from file', self.filepath)
        return {'FINISHED'}

class PDTOOLS_OT_AssignMtxToVerts(bpy.types.Operator):
    bl_idname = "pdtools.assign_mtx_verts"
    bl_label = "Assign To Selected"
    bl_description = "Assign Matrix to Selected Vertices"

    mtx: IntProperty()

    def execute(self, context):
        nverts = pdu.assign_mtx_to_selected_verts(self.mtx)
        s = 's' if nverts > 1 else ''
        self.report({"INFO"}, f'Matrix {self.mtx:02X} assigned to {nverts} vert{s}')
        return {'FINISHED'}


def load_model(context, name):
    scn = context.scene
    romdata = rom.Romdata(scn.rompath)
    pdi.import_model(romdata, name)


class PDTOOLS_OT_ImportModelFromROM(bpy.types.Operator):
    bl_idname = "pdtools.import_model_rom"
    bl_label = ""

    @classmethod
    def description(cls, context, properties):
        scn = context.scene
        if scn.rompath:
            return 'Import a model from the ROM'
        else:
            return 'ROM not loaded. Go to Preferences > Addon'

    message = bpy.props.StringProperty(
        name = "message",
        description = "message",
        default = ''
    )

    guns: bpy.props.BoolProperty(default=True)
    props: bpy.props.BoolProperty(default=False)
    chars: bpy.props.BoolProperty(default=False)

    def execute(self, context):
        scn = context.scene
        item = scn.pdmodel_list[scn.pdmodel_listindex]
        load_model(context, item.filename)
        return {'FINISHED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=300)

    def draw(self, context):
        self.layout.label(text='Import Model From ROM')
        scn = context.scene
        self.layout.template_list("PDTOOLS_UL_ModelList", "", scn, "pdmodel_list",
                                  scn, "pdmodel_listindex", rows=20)


classes = [
    PDTOOLS_OT_LoadRom,
    PDTOOLS_OT_ImportModelFromROM,
    PDTOOLS_OT_ImportModelFromFile,
    PDTOOLS_OT_AssignMtxToVerts,
]

def register():
    for cl in classes:
        bpy.utils.register_class(cl)


def unregister():
    for cl in classes:
        bpy.utils.unregister_class(cl)


if __name__ == '__main__':
    register()
