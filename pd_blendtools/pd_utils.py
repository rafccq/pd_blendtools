import zlib
import os
import json
from functools import cache
from pathlib import Path
from glob import glob
import struct

import bpy
import bmesh
from mathutils import Vector
from bl_ui.space_toolsystem_common import ToolSelectPanelHelper

import mtxpalette as mtxp
from gbi import GDLcodes
import pd_blendprops as pdprops

MAX_GDL_CMDS = 512

def printGDL(data, nspaces = 0, byte_order='big'):
    spaces = ' ' * nspaces if nspaces > 0 else ''
    addr = 0
    for i in range(0, MAX_GDL_CMDS):
        val = data[addr:addr+8]
        cmd = int.from_bytes(val, byte_order)

        # code = (cmd & 0xff00000000000000) >> 56
        w0 = int.from_bytes(data[addr:addr+4], byte_order)
        w1 = int.from_bytes(data[addr+4:addr+8], byte_order)
        code = (w0 & (0xff << 24)) >> 24
        # if byte_order != 'big':
        #     code = (cmd & 0x000000ff00000000) >> 32

        name = GDLcodes[code] if code in GDLcodes else '--'
        # print(f'{spaces}{cmd:016X}: {name}')
        print(f'{spaces}{w0:08X}{w1:08X}: {name}')

        if name == 'G_ENDDL': break
        addr += 8

def is_cmd_ptr(cmd):
    return cmd in [0x04, 0x06, 0x07, 0xFD]

def decompress(buffer):
    if buffer[0:2] == b'\x11\x73':
        return zlib.decompress(buffer[5:], wbits=-15)
    elif buffer[0:2] == b'\x11\x72':
        return zlib.decompress(buffer[2:], wbits=-15)

    raise Exception('decompress: invalid header (not 1172 or 1173)')

def decompressandgetunused(buffer):
    header = int.from_bytes(buffer[0:2], 'big')
    assert(header == 0x1173)
    obj = zlib.decompressobj(wbits=-15)
    bindata = obj.decompress(buffer[5:])
    return bindata, obj.unused_data

def compress(data):
    compressor = zlib.compressobj(wbits=-15)
    stream = compressor.compress(data)
    stream += compressor.flush()
    return b'\x11\x73' + len(data).to_bytes(3, 'big') + stream

def offsetpointer_x64(data, addr, offset, byteorder, signed=False):
    val = int.from_bytes(data[addr: addr + 8], byteorder=byteorder)
    data[addr: addr + 8] = (val + offset).to_bytes(8, byteorder=byteorder, signed=signed)

def print_bin(title, data, start, nbytes, group_size=4, groups_per_row=4):
    if title: print(title)

    s = ''
    i = 0
    g = 1
    nbytes = len(data) if nbytes < 0 else nbytes
    end = start + min(nbytes, len(data) - start)
    # print(f'    start {start:08X} end {end:08X} nbytes {nbytes:08X}')
    for k in range(start, end):
        # print(f'      {k:04X} [{start+k:08x}]')
        if i != 0 and i % (groups_per_row * group_size) == 0:
            s += '\n'
        space = ' ' if g % group_size == 0 else ''
        s += f'{data[k]:02X}{space}'
        i += 1
        g += 1
    print(s)


def print_dict(dict, indent=4):
    print(json.dumps(dict, indent=indent))

