import bpy

from utils import (
    pd_utils as pdu,
    bg_utils as bgu
)
from data.bytestream import ByteStream
from data.typeinfo import TypeInfo
from pd_data.pd_bgtiles import GEOTYPE_TILE_I
from pd_data.decl_bgtiles import decl_geotilei
from data.datablock import DataBlock
import pd_mtx as mtx
import pd_blendprops as pdprops


def get_numrooms():
    coll = bpy.data.collections['Rooms']
    rooms = list(filter(lambda r: r.pd_obj.type == pdprops.PD_OBJTYPE_ROOM, coll.objects))
    return len(rooms)

def colRGBA_to_444(col):
    r = int(col[0]*15)
    g = int(col[1]*15)
    b = int(col[2]*15)
    return (r << 8) | (g << 4) | b

def tile_bbox(verts):
    xmin = ymin = zmin = xmax = ymax = zmax = 0
    for idx, v in enumerate(verts):
        if v.x < verts[xmin].x: xmin = idx
        if v.y < verts[ymin].y: ymin = idx
        if v.z < verts[zmin].z: zmin = idx
        if v.x > verts[xmax].x: xmax = idx
        if v.y > verts[ymax].y: ymax = idx
        if v.z > verts[zmax].z: zmax = idx

    return xmin, ymin, zmin, xmax, ymax, zmax

def export_tile(bl_tile, R_inv, floortypes):
    pd_tile = bl_tile.pd_tile
    tileverts = bl_tile.data.vertices
    numvtx = len(tileverts)

    TypeInfo.register('geotilei', decl_geotilei, False, varmap={'N': numvtx})

    tile = DataBlock.New('geotilei')
    tileheader = tile['header']
    tileheader['type'] = GEOTYPE_TILE_I
    tileheader['numvertices'] = numvtx
    tileheader['flags'] = pdu.flags_pack(pd_tile.flags, pdprops.TILE_FLAGS_VALUES)

    tile['floortype'] = floortypes[pd_tile.floortype]

    verts = bgu.verts_world(bl_tile, R_inv, round)

    conv = lambda e: (round(e.x), round(e.y), round(e.z))
    tv = tile['vertices']
    vidx = 0
    for v in verts:
        tv[vidx + 0], tv[vidx + 1], tv[vidx + 2] = conv(v)
        vidx += 3

    bbox = tile_bbox(verts)
    tile['xmin'] = bbox[0]
    tile['ymin'] = bbox[1]
    tile['zmin'] = bbox[2]
    tile['xmax'] = bbox[3]
    tile['ymax'] = bbox[4]
    tile['zmax'] = bbox[5]

    tile['floorcol'] = colRGBA_to_444(pd_tile.floorcol)

    return tile

def export(filename, compress):
    numrooms = get_numrooms()
    if numrooms == 0: return

    decl_tileroom = ['u32 ofs']
    TypeInfo.register('tileroom', decl_tileroom)

    dataout = bytearray()
    rd = ByteStream(dataout)
    rd.write(dataout, numrooms+1, 'u32')

    # list of offsets where each room's tiles start
    rooms_ofs = []
    for _ in range(numrooms+2):
        room = DataBlock.New('tileroom')
        rd.write_block(dataout, room)
        rooms_ofs.append(room)

    rooms_ofs[0].update(dataout, 'ofs', len(dataout))
    rooms_ofs[1].update(dataout, 'ofs', len(dataout))

    floortypes = {e[0].lower(): e[2] for e in pdprops.TILE_FLOORTYPES}

    # retrieve the scene tiles and sort them by room
    coll = bpy.data.collections['Tiles']
    tiles = [tile for tile in coll.objects if tile.pd_obj.type == pdprops.PD_OBJTYPE_TILE]
    tiles.sort(key = lambda tile: tile.pd_tile.roomnum) # TODO assign roomnum to rooms created by the user

    R_inv = mtx.rot_blender_inv()
    roomidx = 1
    prev_room = tiles[0].pd_tile.room

    for bl_tile in tiles:
        pd_tile = bl_tile.pd_tile
        room = pd_tile.room
        # print(f'  {bl_tile} [{roomidx}] OFS {len(dataout):04X} r {room}')

        if room != prev_room:
            roomidx += 1
            rooms_ofs[roomidx].update(dataout, 'ofs', len(dataout))

        prev_room = room

        tile = export_tile(bl_tile, R_inv, floortypes)
        rd.write_block(dataout, tile)

    rooms_ofs[roomidx+1].update(dataout, 'ofs', len(dataout))

    if compress:
        dataout = pdu.compress(dataout)

    pdu.write_file(filename, dataout)
