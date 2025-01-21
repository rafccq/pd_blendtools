import os
import traceback

import bpy
from bpy.types import Operator, WorkSpaceTool
import gpu
import bmesh
from gpu_extras.batch import batch_for_shader
from bpy_extras.io_utils import ImportHelper, ExportHelper
from bpy.props import IntProperty, FloatProperty, StringProperty, BoolProperty
from bl_ui import space_toolsystem_common
from mathutils import Vector
import aud


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


class PDTOOLS_OT_RoomSplitByPortal(Operator):
    bl_idname = "pdtools.room_split_by_portal"
    bl_label = "Split Room By Portal"
    # bl_options = {'REGISTER', 'INTERNAL'}

    def execute(self, context):
        # self.report({'INFO'}, self.msg)
        scn = context.scene
        bl_roomblock = context.active_object
        bl_portal = scn.pd_portal
        bl_roomblock_new = bgu.room_split_by_portal(bl_roomblock, bl_portal, context)
        bpy.ops.object.select_all(action='DESELECT')
        bpy.context.view_layer.objects.active = bl_roomblock_new
        bl_roomblock_new.select_set(True)
        scn.pd_portal = None
        return {'FINISHED'}

    def invoke(self, context, event):
        return self.execute(context)


class PDTOOLS_OT_RoomSelectAllBlocks(Operator):
    bl_idname = "pdtools.op_room_select_all_blocks"
    bl_label = "Select All Blocks In Room"
    # bl_options = {'REGISTER', 'INTERNAL'}

    def execute(self, context):
        bl_room = context.active_object
        bl_room = bgu.parent_room(bl_room) if pdu.pdtype(bl_room) == pdprops.PD_OBJTYPE_ROOMBLOCK else bl_room

        bpy.ops.object.select_all(action="DESELECT")
        for child in bl_room.children:
            child.select_set(True)

        return {'FINISHED'}

# class PDTOOLS_OT_RoomSplitByPortal(bpy.types.Operator):
class PDTOOLS_OT_PortalFromEdge(Operator):
    bl_idname = "pdtools.op_portal_from_edge"
    bl_label = "Portal From Edge"
    # bl_options = {'REGISTER', 'INTERNAL'}

    def ws_update_geometry(_self, _ctx):
        PD_WSTOOL_PortalFromEdge.update_geometry()

    direction: bpy.props.EnumProperty(
        items=[
            ('vertical', 'Vertical', 'Vertical', 'Vertical', 1),
            ('horizontal', 'Horizontal', 'Horizontal', 'Horizontal', 2),
        ],
        name='Direction',
        description='Portal Direction (World)',
        default='vertical',
    )

    elevation: FloatProperty(name='Elevation', default=0, min=-180, max=180,
                             description='Rotation From The Edge Towards The Up Direction',
                             update=ws_update_geometry)

    pitch: FloatProperty(name='Pitch', default=0, min=-180, max=180,
                         # description='' ,
                         description='Rotation Around The Edge Axis',
                         update=ws_update_geometry)

    width: FloatProperty(name='width', default=10, min=1, max=10000,
                         update=ws_update_geometry)

    height: FloatProperty(name='height', default=10, min=1, max=10000,
                          update = ws_update_geometry)

    def execute(self, context):
        bl_obj = context.edit_object
        bm = bmesh.from_edit_mesh(bl_obj.data)

        edges_sel = [e for e in bm.edges if e.select]

        n = len(edges_sel)
        if n != 1:
            bm.free()
            msg = 'No Selection' if n < 1 else 'Select Only One Edge'
            pdu.msg_box('', msg, 'ERROR')
            return {'FINISHED'}

        tool = context.workspace.tools.from_space_view3d_mode(context.mode, create=False)
        props = tool.operator_properties(self.bl_idname)

        w, h = props.width, props.height
        elv, pitch = props.elevation, props.pitch
        direction = props.direction

        edge = edges_sel[0]
        M = bl_obj.matrix_world
        verts = bgu.portal_verts_from_edge(edge, M, w, h, elv, pitch, direction)
        print(w, h, edge)
        print(verts)
        print(M)
        bgu.new_portal_from_verts(bl_obj, verts)
        edge.select = False
        bm.free()
        return {'FINISHED'}

    def invoke(self, context, event):
        return self.execute(context)