def print_dict2(dict, name, declmap, sz, showdec=False, pad=0, numspaces=0):
    spaces = ' ' * numspaces if numspaces > 0 else ''

    decl = declmap[name]
    for field in decl:
        info = field_info(field)
        # print(info)
        if info['is_cmd']: continue # TODO TEMP

        typename = info['typename']
        fieldname = info['fieldname']
        is_struct = info['is_struct']
        is_pointer = info['is_pointer']
        is_array = info['is_array']

        if is_struct and not is_pointer and not is_array:
            print(f'{spaces}{fieldname}:')
            print_dict2(dict[fieldname], typename, declmap, sz, showdec, pad, numspaces+2)
            continue

        if info['is_array']:
            arraysize = info['array_size']
            arraysize = info[f'{fieldname}_len'] if arraysize == 0 else arraysize # TODO fieldname_len no longer exists
            # arraysize = info
            for i in range(0, arraysize):
                if is_struct:
                    print(f'{spaces}{fieldname}[{i}]:')
                    print_dict2(dict[fieldname][i], typename, declmap, sz, showdec, pad, numspaces+2)
                    continue

                size = sz['pointer'] if info['is_pointer'] else sz[typename]
                fmt = '0' + str(size*2) + 'X'
                name = f'{fieldname}[{i}]'.ljust(pad)
                val = dict[fieldname][i]
                dec = f' ({val})' if showdec else ''
                print(f'{spaces}{name}: {dict[fieldname][i]:{fmt}}{dec}')
            continue
        # elif info['is_struct'] and not info['is_pointer']:
        #     name = fieldname.ljust(pad)
        #     print(f'{spaces}{name}: {dict[fieldname]}')
        #     continue

        size = sz['pointer'] if info['is_pointer'] else sz[typename]
        name = fieldname.ljust(pad)
        fmt = '0' + str(size*2) + 'X'

        val = dict[fieldname]
        dec = f' ({val})' if showdec else ''
        print(f'{spaces}{name}: {val:{fmt}}{dec}')

def globs(path, *args):
    files = glob(f'{path}/{args[0]}')
    for i in range(1, len(args)):
        files += glob(f'{path}/{args[i]}')

    return files

def _globs(path, *args):
    result = []
    for pattern in args:
        files = Path(f'{path}').glob(pattern)
        for file in files: result.append(pattern)

    return result

def ALIGN8(addr):
    return ((addr + 0x7) | 0x7) ^ 0x7

def align(addr, alignment):
    m = alignment - 1
    return ((addr + m) | m) ^ m

def read_file(filename):
    with open(filename, 'rb') as fd:
        data = fd.read()

    return data

def write_file(filename, data, log=True):
    fd = open(f'{filename}', 'wb')
    fd.write(data)
    fd.close()

    if log: print(f'file written: {filename}')

def read_tri4(cmd, ofs=0):
    bo = 'big'
    w0 = int.from_bytes(cmd[:4], bo)
    w1 = int.from_bytes(cmd[4:], bo)

    tris = []
    for idx in range(0,4):
        i0 = w1 & 0x0f; w1 >>= 4
        i1 = w1 & 0x0f; w1 >>= 4
        i2 = w0 & 0x0f; w0 >>= 4

        if i0 or i1 or i2:
            tri = (i0+ofs, i1+ofs, i2+ofs)

            if tri in tris:
                print(f'WARNING: duplicated tri, skipping: {tri}')
                continue

            tris.append(tri)

    return tris

import ctypes

def read_vtxs(vtxdata, numvtx, sc):
    bo = 'big'
    vtxs = []
    # sc = 0.1
    for i in range(numvtx):
        idx = i*12
        vtx = vtxdata[idx:idx+12]
        x = int.from_bytes(vtx[0:2], bo)
        y = int.from_bytes(vtx[2:4], bo)
        z = int.from_bytes(vtx[4:6], bo)
        flag = vtx[6]
        color = vtx[7]
        s = int.from_bytes(vtx[8:10], bo)
        t = int.from_bytes(vtx[10:12], bo)

        x = ctypes.c_short(x & 0xFFFF).value
        y = ctypes.c_short(y & 0xFFFF).value
        z = ctypes.c_short(z & 0xFFFF).value
        s = ctypes.c_short(s & 0xFFFF).value
        t = ctypes.c_short(t & 0xFFFF).value

        vtxs.append((x*sc, y*sc, z*sc, s, t, color))

    return vtxs

