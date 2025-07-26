cmd_size = [
    3,  # INTROCMD_SPAWN
    4,  # INTROCMD_WEAPON
    4,  # INTROCMD_AMMO
    8,  # INTROCMD_3
    2,  # INTROCMD_4
    2,  # INTROCMD_OUTFIT
    10, # INTROCMD_6
    3,  # INTROCMD_WATCHTIME
    2,  # INTROCMD_CREDITOFFSET
    3,  # INTROCMD_CASE
    3,  # INTROCMD_CASERESPAWN
    2,  # INTROCMD_HILL
]

ENDMARKER_INTROCMD = 0x0C
ENDMARKER_PROPS = 0x34

# object flags
OBJTYPE_DOOR               = 0x01
OBJTYPE_DOORSCALE          = 0x02
OBJTYPE_BASIC              = 0x03
OBJTYPE_KEY                = 0x04
OBJTYPE_ALARM              = 0x05
OBJTYPE_CCTV               = 0x06
OBJTYPE_AMMOCRATE          = 0x07
OBJTYPE_WEAPON             = 0x08
OBJTYPE_CHR                = 0x09
OBJTYPE_SINGLEMONITOR      = 0x0a
OBJTYPE_MULTIMONITOR       = 0x0b
OBJTYPE_HANGINGMONITORS    = 0x0c
OBJTYPE_AUTOGUN            = 0x0d
OBJTYPE_LINKGUNS           = 0x0e
OBJTYPE_DEBRIS             = 0x0f
OBJTYPE_10                 = 0x10
OBJTYPE_HAT                = 0x11
OBJTYPE_GRENADEPROB        = 0x12
OBJTYPE_LINKLIFTDOOR       = 0x13
OBJTYPE_MULTIAMMOCRATE     = 0x14
OBJTYPE_SHIELD             = 0x15
OBJTYPE_TAG                = 0x16
OBJTYPE_BEGINOBJECTIVE     = 0x17
OBJTYPE_ENDOBJECTIVE       = 0x18
OBJECTIVETYPE_DESTROYOBJ   = 0x19
OBJECTIVETYPE_COMPFLAGS    = 0x1a
OBJECTIVETYPE_FAILFLAGS    = 0x1b
OBJECTIVETYPE_COLLECTOBJ   = 0x1c
OBJECTIVETYPE_THROWOBJ     = 0x1d
OBJECTIVETYPE_HOLOGRAPH    = 0x1e
OBJECTIVETYPE_1F           = 0x1f
OBJECTIVETYPE_ENTERROOM    = 0x20
OBJECTIVETYPE_THROWINROOM  = 0x21
OBJTYPE_22                 = 0x22
OBJTYPE_BRIEFING           = 0x23
OBJTYPE_GASBOTTLE          = 0x24
OBJTYPE_RENAMEOBJ          = 0x25
OBJTYPE_PADLOCKEDDOOR      = 0x26
OBJTYPE_TRUCK              = 0x27
OBJTYPE_HELI               = 0x28
OBJTYPE_29                 = 0x29
OBJTYPE_GLASS              = 0x2a
OBJTYPE_SAFE               = 0x2b
OBJTYPE_SAFEITEM           = 0x2c
OBJTYPE_TANK               = 0x2d
OBJTYPE_CAMERAPOS          = 0x2e
OBJTYPE_TINTEDGLASS        = 0x2f
OBJTYPE_LIFT               = 0x30
OBJTYPE_CONDITIONALSCENERY = 0x31
OBJTYPE_BLOCKEDPATH        = 0x32
OBJTYPE_HOVERBIKE          = 0x33
OBJTYPE_END                = 0x34
OBJTYPE_HOVERPROP          = 0x35
OBJTYPE_FAN                = 0x36
OBJTYPE_HOVERCAR           = 0x37
OBJTYPE_PADEFFECT          = 0x38
OBJTYPE_CHOPPER            = 0x39
OBJTYPE_MINE               = 0x3a
OBJTYPE_ESCASTEP           = 0x3b