class PD_WSTOOL_PortalFromEdge(WorkSpaceTool):
    bl_space_type = 'VIEW_3D'
    bl_context_mode = 'EDIT_MESH'
    bl_idname = "pdtools.ws_new_portal_from_edge"
    bl_label = "Portal From Edge"
    bl_description = "Creates a new portal from the selected edge"
    bl_icon = "ops.mesh.primitive_cube_add_gizmo"
    bl_widget = None
    # bl_keymap = (
    #     ("object.simple_operator", {"type": 'LEFTMOUSE', "value": 'PRESS'}, None),
    # )

    _batch = None
    _draw_handle = None
    _shader = None

    @staticmethod
    def draw_prop(layout, props, name):
        layout.label(text=f'{name}:')
        layout.prop(props, name.lower(), text='')

    @staticmethod
    def draw_settings(context, layout, tool, extra=False):
        props = tool.operator_properties('pdtools.op_portal_from_edge')

        if extra:
            col = layout.column()
            row = col.row()
            PD_WSTOOL_PortalFromEdge.draw_prop(row, props, 'Direction')
            row = col.row()
            PD_WSTOOL_PortalFromEdge.draw_prop(row, props, 'Elevation')
            row = col.row()
            PD_WSTOOL_PortalFromEdge.draw_prop(row, props, 'Pitch')
            return

        PD_WSTOOL_PortalFromEdge.draw_prop(layout, props, 'width')
        PD_WSTOOL_PortalFromEdge.draw_prop(layout, props, 'height')

        # this will call this very function, with the parameter extra = True
        layout.popover("TOPBAR_PT_tool_settings_extra", text="...")
        layout.operator("pdtools.op_portal_from_edge", text='Create Portal')

    @classmethod
    def poll(self, context):
        if context.object and context.object.type == 'MESH':
            return context.object.mode == 'EDIT'

    @classmethod
    def update_geometry(cls):
        # Get current properties
        context = bpy.context
        tool = context.workspace.tools.from_space_view3d_mode(
            context.mode, create=False
        )
        if tool and tool.idname == cls.bl_idname:
            bl_obj = context.edit_object
            bm = bmesh.from_edit_mesh(bl_obj.data)

            edges_sel = [e for e in bm.edges if e.select]

            if len(edges_sel) != 1:
                bm.free()
                context.area.tag_redraw()
                return 1

            props = tool.operator_properties(PDTOOLS_OT_PortalFromEdge.bl_idname)
            w, h = props.width, props.height

            elv, pitch = props.elevation, props.pitch
            direction = props.direction

            edge = edges_sel[0]
            M = bl_obj.matrix_world
            coords = bgu.portal_verts_from_edge(edge, M, w, h, elv, pitch, direction)
            indices = [(0, 1), (1, 2), (2, 3), (3, 0)]

            cls._batch = batch_for_shader(
                cls._shader, 'LINES',
                {'pos': coords}, indices= indices
            )

            # Force viewport update
            if context.area:
                context.area.tag_redraw()

            bm.free()
            return 0
    @classmethod
    def draw_callback_px(cls):
        if cls._shader:
            res = cls.update_geometry()
            if res: return

            gpu.state.line_width_set(2)
            cls._shader.bind()
            cls._shader.uniform_float("color", (1, 1, 0, 1))
            cls._batch.draw(cls._shader)

    @classmethod
    def setup_draw_handler(cls):
        if cls._draw_handle is None:
            if not cls._shader:
                cls._shader = gpu.shader.from_builtin('UNIFORM_COLOR')
                # initial geometry creation
                cls.update_geometry()

            cls._draw_handle = bpy.types.SpaceView3D.draw_handler_add(
                cls.draw_callback_px, (), 'WINDOW', 'POST_VIEW')

    @classmethod
    def remove_draw_handler(cls):
        if cls._draw_handle is not None:
            bpy.types.SpaceView3D.draw_handler_remove(cls._draw_handle, 'WINDOW')
            cls._draw_handle = None


class PDTOOLS_OT_PortalFromFace(Operator):
    bl_idname = "pdtools.op_portal_from_face"
    bl_label = "PD: Portal From Face"
    bl_description = "Creates A Portal From The Selected Face"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        err = bgu.new_portal_from_faces(context)
        if err:
            pdu.msg_box('', err, 'ERROR')
        return {'FINISHED'}

