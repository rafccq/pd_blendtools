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

    TypeInfo.sizeof.cache_clear()
    TypeInfo.offsetof.cache_clear()
    TypeInfo._struct_size.cache_clear()

    TypeInfo.register('geotilei', decl_geotilei, False, varmap={'N': numvtx})

    tiledata = DataBlock.New('geotilei')
    tileheader = tiledata['header']
    tileheader['type'] = GEOTYPE_TILE_I
    tileheader['numvertices'] = numvtx
    tileheader['flags'] = pdu.flags_pack(pd_tile.flags, pdprops.TILE_FLAGS_VALUES)

    tiledata['floortype'] = floortypes[pd_tile.floortype]

    verts = bgu.verts_world(bl_tile, R_inv, round)

    conv = lambda e: (round(e.x), round(e.y), round(e.z))
    tv = tiledata['vertices']
    vidx = 0
    for v in verts:
        tv[vidx + 0], tv[vidx + 1], tv[vidx + 2] = conv(v)
        vidx += 3

    bbox = tile_bbox(verts)
    tiledata['xmin'] = bbox[0]
    tiledata['ymin'] = bbox[1]
    tiledata['zmin'] = bbox[2]
    tiledata['xmax'] = bbox[3]
    tiledata['ymax'] = bbox[4]
    tiledata['zmax'] = bbox[5]

    tiledata['floorcol'] = colRGBA_to_444(pd_tile.floorcol)

    return tiledata

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

    # build the tile map (roomnum -> [tiles])
    tilemap = {}
    coll = bpy.data.collections['Tiles']
    for tile in coll.objects:
        if pdu.pdtype(tile) != pdprops.PD_OBJTYPE_TILE: continue
        bl_room = tile.pd_tile.room
        pd_room = bl_room.pd_room
        if pd_room.roomnum in tilemap:
            tilemap[pd_room.roomnum].append(tile)
        else:
            tilemap[pd_room.roomnum] = [tile]

    floortypes = {e[0].lower(): e[2] for e in pdprops.TILE_FLOORTYPES}
    R_inv = mtx.rot_blender_inv()

    for roomnum in range(1, numrooms + 1):
        rooms_ofs[roomnum].update(dataout, 'ofs', len(dataout))
        print('  >> room', roomnum)
        if roomnum not in tilemap: continue

        # write the tiles vertices
        tiles = tilemap[roomnum]
        for bl_tile in tiles:
            tiledata = export_tile(bl_tile, R_inv, floortypes)
            rd.write_block(dataout, tiledata, reread_arraysize=True)

    rooms_ofs[roomnum+1].update(dataout, 'ofs', len(dataout))

    if compress:
        dataout = pdu.compress(dataout)

    pdu.write_file(filename, dataout)
