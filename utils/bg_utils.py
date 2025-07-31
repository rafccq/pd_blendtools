import struct
import math

import bpy
from mathutils import Vector, Matrix
import bmesh

from . import pd_utils as pdu
from materials import pd_materials as pdm
import pd_blendprops as pdprops
import pd_mtx as mtx


as_u32 = lambda f: struct.unpack('>I', struct.pack('>f', f))[0]
as_u16 = lambda f: struct.unpack('>H', struct.pack('>e', f))[0]
ident = lambda e: e
coord_as_u32 = lambda coord, f=ident: (as_u32(f(coord.x)), as_u32(f(coord.y)), as_u32(f(coord.z)))


class Bbox:
    MAX = 2**16 - 1
    MIN = -(MAX+1)

    def __init__(self, xmin=MAX, xmax=MIN, ymin=MAX, ymax=MIN, zmin=MAX, zmax=MIN):
        self.xmin = xmin
        self.xmax = xmax
        self.ymin = ymin
        self.ymax = ymax
        self.zmin = zmin
        self.zmax = zmax

    def update(self, p):
        if p.x < self.xmin: self.xmin = p.x
        elif p.x > self.xmax: self.xmax = p.x

        if p.y < self.ymin: self.ymin = p.y
        elif p.y > self.ymax: self.ymax = p.y

        if p.z < self.zmin: self.zmin = p.z
        elif p.z > self.zmax: self.zmax = p.z

def obj_get_child_meshes(obj):
    children = [c for c in obj.children]

    meshes = []
    while children:
        child = children.pop(0)
        children += [c for c in child.children]

        if child.data:
            meshes.append(child.data)

    return meshes

def closest_face(pos, mesh, M):
    mindist = 2 ** 32
    for face in mesh.polygons:
        c = M @ face.center
        dist = (c - pos).length
        if dist < mindist: mindist = dist

    return mindist

def portal_find_rooms(bl_portal):
    c = pdu.verts_median(bl_portal.data.vertices)
    rooms = bpy.context.scene['rooms'].values()
    rooms_dist = []
    for bl_room in rooms:
        dist = (c - bl_room.location).length
        rooms_dist.append((bl_room, dist))

    rooms_dist.sort(key=lambda e: e[1])

    candidates = rooms_dist[:8]
    closests = []
    for room_dist in candidates:
        room = room_dist[0]
        meshes = obj_get_child_meshes(room)
        mindist = 2 ** 32
        for mesh in meshes:
            dist = closest_face(c, mesh, room.matrix_world)
            if dist < mindist: mindist = dist
        closests.append((room, mindist))

    closests.sort(key=lambda e: e[1])

    if not closests:
        print('WARNING no rooms')
        return None

    if len(closests) < 2:
        print('WARNING not enough rooms')
        return closests[0][0], None

    res = closests[0][0], closests[1][0]

    room1pos = closests[0][0].location
    d = room1pos - c
    normal = bl_portal.data.polygons[0].normal

    # first room is always the one behind the portal
    if normal.dot(d) > 0:
        res = closests[1][0], closests[0][0]

    return res

def parent_room(bl_roomblock):
    if pdu.pdtype(bl_roomblock) != pdprops.PD_OBJTYPE_ROOMBLOCK: return None

    bl_obj = bl_roomblock
    while bl_obj:
        if pdu.pdtype(bl_obj) == pdprops.PD_OBJTYPE_ROOM: return bl_obj
        bl_obj = bl_obj.parent

    return None

def init_portal(bl_portal, name):
    bl_portal.show_wire = True
    portalmat = pdm.portal_material()
    bl_portal.color = (0, 0.8, 0.8, 0)
    bl_portal.data.materials.append(portalmat)
    pdu.add_to_collection(bl_portal, 'Portals')
    bl_portal.pd_obj.name = name
    bl_portal.pd_obj.type = pdprops.PD_OBJTYPE_PORTAL

def new_room_with_block(bl_roomblock, layer, context):
    scn = context.scene
    roomnum = len(scn['rooms']) + 1
    bl_roomblock.name = f'block 0 ({layer}) R{roomnum:02X}'

    bl_room = pdu.new_obj(f'Room_{roomnum:02X}', link=False, dsize=0.0001)
    bl_room.pd_obj.name = bl_room.name
    bl_room.pd_obj.type = pdprops.PD_OBJTYPE_ROOM
    bl_room.pd_room.roomnum = roomnum
    pdu.add_to_collection(bl_room, 'Rooms')
    bl_roomblock.parent = bl_room

    scn['rooms'][str(roomnum)] = bl_room
    return bl_room