def createCube():
    verts = [
        (-0.285437, -0.744976, -0.471429),
        (-0.285437, -0.744976, -2.471429),
        (1.714563, -0.744976, -2.471429),
        (1.714563, -0.744976, -0.471429),
        (-0.285437, 1.255024, -0.471429),
        (-0.285437, 1.255024, -2.471429),
        (1.714563, 1.255024, -2.471429),
        (1.714563, 1.255024, -0.471429)
    ]

    faces = [
        (4, 5, 1), (5, 6, 2), (6, 7, 3), (4, 0, 7),
        (0, 1, 2), (7, 6, 5), (0, 4, 1), (1, 5, 2),
        (2, 6, 3), (7, 0, 3), (3, 0, 2), (4, 7, 5)
    ]

    collection = bpy.data.collections['Meshes']
    parent_object = bpy.data.objects.new('0.Mesh', None)
    # bpy.context.scene.objects.link(parent_object)
    collection.objects.link(parent_object)

    for i in range(0, 2):
        mesh_data = bpy.data.meshes.new("cube_mesh_data")
        mesh_data.from_pydata(verts, [], faces)
        obj = bpy.data.objects.new(f'0.Mesh-{i}', mesh_data)
        obj.parent = parent_object
        collection.objects.link(obj)

    # bpy.data.collections['Meshes'].objects.link(parent_object)

def mesh_from_verts(verts, name = '', triangulate = True):
    bm = bmesh.new()
    for v in verts:
        bm.verts.new(v)
    bm.faces.new(bm.verts)

    bm.normal_update()

    if triangulate:
        bmesh.ops.triangulate(bm, faces=bm.faces[:])

    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()

    return mesh

def clear_collection(collname):
    collection = bpy.data.collections[collname]
    meshes = set()
    for obj in collection.objects:
        if obj.type == 'MESH':
            meshes.add(obj.data)
        # Delete the object
        bpy.data.objects.remove(obj)

    for mesh in meshes:
        bpy.data.meshes.remove(mesh)

def new_collection(name):
    lib = bpy.data.collections
    if name in lib:
        coll = lib[name]
        if not bpy.context.scene.user_of_id(coll):
            bpy.context.scene.collection.children.link(coll)
        return coll

    coll = lib.new(name)
    bpy.context.scene.collection.children.link(coll)
    return coll

def clear_scene():
    for coll in pdprops.PD_COLLECTIONS:
        clear_collection(coll)

    for group in bpy.data.node_groups:
        bpy.data.node_groups.remove(group)

def new_empty_obj(name, parent=None, dsize = 0, dtype='PLAIN_AXES', link=True):
    obj = bpy.data.objects.new(name, None)
    obj.empty_display_size = dsize
    obj.empty_display_type = dtype

    if parent: obj.parent = parent

    if link:
        collection = active_collection()
        collection.objects.link(obj)

    return obj

def active_collection():
    view_layer = bpy.context.view_layer
    return view_layer.active_layer_collection.collection

def active_mesh():
    obj = bpy.context.view_layer.objects.active
    if not obj: return None
    return obj.data

def select(item, idx):
    mesh = active_mesh()
    if not mesh:
        print('no selection')

    print(f'Select {item} {idx}, mesh: {mesh.name}')
    bpy.ops.object.mode_set(mode='EDIT')

    bm = bmesh.from_edit_mesh(mesh)

    item = item.lower()

    if item == 'vtx':
        bm.verts.ensure_lookup_table()
        bm.verts[idx].select = True
    elif item == 'face':
        bm.faces.ensure_lookup_table()
        bm.faces[idx].select = True
    else:
        print('invalid item:', item)

def select_obj(bl_obj, clear_selection=True):
    if clear_selection:
        bpy.ops.object.select_all(action='DESELECT')

    bpy.context.view_layer.objects.active = bl_obj
    bl_obj.select_set(True)

def show_normals():
    mesh = active_mesh()
    if not mesh:
        print('no selection')

    bpy.ops.object.mode_set(mode='EDIT')

    bm = bmesh.from_edit_mesh(mesh)
    bm.verts.ensure_lookup_table()

    selected_verts = [v for v in bm.verts if v.select]

    layers = bm.loops.layers
    uv_layer = layers.uv.active

    for idx, vert in enumerate(selected_verts):
        print('-'*40)
        print(f'v {vert.index}')
        print('-'*40)
        # norms = set()
        for loop in vert.link_loops:
            normal = mesh.loops[loop.index].normal
            normal = normal.to_tuple()
            normal = tuple(round(e, 3) for e in normal)
            uv = loop[uv_layer].uv.to_tuple()
            uv = tuple((round(e, 3) for e in uv))
            print(f'  {loop.face.index} {normal} uv {uv}')

        # for norm in norms:
        #     print(f'  {norm}')

    bm.free()

