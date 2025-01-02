import os
import traceback

import bpy
from bpy.types import Operator
from bpy_extras.io_utils import ImportHelper, ExportHelper
from bpy.props import IntProperty, StringProperty, BoolProperty

import romdata as rom
import pd_import as pdi
import pd_export as pde
import pd_utils as pdu
import pd_addonprefs as pdp
import pd_blendprops as pdprops
import bg_utils as bgu
import tiles_import as tiles
from mtxpalette_panel import gen_icons

class PDTOOLS_OT_LoadRom(Operator, ImportHelper):
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

        # save into the addon settings
        pdp.pref_save(pdp.PD_PREF_ROMPATH, filepath)

        # fill the scene's list of models
        scn.pdmodel_list.clear()
        for filename in romdata.fileoffsets.keys():
            if filename[0] not in ['P', 'G', 'C']: continue

            item = scn.pdmodel_list.add()
            item.filename = filename
            # if item.alias: # TODO


class PDTOOLS_OT_ExportModel(Operator, ExportHelper):
    bl_idname = "pdtools.export_model"
    bl_label = "Export Model"
    bl_description = "Export the Model"

    filename_ext = ''

    def execute(self, context):
        print(f'Export model: {self.filepath}')
        model_obj = pdu.get_model_obj(context.object)
        try:
            pde.export_model(model_obj, self.filepath)
        except RuntimeError as ex:
            traceback.print_exc()
            pass

        self.report({'INFO'}, "Model Exported")
        return {'FINISHED'}

    def invoke(self, context, _event):
        obj = pdu.get_model_obj(context.object)
        props = obj.pdmodel_props

        blend_filepath = context.blend_data.filepath
        self.filepath = os.path.join(blend_filepath, props.name)
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}


class PDTOOLS_OT_ImportModelFromFile(Operator, ImportHelper):
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


class PDTOOLS_OT_AssignMtxToVerts(Operator):
    bl_idname = "pdtools.assign_mtx_verts"
    bl_label = "Assign To Selected"
    bl_description = "Assign Matrix to Selected Vertices"

    mtx: IntProperty()

    def execute(self, context):
        nverts = pdu.assign_mtx_to_selected_verts(self.mtx)
        s = 's' if nverts > 1 else ''
        self.report({"INFO"}, f'Matrix {self.mtx:02X} assigned to {nverts} vert{s}')
        return {'FINISHED'}


class PDTOOLS_OT_SelectVertsUnassignedMtxs(Operator):
    bl_idname = "pdtools.select_vtx_unassigned_mtxs"
    bl_label = "Select Unassigned"
    bl_description = "Select Vertices With No Assigned Matrix"

    def execute(self, context):
        nverts = pdu.select_vtx_unassigned_mtxs()
        s = 's' if nverts > 1 else ''
        self.report({"INFO"}, f'{nverts} vert{s} selected')
        pdu.redraw_ui()
        return {'FINISHED'}


class PDTOOLS_OT_PortalFindRooms(Operator):
    bl_idname = "pdtools.portal_find_rooms"
    bl_label = "Auto Find"
    bl_description = "Find and assign 2 nearest rooms to the portal"

    def execute(self, context):
        bl_portal = context.active_object
        rooms = bgu.portal_find_rooms(bl_portal)
        print(rooms)
        # TODO check result

        props_portal = bl_portal.pd_portal
        props_portal.room1 = rooms[0]
        props_portal.room2 = rooms[1]

        return {'FINISHED'}

class PDTOOLS_OT_TileApplyProps(Operator):
    bl_idname = "pdtools.tile_apply_props"
    bl_label = "Apply Tile Props"
    bl_description = "Apply Props to Selected Tiles"

    def execute(self, context):
        prop = context.pd_tile
        for bl_tile in context.selected_objects:
            bl_tile.pd_tile.flags = prop.flags
            bl_tile.pd_tile.floorcol = prop.floorcol
            bl_tile.pd_tile.floortype = prop.floortype
            # bl_tile.pd_tile.room = prop.room
        n = tiles.bg_colortiles(context)
        return {'FINISHED'}


class PDTOOLS_OT_RoomCreatePortalBetween(Operator):
    bl_idname = "pdtools.room_create_portal_between"
    bl_label = "Create Portal"
    bl_description = "Create Portal Between Rooms"

    @classmethod
    def poll(cls, context):
        sel = context.selected_objects
        n = len(sel)
        isroom = lambda o: (o.pd_obj.type & 0xff00) == pdprops.PD_OBJTYPE_ROOMBLOCK
        # typeok = all([(o.pd_obj.type & 0xff00) == pdprops.PD_OBJTYPE_ROOMBLOCK for o in sel])
        return n == 2 and isroom(sel[0]) and isroom(sel[1])

    def execute(self, context):
        sel = context.selected_objects
        room1 = sel[0]
        room2 = sel[1]
        return {'FINISHED'}


class PDTOOLS_OT_SelectDirectory(Operator):
    bl_idname = "pdtools.select_directory"
    bl_label = "Select Directory"
    bl_options = {'REGISTER'}

    # Define this to tell 'fileselect_add' that we want a directoy
    directory: StringProperty(
        name="Path",
        description="Select Directory"
    )

    # Filters folders
    filter_folder: BoolProperty(
        default=True,
        options={"HIDDEN"}
    )

    def execute(self, context):
        print("Selected dir: '" + self.directory + "'")
        return {'FINISHED'}

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}


def load_model(_context, name):
    rompath = pdp.pref_get(pdp.PD_PREF_ROMPATH)
    romdata = rom.Romdata(rompath)
    pdi.import_model(romdata, name)


class PDTOOLS_OT_ImportModelFromROM(Operator):
    bl_idname = "pdtools.import_model_rom"
    bl_label = "Import From ROM"

    @classmethod
    def description(cls, context, properties):
        scn = context.scene
        if scn.rompath:
            return 'Import a model from the ROM'
        else:
            return 'ROM not loaded. Go to Preferences > Add-ons > pd_blendtools'

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

        # when the addon is first installed, the icons need to be generated
        # because the lost_post handler won't be called
        if len(scn.color_collection) == 0:
            gen_icons(context)

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


class PDTOOLS_OT_MessageBox(bpy.types.Operator):
    bl_idname = "pdtools.messagebox"
    bl_label = "Message Box"
    # bl_options = {'REGISTER', 'INTERNAL'}

    msg: StringProperty(default='')

    def execute(self, context):
        self.report({'INFO'}, self.msg)
        print(f'OP: {self.msg}')
        return {'FINISHED'}

    def invoke(self, context, event):
        return self.execute(context)


classes = [
    PDTOOLS_OT_LoadRom,
    PDTOOLS_OT_ImportModelFromROM,
    PDTOOLS_OT_ImportModelFromFile,
    PDTOOLS_OT_AssignMtxToVerts,
    PDTOOLS_OT_ExportModel,
    PDTOOLS_OT_SelectVertsUnassignedMtxs,
    PDTOOLS_OT_SelectDirectory,
    PDTOOLS_OT_PortalFindRooms,
    PDTOOLS_OT_RoomCreatePortalBetween,
    PDTOOLS_OT_TileApplyProps,
    PDTOOLS_OT_MessageBox,
]

def register():
    for cl in classes:
        bpy.utils.register_class(cl)


def unregister():
    for cl in classes:
        bpy.utils.unregister_class(cl)


if __name__ == '__main__':
    register()
