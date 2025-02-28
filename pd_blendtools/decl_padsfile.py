PADFLAG_INTPOS          = 0x0001
PADFLAG_UPALIGNTOX      = 0x0002
PADFLAG_UPALIGNTOY      = 0x0004
PADFLAG_UPALIGNTOZ      = 0x0008
PADFLAG_UPALIGNINVERT   = 0x0010
PADFLAG_LOOKALIGNTOX    = 0x0020
PADFLAG_LOOKALIGNTOY    = 0x0040
PADFLAG_LOOKALIGNTOZ    = 0x0080
PADFLAG_LOOKALIGNINVERT = 0x0100
PADFLAG_HASBBOXDATA     = 0x0200
PADFLAG_AIWAITLIFT      = 0x0400
PADFLAG_AIONLIFT        = 0x0800
PADFLAG_AIWALKDIRECT    = 0x1000
PADFLAG_AIDROP          = 0x2000
PADFLAG_AIDUCK          = 0x4000
PADFLAG_8000            = 0x8000
PADFLAG_10000           = 0x10000
PADFLAG_20000           = 0x20000


PADFIELD_POS    = 0x0002
PADFIELD_LOOK   = 0x0004
PADFIELD_UP     = 0x0008
PADFIELD_NORMAL = 0x0010
PADFIELD_BBOX   = 0x0020
PADFIELD_ROOM   = 0x0040
PADFIELD_FLAGS  = 0x0080
PADFIELD_LIFT   = 0x0100

decl_padsfileheader = [
    's32 numpads',
    's32 numcovers',
    's32 waypointsoffset',
    's32 waygroupsoffset',
    's32 coversoffset',
    's16 padoffsets[N]',
]

decl_cover = [
	'struct coord pos',
	'struct coord look',
	'u16 flags',
	'u16 _pad_',
]

decl_waygroup = [
	's32 *neighbours',
	's32 *waypoints',
	's32 unk08',
]

decl_waypoint = [
	's32 padnum',
	's32 *neighbours',
	's32 groupnum',
	's32 unk0c',
]

decl_coord = [
	'f32 x',
	'f32 y',
	'f32 z',
]

decl_arrays32 = [
	's32 value'
]

padsfile_decls = {
	'coord': decl_coord,
    'cover': decl_cover,
    'waygroup': decl_waygroup,
    'waypoint': decl_waypoint,
	'arrays32': decl_arrays32
}