def assign_mtx_to_selected_verts(mtx):
    obj = bpy.context.active_object
    if obj.mode != 'EDIT':
        print('ERROR: must be in Edit mode to assign matrix to vertices')
        return 0

    bm = bmesh.from_edit_mesh(obj.data)
    layer_mtx = bm.loops.layers.color["matrices"]
    verts = [v for v in bm.verts if v.select]
    for v in verts:
        print(v.index)

        for loop in v.link_loops:
            loop[layer_mtx] = mtxp.mtx2color(mtx)

    return len(verts)

# returns the index in the list of the first element that matches the condition
def index_where(array, condition, default = -1):
    return next((idx for idx, e in enumerate(array) if condition(e)), default)

def get_model_obj(obj):
    while obj:
        name = obj.pd_model.name
        if name and name[0] in ['P', 'C', 'G']: return obj
        obj = obj.parent

    return None

# Select vertices that don't have a matrix assigned and returns the number of vertices selected
# It assumes a mesh is selected and edit mode is on
def select_vtx_unassigned_mtxs():
    mesh = active_mesh()

    bm = bmesh.from_edit_mesh(mesh)
    bm.verts.ensure_lookup_table()

    verts = get_vtx_unassigned_mtxs(bm)
    for v in verts:
        v.select = True

    bm.free()
    return len(verts)

def get_vtx_unassigned_mtxs(mesh):
    layers = mesh.loops.layers
    has_mtx = 'matrices' in layers.color

    if not has_mtx:
        return 0

    layer_mtx = layers.color["matrices"] if has_mtx else None

    result = []
    for idx, vert in enumerate(mesh.verts):
        loops = vert.link_loops
        mtxcol = loops[0][layer_mtx]
        col = mtxp.col2hex(mtxcol)
        if col not in mtxp.mtxpalette:
            result.append(vert)

    return result

def redraw_ui() -> None:
    """Forces blender to redraw the UI."""
    for screen in bpy.data.screens:
        for area in screen.areas:
            area.tag_redraw()

def msg_box(title, message, icon = 'INFO'):
    def draw(self, _context):
        self.layout.label(text=message, icon=icon)
    bpy.context.window_manager.popup_menu(draw, title = title, icon = icon)

def new_obj(name, parent=None, dsize=50, link=True):
    obj = new_empty_obj(name, link=link, dsize=dsize)

    if parent:
        obj.parent = parent

    return obj

def s8(value):
    return struct.unpack('b', value.to_bytes(1, 'little'))[0]

def s16(value):
    return struct.unpack('h', value.to_bytes(2, 'little'))[0]

def s32(value):
    return struct.unpack('i', value.to_bytes(4, 'little'))[0]

def f32(value):
    return struct.unpack('f', value.to_bytes(4, 'little'))[0]

def u32(value):
    return struct.unpack('I', value.to_bytes(4, 'little'))[0]

def addon_path():
    return os.path.dirname(os.path.realpath(__file__))

def addon_name():
    return os.path.basename(addon_path())

def addon_prefs():
    return bpy.context.preferences.addons[addon_name()].preferences

@cache
def ini_file(filename):
    configs = {}
    file = open(filename, "r")

    for line in file:
        if line.strip().startswith('#'): continue
        tokens = [e.strip() for e in line.rpartition('=')]
        configs[tokens[0].lower()] = tokens[2]

    return configs

def add_to_collection(obj, col_name='', coll = None):
    collection = new_collection(col_name) if not coll else coll
    collection.objects.link(obj)
    for child in obj.children:
        collection.objects.link(child)

def verts_median(verts):
    return points_median([v.co for v in verts])

