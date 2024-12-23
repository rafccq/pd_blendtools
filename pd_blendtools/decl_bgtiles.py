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