class PDTOOLS_OT_TilesFromFaces(Operator):
    bl_idname = "pdtools.op_tiles_from_faces"
    bl_label = "PD: Tiles From Faces"
    bl_description = "Creates Tiles From The Selected Faces"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        bl_obj = context.edit_object
        bm = bmesh.from_edit_mesh(bl_obj.data)
        faces_sel = [f for f in bm.faces if f.select]

        if not faces_sel:
            pdu.msg_box('', 'No Selection', 'ERROR')
            bm.free()
            return {'FINISHED'}

        lib = bpy.data.collections
        num = len(lib['Tiles'].objects) if 'Tiles' in lib else 0
        tiles = []
        for face in faces_sel:
            bl_tile = bgu.tile_from_face(f'Tile_{num}', bl_obj, face)
            tiles.append(bl_tile)
            num += 1

        # switch to object mode and select all the newly created tiles
        bpy.ops.object.mode_set(mode="OBJECT")
        bpy.ops.object.select_all(action='DESELECT')
        for tile in tiles: tile.select_set(True)
        pdu.set_active_obj(tiles[0])
        bm.free()
        return {'FINISHED'}


class PDTOOLS_OT_TilesSelectSameRoom(Operator):
    bl_idname = "pdtools.op_tiles_select_room"
    bl_label = "PD: Select All From Room"
    bl_description = "Select All Tiles From The Same Room"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        bl_obj = context.active_object
        pd_tile = bl_obj.pd_tile

        bpy.ops.object.select_all(action='DESELECT')
        tiles = bpy.data.collections['Tiles'].objects
        for bl_tile2 in tiles:
            pd_tile2 = bl_tile2.pd_tile
            if pd_tile2.roomnum == pd_tile.roomnum:
                bl_tile2.select_set(True)

        return {'FINISHED'}

class PDTOOLS_OT_SetupLiftCreateStop(Operator):
    bl_idname = "pdtools.op_setup_lift_create_stop"
    bl_label = "PD: Create Stop"
    bl_description = "Create Lift Stop"
    bl_options = {'REGISTER', 'UNDO'}

    index: IntProperty(name='index', default=0, options={'LIBRARY_EDITABLE'})

    def execute(self, context):
        bl_obj = context.active_object
        pd_lift = bl_obj.pd_lift

        name = f'{bl_obj.name} stop{self.index+1}'
        bl_stop = pdu.new_empty_obj(name, bl_obj, dsize=50, dtype='CIRCLE')
        bl_stop.pd_obj.type = pdprops.PD_PROP_LIFT_STOP
        bl_stop.scale = Vector([1/sc for sc in bl_obj.scale])

        if self.index == 0:
            pd_lift.stop1 = bl_stop
        elif self.index == 1:
            pd_lift.stop2 = bl_stop
        elif self.index == 2:
            pd_lift.stop3 = bl_stop
        elif self.index == 3:
            pd_lift.stop4 = bl_stop

        return {'FINISHED'}


class PDTOOLS_OT_SetupLiftRemoveStop(Operator):
    bl_idname = "pdtools.op_setup_lift_remove_stop"
    bl_label = "PD: Remove Stop"
    bl_description = "Remove Lift Stop"
    bl_options = {'REGISTER', 'UNDO'}

    index: IntProperty(name='index', default=0, options={'LIBRARY_EDITABLE'})

    def execute(self, context):
        bl_obj = context.active_object
        pd_lift = bl_obj.pd_lift
        stops = [pd_lift.stop1, pd_lift.stop2, pd_lift.stop3, pd_lift.stop4]
        stop = stops[self.index]

        print(self.index, stop)

        bpy.data.objects.remove(stop, do_unlink=True)

        return {'FINISHED'}


class PDTOOLS_OT_SetupInterlinkCreate(Operator):
    bl_idname = "pdtools.op_setup_interlink_create"
    bl_label = "PD: Create Interlink Object"
    bl_description = "Create Interlink Object"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        bl_obj = context.active_object
        pd_lift = bl_obj.pd_lift
        pd_interlinks = pd_lift.interlinks

        interlink = pd_interlinks.add()
        interlink.name = f'{bl_obj.name} Interlink {len(pd_interlinks)}'
        interlink.controlled = bl_obj
        return {'FINISHED'}


class PDTOOLS_OT_SetupInterlinkRemove(Operator):
    bl_idname = "pdtools.op_setup_interlink_remove"
    bl_label = "PD: Remove Interlink Object"
    bl_description = "Remove Interlink Object"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        bl_obj = context.active_object
        pd_lift = bl_obj.pd_lift
        pd_interlinks = pd_lift.interlinks

        if len(pd_interlinks) == 0: return {'FINISHED'}

        pd_interlinks.remove(pd_lift.active_interlink_idx)

        return {'FINISHED'}


class PDTOOLS_OT_SetupDoorSelectSibling(Operator):
    bl_idname = "pdtools.door_select_sibling"
    bl_label = "Select Sibling"
    bl_options = {'REGISTER', 'INTERNAL'}

    def execute(self, context):
        bl_door = context.active_object
        bl_sibling = bl_door.pd_door.sibling
        bpy.ops.object.select_all(action='DESELECT')
        bpy.context.view_layer.objects.active = bl_sibling
        bl_sibling.select_set(True)
        return {'FINISHED'}

    def invoke(self, context, event):
        return self.execute(context)


