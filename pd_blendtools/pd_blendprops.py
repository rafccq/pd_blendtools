import bpy
from bpy.types import PropertyGroup, Object, Panel, Scene
from bpy.props import *
from bpy.utils import register_class, unregister_class
from mathutils import Euler, Vector, Matrix

import nodes.nodeutils as ndu
import pd_utils as pdu
import tiles_import as tiles
import setup_import as stpi
from decl_bgtiles import *
import pd_padsfile as pdp
import pd_mtx as mtx


PD_OBJTYPE_MODEL        = 0x0100
#### BG
PD_OBJTYPE_ROOM         = 0x0200
PD_OBJTYPE_ROOMBLOCK    = 0x0300
PD_OBJTYPE_PORTAL       = 0x0400
PD_OBJTYPE_LIGHT        = 0x0500
PD_OBJTYPE_TILE         = 0x0600
#### Setup
PD_OBJTYPE_PROP         = 0x0700
PD_OBJTYPE_INTRO        = 0x0800

PD_PROP_DOOR            = PD_OBJTYPE_PROP | 0x01
PD_PROP_TINTED_GLASS    = PD_OBJTYPE_PROP | 0x2f
PD_PROP_LIFT            = PD_OBJTYPE_PROP | 0x30
PD_PROP_LIFT_STOP       = PD_OBJTYPE_PROP | 0xf0


class PDObject(PropertyGroup):
    name: StringProperty(name='name', default='', options={'LIBRARY_EDITABLE'})
    type: IntProperty(name='type', default=0, options={'LIBRARY_EDITABLE'})


class PDObject_Model(PropertyGroup):
    idx: IntProperty(name='idx', default=0, options={'LIBRARY_EDITABLE'})
    layer: IntProperty(name='layer', default=0, options={'LIBRARY_EDITABLE'})


# both room and roomblock objects will use this class
class PDObject_RoomBlock(PropertyGroup):
    roomnum: IntProperty(name='roomnum', default=0, options={'LIBRARY_EDITABLE'})

    blocknum: IntProperty(name='blocknum', default=0, options={'LIBRARY_EDITABLE'})
    layer: StringProperty(name='layer', default='', options={'LIBRARY_EDITABLE'})
    blocktype: StringProperty(name='blocktype', default='', options={'LIBRARY_EDITABLE'})
    bsp_position: FloatVectorProperty(name='bsp_position', default=(0,0,0), options={'LIBRARY_EDITABLE'})
    bsp_normal: FloatVectorProperty(name='bsp_normal', default=(1,0,0), options={'LIBRARY_EDITABLE'})


def check_isroom(_scene, obj):
    return pdu.pdtype(obj) == PD_OBJTYPE_ROOM

def check_isportal(_scene, obj):
    return pdu.pdtype(obj) == PD_OBJTYPE_PORTAL

class PDObject_Portal(PropertyGroup):
    room1: PointerProperty(name='room1', type=bpy.types.Object, poll=check_isroom, options={'LIBRARY_EDITABLE'})
    room2: PointerProperty(name='room2', type=bpy.types.Object, poll=check_isroom, options={'LIBRARY_EDITABLE'})


# cycle independent params
TILE_FLOORTYPES = [
    ('Default', 'Default',  0),
    ('Wood', 'Wood',        1),
    ('Stone', 'Stone',      2),
    ('Carpet', 'Carpet',    3),
    ('Metal', 'Metal',      4),
    ('Mud', 'Mud',          5),
    ('Water', 'Water',      6),
    ('Dirt', 'Dirt',        7),
    ('Snow', 'Snow',        8),
]

FLOORTYPES_VALUES = { name.lower(): val for name, _, val in TILE_FLOORTYPES }

TILE_FLAGS = [
    'Floor1',
    'Floor2',
    'Wall',
    'Block Sight',
    'Block Shoot',
    'Lift Floor',
    'Ladder',
    'Rampwall',
    'Slope',
    'Underwater',
    '0400',
    'Aibotcrouch',
    'Aibotduck',
    'Step',
    'Die',
    'Ladder Player Only',
]

