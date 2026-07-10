import bpy
from bpy.types import Operator, WorkSpaceTool
import bmesh
import gpu
from bl_ui import space_toolsystem_common
from gpu_extras.batch import batch_for_shader
from bpy_extras import view3d_utils
from mathutils import Vector
from bpy.props import IntProperty, StringProperty, BoolProperty, EnumProperty, FloatProperty

from utils import bg_utils as bgu
from pd_data.pd_padsfile import *
import pd_blendprops as pdprops
import materials.pd_materials as pdm


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

class PDTOOLS_OT_RoomCreateFromObject(Operator):
    bl_idname = "pdtools.room_create_from_obj"
    bl_label = "Create From Object"
    # bl_options = {'REGISTER', 'INTERNAL'}

    @classmethod
    def poll(cls, ctx):
        ctx_obj = ctx.object
        obj = ctx.active_object

        if not ctx_obj or not obj:
            return

        objtype = pdu.pdtype(obj)
        typeok = objtype not in [pdprops.PD_OBJTYPE_ROOM, pdprops.PD_OBJTYPE_ROOMBLOCK]
        return ctx_obj.type == 'MESH' and typeok

    def room_from_obj(self, bl_obj, layer='opa'):
        scn = bpy.context.scene
        if 'rooms' not in scn:
            scn['rooms'] = {}

        pos = bl_obj.matrix_world.translation
        roomnum = bgu.room_nextnum()
        bl_room = bgu.new_room(roomnum, pos)

        # remove the object from the collection it is currently in
        for collection in bl_obj.users_collection:
            collection.objects.unlink(bl_obj)

        bgu.set_mesh_attrs(bl_obj.data)

        pdu.add_to_collection(bl_obj, 'Rooms')

        bl_obj.parent = bl_room
        bl_obj.location = (0, 0, 0)
        bl_obj.name = bgu.blockname(roomnum, 0, pdprops.BLOCKTYPE_DL, layer)
        bgu.roomblock_set_props(bl_obj, bl_room, roomnum, bl_room, 0, layer, pdprops.BLOCKTYPE_DL)
        pdm.mat_convert_all_in(bl_obj)

    def execute(self, context):
        bl_obj = context.active_object
        self.room_from_obj(bl_obj)
        return {'FINISHED'}


ENUM_LAYERS = [
    ('opa', 'Primary (opaque)', 'Primary (opaque)'),
    ('xlu', 'Secondary (translucent)', 'Secondary (translucent)')
]