# object flags
OBJFLAG_FALL                       = 0x00000001
OBJFLAG_00000002                   = 0x00000002 # Editor: "In Air Rotated 90 Deg Upside-Down"
OBJFLAG_UPSIDEDOWN                 = 0x00000004
OBJFLAG_00000008                   = 0x00000008 # Editor: "In Air"
OBJFLAG_00000010                   = 0x00000010 # Editor: "Scale to Pad Bounds"
OBJFLAG_XTOPADBOUNDS               = 0x00000020
OBJFLAG_YTOPADBOUNDS               = 0x00000040
OBJFLAG_ZTOPADBOUNDS               = 0x00000080
OBJFLAG_00000100                   = 0x00000100 # G5 mines, Air Base brown door, AF1 grate and escape door, Defense shuttle, Ruins mines, MBR lift door. Editor suggests "Force Collisions" but this seems wrong
OBJFLAG_ORTHOGONAL                 = 0x00000200
OBJFLAG_IGNOREFLOORCOLOUR          = 0x00000400
OBJFLAG_PATHBLOCKER                = 0x00000800 # Glass and explodable scenery which may be blocking a path segment
OBJFLAG_IGNOREROOMCOLOUR           = 0x00001000 # Editor: "Absolute Position"
OBJFLAG_AIUNDROPPABLE              = 0x00002000 # AI cannot drop item
OBJFLAG_ASSIGNEDTOCHR              = 0x00004000
OBJFLAG_INSIDEANOTHEROBJ           = 0x00008000 # Eg. gun inside a crate or suitcase inside a dumpster
OBJFLAG_FORCEMORTAL                = 0x00010000
OBJFLAG_INVINCIBLE                 = 0x00020000
OBJFLAG_COLLECTABLE                = 0x00040000
OBJFLAG_THROWNLAPTOP               = 0x00080000
OBJFLAG_UNCOLLECTABLE              = 0x00100000
OBJFLAG_BOUNCEIFSHOT               = 0x00200000 # Bounce or explode
OBJFLAG_FORCENOBOUNCE              = 0x00400000 # Override the above
OBJFLAG_HELDROCKET                 = 0x00800000 # Rocket obj that's currently in an equipped rocket launcher
OBJFLAG_01000000                   = 0x01000000 # Editor: "Embedded Object"
OBJFLAG_CANNOT_ACTIVATE            = 0x02000000 # Makes it do nothing if player presses B on object. Used mostly for doors.
OBJFLAG_AISEETHROUGH               = 0x04000000 # Glass, glass doors, small objects such as plant pots
OBJFLAG_AUTOGUN_3DRANGE            = 0x08000000 # Autogun uses 3 dimensions when checking if target is in range
OBJFLAG_DEACTIVATED                = 0x10000000
OBJFLAG_AMMOCRATE_EXPLODENOW       = 0x10000000
OBJFLAG_DOOR_HASPORTAL             = 0x10000000
OBJFLAG_GLASS_HASPORTAL            = 0x10000000
OBJFLAG_WEAPON_LEFTHANDED          = 0x10000000
OBJFLAG_ESCSTEP_ZALIGNED           = 0x10000000
OBJFLAG_AUTOGUN_SEENTARGET         = 0x20000000
OBJFLAG_CAMERA_DISABLED            = 0x20000000
OBJFLAG_CHOPPER_INIT               = 0x20000000
OBJFLAG_DOOR_OPENTOFRONT           = 0x20000000
OBJFLAG_HOVERCAR_INIT              = 0x20000000
OBJFLAG_HOVERPROP_20000000         = 0x20000000
OBJFLAG_LIFT_LATERALMOVEMENT       = 0x20000000
OBJFLAG_MONITOR_20000000           = 0x20000000
OBJFLAG_WEAPON_AICANNOTUSE         = 0x20000000
OBJFLAG_AUTOGUN_DAMAGED            = 0x40000000
OBJFLAG_CAMERA_BONDINVIEW          = 0x40000000
OBJFLAG_DOOR_KEEPOPEN              = 0x40000000
OBJFLAG_HOVERBIKE_MOVINGWHILEEMPTY = 0x40000000
OBJFLAG_HOVERCAR_40000000          = 0x40000000 # Set but not read
OBJFLAG_LIFT_TRIGGERDISABLE        = 0x40000000
OBJFLAG_MONITOR_RENDERPOSTBG       = 0x40000000
OBJFLAG_WEAPON_NOAMMO              = 0x40000000 # Don't give ammo when picking up
OBJFLAG_80000000                   = 0x80000000
OBJFLAG_CHOPPER_INACTIVE           = 0x80000000
OBJFLAG_DOOR_TWOWAY                = 0x80000000 # Door swings in both directions
OBJFLAG_HOVERCAR_ISHOVERBOT        = 0x80000000
OBJFLAG_LIFT_CHECKCEILING          = 0x80000000
OBJFLAG_WEAPON_CANMIXDUAL          = 0x80000000