def new_room_from_selection(context):
    # must be in edit mode
    bl_roomblocksrc = context.edit_object
    bl_roomsrc = parent_room(bl_roomblocksrc)

    bpy.ops.mesh.separate(type='SELECTED')
    bpy.ops.object.mode_set(mode='OBJECT')

    # get the newly created object, which will be a roomblock
    bl_roomblock_new = context.selected_objects[-1]

    # reposition vertices
    verts = bl_roomblock_new.data.vertices
    center = pdu.verts_median(verts)
    for v in verts:
        v.co -= center

    bl_room = new_room_with_block(bl_roomblock_new, 'opa', context)
    # to blender coords
    R = bl_roomsrc.matrix_world.to_3x3()
    bl_room.matrix_world = R @ bl_room.matrix_world
    bl_room.matrix_world.translation = bl_roomsrc.location + R @ center

    # set the new roomblock as the only selection and enter edit mode
    # bpy.ops.object.select_all(action='DESELECT')
    # bpy.context.view_layer.objects.active = bl_roomblock_new
    # bpy.ops.object.mode_set(mode='EDIT')

# repositions the mesh to its median point, and make the verts relative to it
def center_mesh(bl_obj):
    verts = bl_obj.data.vertices
    center = pdu.verts_median(verts)
    for v in verts:
        v.co -= center
    bl_obj.matrix_world.translation = center

def new_room(roomnum, pos=None):
    bl_room = pdu.new_obj(f'Room_{roomnum:02X}', link=False, dsize=0.0001)

    bl_room.pd_obj.name = bl_room.name
    bl_room.pd_obj.type = pdprops.PD_OBJTYPE_ROOM
    bl_room.pd_room.roomnum = roomnum
    bl_room.pd_room.room = bl_room

    pdu.add_to_collection(bl_room, 'Rooms')
    bl_room.matrix_world.translation = pos if pos else (0, 0, 0)

    scn = bpy.context.scene
    scn['rooms'][str(roomnum)] = bl_room

    return bl_room

def get_numrooms():
    coll = bpy.data.collections['Rooms']
    nrooms = 0
    for bl_obj in coll.objects:
        if pdu.pdtype(bl_obj) != pdprops.PD_OBJTYPE_ROOM: continue
        nrooms += 1
    return nrooms

def check_normals(faces):
    if not faces:
        return 'No Selection'

    normal0 = faces[0].normal
    for f in faces:
        d = f.normal - normal0
        if d.length > 0.0001:
            return 'Invalid Selection: All Faces Must Have The Same Normal'

    return None

def new_portal_from_faces(context):
    sel_mode = context.tool_settings.mesh_select_mode
    sel = ''.join(['1' if s else '0' for s in sel_mode])
    if sel != '001':
        return 'Invalid Selection Mode: Faces Must Be Selected'

    bl_obj = context.edit_object
    bm = bmesh.from_edit_mesh(bl_obj.data)

    faces_sel = [f for f in bm.faces if f.select]
    res = check_normals(faces_sel)
    if res:
        print(res)
        return res

    bpy.ops.mesh.separate(type='SELECTED')
    bpy.ops.mesh.delete(type='FACE')

    bpy.ops.object.mode_set(mode='OBJECT')

    bl_portal = context.selected_objects[-1]
    coll_portals = bpy.data.collections['Portals']
    n = len(coll_portals.objects) + 1
    name = f'portal_{n:02X}'
    bl_portal.name = name

    room = None
    if pdu.pdtype(bl_obj) == pdprops.PD_OBJTYPE_ROOMBLOCK:
        room = parent_room(bl_obj)
        roomnum = room.pd_room.roomnum
        bl_portal.name += f'({roomnum:02X})'
        bl_portal.pd_portal.room1 = room

    # remove from the collection it was added to, to avoid ending up in 2 collections
    coll = bl_obj.users_collection[0]
    coll.objects.unlink(bl_portal)
    bl_portal.parent = None

    bpy.ops.object.select_all(action='DESELECT')

    init_portal(bl_portal, name)
    bpy.context.view_layer.objects.active = bl_portal

    verts = bl_portal.data.vertices
    center = pdu.verts_median(verts)
    for v in verts:
        v.co -= center

    # to blender coords
    parent = room if room else bl_obj
    R = parent.matrix_world.copy()
    R.translation = (0,0,0)
    bl_portal.matrix_world.translation = parent.location + R @ center

