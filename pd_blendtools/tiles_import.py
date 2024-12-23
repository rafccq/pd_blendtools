import numpy
import os

import bpy

from pd_bgtiles import PatchBGTiles as PD_BGTiles
from decl_bgtiles import *
from typeinfo import TypeInfo
import pd_utils as pdu
import mtxpalette as mtxp
import romdata as rom

GEOFLAG_FLOOR1            = 0x0001
GEOFLAG_FLOOR2            = 0x0002
GEOFLAG_WALL              = 0x0004
GEOFLAG_BLOCK_SIGHT       = 0x0008
GEOFLAG_BLOCK_SHOOT       = 0x0010
GEOFLAG_LIFTFLOOR         = 0x0020
GEOFLAG_LADDER            = 0x0040
GEOFLAG_RAMPWALL          = 0x0080
GEOFLAG_SLOPE             = 0x0100
GEOFLAG_UNDERWATER        = 0x0200
GEOFLAG_0400              = 0x0400
GEOFLAG_AIBOTCROUCH       = 0x0800
GEOFLAG_AIBOTDUCK         = 0x1000
GEOFLAG_STEP              = 0x2000
GEOFLAG_DIE               = 0x4000
GEOFLAG_LADDER_PLAYERONLY = 0x8000

FLOORTYPE_DEFAULT = 0
FLOORTYPE_WOOD    = 1
FLOORTYPE_STONE   = 2
FLOORTYPE_CARPET  = 3
FLOORTYPE_METAL   = 4
FLOORTYPE_MUD     = 5
FLOORTYPE_WATER   = 6
FLOORTYPE_DIRT    = 7
FLOORTYPE_SNOW    = 8
TILECOLOR_CMDS = ['reset', 'wallfloor', 'flag', 'floorcol', 'floortype']

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


def register():
    TypeInfo.register_all(bgtiles_decl)

def bg_loadtiles(lvname):
    blend_dir = os.path.dirname(bpy.data.filepath)
    romdata = rom.load(f'{blend_dir}/pd.ntsc-final.z64')

    filename = f'bgdata/{lvname}_tilesZ'
    tiledata = romdata.filedata(filename)
    # pdu.print_bin(f'^{lvname.upper()}', tiledata, 0, 64)
    tiledata = PD_BGTiles(tiledata)

    for idx, geo in enumerate(tiledata.geos):
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
            tileobj = bpy.data.objects.new(f'{basename}', tilemesh)
            tileobj['flags'] = geo['header']['flags']
            tileobj['floorcol'] = geo['floorcol']
            tileobj['floortype'] = geo['floortype']
            # tileobj.display_type = 'WIRE'
            tileobj.show_wire = True
            collection = pdu.active_collection()
            collection.objects.link(tileobj)

yellow = (.8, .8, 0, 1)
red = (.8, 0, 0, 1)
white = (1, 1, 1, 1)
def col444_to_RGBA(col):
    r = ((col & 0xf00) >> 8) / 15
    g = ((col & 0x0f0) >> 4) / 15
    b = (col & 0x00f) / 15

    return r, g, b, 1

def bg_colortiles(cmd, flag=None):
    if cmd not in TILECOLOR_CMDS: raise RuntimeError(f'bg_colortiles() Invalid cmd {cmd}')

    numaffected = 0
    for tile in bpy.context.scene.objects:
        if not tile.name.startswith('Tile_'): continue

        color = white
        if cmd == 'wallfloor':
            flags = tile['flags']
            isfloor = (flags & GEOFLAG_FLOOR1) or (flags & GEOFLAG_FLOOR2)
            color = yellow if isfloor else red
            numaffected += 1
        elif cmd == 'floorcol':
            color = col444_to_RGBA(tile['floorcol'])
            numaffected += 1
        elif cmd == 'flag':
            flags = tile['flags']
            color = red if flags & flag else white
            if flags & flag: numaffected += 1
        elif cmd == 'floortype':
            floortype = tile['floortype']
            hexcol = FLOORTYPE_COLORS[floortype]
            color = mtxp.hex2col(hexcol)

        tile.color = color

    print(f'tiles tagged: {numaffected}')