# intro cmds
INTROCMD_SPAWN        = 0
INTROCMD_WEAPON       = 1
INTROCMD_AMMO         = 2
INTROCMD_3            = 3
INTROCMD_4            = 4
INTROCMD_OUTFIT       = 5
INTROCMD_6            = 6
INTROCMD_WATCHTIME    = 7
INTROCMD_CREDITOFFSET = 8
INTROCMD_CASE         = 9
INTROCMD_CASERESPAWN  = 10
INTROCMD_HILL         = 11
INTROCMD_END          = 12


decl_defaultobj = [
    'u16 extrascale',
    'u8 hidden2',
    'u8 type',
    's16 modelnum',
    's16 pad',
    'u32 flags',
    'u32 flags2',
    'u32 flags3',
    # 'u32 _pad_',
    'struct prop* prop',
    'struct model* model',
    'f32 realrot[3][3]',
    'u32 hidden',
    'struct geotilef* geotilef', # union
    'struct projectile* projectile', #union
    's16 damage',
    's16 maxdamage',
    'u8 shadecol[4]',
    'u8 nextcol[4]',
    'u16 floorcol',
    's8 geocount',
    # 's8 _pad_',
]

decl_objheader = [
    'u16 unk00_1',
    'u8 unk00_2',
    'u8 type',
]

# objtype 0x01
decl_doorobj = [
    'struct defaultobj base',
    'f32 maxfrac',
    'f32 perimfrac',
    'f32 accel',
    'f32 decel',
    'f32 maxspeed',
    'u16 doorflags',
    'u16 doortype',
    'u32 keyflags',
    's32 autoclosetime',
    'f32 frac',
    'f32 fracspeed',
    's8 mode',
    's8 glasshits',
    's16 fadealpha',
    's16 xludist',
    's16 opadist',
    'struct coord startpos',
    'f32 mtx98[3][3]',
    'struct doorobj* sibling',
    's32 lastopen60',
    's16 portalnum',
    's8 soundtype',
    's8 fadetime60',
    's32 lastcalc60',
    'u8 laserfade',
    'u8 unusedmaybe[3]',
    'u8 shadeinfo1[4]',
    'u8 shadeinfo2[4]',
    'u8 actual1',
    'u8 actual2',
    'u8 extra1',
    'u8 extra2',
    # 'u32 _pad_ ',
]

# objtype 0x02
decl_doorscaleobj = [
    'struct obj_header header',
    'f32 scale',
]

# objtype 0x04
decl_keyobj = [
    'struct defaultobj base',
    'u32 keyflags',
]

# objtype 0x06
decl_cctvobj = [
    'struct defaultobj base',
    's16 lookatpadnum',
    's16 toleft',
    'f32 camrotm[4][4]',
    'f32 yzero',
    'f32 yrot',
    'f32 yleft',
    'f32 yright',
    'f32 yspeed',
    'f32 ymaxspeed',
    's32 seebondtime60',
    'f32 maxdist',
    'f32 xzero',
]

decl_ammocrateobj = [
    'struct defaultobj base',
    's32 ammotype',
]

# objtype 0x08
decl_weaponobj = [
    'struct defaultobj base',
    'u8 weaponnum', # union {
    'u8 unk5d',
    'u8 unk5e',
    'u8 gunfunc', # }
    's8 fadeouttimer60',
    's8 dualweaponnum',
    's16 timer240', # union
    'struct weaponobj* dualweapon',
]

# objtype 0x09
decl_packedchr = [
    's16 chrindex',
    's8 unk02',
    's8 typenum',
    'u32 spawnflags',
    's16 chrnum',
    'u16 padnum',
    'u8 bodynum',
    's8 headnum',
    'u16 ailistnum',
    'u16 padpreset',
    'u16 chrpreset',
    'u16 hearscale',
    'u16 viewdist',
    'u32 flags',
    'u32 flags2',
    'u8 team',
    'u8 squadron',
    's16 chair',
    'u32 convtalk',
    'u8 tude',
    'u8 naturalanim',
    'u8 yvisang',
    'u8 teamscandist',
]

