import bpy
from bpy.types import PropertyGroup, Object, Panel, Scene
from bpy.props import StringProperty, IntProperty, PointerProperty, FloatVectorProperty, BoolVectorProperty
from bpy.utils import register_class, unregister_class
from mathutils import Vector, Matrix

import nodes.nodeutils as ndu
import pd_utils as pdu
import tiles_import as tiles
from decl_bgtiles import *

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

classes = [
    PDObject,
    PDObject_Model,
    PDObject_RoomBlock,
    PDObject_Portal,
    PDObject_Tile,
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

    del Scene.pd_room_goto
    del Scene.pd_tile_hilightmode
    del Scene.pd_tilehilight
    del Scene.collections_sel
    del Scene.collections_vis

    for cls in reversed(classes):
        unregister_class(cls)