class PDTOOLS_OT_SetupDoorPlaySound(Operator):
    bl_idname = "pdtools.door_play_sound"
    bl_label = ""

    open: BoolProperty(name='open', default=True, options={'LIBRARY_EDITABLE'})
    soundnum: StringProperty(name='soundnum', options={'LIBRARY_EDITABLE'})

    @classmethod
    def description(cls, context, _properties):
        close = hasattr(context, 'doorclose')
        return 'Play: Door Close' if close else 'Play: Door Open'

    def execute(self, _context):
        blend_dir = os.path.dirname(bpy.data.filepath) # TODO propertly get the sound dir
        device = aud.Device()
        device.stopAll()
        openclose = 'OPEN' if self.open else 'CLOSE'
        name = f'{self.soundnum}{openclose}'
        sound = aud.Sound(f'{blend_dir}/sounds/{name}.ogg')
        sound_buffered = aud.Sound.cache(sound)
        device.play(sound_buffered)
        return {'FINISHED'}


class PDTOOLS_OT_MessageBox(Operator):
    bl_idname = "pdtools.messagebox"
    bl_label = "Message Box"

    msg: StringProperty(default='')

    def execute(self, _context):
        self.report({'INFO'}, self.msg)
        # print(f'OP: {self.msg}')
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
    PDTOOLS_OT_RoomSplitByPortal,
    PDTOOLS_OT_RoomSelectAllBlocks,
    PDTOOLS_OT_TileApplyProps,
    PDTOOLS_OT_PortalFromEdge,
    PDTOOLS_OT_PortalFromFace,
    PDTOOLS_OT_TilesFromFaces,
    PDTOOLS_OT_TilesSelectSameRoom,
    PDTOOLS_OT_SetupLiftCreateStop,
    PDTOOLS_OT_SetupLiftRemoveStop,
    PDTOOLS_OT_SetupInterlinkCreate,
    PDTOOLS_OT_SetupInterlinkRemove,
    PDTOOLS_OT_SetupDoorSelectSibling,
    PDTOOLS_OT_SetupDoorPlaySound,
    PDTOOLS_OT_MessageBox,
]

# this callback is to detect when the selected tool changed, and update the drawing
# state of the PortalFromEdge tool
def factory_callback(func):
    def callback(*args, **kwargs):
        idname = args[2]
        if idname == PD_WSTOOL_PortalFromEdge.bl_idname:
            PD_WSTOOL_PortalFromEdge.setup_draw_handler()
            PD_WSTOOL_PortalFromEdge.update_geometry()
        else:
            PD_WSTOOL_PortalFromEdge.remove_draw_handler()

        return func(*args, **kwargs)
    return callback

space_toolsystem_common.activate_by_id = factory_callback(
    space_toolsystem_common.activate_by_id
)

def pd_editmode_menu(self, context):
    self.layout.separator(factor=1.0)
    self.layout.operator(PDTOOLS_OT_PortalFromFace.bl_idname)
    self.layout.operator(PDTOOLS_OT_TilesFromFaces.bl_idname)

def pd_editmode_ctxmenu(self, context):
    if bpy.context.tool_settings.mesh_select_mode[2]:
        self.layout.separator(factor=1.0)
        self.layout.operator(PDTOOLS_OT_PortalFromFace.bl_idname)
        self.layout.operator(PDTOOLS_OT_TilesFromFaces.bl_idname)

def remove_menu():
    bpy.types.VIEW3D_MT_edit_mesh_faces.remove(pd_editmode_menu)
    bpy.types.VIEW3D_MT_edit_mesh_context_menu.remove(pd_editmode_ctxmenu)

def register():
    for cl in classes:
        bpy.utils.register_class(cl)


    bpy.utils.register_tool(PD_WSTOOL_PortalFromEdge,
                            after={"builtin.scale_cage"}, separator=True, group=True)

    bpy.types.VIEW3D_MT_edit_mesh_faces.append(pd_editmode_menu)  # for top menu
    bpy.types.VIEW3D_MT_edit_mesh_context_menu.append(pd_editmode_ctxmenu)  # for context menu


def unregister():
    for cl in classes:
        bpy.utils.unregister_class(cl)

    bpy.utils.unregister_tool(PD_WSTOOL_PortalFromEdge)
    PD_WSTOOL_PortalFromEdge.remove_draw_handler()


if __name__ == '__main__':
    register()