TILE_HIGHLIGHT_MODE = [
    ('Floor Color', 'Tile Floor Color',                      0),
    ('Floor Type',  'Highlight Tiles Based On Floor Type',   1),
    ('Uniform',     'Constant Color For All Tiles',          2),
    ('Wall/Floor',  'Highlight Wall or Floor Tiles',         3),
    ('Flags',       'Highlight Tiles Based On Flags',        4),
    ('Room',        'Highlight All Tiles From Room',         5),
]


class PDObject_Tile(PropertyGroup):
    def update_scene_tiles(self, context):
        src = repr(self)
        if src.startswith('bpy.data.objects'):
            if self.room: self.roomnum = self.room.pd_room.roomnum

            scn = context.scene
            mode = scn.pd_tile_hilightmode
            flags = tile_flags(scn.pd_tile_hilight.flags) if mode in ['flags', 'wallfloor'] else None

            if context.active_object:
                tiles.bg_colortile(context.active_object, context, flags, scn.pd_tile_hilight.room)
        elif src.startswith('bpy.data.scenes'):
            numaffected = tiles.bg_colortiles(context)
            msg = f'{numaffected} Tiles Affected'
            bpy.ops.pdtools.messagebox(msg=msg)
            # pd_utils.msg_box('Tiles', f'{numaffected} Tiles Affected')
        else:
            print(f'WARNING: update_flags() unknown source: {src}')


    flags: BoolVectorProperty(name='flags', size=len(TILE_FLAGS), update=update_scene_tiles, options={'LIBRARY_EDITABLE'})
    floorcol: FloatVectorProperty(name='floorcol', subtype='COLOR', size=4, min=0, max=1, update=update_scene_tiles, options={'LIBRARY_EDITABLE'})
    floortype: ndu.make_prop('floortype', {'floortype': TILE_FLOORTYPES}, 'default', update_scene_tiles)
    roomnum: IntProperty(name='roomnum', default=0, options={'LIBRARY_EDITABLE'})
    room: PointerProperty(name='room', update=update_scene_tiles, type=bpy.types.Object, poll=check_isroom, options={'LIBRARY_EDITABLE'})

# ---------------- SETUP OBJECTS ----------------
def update_pad_bbox(self, _context):
    obj = bpy.context.active_object
    if not obj: return

    proptype = obj.pd_obj.type

    if proptype == PD_PROP_DOOR:
        padbbox = pdp.Bbox(*self.pad_bbox)
        bbox = pdp.Bbox(*self.model_bbox)
        sx = (padbbox.ymax - padbbox.ymin) / (bbox.xmax - bbox.xmin)
        sy = (padbbox.zmax - padbbox.zmin) / (bbox.ymax - bbox.ymin)
        sz = (padbbox.xmax - padbbox.xmin) / (bbox.zmax - bbox.zmin)

        if sx <= 0.000001 or sy <= 0.000001 or sz <= 0.000001:
            sx = sy = sz = 1
    else:
        pd_prop = obj.pd_prop
        pad_bbox = pdp.Bbox(*self.pad_bbox)
        model_bbox = pdp.Bbox(*self.model_bbox)
        modelscale = pd_prop.modelscale * pd_prop.extrascale / (256 * 4096)
        sx, sy, sz = stpi.obj_getscale(modelscale, pad_bbox, model_bbox, pd_prop.flags)

    bbox_p = pdp.Bbox(*self.pad_bbox_p)
    bbox = pdp.Bbox(*self.pad_bbox)
    R = mtx.rot_doorinv() if proptype == PD_PROP_DOOR else Matrix()
    center = obj.location

    normal, up, look = mtx.mtx_basis(obj.matrix_world @ R)
    newpos = pdp.pad_pos(center, bbox_p, look, up, normal)
    pad = pdp.Pad(newpos, look, up, normal, bbox, None)
    center = pdp.pad_center(pad)
    normal, up, look = mtx.mtx_basis(obj.matrix_world)
    stpi.obj_setup_mtx(obj, look, up, center)

    self.pad_pos = newpos
    for i, val in enumerate(self.pad_bbox):
        self.pad_bbox_p[i] = val

    obj.scale = (sx, sy, sz)

