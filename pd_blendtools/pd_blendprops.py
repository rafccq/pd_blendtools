import bpy
from bpy.types import PropertyGroup, Object, Panel, Scene
from bpy.props import (
    StringProperty, IntProperty, PointerProperty, FloatVectorProperty,
    BoolVectorProperty, FloatProperty, CollectionProperty
)
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


class PDObject_SetupBaseObject(PropertyGroup):
    extrascale: IntProperty(name='extrascale', default=0, options={'LIBRARY_EDITABLE'})
    health: IntProperty(name='health', default=0, options={'LIBRARY_EDITABLE'})
    flags: IntProperty(name='flags', default=0, options={'LIBRARY_EDITABLE'})
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
