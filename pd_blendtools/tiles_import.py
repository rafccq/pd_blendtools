import numpy
import os

import bpy

from pd_bgtiles import PatchBGTiles as PD_BGTiles
from decl_bgtiles import *
from typeinfo import TypeInfo
import pd_utils as pdu
import mtxpalette as mtxp
import romdata as rom
import pd_blendprops as pdprops

FLOORTYPE_COLORS = [
    0xBBBBBB, # DEFAULT
    0x332211, # WOOD
    0x444952, # STONE
    0x881615, # CARPET
    0x39648d, # METAL
    0x491a00, # MUD
    0x0011DD, # WATER
    0x926c4d, # DIRT
    0xffffff  # SNOW
]

yellow = (.8, .8, 0, 1)
red = (.8, 0, 0, 1)
white = (1, 1, 1, 1)

def register():
    TypeInfo.register_all(bgtiles_decl)

floortype_names = {
    0: 'default',
    1: 'wood',
    2: 'stone',
    3: 'carpet',
    4: 'metal',
    5: 'mud',
    6: 'water',
    7: 'dirt',
    8: 'snow',
}

def tile_setprops(bl_tile, geo):
    bl_tile.pd_obj.name = bl_tile.name
    bl_tile.pd_obj.type = pdprops.PD_OBJTYPE_TILE
    flags = geo['header']['flags']
    for i in range(16):
        bl_tile.pd_tile.flags[i] = bool(flags & (1 << i))
    bl_tile.pd_tile.floorcol = col444_to_RGBA(geo['floorcol'])
    bl_tile.pd_tile.floortype = floortype_names[geo['floortype']]
    roomnum = geo['room']
    bl_tile.pd_tile.roomnum = roomnum
    scn = bpy.context.scene
    if 'rooms' in scn and roomnum != 0:
        bl_tile.pd_tile.room = scn['rooms'][str(roomnum)]

def tiles_import(romdata):
    scn = bpy.context.scene

    if scn.import_src_tiles == 'ROM':
        tilesdata = romdata.filedata(scn.rom_tiles)
    else:
        tilesdata = pdu.read_file(scn.file_tiles)

    pdtiles = PD_BGTiles(tilesdata)

    for idx, geo in enumerate(pdtiles.geos):
        # print(geo)
        geotype = geo['header']['type']
        if geotype == GEOTYPE_TILE_I:
            numvtx = geo['header']['numvertices']
            geoverts = geo['vertices']
            verts = []
            for v in range(0, numvtx * 3, 3):
                x, y, z = [numpy.int16(geoverts[v+k]) for k in range(3)]
                verts.append((z, x, y))

            basename = f'Tile_{idx:02X}'
            tilemesh = pdu.mesh_from_verts(verts, f'{basename}_mesh', triangulate=False)
            bl_tile = bpy.data.objects.new(f'{basename}', tilemesh)
            bl_tile['flags'] = geo['header']['flags']
            bl_tile['floorcol'] = geo['floorcol']
            bl_tile['floortype'] = geo['floortype']
            # bl_tile.display_type = 'WIRE'
            bl_tile.show_wire = True
            pdu.add_to_collection(bl_tile, 'Tiles')
            tile_setprops(bl_tile, geo)

def col444_to_RGBA(col):
    r = ((col & 0xf00) >> 8) / 15
    g = ((col & 0x0f0) >> 4) / 15
    b = (col & 0x00f) / 15

    return r, g, b, 1

def bg_colortile(bl_tile, context, flags=None, room=None):
    scn = context.scene
    mode = scn.pd_tile_hilightmode

    affected = 0
    props_tile = bl_tile.pd_tile

    color = white
    if mode == 'wallfloor':
        flags = tile_flags(props_tile.flags)
        isfloor = (flags & GEOFLAG_FLOOR1) or (flags & GEOFLAG_FLOOR2)
        iswall = flags & GEOFLAG_WALL
        if isfloor: color = yellow
        elif iswall: color = red
        affected = 1
    elif mode == 'floorcolor':
        color = props_tile.floorcol
        affected = 1
    elif mode == 'flags':
        tileflags = tile_flags(props_tile.flags)
        affected = 1 if tileflags & flags else 0
        color = red if affected else white
    elif mode == 'floortype':
        floortype = props_tile.floortype
        floortype = pdprops.FLOORTYPES_VALUES[floortype]
        hexcol = FLOORTYPE_COLORS[floortype]
        color = mtxp.hex2col(hexcol)
        affected = 1
    elif mode == 'room':
        affected = 1 if props_tile.room == room else 0
        color = red if affected else white

    bl_tile.color = color

    return affected

def bg_colortiles(context):
    scn = context.scene
    flags = tile_flags(scn.pd_tile_hilight.flags)
    room = scn.pd_tile_hilight.room

    numaffected = 0
    for bl_tile in bpy.data.collections['Tiles'].objects:
        numaffected += bg_colortile(bl_tile, context, flags, room)

    return numaffected