flags1 = [
    (['Fall'],                  0x00000001),
    (['In Air Rotated 90 Deg Upside-Down'], 0x00000002), # Editor: "In Air Rotated 90 Deg Upside-Down"
    (['Upside Down'],           0x00000004),
    (['In Air'],                0x00000008), # Editor: "In Air"
    (['Scale to Pad Bounds'],   0x00000010), # Editor: "Scale to Pad Bounds"
    (['X To Pad Bounds'],       0x00000020),
    (['Y To Pad Bounds'],       0x00000040),
    (['Z To Pad Bounds'],       0x00000080),
    (['Force Collisions ?'],  0x00000100), # G5 mines, Air Base brown door, AF1 grate and escape door, Defense shuttle, Ruins mines, MBR lift door. Editor suggests "Force Collisions" but this seems wrong
    (['Orthogonal'],            0x00000200),
    (['Ignore Floor Colour'],   0x00000400),
    (['Path Blocker'],          0x00000800), # Glass and explodable scenery which may be blocking a path segment
    (['Ignore Room Colour'],    0x00001000), # Editor: "Absolute Position"
    (['AI Undroppable'],        0x00002000), # AI cannot drop item
    (['Assigned To Chr'],       0x00004000),
    (['Inside Another Obj'],    0x00008000), # Eg. gun inside a crate or suitcase inside a dumpster
    (['Force Mortal'],          0x00010000),
    (['Invincible'],            0x00020000),
    (['Collectable'],           0x00040000),
    (['Thrown Laptop'],         0x00080000),
    (['Uncollectable'],         0x00100000),
    (['Bounce If Shot'],        0x00200000), # Bounce or explode
    (['Force No Bounce'],       0x00400000), # Override the above
    (['Held Rocket'],           0x00800000), # Rocket obj that's currently in an equipped rocket launcher
    (['Embedded Object'],       0x01000000), # Editor: "Embedded Object"
    (['Cannot Activate'],       0x02000000), # Makes it do nothing if player presses B on object. Used mostly for doors.
    (['AI See Through'],        0x04000000), # Glass, glass doors, small objects such as plant pots
    (['Auto Gun 3D Range'],     0x08000000), # Autogun uses 3 dimensions when checking if target is in range
    (['Deactivated', 'Ammo Crate Explode Now', 'Door Has Portal', 'Glass Has Portal', 'Weapon Left Handed', 'Esc Step Z Aligned'], 0x10000000),
    (['Auto Gun Seen Target', 'Camera Disabled', 'Chopper Init', 'Door Open To Front', 'Hover Car Init', 'Hover Prop 20000000', 'Lift Lateral Movement', 'Monitor 20000000', 'Weapon AI Cannot Use'], 0x20000000),
    (['Auto Gun Damaged', 'Camera Bond In View', 'Door Keep Open', 'Hover Bike Moving While Empty', 'Hover Car 40000000', 'Lift Trigger Disable', 'Monitor Render Post BG', 'Weapon No Ammo'], 0x40000000),
    (['80000000', 'Chopper Inactive', 'Door Two Way', 'Hover Car Is Hover Bot', 'Lift Check Ceiling', 'Weapon Can Mix Dual'], 0x80000000),
]

