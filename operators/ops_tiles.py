import bpy
from bpy.props import IntProperty

from bpy.types import Operator
from mathutils import Vector
import bmesh
import gpu
import blf
from gpu_extras.batch import batch_for_shader
from bpy_extras.view3d_utils import location_3d_to_region_2d

from utils import (
    bg_utils as bgu,
    pd_utils as pdu,
)
from pd_data.pd_padsfile import *
from pd_import import tiles_import as tlimp
import pd_blendprops as pdprops

TILEPROP_ALL = pdprops.TILEPROP_ALL
TILEPROP_FLAGS = pdprops.TILEPROP_FLAGS
TILEPROP_FLOORCOL = pdprops.TILEPROP_FLOORCOL
TILEPROP_FLOORTYPE = pdprops.TILEPROP_FLOORTYPE
TILEPROP_ROOM = pdprops.TILEPROP_ROOM

class PDTOOLS_OT_TileApplyProps(Operator):
    bl_idname = "pdtools.tile_apply_props"
    bl_label = "Apply Tile Props"
    bl_description = "Apply props to selected tiles"

    prop: IntProperty(name='prop', default=0, options={'LIBRARY_EDITABLE'})

    @classmethod
    def description(cls, context, properties):
        propname = 'All'
        if properties.prop == TILEPROP_FLAGS: propname = 'Flags'
        elif properties.prop == TILEPROP_FLOORCOL: propname = 'Floor Color'
        elif properties.prop == TILEPROP_FLOORTYPE: propname = 'Floor Type'
        elif properties.prop == TILEPROP_ROOM: propname = 'Room'

        return f'Apply {propname} To Selection'

    def execute(self, context):
        pd_tile = context.pd_tile
        for bl_tile in context.selected_objects:
            if self.prop in [TILEPROP_ALL, TILEPROP_FLAGS]:
                bl_tile.pd_tile.flags = pd_tile.flags
            if self.prop in [TILEPROP_ALL, TILEPROP_FLOORCOL]:
                bl_tile.pd_tile.floorcol = pd_tile.floorcol
            if self.prop in [TILEPROP_ALL, TILEPROP_FLOORTYPE]:
                bl_tile.pd_tile.floortype = pd_tile.floortype
            if self.prop in [TILEPROP_ALL, TILEPROP_ROOM]:
                bl_tile.pd_tile.room = pd_tile.room

        tlimp.bg_colortiles(context)
        return {'FINISHED'}


class PDTOOLS_OT_TilesFromFaces(Operator):
    bl_idname = "pdtools.op_tiles_from_faces"
    bl_label = "PD: Tiles From Faces"
    bl_description = "Creates tiles from the selected faces"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        bl_obj = context.edit_object
        bm = bmesh.from_edit_mesh(bl_obj.data)
        bm.faces.ensure_lookup_table()

        faces_sel = [f for f in bm.faces if f.select]

        if not faces_sel:
            pdu.msg_box('', 'No Selection', 'ERROR')
            bm.free()
            return {'FINISHED'}

        layers = bm.loops.layers
        col_layer = layers.color['Col'] if 'Col' in layers.color else None

        lib = bpy.data.collections
        num = len(lib['Tiles'].objects) if 'Tiles' in lib else 0
        tiles = []
        for face in faces_sel:
            bl_tile = bgu.tile_from_face(f'Tile_{num}', bl_obj, face)
            if pdu.pdtype(bl_obj) == pdprops.PD_OBJTYPE_ROOMBLOCK:
                bl_tile.pd_tile.room = bl_obj.pd_room.room

            if col_layer:
                colors = [Vector(loop[col_layer][:]) for loop in face.loops]
                floor_col = sum(colors, Vector((0, 0, 0, 0))) / len(colors)
                bl_tile.pd_tile.floorcol = floor_col

            tiles.append(bl_tile)
            num += 1

        # switch to object mode and select all the newly created tiles
        bpy.ops.object.mode_set(mode="OBJECT")
        bpy.ops.object.select_all(action='DESELECT')
        for tile in tiles: tile.select_set(True)
        pdu.set_active_obj(tiles[0])
        tlimp.bg_colortiles(context)
        return {'FINISHED'}