class PDTOOLS_OT_RoomBlockCreateFromSelection(Operator):
    bl_idname = "pdtools.roomblock_create_from_selection"
    bl_label = "PD: Roomblock From Faces"
    bl_description = "Move selected faces to a new roomblock"
    bl_options = {'REGISTER'}

    layer: bpy.props.EnumProperty(name='layer', default=ENUM_LAYERS[0][0], items=ENUM_LAYERS)

    @classmethod
    def poll(cls, ctx):
        if ctx.object.mode != 'EDIT' or not ctx.tool_settings.mesh_select_mode[2]:
            return False

        return pdu.pdtype(ctx.active_object) == pdprops.PD_OBJTYPE_ROOMBLOCK

    def separate_selection(self):
        selected = {obj.name for obj in bpy.context.selected_objects}

        bpy.ops.mesh.separate(type='SELECTED')

        newobj = None
        for obj in bpy.context.selected_objects:
            if obj and obj.name not in selected:
                newobj = obj

        return newobj

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=200)

    def execute(self, ctx):
        bl_obj = ctx.active_object
        pd_room = bl_obj.pd_room
        bl_room = pd_room.room

        blocknum = bgu.room_next_blocknum(bl_room)
        roomnum = pd_room.roomnum

        layer = self.layer
        lastblock = bgu.room_last_block(bl_room, layer)
        blocktype = pdprops.BLOCKTYPE_DL
        bl_parent = lastblock.parent if lastblock else bl_obj.parent

        bl_newblock = self.separate_selection()

        bl_newblock.name = bgu.blockname(roomnum, blocknum, blocktype, layer)
        bgu.roomblock_set_props(bl_newblock, bl_parent, roomnum, pd_room.room, blocknum, layer, blocktype)

        if lastblock:
            lastblock.pd_room.next = bl_newblock
        elif layer == 'xlu':
            pd_room.first_xlu = bl_newblock
        return {'FINISHED'}

    def draw(self, context):
        scn = context.scene
        layout = self.layout

        layout.prop(self, 'layer', text='Layer')


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

    layer: bpy.props.EnumProperty(name="layer", description="Room Layer", items=pdprops.ENUM_BLOCK_LAYERS)
    blocktype: bpy.props.EnumProperty(name='blocktype', default=BLOCKTYPES[0][0], items=BLOCKTYPES)
    blocklinking: bpy.props.StringProperty(name='blocklinking') # sibling/child

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=150)

    def draw(self, context):
        bl_room = context.object

        layout = self.layout
        col = layout.column()
        col.prop(self, 'layer', text='Layer')
        col.enabled = pdu.pdtype(bl_room) == pdprops.PD_OBJTYPE_ROOM
        col = layout.column()
        col.prop(self, 'blocktype', text='Type')

    def execute(self, context):
        bl_obj = context.object
        is_room = pdu.pdtype(bl_obj) == pdprops.PD_OBJTYPE_ROOM
        bl_room = bgu.parent_room(bl_obj) if not is_room else bl_obj
        bl_lastblock = None
        if is_room or self.blocklinking == 'child':
            # the root is the selected object itself
            bl_root = bl_obj
            bl_lastblock = bgu.room_last_block(bl_root, self.layer)
        else:
            bl_root = bl_obj.parent

        # create the block
        nextsaved = bl_obj.pd_room.next
        bl_newblock = bgu.room_create_block(bl_room, bl_root, self.layer, self.blocktype)

        if self.blocklinking.lower() == 'sibling':
            bl_obj.pd_room.next = bl_newblock
            bl_newblock.pd_room.next = nextsaved
        else:
            if bl_lastblock:
                bl_lastblock.pd_room.next = bl_newblock
            elif is_room and self.layer == pdprops.BLOCK_LAYER_XLU:
                # we only need to handle xlu, because rooms will always have opa blocks
                bl_room.pd_room.first_xlu = bl_newblock

        pdu.select_obj(bl_newblock)

        return {'FINISHED'}


class PDTOOLS_OT_RoomBlockDelete(Operator):
    bl_idname = "pdtools.op_room_block_delete"
    bl_label = "Delete Block"
    bl_description = "Delete the block and its children"
    bl_options = {'REGISTER', 'INTERNAL'}

    def draw(self, context):
        bl_room = context.active_object

        layout = self.layout
        layout.label(text='Are you sure?', icon='ERROR')

    def invoke(self, context, event):
        wm = context.window_manager
        return wm.invoke_props_dialog(self, title='This block and its children will be deleted', cancel_default=True)

    def execute(self, context):
        bl_roomblock = context.active_object

        bl_prevblock = bgu.room_prev_block(bl_roomblock)

        if bl_prevblock:
            bl_prevblock.pd_room.next = bl_roomblock.pd_room.next

        room = bl_roomblock.pd_room.room
        if room.pd_room.first_xlu == bl_roomblock:
            room.pd_room.first_xlu = bl_roomblock.pd_room.next

        parent = bl_roomblock.parent.pd_room
        if parent.child == bl_roomblock:
            parent.child = bl_roomblock.pd_room.next

        bpy.data.objects.remove(bl_roomblock)

        return {'FINISHED'}


ENUM_ROOMPOS = [
    ('Origin', 'Origin', 'Origin'),
    ('3D Cursor', '3D Cursor', '3D Cursor'),
    ('Custom', 'Custom', 'Custom'),
]
class PDTOOLS_OT_RoomCreate(Operator):
    bl_idname = "pdtools.op_room_create"
    bl_label = "Create Room"
    bl_description = "Create a new room"
    bl_options = {'REGISTER', 'INTERNAL'}

    pos: bpy.props.FloatVectorProperty(name='bsp_pos', default=(0,0,0), subtype='XYZ')
    pos_src: bpy.props.EnumProperty(name="Position", items=ENUM_ROOMPOS, default=ENUM_ROOMPOS[0][0], description='Position')

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=160)

    def draw(self, context):
        layout = self.layout
        col = layout.column().split(factor=0.4)
        col.label(text='Position:')
        col.prop(self, 'pos_src', text='')

        col = layout.column()
        if self.pos_src == 'Custom':
            col.prop(self, 'pos', text='')

    def get_pos(self, context):
        if self.pos_src == 'Custom':
            return self.pos
        elif self.pos_src == '3D Cursor':
            return context.scene.cursor.location

        return (0, 0, 0)

    def execute(self, context):
        roomnum = bgu.get_numrooms() + 1
        pos = self.get_pos(context)
        bl_room = bgu.new_room(roomnum, pos)
        pdu.select_obj(bl_room)
        return {'FINISHED'}


