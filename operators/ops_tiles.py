import bpy
from bpy.props import IntProperty

from bpy.types import Operator
from mathutils import Vector
import bmesh

from utils import bg_utils as bgu
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
]

register, unregister = bpy.utils.register_classes_factory(classes)
