import bpy
from bpy.types import Operator
import bmesh

from utils import bg_utils as bgu
from pd_data.pd_padsfile import *
from pd_import import tiles_import as tlimp


class PDTOOLS_OT_TileApplyProps(Operator):
    bl_idname = "pdtools.tile_apply_props"
    bl_label = "Apply Tile Props"
    bl_description = "Apply props to selected tiles"

    def execute(self, context):
        prop = context.pd_tile
        for bl_tile in context.selected_objects:
            bl_tile.pd_tile.flags = prop.flags
            bl_tile.pd_tile.floorcol = prop.floorcol
            bl_tile.pd_tile.floortype = prop.floortype
            # bl_tile.pd_tile.room = prop.room
        n = tlimp.bg_colortiles(context)
        return {'FINISHED'}


class PDTOOLS_OT_TilesFromFaces(Operator):
    bl_idname = "pdtools.op_tiles_from_faces"
    bl_label = "PD: Tiles From Faces"
    bl_description = "Creates tiles from the selected faces"
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
    bl_description = "Select all tiles from the same room"
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

classes = [
    PDTOOLS_OT_TileApplyProps,
    PDTOOLS_OT_TilesFromFaces,
    PDTOOLS_OT_TilesSelectSameRoom,
]

register_cls, unregister_cls = bpy.utils.register_classes_factory(classes)

def register():
    register_cls()