decl_tvscreen = [
    'u32* cmdlist',
    'u16 offset',
    's16 pause60',
    'struct textureconfig* tconfig',
    'f32 rot',
    'f32 xscale',
    'f32 xscalefrac',
    'f32 xscaleinc',
    'f32 xscaleold',
    'f32 xscalenew',
    'f32 yscale',
    'f32 yscalefrac',
    'f32 yscaleinc',
    'f32 yscaleold',
    'f32 yscalenew',
    'f32 xmid',
    'f32 xmidfrac',
    'f32 xmidinc',
    'f32 xmidold',
    'f32 xmidnew',
    'f32 ymid',
    'f32 ymidfrac',
    'f32 ymidinc',
    'f32 ymidold',
    'f32 ymidnew',
    'u8 red',
    'u8 redold',
    'u8 rednew',
    'u8 green',
    'u8 greenold',
    'u8 greennew',
    'u8 blue',
    'u8 blueold',
    'u8 bluenew',
    'u8 alpha',
    'u8 alphaold',
    'u8 alphanew',
    'f32 colfrac',
    'f32 colinc',
]

# objtype 0x0a
decl_singlemonitorobj = [
    'struct defaultobj base',
    'struct tvscreen screen',
    's16 owneroffset',
    's8 ownerpart',
    'u8 imagenum',
]

# objtype 0x0b
decl_multimonitorobj = [
    'struct defaultobj base',
    'struct tvscreen screens[4]',
    'u8 imagenums[4]',
]

# objtype 0x0c
decl_hangingsmonitorobj = [
    'struct defaultobj base',
]

# objtype 0x0d
decl_autogunobj = [
    'struct defaultobj base',
    's16 targetpad',
    's8 firing',
    'u8 firecount',
    'f32 yzero',
    'f32 ymaxleft',
    'f32 ymaxright',
    'f32 yrot',
    'f32 yspeed',
    'f32 xzero',
    'f32 xrot',
    'f32 xspeed',
    'f32 maxspeed',
    'f32 aimdist',
    'f32 barrelspeed',
    'f32 barrelrot',
    's32 lastseebond60',
    's32 lastaimbond60',
    's32 allowsoundframe',
    'struct beam* beam',
    'f32 shotbondsum',
    'struct prop* target',
    'u8 targetteam',
    'u8 ammoquantity',
    's16 nextchrtest',
]

# objtype 0x0e
decl_linkgunsobj = [
    'struct obj_header header',
    's16 offset1',
    's16 offset2',
]

# objtype 0x11
decl_hatobj = [
    'struct defaultobj base',
]

# objtype 0x12
decl_grenadeprobobj = [
    'struct obj_header header',
    's16 chrnum',
    'u16 probability',
]

# objtype 0x13
decl_linkliftdoorobj = [
    'struct obj_header header',
    'struct prop* door',
    'struct prop* lift',
    'struct linkliftdoorobj* next',
    's32 stopnum',
]

decl_multiammocrateslot = [
    'u16 modelnum',
    'u16 quantity',
]

# objtype 0x14
decl_multiammocrateobj = [
    'struct defaultobj base',
    'struct multiammocrateslot slots[19]',
]

# objtype 0x15
decl_shieldobj = [
    'struct defaultobj base',
    'f32 initialamount',
    'f32 amount',
    's32 unk64',
]

# objtype 0x16
decl_tag = [
    # self.read('u32', 'identifier')
    'struct obj_header header',
    'u16 tagnum',
    's16 cmdoffset',
    'struct tag* next',
    'struct defaultobj* obj',
]

# objtype 0x17
decl_objective = [
    'struct obj_header header',
    's32 index',
    'u32 text',
    'u16 unk0c',
    'u8 flags',
    's8 difficulties',
]

# objtype 0x1e
decl_criteria_holograph = [
    'struct obj_header header',
    'u32 obj',
    'u32 status',
    'struct criteria_holograph* next',
]

# objtype 0x20
decl_criteria_roomentered = [
    'struct obj_header header',
    'u32 pad',
    'u32 status',
    'struct criteria_roomentered* next',
]