flags2 = [
    (['Immune To Anti'],          0x00000001), # Counter-op cannot damage this object
    (['00000002'],                0x00000002), # Ruins spikes
    (['Skip Door Locked Msg'],    0x00000004),
    (['Dont load in Multiplayer'],0x00000008), # Editor: "Don't load in Multiplayer"
    (['Exclude A'],               0x00000010),
    (['Exclude SA'],              0x00000020),
    (['Exclude PA'],              0x00000040),
    (['Exclude PD'],              0x00000080),
    (['Immobile'],                0x00000100), # Editor: "Immobile"
    (['Mines'],                   0x00000200), # Editor: "Mines"
    (['Linked To Safe'],          0x00000400), # Applied to safe door and item
    (['Interact Check LOS'],      0x00000800), # Check line of sight when attempting to interact with object
    (['Pickup Without LOS'],      0x00001000), # Object can be picked up without having line of sight
    (['Remove When Destroyed'],   0x00002000),
    (['Immune To Gunfire'],       0x00004000),
    (['Shoot Through'],           0x00008000),
    (['Draw On Top'],             0x00010000),
    (['00020000'],                0x00020000), # G5 mine, Air Base mine
    (['00040000'],                0x00040000), # Only used in CI training
    (['Invisible'],               0x00080000),
    (['Bulletproof'],             0x00100000), # Only magnum and FarSight can shoot through it
    (['Immune to Explosions'],    0x00200000), # Editor: "Immune to Explosions" (Ruins spikes)
    (['Exclude 2P'],              0x00400000),
    (['Exclude 3P'],              0x00800000),
    (['Exclude 4P'],              0x01000000),
    (['Throw Through'],           0x02000000), # Rockets/mines/grenades etc pass through object
    (['Gravity ?'],             0x04000000), # Used quite a lot - gravity?
    (['Locked Front'],            0x08000000), # One-way door lock
    (['Locked Back'],             0x10000000), # One-way door lock
    (['AI Cannot Use', 'Auto Gun Malfunctioning 2'], 0x20000000),
    (['Airlock Door', 'Auto Gun 40000000'], 0x40000000),
    (['Attack Ship Glass', 'Auto Gun Malfunctioning 1', 'Weapon Huge Exp'], 0x80000000),
]

flags3 = [
    (['Grabbable'],             0x00000002),
    (['Door Sticky'],           0x00000004), # eg. Skedar Ruins
    (['00000008'],              0x00000008), # Not used in scripts
    (['00000010'],              0x00000010), # Used heaps
    (['Auto Cutscene Sounds'],  0x00000020), # For doors and objs - play default open/close noises
    (['R Tracked Yellow'],      0x00000040),
    (['Can Hard Free'],         0x00000080), # Can free prop while on screen (MP weapons only)
    (['Hard Freeing'],          0x00000100),
    (['00000200'],              0x00000200), # Not used in scripts
    (['Walk Through'],          0x00000400),
    (['R Tracked Blue'],        0x00000800),
    (['Show Shield'],           0x00001000), # Show shield effect around object (always)
    (['HTM Terminal'],          0x00002000), # Terminal for Hacker Central scenario (HTM = Hack That Mac)
    (['Is Fetch Target'],       0x00004000), # AI bot is fetching this obj
    (['React To Sight'],        0x00008000), # Turn sight blue or red when targeted with R
    (['Interactable'],          0x00010000),
    (['Shield Hit'],            0x00020000), # Turns off when shield no longer visible
    (['Render Post BG'],        0x00040000),
    (['Draw On Top'],           0x00080000),
    (['Hover Bed Shield'],      0x00100000),
    (['Interact Short Range'],  0x00200000),
    (['Player Undroppable'],    0x00400000), # Player does not drop item when dead
    (['Long Push Range'],       0x00800000), # Not used in scripts
    (['Push Freely'],           0x01000000), # Not used in scripts
    (['Geo Cyl'],               0x02000000), # Use cylinder geometry rather than block
    (['04000000'],              0x04000000), # Not used in scripts
    (['08000000'],              0x08000000), # Not used in scripts
    (['Keep Collisions After Fully Destroyed'], 0x10000000), # Editor: "Keep Collisions After Fully Destroyed"
    (['On Shelf'],              0x20000000), # Obj is on a shelf - use bigger pickup range for Small Jo and Play as Elvis cheats and skip line of sight checks
    (['Infrared'],              0x40000000), # Obj is highlighted on IR scanner
    (['80000000'],              0x80000000), # Not used in scripts
]

