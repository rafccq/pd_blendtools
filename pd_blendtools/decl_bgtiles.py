decl_geo = [
    'u8 type',
    'u8 numvertices',
    'u16 flags',
]

decl_geotilei = [
    'struct geo header',
    'u16 floortype',
    'u8 xmin',
    'u8 ymin',
    'u8 zmin',
    'u8 xmax',
    'u8 ymax',
    'u8 zmax',
    'u16 floorcol',
    's16 vertices[N][3]',
]

decl_geotilef = [
    'struct geo header',
    'u16 floortype',
    'u8 xmin',
    'u8 ymin',
    'u8 zmin',
    'u8 xmax',
    'u8 ymax',
    'u8 zmax',
    'u16 floorcol',
    'u16 _pad_',
    'struct coord vertices[N]',
]

decl_geoblock = [
    'struct geo header',
    'f32 ymax',
    'f32 ymin',
    'f32 vertices[8][2]',
]

decl_geocyl = [
    'struct geo header',
    'f32 ymax',
    'f32 ymin',
    'f32 x',
    'f32 z',
    'f32 radius',
]

bgtiles_decl = {
    'geo': decl_geo,
    'geoblock': decl_geoblock,
    'geocyl': decl_geocyl,
}

GEOTYPE_TILE_I = 0
GEOTYPE_TILE_F = 1
GEOTYPE_BLOCK  = 2
GEOTYPE_CYL    = 3


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

# array of bool to int
def tile_flags(prop_flags):
    flags = 0
    n = len(prop_flags)
    for i in range(n):
        flags |= (1 << i) if prop_flags[i] else 0
    return flags