def portal_verts_from_edge(edge, M, width, height, elevation, pitch, direction):
    e_v0 = M @ edge.verts[0].co.copy()
    e_v1 = M @ edge.verts[1].co.copy()

    w, h = width * 0.5, height

    elv = math.radians(elevation)
    sin_e, cos_e = math.sin(elv), math.cos(elv)

    pitch = math.radians(pitch)
    sin_p, cos_p = math.sin(pitch), math.cos(pitch)

    dir_h = (e_v1 - e_v0).normalized()
    dir_v = Vector((0, 0, 1)) if direction == 'vertical' else Vector((0, 1, 0))
    dir_n = dir_h.cross(dir_v)

    mid = (e_v0 + e_v1) * 0.5

    v0 = mid - dir_h * cos_e * w - dir_v * sin_e * w
    v1 = mid + dir_h * cos_e * w + dir_v * sin_e * w
    v2 = v1 + dir_v * cos_p * h + dir_n * sin_p * h
    v3 = v0 + dir_v * cos_p * h + dir_n * sin_p * h

    return [v0, v1, v2, v3]

def new_portal_from_verts(bl_obj, verts):
    center = pdu.points_median(verts)

    for v in verts: v -= center

    portalmesh = pdu.mesh_from_verts(verts, triangulate=False)
    lib = bpy.data.collections
    num = len(lib['Portals'].objects) if 'Portals' in lib else 0
    name = f'Portal_{num:02X}'
    bl_portal = bpy.data.objects.new(name, portalmesh)
    init_portal(bl_portal, name)

    if pdu.pdtype(bl_obj) == pdprops.PD_OBJTYPE_ROOMBLOCK:
        bl_obj = parent_room(bl_obj)
        roomnum = bl_obj.pd_room.roomnum
        bl_portal.name += f'({roomnum:02X})'
        bl_portal.pd_portal.room1 = bl_obj

    bl_portal.location = center

def select(verts):
    for v in verts:
        v.select = True

def room_split_by_portal(bl_roomblock, bl_portal, context):
    normal = bl_portal.data.polygons[0].normal
    verts = bl_portal.data.vertices
    c = pdu.verts_median(verts)
    portal_pos = c + bl_portal.location
    bl_roomblock_new, _ = mesh_split(bl_roomblock, portal_pos, normal, context)

    # adjust the vertices so they're centered around the median
    verts = bl_roomblock_new.data.vertices
    center = pdu.verts_median(verts)
    for v in verts:
        v.co -= center

    bl_room = parent_room(bl_roomblock)
    bl_room_new = new_room_with_block(bl_roomblock_new, 'opa', context)

    # position the new room at room.pos(global) + block.pos(local)
    R = bl_room.matrix_world.copy()
    bl_room_new.matrix_world = R
    R.translation = (0,0,0)
    bl_room_new.matrix_world.translation = bl_room.location + R @ center

    # update the portal with the new room
    d = bl_room_new.location - portal_pos

    pd_portal = bl_portal.pd_portal
    if normal.dot(d) < 0: # room is behind the portal
        pd_portal.room1 = bl_room_new
    else:
        pd_portal.room2 = bl_room_new

    return bl_roomblock_new