class PDObject_SetupBaseObject(PropertyGroup):
    def update_flag(self, prop, propname, flags):
        flagsval = 0
        for i, f in enumerate(prop): flagsval |= flags[i][1] if f else 0
        self[f'{propname}_packed'] = f'{flagsval:08X}'

    def update_flag1(self, context):
        self.update_flag(self.flags1, 'flags1', flags1)

    def update_flag2(self, context):
        self.update_flag(self.flags2, 'flags2', flags2)

    def update_flag3(self, context):
        self.update_flag(self.flags3, 'flags3', flags3)

    def update_flagpacked(self, context):
        def update_array(array, flags):
            f = int(f'0x{flags}', 16)
            n = len(array)
            for i in range(n):
                array[i] = f & 1
                f >>= 1

        update_array(self.flags1, self.flags1_packed)
        update_array(self.flags2, self.flags2_packed)
        update_array(self.flags3, self.flags3_packed)

    extrascale: IntProperty(name='extrascale', default=0, options={'LIBRARY_EDITABLE'})
    maxdamage: IntProperty(name='maxdamage', default=0, options={'LIBRARY_EDITABLE'})

    flags1: BoolVectorProperty(name="Flags1", size=len(flags1), default=(False,) * len(flags1), update=update_flag1)
    flags2: BoolVectorProperty(name="Flags2", size=len(flags2), default=(False,) * len(flags2), update=update_flag2)
    flags3: BoolVectorProperty(name="Flags3", size=len(flags3), default=(False,) * len(flags3), update=update_flag3)

    flags1_packed: StringProperty(name="Flags1_packed", update=update_flagpacked)
    flags2_packed: StringProperty(name="Flags2_packed", update=update_flagpacked)
    flags3_packed: StringProperty(name="Flags3_packed", update=update_flagpacked)

    padnum: IntProperty(name='padnum', default=0, options={'LIBRARY_EDITABLE'})
    pad_pos: FloatVectorProperty(name='pad_pos', default=(0,0,0), size=3, options={'LIBRARY_EDITABLE'})
    # we need to save the "previous" (before it was changed) bbox, in order to derive
    # the original position/center of the new one
    pad_bbox: FloatVectorProperty(name='pad_bbox', default=(0,0,0,0,0,0), size=6, update=update_pad_bbox, options={'LIBRARY_EDITABLE'})
    pad_bbox_p: FloatVectorProperty(name='pad_bbox_p', default=(0,0,0,0,0,0), size=6, options={'LIBRARY_EDITABLE'})
    model_bbox: FloatVectorProperty(name='pad_bbox', default=(0,0,0,0,0,0), size=6, options={'LIBRARY_EDITABLE'})
    modelscale: FloatProperty(name='modelscale', min=0, default=0, options={'LIBRARY_EDITABLE'})


def check_isdoor(_scene, obj):
    return obj.pd_obj.type == PD_PROP_DOOR


DOOR_FLAGS = [
    ('DOORFLAG_0001',       0x0001),
    ('Windowed',            0x0002),
    ('DOORFLAG_0004',       0x0004),
    ('Flip',                0x0008),
    ('Automatic',           0x0010),
    ('DOORFLAG_0020',       0x0020),
    ('Rotated Pad',         0x0040),
    ('DOORFLAG_0080',       0x0080),
    ('DOORFLAG_0100',       0x0100),
    ('Long Range',          0x0200),
    ('Damage On Contact',   0x0400),
    ('Unblockable Open',    0x0800),
    ('DOORFLAG_4000',       0x4000),
]

DOOR_KEYFLAGS = [
    ('10000000', 0x80),
    ('01000000', 0x40),
    ('00100000', 0x20),
    ('00010000', 0x10),
    ('00001000', 0x08),
    ('00000100', 0x04),
    ('00000010', 0x02),
    ('00000001', 0x01),
]