# objtype 0x21
decl_criteria_throwinroom = [
    'struct obj_header header',
    'u32 unk04',
    'u32 pad',
    'u32 status',
    'struct criteria_throwinroom* next',
]

# objtype 0x23
decl_briefingobj = [
    'struct obj_header header',
    'u32 type',
    'u32 text',
    'struct briefingobj* next',
]

# objtype 0x25
decl_textoverride = [
    'struct obj_header header',
    's32 objoffset',
    's32 weapon',
    'u32 obtaintext',
    'u32 ownertext',
    'u32 inventorytext',
    'u32 inventory2text',
    'u32 pickuptext',
    'struct textoverride* next',
    'struct defaultobj* obj',
]

# objtype 0x26
decl_padlockeddoorobj = [
    'struct obj_header header',
    'struct doorobj* door',
    'struct defaultobj* lock',
    'struct padlockeddoorobj* next',
]

# objtype 0x27
decl_truckobj = [
    'struct defaultobj base',
    'u8* ailist',
    'u16 aioffset',
    's16 aireturnlist',
    'f32 speed',
    'f32 wheelxrot',
    'f32 wheelyrot',
    'f32 speedaim',
    'f32 speedtime60',
    'f32 turnrot60',
    'f32 roty',
    'struct path* path',
    's32 nextstep',
]

# objtype 0x28
decl_helioobj = [
    'struct defaultobj base',
    'u8* ailist',
    'u16 aioffset',
    's16 aireturnlist',
    'f32 rotoryrot',
    'f32 rotoryspeed',
    'f32 rotoryspeedaim',
    'f32 rotoryspeedtime',
    'f32 speed',
    'f32 speedaim',
    'f32 speedtime60',
    'f32 yrot',
    'struct path* path',
    's32 nextstep',
]

# objtype 0x2a
decl_glassobj = [
    'struct defaultobj base',
    's16 portalnum',
    's16 _pad_',
]

# objtype 0x2b
# def read_obj_safeobj(self):
#     self.read('u32', 'unk32')

# objtype 0x2c
decl_safeitemobj = [
    'struct obj_header header',
    'struct defaultobj* item',
    'struct safeobj* safe',
    'struct doorobj* door',
    'struct safeitemobj* next',
]

# objtype 0x2e
decl_cameraposobj = [
    # self.read('s32', 'type')
    # 'struct obj_header header',
    's32 type',
    'f32 x',
    'f32 y',
    'f32 z',
    'f32 theta',
    'f32 verta',
    's32 pad',
]

# objtype 0x2f
decl_tintedglassobj = [
    'struct defaultobj base',
    's16 xludist',
    's16 opadist',
    's16 opacity',
    's16 portalnum',
    'f32 unk64',
]

# objtype 0x30
decl_liftobj = [
    'struct defaultobj base',
    's16 pads[4]',
    'struct doorobj* doors[4]',
    'f32 dist',
    'f32 speed',
    'f32 accel',
    'f32 maxspeed',
    's8 soundtype',
    's8 levelcur',
    's8 levelaim',
    's8 _pad_',
    'struct coord coord',
]

# objtype 0x31
decl_linksceneryobj = [
    'struct obj_header header',
    'struct defaultobj* trigger',
    'struct defaultobj* unexp',
    'struct defaultobj* exp',
    'struct linksceneryobj* next',
]

# objtype 0x32
decl_blockedpathobj = [
    'struct obj_header header',
    'struct defaultobj* blocker',
    's16 waypoint1',
    's16 waypoint2',
    'struct blockedpathobj* next',
]

decl_hov = [
    'u8 type',
    'u8 flags',
    # 's16 _pad_',
    'f32 bobycur',
    'f32 bobytarget',
    'f32 bobyspeed',
    'f32 yrot',
    'f32 bobpitchcur',
    'f32 bobpitchtarget',
    'f32 bobpitchspeed',
    'f32 bobrollcur',
    'f32 bobrolltarget',
    'f32 bobrollspeed',
    'f32 groundpitch',
    'f32 y',
    'f32 ground',
    's32 prevframe60',
    's32 prevgroundframe60',
]

# objtype 0x33
decl_hoverbikeobj = [
    'struct defaultobj base',
    'struct hov hov',
    'f32 speed[2]',
    'f32 prevpos[2]',
    'f32 w',
    'f32 rels[2]',
    'f32 exreal',
    'f32 ezreal',
    'f32 ezreal2',
    'f32 leanspeed',
    'f32 leandiff',
    's32 maxspeedtime240',
    'f32 speedabs[2]',
    'f32 speedrel[2]',
]