def points_median(points):
    center = Vector((0,0,0))
    for p in points:
        center += p
    center /= len(points)
    return center


def pdtype(bl_obj):
    return bl_obj.pd_obj.type & 0xff00 if bl_obj else 0

def pdsubtype(bl_obj):
    return bl_obj.pd_obj.type & 0xff if bl_obj else 0

# thanks to 'testure' from the blenderartists forum for this code :)
def unregister_tool(idname, space_type, context_mode):
    cls = ToolSelectPanelHelper._tool_class_from_space_type(space_type)
    tools = cls._tools[context_mode]

    for i, tool_group in enumerate(tools):
        if isinstance(tool_group, tuple):
            for t in tool_group:
                if 'ToolDef' in str(type(t)) and t.idname == idname:
                    if len(tools[i]) == 1:
                        # it's a group with a single item, just remove it from the tools list.
                        tools.pop(i)
                    else:
                        tools[i] = tuple(x for x in tool_group if x.idname != idname)
                    break
        elif tool_group is not None:
            if tool_group.idname == idname:
                tools.pop(i)
                break

    # cleanup any doubled up separators left over after removing a tool
    for i, p in enumerate(reversed(tools)):
        if i < len(tools) - 2 and tools[i] is None and tools[i + 1] is None:
            tools.pop(i)

def set_active_obj(bl_obj):
    bpy.context.view_layer.objects.active = bl_obj

def flags_pack(flaglist, flagvalues):
    packed = 0
    for idx, flag in enumerate(flaglist):
        packed |= flagvalues[idx] if flag else 0

    return packed

def flags_unpack(flaglist, valuepacked, flagvalues):
    n = len(flaglist)
    for idx in range(n):
        flaglist[idx] = bool(flagvalues[idx] & valuepacked)

def waypoint_name(padnum): return f'waypoint_{padnum:02X}'
def group_name(num): return f'Set {num:02X}'

def add_neighbour(bl_waypoint, bl_neighbour):
    pd_waypoint = bl_waypoint.pd_waypoint
    pd_neighbour_wp = bl_neighbour.pd_waypoint

    pd_neighbours = pd_waypoint.neighbours_coll

    # check if the neighbour already exists
    for neighbour in pd_neighbours:
        if neighbour.padnum == pd_waypoint.padnum:
            return

    neighbour_item = pd_neighbours.add()
    neighbour_item.name = waypoint_name(pd_neighbour_wp.padnum)
    neighbour_item.groupnum = pd_waypoint.groupnum
    neighbour_item.padnum = pd_neighbour_wp.padnum

    edge = pdprops.WAYPOINT_EDGETYPES[0][0]
    neighbour_item.edgetype = edge

def waypoint_newgroup():
    groupnum = waypoint_maxgroup()
    groupname = group_name(groupnum)
    bl_group = new_empty_obj(groupname, dsize=0, link=False)
    add_to_collection(bl_group, 'Waypoints')

    return groupnum, bl_group

def waypoint_maxgroup():
    n = 0
    wp_coll = bpy.data.collections['Waypoints']
    for group in wp_coll.objects:
        if group.parent is not None: continue
        n += 1

    return n

def waypoint_remove_neighbour(pd_waypoint, padnum):
    neighbours_coll = pd_waypoint.neighbours_coll
    for idx, neighbour in enumerate(neighbours_coll):
        if neighbour.padnum == padnum:
            neighbours_coll.remove(idx)
            return

def enum_value(bl_obj, enum_name, propval):
    prop = bl_obj.bl_rna.properties[enum_name]
    items = prop.enum_items
    return items.get(propval).value

def get_view_location():
    area = next(area for area in bpy.context.screen.areas if area.type == 'VIEW_3D')
    space = next(space for space in area.spaces if space.type == 'VIEW_3D')
    region = space.region_3d
    return region.view_location

def read_coord(coord):
    return [f32(coord[e]) for e in ['x', 'y', 'z']]

def fcomp(fa, fb, epsilon=1e-5):
    return abs(fa - fb) < epsilon

def fzero(fa, epsilon=1e-5):
    return fcomp(fa, 0, epsilon)