DOORTYPES = [
    ('Sliding',     'Sliding', 0x0),
    ('Flexi1',      'Bunker Flexi Door (GE Only)', 0x1),
    ('Flexi2',      'Bunker Flexi Door (GE Only)', 0x2),
    ('Flexi3',      'Bunker Flexi Door (GE Only)', 0x3),
    ('Vertical',    'Vertical', 0x4),
    ('Swinging',    'Swinging', 0x5),
    ('Eye',         'Caverns (GE Only)', 0x6),
    ('Iris',        'Caverns (GE Only)', 0x7),
    ('Fallaway',    'Surface Grate And Train Floor Panel (GE Only)', 0x8),
    ('Aztec Chair', 'Aztec Door Effect', 0x9),
    ('Hull',        'Attack Ship Windows', 0xa),
    ('Laser',       'Lase Beam/Barricade', 0xb),
]

DOOR_SOUNDTYPES = [
    ('00 None',                'None',                 0x00),
    ('01 Electronic',          'Electronic',           0x01),
    ('02 Target SFX',          'Target SFX',           0x02),
    ('03 Hydraulic 1',         'Hydraulic 1',          0x03),
    ('04 Skedar Ruins',        'Skedar Ruins',         0x04),
    ('05 Skedar Elevator',     'Skedar Elevator',      0x05),
    ('06 Wooden',              'Wooden',               0x06),
    ('07 Target SFX',          'Target SFX',           0x07),
    ('08 Sliding 1',           'Sliding 1',            0x08),
    ('09 Wooden (Target SFX)', 'Wooden (Target SFX)',  0x09),
    ('0A Roller',              'Roller',               0x0a),
    ('0B Metal',               'Metal',                0x0b),
    ('0C Target SFX/Latch',    'Target SFX/Latch',     0x0c),
    ('0D Locker',              'Locker',               0x0d),
    ('0E Target SFX',          'Target SFX',           0x0e),
    ('0F Automatic 1',         'Automatic 1',          0x0f),
    ('10 Stone',               'Stone',                0x10),
    ('11 Automatic 2',         'Automatic 2',          0x11),
    ('12 Elevator',            'Elevator',             0x12),
    ('13 Lift 1',              'Lift 1',               0x13),
    ('14 Lift 2',              'Lift 2',               0x14),
    ('15 Lift 3',              'Lift 3',               0x15),
    ('16 Lift 4',              'Lift 4',               0x16),
    ('17 Hydraulic 2',         'Hydraulic 2',          0x17),
    ('18 Blast Door',          'Blast Door',           0x18),
    ('19 Automatic 1',         'Automatic 1',          0x19),
    ('1A Lift 5',              'Lift 5',               0x1a),
    ('1B Lift 6',              'Lift 6',               0x1b),
    ('1C Sliding 2',           'Sliding 2',            0x1c),
    ('1D Skedar Ship',         'Skedar Ship',          0x1d),
    ('1E Blast Door (Alt)',    'Blast Door (Alt)',     0x1e),
    ('1F Lift 7',              'Lift 7',               0x1f),
    ('20 Lift 8',              'Lift 8',               0x20),
    ('21 None',                'None',                 0x21),
]


