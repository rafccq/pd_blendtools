decl_primarydata = [
    'u32* zero',
    'u32* rooms',
    'u32* portals',
    'u32* bgcmds',
    'u32* lightfile',
    'u32* table5',
]

decl_coord = [
    'f32 x',
    'f32 y',
    'f32 z',
]

decl_bgroom = [
    'u32* unk00',
    'struct coord pos',
    'u8 unk10',
    'u8 unk11',
    's16 _pad_',
]

decl_bgportal = [
    'u16 verticesoffset',
    's16 roomnum1',
    's16 roomnum2',
    'u8 flags',
    'u8 _pad_',
]

decl_portalvertices = [
    'u8 count',
    'u8 _pad_[3]',
    'struct coord vertices[N]',
]

decl_bgcmd = [
    'u8 type',
    'u8 len',
    'u8 _pad_[2]',
    'u32 param',
]

decl_roomgfxdata = [
    'struct gfxvtx *vertices',
    'u32 *colours',
    'struct roomblock *opablocks',
    'struct roomblock *xlublocks',
    's16 lightsindex',
    's16 numlights',
    's16 numvertices',
    's16 numcolours',
    # 'struct roomblock blocks[N]',
]

decl_roomblock = [
    'u8 type',
    'u8 _pad_[3]',
    'struct roomblock *next',
    'Gfx *gdl|child', #union
    'struct gfxvtx *vertices|coord1', #union
    'u32 *colours', #union
]

decl_bbox = [
    'u16 min_x',
    'u16 min_y',
    'u16 min_z',
    'u16 max_x',
    'u16 max_y',
    'u16 max_z',
]

decl_gfxvtx = [
    's16 x',
    's16 y',
    's16 z',
    'u8 flags',
    'u8 colour',
    's16 s',
    's16 t',
]

decl_vec3s16 = [
    's16 s[3]'
]
decl_light = [
    'u16 roomnum',
    'u16 colour',
    'u8 brightness',
    'u8 unk05_00',
    'u8 brightnessmult',
    's8 dirx',
    's8 diry',
    's8 dirz',
    'struct vec3s16 bbox[4]',
]

decl_header = [
    'u32 section1inflatedsize',
    'u32 section1compsize',
    'u32 primcompsize',
    'u16 section2inflatedsize',
    'u16 section2compsize',
    'u16 inflatedsize',
    'u16 section3compsize',
]

bgfile_decls = {
    'vec3s16': decl_vec3s16,
    'primarydata': decl_primarydata,
    'header': decl_header,
    'coord': decl_coord,
    'bgroom': decl_bgroom,
    'bgportal': decl_bgportal,
    'bgcmd': decl_bgcmd,
    'roomgfxdata': decl_roomgfxdata,
    'roomblock': decl_roomblock,
    'bbox': decl_bbox,
    'gfxvtx': decl_gfxvtx,
    'light': decl_light,
}