# objtype 0x35
decl_hoverpropobj = [
    'struct defaultobj base',
    'struct hov hov',
]

# objtype 0x36
decl_fanobj = [
    'struct defaultobj base',
    'f32 yrot',
    'f32 yrotprev',
    'f32 ymaxspeed',
    'f32 yspeed',
    'f32 yaccel',
    's8 on',
    'u8 pad[3]',
]

# objtype 0x37
decl_hovercarobj = [
    'struct defaultobj base',
    'u8* ailist',
    'u16 aioffset',
    's16 aireturnlist',
    'f32 speed',
    'f32 speedaim',
    'f32 speedtime60',
    'f32 turnyspeed60',
    'f32 turnxspeed60',
    'f32 turnrot60',
    'f32 roty',
    'f32 rotx',
    'f32 rotz',
    'struct path* path',
    's32 nextstep',
    's16 status',
    's16 dead',
    's16 deadtimer60',
    's16 sparkstimer60',
]

# objtype 0x38
decl_padeffectobj = [
    'struct obj_header header',
    's32 effect',
    's32 pad',
]

# objtype 0x39
decl_chopperobj = [
    'struct defaultobj base',
    'u8* ailist',
    'u16 aioffset',
    's16 aireturnlist',
    # 'struct coord coord',
    'f32 speed',
    'f32 speedaim',
    'f32 speedtime60',
    'f32 turnyspeed60',
    'f32 turnxspeed60',
    'f32 turnrot60',
    'f32 roty',
    'f32 rotx',
    'f32 rotz',
    'struct path* path',
    's32 nextstep',
    's16 weaponsarmed',
    's16 ontarget',
    's16 target',
    'u8 attackmode',
    'u8 cw',
    'f32 vx',
    'f32 vy',
    'f32 vz',
    'f32 power',
    'f32 otx',
    'f32 oty',
    'f32 otz',
    'f32 bob',
    'f32 bobstrength',
    'u32 targetvisible',
    's32 timer60',
    's32 patroltimer60',
    'f32 gunturnyspeed60',
    'f32 gunturnxspeed60',
    'f32 gunroty',
    'f32 gunrotx',
    'f32 barrelrotspeed',
    'f32 barrelrot',
    'struct fireslotthing* fireslotthing',
    'u32 dead',
]

# objtype 0x3a
'''
decl_mineobj = [
    'struct defaultobj base',
    's32 _pad_[3]',
]
'''

# objtype 0x3b
decl_escalatorobj = [
    'struct defaultobj base',
    's32 frame',
    'struct coord prevpos',
]

decl_intro_cmd = [
    's32 cmd',
    's32 params[N]',
]

decl_path = [
    's32* pads',
    'u8 id',
    'u8 flags',
    's16 len',
]

decl_ailist = [
    'u8* list',
    's32 id',
]

decl_stagesetup = [
    'struct waypoint *waypoints',
    'struct waygroup *waygroups',
    'void *cover',
    's32 *intro',
    'u32 *props',
    'struct path *paths',
    'struct ailist *ailists',
    's8 *padfiledata',
]

decl_pads = [
    's32 pads[]'
]