class PDObject_SetupDoor(PropertyGroup):
    def update_doorflags(self, context):
        src = repr(self)

    door_type: ndu.make_prop('door_type', {'door_type': DOORTYPES}, 'sliding', None)
    sound_type: ndu.make_prop('sound_type', {'sound_type': DOOR_SOUNDTYPES}, '00none', None)

    maxfrac: FloatProperty(name='maxfrac', min=0, default=0, options={'LIBRARY_EDITABLE'})
    perimfrac: FloatProperty(name='perimfrac', min=0, default=0, options={'LIBRARY_EDITABLE'})
    accel: FloatProperty(name='accel', min=0, default=0, options={'LIBRARY_EDITABLE'})
    decel: FloatProperty(name='decel', min=0, default=0, options={'LIBRARY_EDITABLE'})
    maxspeed: FloatProperty(name='maxspeed', min=0, default=0, options={'LIBRARY_EDITABLE'})
    autoclosetime: FloatProperty(name='autoclosetime', min=0, default=0, description='Time To Open (In ms)', options={'LIBRARY_EDITABLE'})

    door_flags: BoolVectorProperty(name='door_flags', size=len(DOOR_FLAGS), options={'LIBRARY_EDITABLE'})
    key_flags: BoolVectorProperty(name='key_flags', size=len(DOOR_KEYFLAGS), options={'LIBRARY_EDITABLE'})

    sibling: PointerProperty(name='sibling', type=bpy.types.Object, poll=check_isdoor, options={'LIBRARY_EDITABLE'})
    laserfade: IntProperty(name='laserfade', min=0, max=255, default=0, description='Laser Opacity', options={'LIBRARY_EDITABLE'})


class PDObject_SetupTintedGlass(PropertyGroup):
    opadist: FloatProperty(name='opadist', default=0, options={'LIBRARY_EDITABLE'})
    xludist: FloatProperty(name='xludist', default=0, options={'LIBRARY_EDITABLE'})


class PDObject_SetupInterlinkObject(PropertyGroup):
    name: StringProperty(name='name', options={'LIBRARY_EDITABLE'})
    controller: PointerProperty(name='controller', type=bpy.types.Object, options={'LIBRARY_EDITABLE'})
    controlled: PointerProperty(name='controlled', type=bpy.types.Object, options={'LIBRARY_EDITABLE'})
    stopnum: IntProperty(name='lift_stop', default=0, min=1, max=4, options={'LIBRARY_EDITABLE'})


def check_is_elevstop(_scene, obj):
    return obj and obj.pd_obj.type == PD_PROP_LIFT_STOP


class PDObject_SetupLift(PropertyGroup):
    sound: IntProperty(name='sound', default=0x16, min=0, max=0x3f, options={'LIBRARY_EDITABLE'})
    door1: PointerProperty(name='door1', type=Object, poll=check_isdoor, options={'LIBRARY_EDITABLE'})
    door2: PointerProperty(name='door2', type=Object, poll=check_isdoor, options={'LIBRARY_EDITABLE'})
    door3: PointerProperty(name='door3', type=Object, poll=check_isdoor, options={'LIBRARY_EDITABLE'})
    door4: PointerProperty(name='door4', type=Object, poll=check_isdoor, options={'LIBRARY_EDITABLE'})
    stop1: PointerProperty(name='stop1', type=Object, poll=check_is_elevstop, options={'LIBRARY_EDITABLE'})
    stop2: PointerProperty(name='stop2', type=Object, poll=check_is_elevstop, options={'LIBRARY_EDITABLE'})
    stop3: PointerProperty(name='stop3', type=Object, poll=check_is_elevstop, options={'LIBRARY_EDITABLE'})
    stop4: PointerProperty(name='stop4', type=Object, poll=check_is_elevstop, options={'LIBRARY_EDITABLE'})
    accel: FloatProperty(name='accel', default=0, options={'LIBRARY_EDITABLE'})
    maxspeed: FloatProperty(name='maxspeed', default=0, options={'LIBRARY_EDITABLE'})
    interlinks: CollectionProperty(name='interlinks', type=PDObject_SetupInterlinkObject)
    active_interlink_idx: IntProperty(name='active_interlink_idx', default=0, options={'LIBRARY_EDITABLE'})


classes = [
    PDObject,
    PDObject_Model,
    PDObject_RoomBlock,
    PDObject_Portal,
    PDObject_Tile,
    PDObject_SetupBaseObject,
    PDObject_SetupDoor,
    PDObject_SetupTintedGlass,
    PDObject_SetupInterlinkObject,
    PDObject_SetupLift,
]

