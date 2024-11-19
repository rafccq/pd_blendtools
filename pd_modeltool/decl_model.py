decl_modeldef = [
    'struct modelnode *rootnode',
    'struct skeleton *skel',
    'struct modelnode **parts',
    's16 numparts',
    's16 nummatrices',
    'f32 scale',
    's16 rwdatalen',
    's16 numtexconfigs',
    # 's32 _pad_',
    'struct textureconfig *texconfigs',
]

decl_modelnode = [
    'u16 type',
    'u16 _pad_',
    'struct modelrodata *rodata',
    'struct modelnode *parent',
    'struct modelnode *next',
    'struct modelnode *prev',
    'struct modelnode *child',
]

decl_texconfig = [
    'u8* texturenum',
    'u8 width',
    'u8 height',
    'u8 level',
    'u8 format',
    'u8 depth',
    'u8 s',
    'u8 t',
    'u8 unk0b;',
]

decl_rodata_chrinfo = [ # type 0x01
    'u16 animpart',
    's16 mtxindex',
    'f32 unk04',
    'u16 rwdataindex',
]

decl_rodata_position = [ # type 0x02
    'struct coord pos',
    'u16 part',
    's16 mtxindexes[3]',
    'f32 drawdist',
]

decl_rodata_gundl = [ # type 0x04
    'Gfx *opagdl',
    'Gfx *xlugdl',
    'void *baseaddr',
    'struct gfxvtx *vertices',
    's16 numvertices',
    's16 unk12',
]

decl_rodata_distance = [ # type 0x08
    'f32 neardist',
    'f32 fardist',
    'struct modelnode *target',
    'u16 rwdataindex',
]

decl_rodata_reorder = [ # type 0x09
    'f32 unk00',
    'f32 unk04',
    'f32 unk08',
    'f32 unk0c[3]',
    'struct modelnode *unk18',
    'struct modelnode *unk1c',
    's16 side',
    'u16 rwdataindex',
]

decl_rodata_bbox = [ # type 0x0a
    's32 hitpart',
    'f32 xmin',
    'f32 xmax',
    'f32 ymin',
    'f32 ymax',
    'f32 zmin',
    'f32 zmax',
]

decl_rodata_type0b = [ # type 0x0b
    'u32 unk00',
    'u32 unk04',
    'u32 unk08',
    'u32 unk0c',
    'u32 unk10',
    'u32 unk14',
    'u32 unk18',
    'u32 unk1c',
    'u32 unk20',
    'u32 unk24',
    'u32 unk28',
    'u32 unk2c',
    'u32 unk30',
    'u32 unk34',
    'u32 unk38',
    'void *unk3c',
    'u32 unk40',
    'u16 rwdataindex',
    'void *baseaddr',
]

decl_rodata_chrgunfire = [ # type 0x0c
    'struct coord pos',
    'struct coord dim',
    'struct textureconfig *texture',
    'f32 unk1c',
    'u16 rwdataindex',
    'void *baseaddr',
]

decl_rodata_type11 = [ # type 0x11
    'u32 unk00',
    'u32 unk04',
    'u32 unk08',
    'u32 unk0c',
    'u32 unk10',
    'void *unk14',
]

decl_rodata_toggle = [ # type 0x12
    'struct modelnode *target',
    'u16 rwdataindex',
]

decl_rodata_positionheld = [ # type 0x15
    'struct coord pos',
    's16 mtxindex',
]

decl_rodata_stargunfire = [ # type 0x16
    's32 unk00',
    'struct gfxvtx *vertices',
    'Gfx *gdl',
    'void *baseaddr',
]

decl_rodata_headspot = [ # type 0x17
    'u16 rwdataindex'
]

decl_rodata_dl = [ # type 0x18
    'Gfx *opagdl',
    'Gfx *xlugdl',
    'u32 *colourtable',
    'struct gfxvtx *vertices',
    's16 numvertices',
    's16 mcount',
    'u16 rwdataindex',
    'u16 numcolours',
]

decl_rodata_type19 = [ # type 0x19
    's32 numvertices',
    'struct coord vertices[4]',
]

decl_coord = [
    'f32 x',
    'f32 y',
    'f32 z',
]

decl_parts = [
    'u8* parts[N]',
    's16 partsnum[N]',
]

rodata_decls = {
    0x01: 'modelrodata_chrinfo',
    0x02: 'modelrodata_position',
    0x04: 'modelrodata_gundl',
    0x08: 'modelrodata_distance',
    0x09: 'modelrodata_reorder',
    0x0a: 'modelrodata_bbox',
    0x0b: 'modelrodata_type0b',
    0x0c: 'modelrodata_chrgunfire',
    0x0d: 'modelrodata_type0d',
    0x11: 'modelrodata_type11',
    0x12: 'modelrodata_toggle',
    0x15: 'modelrodata_positionheld',
    0x16: 'modelrodata_stargunfire',
    0x17: 'modelrodata_headspot',
    0x18: 'modelrodata_dl',
    0x19: 'modelrodata_type19',
}

model_decls = {
    'coord': decl_coord,
    'modeldef': decl_modeldef,
    'modelnode': decl_modelnode,
    'texconfig': decl_texconfig,
    'modelrodata_chrinfo': decl_rodata_chrinfo,
    'modelrodata_position': decl_rodata_position,
    'modelrodata_gundl': decl_rodata_gundl,
    'modelrodata_distance': decl_rodata_distance,
    'modelrodata_reorder': decl_rodata_reorder,
    'modelrodata_bbox': decl_rodata_bbox,
    'modelrodata_type0b': decl_rodata_type0b,
    'modelrodata_chrgunfire': decl_rodata_chrgunfire,
    'modelrodata_type11': decl_rodata_type11,
    'modelrodata_toggle': decl_rodata_toggle,
    'modelrodata_positionheld': decl_rodata_positionheld,
    'modelrodata_stargunfire': decl_rodata_stargunfire,
    'modelrodata_headspot': decl_rodata_headspot,
    'modelrodata_dl': decl_rodata_dl,
    'modelrodata_type19': decl_rodata_type19,
}