setupfile_decls = {
    # objs that need to be referenced by name
    'stagesetup': decl_stagesetup,
    'obj_header': decl_objheader,
    'defaultobj': decl_defaultobj,
    'coord': ['f32 f[3]'],
    'tvscreen': decl_tvscreen,
    'hov': decl_hov,
    'path': decl_path,
    'ailist': decl_ailist,
    'pads': decl_pads,
    'multiammocrateslot': decl_multiammocrateslot,
    0x01: decl_doorobj,
    0x02: decl_doorscaleobj,
    0x03: decl_defaultobj,
    0x04: decl_keyobj,
    0x05: decl_defaultobj,
    0x06: decl_cctvobj,
    0x07: decl_ammocrateobj,
    0x08: decl_weaponobj,
    0x09: decl_packedchr,
    0x0a: decl_singlemonitorobj,
    0x0b: decl_multimonitorobj,
    0x0c: decl_hangingsmonitorobj,
    0x0d: decl_autogunobj,
    0x0e: decl_linkgunsobj,
    0x0f: decl_defaultobj,
    0x11: decl_hatobj,
    0x12: decl_grenadeprobobj,
    0x13: decl_linkliftdoorobj,
    0x14: decl_multiammocrateobj,
    0x15: decl_shieldobj,
    0x16: decl_tag,
    0x17: decl_objective,
    0x18: ['u8 _pad_[4]'],
    0x19: ['u8 cmd0[4]', 'u32 cmd1'],
    0x1a: ['u8 cmd0[4]', 'u32 cmd1'],
    0x1b: ['u8 cmd0[4]', 'u32 cmd1'],
    0x1c: ['u8 cmd0[4]', 'u32 cmd1'],
    0x1d: ['u8 cmd0[4]', 'u32 cmd1'],
    0x1e: decl_criteria_holograph,
    0x1f: ['u8 _pad_[4]'],
    0x20: decl_criteria_roomentered,
    0x21: decl_criteria_throwinroom,
    0x22: ['u8 _pad_[4]'],
    0x23: decl_briefingobj,
    0x24: decl_defaultobj,
    0x25: decl_textoverride,
    0x26: decl_padlockeddoorobj,
    0x27: decl_truckobj,
    0x28: decl_helioobj,
    0x29: decl_defaultobj,
    0x2a: decl_glassobj,
    0x2b: decl_defaultobj,
    0x2c: decl_safeitemobj,
    0x2d: ['u8 _pad_[128]'],
    0x2e: decl_cameraposobj,
    0x2f: decl_tintedglassobj,
    0x30: decl_liftobj,
    0x31: decl_linksceneryobj,
    0x32: decl_blockedpathobj,
    0x33: decl_hoverbikeobj,
    # 0x34: OBJTYPE_END
    0x34: decl_objheader,
    0x35: decl_hoverpropobj,
    0x36: decl_fanobj,
    0x37: decl_hovercarobj,
    0x38: decl_padeffectobj,
    0x39: decl_chopperobj,
    0x3a: decl_weaponobj,
    0x3b: decl_escalatorobj,
}

OBJ_NAMES = {
    0x01: 'doorobj',
    0x02: 'doorscaleobj',
    0x03: 'defaultobj',
    0x04: 'keyobj',
    0x05: 'defaultobj',
    0x06: 'cctvobj',
    0x07: 'ammocrateobj',
    0x08: 'weaponobj',
    0x09: 'packedchr',
    0x0a: 'singlemonitorobj',
    0x0b: 'multimonitorobj',
    0x0c: 'hangingsmonitorobj',
    0x0d: 'autogunobj',
    0x0e: 'linkgunsobj',
    0x0f: 'defaultobj',
    0x11: 'hatobj',
    0x12: 'grenadeprobobj',
    0x13: 'linkliftdoorobj',
    0x14: 'multiammocrateobj',
    0x15: 'shieldobj',
    0x16: 'tag',
    0x17: 'objective',
    0x18: 'type_18',
    0x19: 'type_19',
    0x1a: 'type_1a',
    0x1b: 'type_1b',
    0x1c: 'type_1c',
    0x1d: 'type_1d',
    0x1e: 'criteria_holograph',
    0x1f: 'type_1f',
    0x20: 'criteria_roomentered',
    0x21: 'criteria_throwinroom',
    0x22: 'type_22',
    0x23: 'briefingobj',
    0x24: 'defaultobj',
    0x25: 'textoverride',
    0x26: 'padlockeddoorobj',
    0x27: 'truckobj',
    0x28: 'helioobj',
    0x29: 'defaultobj',
    0x2a: 'glassobj',
    0x2b: 'defaultobj',
    0x2c: 'safeitemobj',
    0x2d: 'type_2d',
    0x2e: 'cameraposobj',
    0x2f: 'tintedglassobj',
    0x30: 'liftobj',
    0x31: 'linksceneryobj',
    0x32: 'blockedpathobj',
    0x33: 'hoverbikeobj',
    0x34: 'END',
    0x35: 'hoverpropobj',
    0x36: 'fanobj',
    0x37: 'hovercarobj',
    0x38: 'padeffectobj',
    0x39: 'chopperobj',
    0x3a: 'weaponobj',
    0x3b: 'escalatorobj',
}