class PDTOOLS_OT_PortalFromEdgeEditMode(Operator):
    bl_idname = "pdtools.op_portal_from_edge_editmode"
    bl_label = "Portal From Edge"

    def ws_update_geometry(_self, _ctx):
        PD_WSTOOL_PortalFromEdge.update_geometry()

    direction: EnumProperty(
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
                         description='Rotation Around The Edge Axis',
                         update=ws_update_geometry)

    width: FloatProperty(name='width', default=10, min=1, max=10000,
                         update=ws_update_geometry)

    use_edge_width: BoolProperty(name='use_edge_width', default=True)
    edge_width: FloatProperty(name='edge_width')

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

        w = props.edge_width if props.use_edge_width else props.width
        h = props.height
        elv, pitch = props.elevation, props.pitch
        direction = props.direction

        edge = edges_sel[0]

        M = bl_obj.matrix_world
        verts = bgu.portal_verts_from_edge(edge, M, w, h, elv, pitch, direction)
        bgu.new_portal_from_verts(verts, bl_obj)
        edge.select = False

        return {'FINISHED'}

    def invoke(self, context, event):
        return self.execute(context)


def draw_prop(layout, props, name, label = None, enabled = True):
    row = layout.row()

    if not label:
        label = name.title()

    row.label(text=f'{label}:')
    row.prop(props, name.lower(), text='')
    row.enabled = enabled

class PD_WSTOOL_PortalFromEdge(WorkSpaceTool):
    bl_space_type = 'VIEW_3D'
    bl_context_mode = 'EDIT_MESH'
    bl_idname = "pdtools.ws_new_portal_from_edge"
    bl_label = "Portal From Edge"
    bl_description = "Creates a new portal from the selected edge"
    bl_icon = "ops.sculpt.border_mask"
    bl_widget = None

    _batch = None
    _draw_handle = None
    _shader = None

    @staticmethod
    def draw_settings(context, layout, tool, extra=False):
        props = tool.operator_properties(PDTOOLS_OT_PortalFromEdgeEditMode.bl_idname)

        if extra:
            col = layout.column()
            row = col.row()
            draw_prop(row, props, 'Direction')
            row = col.row()
            draw_prop(row, props, 'Elevation')
            row = col.row()
            draw_prop(row, props, 'Pitch')
            return

        draw_prop(layout, props, 'use_edge_width', label = 'Use Edge Width')
        draw_prop(layout, props, 'width', not props.use_edge_width)
        draw_prop(layout, props, 'height')

        # this will call this very function, with the parameter extra = True
        layout.popover("TOPBAR_PT_tool_settings_extra", text="...")
        layout.operator("pdtools.op_portal_from_edge_editmode", text='Create Portal')

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

            props = tool.operator_properties(PDTOOLS_OT_PortalFromEdgeEditMode.bl_idname)
            w, h = props.width, props.height

            elv, pitch = props.elevation, props.pitch
            direction = props.direction

            edge = edges_sel[0]
            if props.use_edge_width:
                w = props.edge_width = edge.calc_length()

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
    bl_idname = "pdtools.op_portals_from_faces"
    bl_label = "PD: Portals From Faces"
    bl_description = "Creates portals from the selected faces"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        # err = bgu.new_portal_from_faces(context)
        # if err:
        #     pdu.msg_box('', err, 'ERROR')
        bl_obj = context.edit_object
        bm = bmesh.from_edit_mesh(bl_obj.data)
        faces_sel = [f for f in bm.faces if f.select]

        if not faces_sel:
            pdu.msg_box('', 'No Selection', 'ERROR')
            bm.free()
            return {'FINISHED'}

        lib = bpy.data.collections
        num = len(lib['Portals'].objects) if 'Portals' in lib else 0
        portals = []
        for face in faces_sel:
            bl_portal = bgu.portal_from_face(f'portal_{num}', bl_obj, face)
            if pdu.pdtype(bl_obj) == pdprops.PD_OBJTYPE_ROOMBLOCK:
                bl_portal.pd_portal.room1 = bl_obj

            portals.append(bl_portal)
            num += 1

        # switch to object mode and select all the newly created portals
        bpy.ops.object.mode_set(mode="OBJECT")
        bpy.ops.object.select_all(action='DESELECT')
        for tile in portals: tile.select_set(True)
        pdu.set_active_obj(portals[0])
        bm.free()
        return {'FINISHED'}