shader_tiles = gpu.shader.from_builtin('SMOOTH_COLOR')


def line(verts, colors, v0, v1, col):
    verts += [v0, v1]
    colors += [col, col]

def get_tile_flags_preset(normal):
    eps = 0.05
    if pdu.fcomp(normal.z, 0, eps):
        return 'Wall'
    if pdu.fcomp(normal.z, 1, eps):
        return 'Ground'

    return ''

_keys = list(pdprops.TILE_FLAGS_PRESETS_MAP.keys())
FLAGS_PRESETS = [_keys[i] for i in range(len(_keys) - 1)]

class PDTOOLS_OT_TileCreateMode(Operator):
    bl_idname = "pdtools.op_tile_create_mode"
    bl_label = "PD: Create Tile"
    bl_description = "Create Tiles From Mesh (Edit Mode)"
    bl_options = {'REGISTER', 'UNDO'}


    merge = False
    pos_text = None
    edge_idx = 1
    tiletype = ''
    tileflags_preset = ''
    floortype_idx = 1
    tiletype_auto = True
    verts = []
    floorcols = []
    flag_preset_idx = 0

    def get_extremes(self, verts, dir):
        min = max = 0
        for i, v in enumerate(verts):
            dot = v.dot(dir)
            if dot < verts[min].dot(dir): min = i
            if dot > verts[max].dot(dir): max = i

        return verts[min], verts[max]

    def selected_faces(self, bm):
        sel_faces = []
        for f in bm.faces:
            if not f.select: continue
            sel_faces.append(f)

        return sel_faces

    def make_tiles(self, context):
        if not self.verts: return

        scn = context.scene
        bl_obj = context.active_object

        has_vtxcolors = len(self.floorcols) > 0
        n = len(self.verts) // 4
        for i in range(n):
            verts = [self.verts[i*4 + idx] for idx in range(4)]
            tile = bgu.obj_from_verts('Tile', verts, pdprops.PD_OBJTYPE_TILE, 'Tiles')

            # setup tile props
            pd_tile = tile.pd_tile
            if pdu.pdtype(bl_obj) == pdprops.PD_OBJTYPE_ROOMBLOCK:
                pd_tile.room = bl_obj.pd_room.room

            pd_tile.floortype = pdprops.ENUM_SURFACE_TYPES[self.floortype_idx][0].lower()
            if self.tileflags_preset:
                pdprops.tile_apply_flags_preset(pd_tile, self.tileflags_preset)

            if self.tiletype_auto:
                preset = get_tile_flags_preset(self.selected_face)
            else:
                preset = FLAGS_PRESETS[self.flag_preset_idx].title()

            pd_tile.floorcol = self.floorcols[i] if has_vtxcolors else (1, 1, 1, 1)

            if preset:
                pdprops.tile_apply_flags_preset(pd_tile, preset.lower())


    def deselect_faces(self, context):
        obj = context.active_object
        bm = bmesh.from_edit_mesh(obj.data)
        bm.faces.ensure_lookup_table()
        for f in bm.faces: f.select = False
        bmesh.update_edit_mesh(obj.data)

    def make_tiledata(self, bm, face, M, verts=None):
        if not verts: verts = [v.co for v in face.verts]

        col_cy = (0.0, 1.0, 1.0)
        col_yel = (1.0, 1.0, 0.0)

        line_verts, colors = [], []

        #### basis 0 ####
        e_idx = self.edge_idx % len(face.edges)
        self.edge_idx = e_idx

        e = face.edges[e_idx]
        e0 = (e.verts[1].co - e.verts[0].co).normalized()

        idx = 1 if e_idx == 0 else 0

        #### basis 1 ####
        e1 = -e0.cross(face.normal).normalized()

        #### bounds 1 ####
        min0, max0 = self.get_extremes(verts, e0)
        dim0 = (max0 - min0).length
        dim0 = (max0 - min0).dot(e0)

        min1, max1 = self.get_extremes(verts, e1)
        dim1 = (max1 - min1).length
        dim1 = (max1 - min1).dot(e1)

        n = face.normal
        min2, _ = self.get_extremes(verts, n)
        t0 = min0.dot(e0) * e0 + min1.dot(e1) * e1 + min2.dot(n) * n
        t1 = t0 + dim0 * e0

        t2 = t1 + dim1 * e1
        t3 = t2 - dim0 * e0

        # tile lines
        line(line_verts, colors, t0, t1, col_yel)
        line(line_verts, colors, t1, t2, col_yel)
        line(line_verts, colors, t2, t3, col_yel)
        line(line_verts, colors, t3, t0, col_yel)

        # save vertices world coords to create the tiles later
        for v in [t0, t1, t2, t3]:
            self.verts.append(M @ v)

        # add vertex colors from the face
        layers = bm.loops.layers
        col_layer = layers.color['Col'] if 'Col' in layers.color else None

        if col_layer:
            vtx_colors = [Vector(loop[col_layer][:]) for loop in face.loops]
            floorcol = sum(vtx_colors, Vector((0, 0, 0, 0))) / len(vtx_colors)
            self.floorcols.append(floorcol)

        # draw base edge
        line(line_verts, colors, e.verts[0].co, e.verts[1].co, col_cy)

        ############ convert to world_coords ##########
        for i, c in enumerate(line_verts):
            line_verts[i] = M @ c

        return line_verts, colors

    def draw_callback(self, context):
        try:
            bl_obj = context.active_object
            if bl_obj.mode != 'EDIT': return

            self.pos_text = None

            bm = bmesh.from_edit_mesh(bl_obj.data)
            bm.faces.ensure_lookup_table()

            self.selected_face = None
            faces = self.selected_faces(bm)

            if not faces: return

            face = faces[0]
            self.selected_face = face.normal

            M = bl_obj.matrix_world
            line_verts, colors = [], []

            self.verts = []
            self.floorcols = []

            if self.merge:
                verts = [v.co for f in bm.faces if f.select for v in f.verts]
                line_verts, colors = self.make_tiledata(bm, face, M, verts)
            else:
                for face in faces:
                    verts, cols = self.make_tiledata(bm, face, M)
                    for v, c in zip(verts, cols):
                        line_verts.append(v)
                        colors.append(c)

            gpu.state.line_width_set(1.5)
            batch = batch_for_shader(shader_tiles, 'LINES', {"pos": line_verts, 'color': colors})

            shader_tiles.bind()
            batch.draw(shader_tiles)

            # get position of text in 3d space
            region, rv3d = pdu.get_region(context, 'VIEW_3D', 'WINDOW')
            if rv3d:
                # first 8 verts define the first face, we use its mid point for the 3d text
                tmpverts = [line_verts[i] for i in range(8)]
                mid = sum(tmpverts, Vector()) / len(tmpverts)
                self.pos_text = location_3d_to_region_2d(region, rv3d, mid)
        except Exception:
            print(traceback.format_exc())

    def draw_text(self, text, pos, size, col):
        blf.position(0, pos[0], pos[1], 0)
        blf.size(0, size)
        blf.color(0, col[0], col[1], col[2], 1)
        blf.draw(0, text)

    def text_draw_lines(self, lines, pos, size, col, dy):
        y = pos.y
        for text in lines:
            self.draw_text(text, (pos.x, y), size, col)
            y -= dy

    def draw_callback_text(self, context):
        if context.active_object.mode != 'EDIT': return

        x = 60 if pdu.region_visible(context, 'TOOLS') else 10
        y = 230

        lines = ['Create Tile:']
        lines += ['Auto Flags: ' + ('on' if self.tiletype_auto else 'off') + ' (H)']
        flag_preset = FLAGS_PRESETS[self.flag_preset_idx].title()
        text_flag_preset = 'Flags: ' + ('Auto' if self.tiletype_auto else flag_preset)
        if not self.tiletype_auto:
            text_flag_preset += ' (y/u)'
        lines += [text_flag_preset]
        lines += ['Merge: ' + ('on' if self.merge else 'off') + ' (M)']
        floortype = pdprops.ENUM_SURFACE_TYPES[self.floortype_idx][0]
        lines += ['Floor Type: ' + pdprops.ENUM_SURFACE_TYPES[self.floortype_idx][0] + ' (o/p)']
        lines += ['Base Edge: ' + str(self.edge_idx) + ' (j/k)']

        pos = Vector((x, y))
        self.text_draw_lines(lines, pos, 18, (1, 1, 1), 30)

        pos = self.pos_text
        if not pos: return

        #### "3D" Text
        if not self.selected_face: return

        if self.tiletype_auto:
            flag_preset = get_tile_flags_preset(self.selected_face)

        dx, _ = blf.dimensions(0, flag_preset)
        pos.x -= dx
        x, y = pos
        size = 20
        c = 0.8
        col = (c, c, c)
        self.draw_text(flag_preset, (x, y), size, col)

        # show floortype for ground tiles
        if 'ground' in flag_preset.lower():
            pos.y -= 30
            self.draw_text(floortype, pos, size, col)

    def finish(self):
        # remove handlers
        bpy.types.SpaceView3D.draw_handler_remove(self._draw_handler, 'WINDOW')
        bpy.types.SpaceView3D.draw_handler_remove(self._draw_handler_text, 'WINDOW')

    def modal(self, context, event):
        context.area.tag_redraw()

        if context.active_object.mode != 'EDIT':
            self.finish()
            return {'CANCELLED'}

        if event.type in {'RIGHTMOUSE'}:
            self.finish()
            return {'CANCELLED'}

        if event.type == 'M' and event.value == 'PRESS':
            self.merge = not self.merge
            return {'RUNNING_MODAL'}

        if event.type == 'RET' and event.value == 'PRESS':
            self.make_tiles(context)
            self.deselect_faces(context)
            return {'RUNNING_MODAL'}

        if event.type == 'J' and event.value == 'PRESS':
            self.edge_idx += 1
            return {'RUNNING_MODAL'}

        if event.type == 'K' and event.value == 'PRESS':
            self.edge_idx -= 1
            return {'RUNNING_MODAL'}

        if event.type == 'H' and event.value == 'PRESS':
            self.tiletype_auto = not self.tiletype_auto
            return {'RUNNING_MODAL'}

        if event.type in ['O', 'P'] and event.value == 'PRESS':
            n = len(pdprops.ENUM_SURFACE_TYPES)
            delta = -1 if event.type == 'O' else 1
            self.floortype_idx = (self.floortype_idx - 1 + delta) % (n - 1) + 1
            return {'RUNNING_MODAL'}

        if event.type in ['Y', 'U'] and event.value == 'PRESS':
            n = len(FLAGS_PRESETS)
            delta = -1 if event.type == 'Y' else 1
            self.flag_preset_idx = (self.flag_preset_idx + delta) % n
            return {'RUNNING_MODAL'}

        return {'PASS_THROUGH'}

    def invoke(self, context, event):
        if context.area.type == 'VIEW_3D':
            args = (context,)
            self._draw_handler = bpy.types.SpaceView3D.draw_handler_add(
                self.draw_callback, args, 'WINDOW', 'POST_VIEW')

            self._draw_handler_text = bpy.types.SpaceView3D.draw_handler_add(
                self.draw_callback_text, args, 'WINDOW', 'POST_PIXEL')

            context.window_manager.modal_handler_add(self)
            return {'RUNNING_MODAL'}
        return {'CANCELLED'}


class PDTOOLS_OT_TilesSelectSameRoom(Operator):
    bl_idname = "pdtools.op_tiles_select_room"
    bl_label = "PD: Select All From Room"
    bl_description = "Select all tiles from the same room"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        bl_obj = context.active_object
        pd_tile = bl_obj.pd_tile

        bpy.ops.object.select_all(action='DESELECT')
        tiles = pdu.all_objects_in_collection('Tiles')
        for bl_tile2 in tiles:
            pd_tile2 = bl_tile2.pd_tile
            if pd_tile2.room == pd_tile.room:
                bl_tile2.select_set(True)

        return {'FINISHED'}

classes = [
    PDTOOLS_OT_TileApplyProps,
    PDTOOLS_OT_TilesFromFaces,
    PDTOOLS_OT_TilesSelectSameRoom,
    PDTOOLS_OT_TileCreateMode,
]

register, unregister = bpy.utils.register_classes_factory(classes)