PD_COLLECTIONS = [
    'Rooms',
    'Portals',
    'Tiles',
    'Props',
    'Intro',
]

def update_scene_vis(self, context):
    for idx, name in enumerate(PD_COLLECTIONS):
        coll = bpy.data.collections[name]
        coll.hide_viewport = not context.scene.collections_vis[idx]

def update_scene_sel(self, context):
    for idx, name in enumerate(PD_COLLECTIONS):
        coll = bpy.data.collections[name]
        coll.hide_select = not context.scene.collections_sel[idx]

def update_scene_tilehighlight(_self, context):
    n = tiles.bg_colortiles(context)
    bpy.ops.pdtools.messagebox(msg=f'{n} Tiles Affected')
    # pd_utils.msg_box(f'{n} Tiles Affected')

def update_scene_roomgoto(self, _context):
    area = next(area for area in bpy.context.screen.areas if area.type == 'VIEW_3D')
    space = next(space for space in area.spaces if space.type == 'VIEW_3D')
    region = space.region_3d
    room = self.pd_room_goto
    V = region.view_matrix
    look = Vector([V[2][i] for i in range(3)])
    region.view_location = room.location - look * region.view_distance

def register():
    for cls in classes:
        register_class(cls)

    Object.pd_obj = bpy.props.PointerProperty(type=PDObject)
    Object.pd_model = bpy.props.PointerProperty(type=PDObject_Model)
    Object.pd_room = bpy.props.PointerProperty(type=PDObject_RoomBlock)
    Object.pd_portal = bpy.props.PointerProperty(type=PDObject_Portal)
    Object.pd_tile = bpy.props.PointerProperty(type=PDObject_Tile)

    # setup props
    Object.pd_prop = bpy.props.PointerProperty(type=PDObject_SetupBaseObject)
    Object.pd_door = bpy.props.PointerProperty(type=PDObject_SetupDoor)
    Object.pd_tintedglass = bpy.props.PointerProperty(type=PDObject_SetupTintedGlass)
    Object.pd_lift = bpy.props.PointerProperty(type=PDObject_SetupLift)

    n_coll = len(PD_COLLECTIONS)
    Scene.collections_vis = BoolVectorProperty(name='collections_vis', size=n_coll, default=[1]*n_coll, update=update_scene_vis, options={'LIBRARY_EDITABLE'})
    Scene.collections_sel = BoolVectorProperty(name='collections_sel', size=n_coll, default=[1]*n_coll, update=update_scene_sel, options={'LIBRARY_EDITABLE'})
    Scene.pd_tile_hilight = bpy.props.PointerProperty(type=PDObject_Tile)
    Scene.pd_tile_hilightmode = ndu.make_prop('pd_tile_hilightmode', {'pd_tile_hilightmode': TILE_HIGHLIGHT_MODE}, 'floorcolor', update_scene_tilehighlight)
    Scene.pd_room_goto = bpy.props.PointerProperty(type=bpy.types.Object, update=update_scene_roomgoto, poll=check_isroom)
    Scene.pd_portal = bpy.props.PointerProperty(type=bpy.types.Object, poll=check_isportal)
    Scene.flags_filter = StringProperty(name="Flags Filter", default='', options={'TEXTEDIT_UPDATE'})
    Scene.flags_toggle = BoolProperty(name="Flags Toggle", default=False, description='Show Flags As Toggle/Checkbox')


def unregister():
    del Object.pd_tile
    del Object.pd_portal
    del Object.pd_room
    del Object.pd_model
    del Object.pd_obj
    del Object.pd_prop
    del Object.pd_door
    del Object.pd_tintedglass
    del Object.pd_lift

    del Scene.pd_room_goto
    del Scene.pd_tile_hilightmode
    del Scene.pd_tilehilight
    del Scene.collections_sel
    del Scene.collections_vis

    for cls in reversed(classes):
        unregister_class(cls)