# bisects the mesh at the specified position/normal
# returns the vertices along the bisection plane
def mesh_split(obj, pos, normal, context):
    meshdata = obj.data
    savedmode = context.object.mode
    bpy.ops.object.mode_set(mode='EDIT')
    context.tool_settings.mesh_select_mode = (True, True, True)
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.bisect(plane_co=pos, plane_no=normal, use_fill=False,
                        clear_inner=False, clear_outer=False)

    bpy.ops.mesh.select_all(action='DESELECT')
    bm = bmesh.from_edit_mesh(meshdata)
    bm.faces.ensure_lookup_table()
    bm.verts.ensure_lookup_table()

    M = obj.matrix_world
    front, back, along = [], [], []
    for v in bm.verts:
        vp = (pos - M @ v.co).normalized()
        dot = vp.dot(normal)

        zero = abs(dot) < 0.0001

        if dot < 0 or zero:
            front.append(v)
        if dot > 0 or zero:
            back.append(v)
        if zero:
            along.append(v)

    select(back)

    bm.select_mode = {'VERT', 'EDGE', 'FACE'}
    bm.select_flush_mode()

    bpy.ops.mesh.separate(type='SELECTED')
    bpy.ops.object.mode_set(mode=savedmode)
    new_obj = context.selected_objects[-1]

    bm.free()
    return new_obj, along

def dissolve_colinear_verts(obj):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.faces.ensure_lookup_table()
    bm.edges.ensure_lookup_table()
    bm.verts.ensure_lookup_table()

    face = bm.faces[0]
    to_dissolve = []
    prev = None
    for loop in face.loops:
        e = loop.edge
        tangent = e.calc_tangent(loop)

        if tangent == prev:
            to_dissolve.append(e)

        prev = tangent

    for e in to_dissolve:
        res = bmesh.utils.vert_dissolve(e.verts[0])
        if not res:
            print(f'WARNING: Unable to dissolve vert: {e.verts[0].index} edge: {e} obj: {obj}')

    bm.to_mesh(obj.data)
    bm.free()

def tile_from_face(name, bl_obj, face):
    M = bl_obj.matrix_world
    verts = [M @ v.co for v in face.verts]
    center = pdu.points_median(verts)

    for v in verts:
        v -= center

    tilemesh = pdu.mesh_from_verts(verts, name, triangulate=False)
    bl_tileobj = bpy.data.objects.new(f'{name}', tilemesh)
    dissolve_colinear_verts(bl_tileobj)
    bl_tileobj.show_wire = True
    bl_tileobj.location = center
    pdu.add_to_collection(bl_tileobj, 'Tiles')
    bl_tileobj.pd_obj.type = pdprops.PD_OBJTYPE_TILE
    return bl_tileobj

def blockname(roomnum, blockidx, blocktype, layer):
    bsp = ' (BSP)' if blocktype == 'BSP' else ''
    return f'block {blockidx} ({layer}){bsp} R{roomnum:02X}'

def roomblock_set_props(bl_roomblock, roomnum, bl_room, blocknum, layer, blocktype, bsp_pos=None, bsp_norm=None):
    bl_roomblock.pd_obj.name = f'block {blocknum}'
    bl_roomblock.pd_obj.type = pdprops.PD_OBJTYPE_ROOMBLOCK

    bl_roomblock.pd_room.blocknum = blocknum
    bl_roomblock.pd_room.roomnum = roomnum
    bl_roomblock.pd_room.room = bl_room
    bl_roomblock.pd_room.layer = layer
    bl_roomblock.pd_room.blocktype = blocktype

    # we need to set the block as active so the function get_blockparent_items can grab it
    bpy.context.view_layer.objects.active = bl_roomblock
    bl_roomblock.pd_room.parent_enum = bl_roomblock.parent.name

    if bsp_pos:
        R = mtx.rot_blender()
        bl_roomblock.pd_room.bsp_pos = R @ Vector(bsp_pos)
        bl_roomblock.pd_room.bsp_normal = R @ Vector(bsp_norm)

def roomblock_changelayer(bl_roomblock, layer):
    bl_roomblock.pd_room.layer = layer

    blocks = [b for b in bl_roomblock.children]
    for block in blocks: blocks += [b for b in block.children]

    for block in blocks: block.pd_room.layer = layer

# returns a list of the vertices in this mesh, in world space
def verts_world(bl_obj, M = Matrix.Identity(4), conv = lambda e: e):
    pos = bl_obj.matrix_world.translation
    verts = []

    for v in bl_obj.data.vertices:
        vt = M @ (pos + v.co)
        vt.x, vt.y, vt.z = conv(vt.x), conv(vt.y), conv(vt.z)
        verts.append(vt)

    return verts

def get_bbox(verts):
    bbox = Bbox()
    for v in verts:
        bbox.update(v)
    return bbox
