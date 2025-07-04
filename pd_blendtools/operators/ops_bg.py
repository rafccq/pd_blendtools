import bpy
from bpy.types import Operator, WorkSpaceTool
import bmesh
import gpu
from bpy.props import EnumProperty, FloatProperty
from bl_ui import space_toolsystem_common
from gpu_extras.batch import batch_for_shader

from utils import bg_utils as bgu
from pd_data.pd_padsfile import *
import pd_blendprops as pdprops


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


class PDTOOLS_OT_RoomCreatePortalBetween(Operator):
    bl_idname = "pdtools.room_create_portal_between"
    bl_label = "Create Portal"
    bl_description = "Create portal between rooms"

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


class PDTOOLS_OT_RoomSelectRoom(Operator):
    bl_idname = "pdtools.op_room_select_room"
    bl_label = "Select Room"
    bl_description = "Select Room"
    bl_options = {'REGISTER', 'INTERNAL'}

    def execute(self, context):
        bl_roomblock = context.active_object
        bl_room = bgu.parent_room(bl_roomblock)
        pdu.select_obj(bl_room)
        return {'FINISHED'}


BLOCKTYPES = [
    (e, e, e) for e in [pdprops.BLOCKTYPE_DL, pdprops.BLOCKTYPE_BSP]
]

class PDTOOLS_OT_RoomCreateBlock(Operator):
    bl_idname = "pdtools.op_room_create_block"
    bl_label = "Create Block"
    bl_description = "Create a new block in this room"
    bl_options = {'REGISTER', 'INTERNAL'}

    layer: EnumProperty(name="layer", description="Room Layer", items=pdprops.BLOCK_LAYER)
    blocktype: EnumProperty(name='blocktype', default=BLOCKTYPES[0][0], items=BLOCKTYPES, options={'LIBRARY_EDITABLE'})

    def invoke(self, context, event):
        bl_room = context.active_object

        if pdu.pdtype(bl_room) == pdprops.PD_OBJTYPE_ROOM:
            wm = context.window_manager
            return wm.invoke_props_dialog(self, width=150)

        return self.execute(context)

    def draw(self, context):
        bl_room = context.active_object

        if pdu.pdtype(bl_room) != pdprops.PD_OBJTYPE_ROOM:
            return

        layout = self.layout
        col = layout.column()
        col.prop(self, 'layer', text='Layer')
        col.prop(self, 'blocktype', text='Type')

    def execute(self, context):
        bl_room = context.active_object

        blocks = [b for b in bl_room.children]
        for block in blocks: blocks += [b for b in block.children]
        blocknum = 1 + max([block.pd_room.blocknum for block in blocks])

        pd_room = bl_room.pd_room
        roomnum = pd_room.roomnum
        layer = self.layer
        name = bgu.blockname(roomnum, blocknum, self.blocktype, layer)

        bl_roomblock = bpy.data.objects.new(name, None)
        bl_roomblock.parent = bl_room
        bl_roomblock.pd_room.parent_enum = bl_room.name

        pdu.add_to_collection(bl_roomblock, 'Rooms')
        bgu.roomblock_set_props(bl_roomblock, roomnum, pd_room.room, blocknum, layer, self.blocktype)

        pdu.select_obj(bl_roomblock)
        return {'FINISHED'}


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
    bl_description = "Creates a portal from the selected face"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        err = bgu.new_portal_from_faces(context)
        if err:
            pdu.msg_box('', err, 'ERROR')
        return {'FINISHED'}


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

classes = [
    PDTOOLS_OT_PortalFindRooms,
    PDTOOLS_OT_RoomCreatePortalBetween,
    PDTOOLS_OT_RoomSplitByPortal,
    PDTOOLS_OT_RoomSelectAllBlocks,
    PDTOOLS_OT_RoomSelectRoom,
    PDTOOLS_OT_RoomCreateBlock,
    PDTOOLS_OT_PortalFromEdge,
    PDTOOLS_OT_PortalFromFace,
]

register_cls, unregister_cls = bpy.utils.register_classes_factory(classes)

def register():
    register_cls()
    bpy.utils.register_tool(PD_WSTOOL_PortalFromEdge,
                            after={"builtin.scale_cage"}, separator=True, group=True)

def unregister():
    unregister_cls()

    bpy.utils.unregister_tool(PD_WSTOOL_PortalFromEdge)
    PD_WSTOOL_PortalFromEdge.remove_draw_handler()