shader_portal = gpu.shader.from_builtin('UNIFORM_COLOR')

class PDTOOLS_OT_PortalFromEdge(Operator):
    bl_idname = "pdtools.op_portal_from_edge"
    bl_label = "PD: Create Portal From Edge"
    bl_description = "Creates portal from the edge under the mouse cursor"
    bl_options = {'REGISTER', 'UNDO'}

    status_text = 'Left Click: Create Portal | Right Click/ESC: Cancel | Mouse Wheel: Change Height | Alt: Bigger Step Size'

    _current_edge = None
    _last_object = None

    vtx0 = None
    vtx1 = None
    height_auto = None
    height_manual = 1
    steps_v = 1
    altdown = False

    v0 = None
    v1 = None
    v2 = None
    v3 = None

    def update_edgedata(self, context, event):
        edge_data = self.get_edge_under_mouse(context, event)

        if edge_data:
            # check if the user hovered over a different edge/object
            if (self._current_edge != edge_data['edge_index'] or
                    self._last_object != edge_data['object']):
                self._current_edge = edge_data['edge_index']
                self._last_object = edge_data['object']
        else:
            if self._current_edge is not None:
                self._current_edge = None
                self._last_object = None

    def create_portal(self):
        b0 = self.vtx0
        b1 = self.vtx1

        if not b0 or not b1: return

        h = self.height_auto if self.height_auto else self.height_manual
        u0 = b1 + Vector((0, 0, h))
        u1 = b0 + Vector((0, 0, h))

        bgu.new_portal_from_verts([b0, b1, u0, u1])

    def finish(self, context):
        bpy.types.SpaceView3D.draw_handler_remove(self._draw_handler, 'WINDOW')
        context.area.tag_redraw()

    def modal(self, context, event):
        context.area.tag_redraw()

        if event.type == 'MOUSEMOVE':
            self.update_edgedata(context, event)

        if event.type in {'RIGHTMOUSE', 'ESC'}:
            self.finish(context)
            return {'CANCELLED'}

        if event.type == 'LEFTMOUSE' and event.value == 'PRESS':
            self.create_portal()
            self.finish(context)
            return {'FINISHED'}

        if event.type == 'LEFT_ALT' and event.value == 'PRESS':
            self.altdown = True
        if event.type == 'LEFT_ALT' and event.value == 'RELEASE':
            self.altdown = False

        if event.type in ['WHEELUPMOUSE', 'WHEELDOWNMOUSE']:
            s = 10 if event.type == 'WHEELUPMOUSE' else -10
            f = 3 if self.altdown else 1
            self.height_manual += f*s/10
            self.steps_v += s
            self.steps_v = max(1, self.steps_v)
            self.update_edgedata(context, event)

        return {'RUNNING_MODAL'}

    def get_extremity(self, edge, vtx, stop_at_perp=True):
        if stop_at_perp and self.get_edge_perpendicular(vtx): return vtx

        prev_edge = edge
        next_edge = None
        last_vtx = vtx

        v0 = (edge.verts[1].co - edge.verts[0].co).normalized()

        queue = [vtx]
        nstep = 1
        while queue:
            v = queue.pop()
            next_edge = None
            for e in v.link_edges:
                if e == prev_edge: continue

                v1 = (e.verts[1].co - e.verts[0].co).normalized()
                dot = v0.dot(v1)

                if pdu.fcomp(abs(dot), 1.0):
                    prev_edge = e
                    next_edge = e
                    break

            if next_edge:
                last_vtx = next_edge.other_vert(v)
                perp = self.get_edge_perpendicular(v)
                if perp:
                    if stop_at_perp: return v
                    elif self.steps_v > 0 and nstep >= self.steps_v:
                        return v
                queue.append(last_vtx)
            nstep += 1

        return last_vtx

    # tries to find a perpendicular edge aligned with the Z axis, from this vtx
    def get_edge_perpendicular(self, vtx):
        up = Vector((0, 0, 1))
        for e in vtx.link_edges:
            v_other = e.other_vert(vtx)
            v = (v_other.co - vtx.co).normalized()
            dot = v.dot(up)
            if pdu.fcomp(dot, 1.0):
                return e

        return None

    def get_edge_under_mouse(self, context, event, max_distance=10):
        """Get edge under mouse cursor"""

        region = context.region
        region_3d = context.space_data.region_3d
        coord = (event.mouse_region_x, event.mouse_region_y)

        view_vector = view3d_utils.region_2d_to_vector_3d(region, region_3d, coord)
        ray_origin = view3d_utils.region_2d_to_origin_3d(region, region_3d, coord)

        # raycast to get the obj, face_index etc under the mouse
        result, location, normal, face_index, obj, matrix = context.scene.ray_cast(
            context.view_layer.depsgraph,
            ray_origin,
            view_vector
        )

        if not result or obj.type != 'MESH':
            return None

        bm = bmesh.new()
        bm.from_mesh(obj.data)
        bm.transform(obj.matrix_world)
        bm.faces.ensure_lookup_table()

        if face_index >= len(bm.faces):
            bm.free()
            return None

        face = bm.faces[face_index]

        closest_edge = None
        closest_distance = float('inf')

        # search for the closest edge
        for edge in face.edges:
            v1_2d = view3d_utils.location_3d_to_region_2d(region, region_3d, edge.verts[0].co)
            v2_2d = view3d_utils.location_3d_to_region_2d(region, region_3d, edge.verts[1].co)

            if v1_2d is None or v2_2d is None:
                continue

            mouse_vec = Vector(coord)
            edge_vec = v2_2d - v1_2d
            edge_length = edge_vec.length

            if edge_length < 0.001:
                continue

            edge_dir = edge_vec / edge_length
            t = (mouse_vec - v1_2d).dot(edge_dir)
            t = max(0, min(edge_length, t))

            closest_point = v1_2d + edge_dir * t
            distance = (mouse_vec - closest_point).length

            if distance < closest_distance:
                closest_distance = distance
                closest_edge = edge

        edge_idx = closest_edge.index if closest_edge else -1
        if closest_edge and closest_distance <= max_distance:
            h0 = self.get_extremity(closest_edge, closest_edge.verts[0])
            h1 = self.get_extremity(closest_edge, closest_edge.verts[1])

            p0 = self.get_edge_perpendicular(h0)
            p1 = self.get_edge_perpendicular(h1)
            self.height_auto = None
            if p0 or p1:
                perp = p0 if p0 else p1
                v0 = self.get_extremity(perp, perp.verts[0], False)
                self.height_auto = abs(v0.co.z - h0.co.z)

            self.vtx0 = h0.co.copy()
            self.vtx1 = h1.co.copy()

        bm.free()

        if closest_distance <= max_distance:
            return { 'edge_index': edge_idx, 'object': obj }

        return None

    def invoke(self, context, event):
        # add draw handler
        if context.area.type == 'VIEW_3D':
            self._draw_handler = bpy.types.SpaceView3D.draw_handler_add(
                self.draw_callback, (context,), 'WINDOW', 'POST_VIEW')

            context.window_manager.modal_handler_add(self)
            return {'RUNNING_MODAL'}
        return {'CANCELLED'}

    def draw_callback(self, context):
        context.workspace.status_text_set(text=self.status_text)
        b0 = self.vtx0
        b1 = self.vtx1

        if not b0 or not b1: return

        h = self.height_auto if self.height_auto else self.height_manual
        u0 = b1 + Vector((0, 0, h))
        u1 = b0 + Vector((0, 0, h))

        coords = [b0, b1, b1, u0, u0, u1, b0, u1]
        batch = batch_for_shader(shader_portal, 'LINES', {"pos": coords})
        shader_portal.uniform_float("color", (0.0, 1.0, 1.0, 1.0))
        batch.draw(shader_portal)


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
    PDTOOLS_OT_RoomBlockDelete,
    PDTOOLS_OT_RoomSelectRoom,
    PDTOOLS_OT_RoomCreateBlock,
    PDTOOLS_OT_RoomCreate,
    PDTOOLS_OT_RoomCreateFromObject,
    PDTOOLS_OT_RoomBlockCreateFromSelection,
    PDTOOLS_OT_PortalFromEdgeEditMode,
    PDTOOLS_OT_PortalFromFace,
    PDTOOLS_OT_PortalFromEdge,
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
