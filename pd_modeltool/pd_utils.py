import zlib
import json
import os
import struct
from pathlib import Path
from glob import glob

import bpy
import bmesh

GDLcodes = {
    0x00: 'G_SPNOOP',
    0x01: 'G_MTX',
    0x03: 'G_MOVEMEM',
    0x04: 'G_VTX',
    0x06: 'G_DL',
    0x07: 'G_COL',
    0xB1: 'G_TRI4',
    0xB2: 'G_RDPHALF_CONT',
    0xB3: 'G_RDPHALF_2',
    0xB4: 'G_RDPHALF_1',
    0xB6: 'G_CLEARGEOMETRYMODE',
    0xB7: 'G_SETGEOMETRYMODE',
    0xB8: 'G_ENDDL',
    0xB9: 'G_SetOtherMode_L',
    0xBA: 'G_SetOtherMode_H',
    0xBB: 'G_TEXTURE',
    0xBC: 'G_MOVEWORD',
    0xBD: 'G_POPMTX',
    0xBE: 'G_CULLDL',
    0xBF: 'G_TRI1',
    0xC0: 'G_NOOP',
    0xE4: 'G_TEXRECT',
    0xE5: 'G_TEXRECTFLIP',
    0xE6: 'G_RDPLOADSYNC',
    0xE7: 'G_RDPPIPESYNC',
    0xE8: 'G_RDPTILESYNC',
    0xE9: 'G_RDPFULLSYNC',
    0xEA: 'G_SETKEYGB',
    0xEB: 'G_SETKEYR',
    0xEC: 'G_SETCONVERT',
    0xED: 'G_SETSCISSOR',
    0xEE: 'G_SETPRIMDEPTH',
    0xEF: 'G_RDPSetOtherMode',
    0xF0: 'G_LOADTLUT',
    0xF2: 'G_SETTILESIZE',
    0xF3: 'G_LOADBLOCK',
    0xF4: 'G_LOADTILE',
    0xF5: 'G_SETTILE',
    0xF6: 'G_FILLRECT',
    0xF7: 'G_SETFILLCOLOR',
    0xF8: 'G_SETFOGCOLOR',
    0xF9: 'G_SETBLENDCOLOR',
    0xFA: 'G_SETPRIMCOLOR',
    0xFB: 'G_SETENVCOLOR',
    0xFC: 'G_SETCOMBINE',
    0xFD: 'G_SETTIMG',
    0xFE: 'G_SETZIMG',
    0xFF: 'G_SETCIMG',
}

setup_props_names = {
    'stagesetup': 'stagesetup',
    'obj_header': 'objheader',
    'defaultobj': 'defaultobj',
    'coord': 'coord',
    'tvscreen': 'tvscreen',
    'hov': 'hov',
    'path': 'path',
    'ailist': 'ailist',
    'pads': 'pads',
    'multiammocrateslot': 'multiammocrateslot',
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
    0x1e: 'criteria_holograph',
    0x20: 'criteria_roomentered',
    0x21: 'criteria_throwinroom',
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
    0x2e: 'cameraposobj',
    0x2f: 'tintedglassobj',
    0x30: 'liftobj',
    0x31: 'linksceneryobj',
    0x32: 'blockedpathobj',
    0x33: 'hoverbikeobj',
    0x34: 'objheader',
    0x35: 'hoverpropobj',
    0x36: 'fanobj',
    0x37: 'hovercarobj',
    0x38: 'padeffectobj',
    0x39: 'chopperobj',
    0x3a: 'weaponobj',
    0x3b: 'escalatorobj',
}

G_ENDDL = 0xb8
MAX_GDL_CMDS = 512

def printGDL(data, nspaces = 0, byte_order='big'):
    spaces = ' ' * nspaces if nspaces > 0 else ''
    addr = 0
    for i in range(0, MAX_GDL_CMDS):
        val = data[addr:addr+16]
        # cmd = int.from_bytes(val, byte_order)

        w0 = int.from_bytes(data[addr:addr+8], byte_order)
        w1 = int.from_bytes(data[addr+8:addr+16], byte_order)
        code = (w0 & (0xff << 24)) >> 24
        # code = (w0 & (0xff << 32)) >> 32

        # w0 = int.from_bytes(data[addr:addr+8], byte_order)
        # w1 = int.from_bytes(data[addr+8:addr+16], byte_order)
        name = GDLcodes[code] if code in GDLcodes else '--'
        print(f'{spaces}{w0<<32:016X} {w1:016X}: {name}')

        val = (w0 << 32) | (w1)
        # print(f'{spaces}{val:016X}: {name}')

        if name == 'G_ENDDL': break
        addr += 16

def printGDL_x86(data, nspaces = 0, byte_order='big'):
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

def print_bin(title, data, start, nbytes, group_size=1, groups_per_row=4):
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

def field_info(decl):
    '''
    supported types are primitives, structs, arrays and pointers:
    - primitives (there's no actual processing of tokens, so "anything" can be a primitive),
        however, when used by bytereader, primitives must be the ones declared in the "sz" map
        Examples:
            'f32 xmin'
            'f32 xmax'
            'u16 rwdataindex'

    - structs: which are declarations that must be registered
        Examples:
            'struct coord pos'

    - arrays of supported types, of any dimension
        Examples:
	        'struct fontchar chars[94]'
            's16 mtxindexes[3]'
            's16 rotmtx[3][3]'
            'f32 3dsomething[3][3][3]'

        - arrays of undetermined size are also supported:
            's32 values[]'
            in such cases, and "endmarker" must be supplied to bytereader

    - pointers to supported types
        Examples:
            'void *baseaddr'
            'struct textureconfig *texture'
            'struct modelnode **parts'

    - arrays of supported types
        Examples:
            'struct coord vertices[4]'
            'u8* parts[3]'
            'f32 unk0c[3]'
    '''
    # print('decl:', decl)
    decl = decl.strip()
    decl.replace('\t', ' ')

    if ':' in decl: return parse_cmd(decl)

    is_struct = decl.startswith('struct') and '*' not in decl
    decl = decl.replace('struct', '').strip()

    first_space = decl.find(' ')
    typename, field = decl[:first_space].strip(), decl[first_space:].strip()

    is_pointer = '*' in typename or field.startswith('*')
    is_array = '[' in decl and ']' in decl
    # print('field:', field)

    i = 0
    while field[i] == '*':
        typename += '*'
        i += 1

    array_size = parse_array_size(field) if is_array else None
    field = field.replace('*', '')

    if is_array: field = field[:field.find('[')]

    field = field.strip()

    return {
        'typename': typename,
        'fieldname': field,
        'is_pointer': is_pointer,
        'is_array': is_array,
        'is_struct': is_struct,
        'array_size': array_size,
        'is_cmd': False,
    }

def parse_cmd(decl):
    parts = decl.split(':')
    cmd = parts[0]
    param = parts[1].strip()

    return {
        'is_cmd': True,
        'cmd': cmd,
        'cmd_param': param,
    }

# returns the expression inside an array declaration, ex: [15+96], returns 15+96
def parse_array(decl):
    open = decl.find('[')
    close = decl.find(']')

    if open + 1 == close:
        return '0', decl[close+1:]
    if open < 0 and close < 0:
        # print('not found')
        return None, decl
    elif open >= 0 and close < 0:
        print('parse error: unmatched open bracket')
        return None, None
    elif open < 0 and close >= 0:
        print('parse error: unmatched close bracket')
        return None, None
    elif open > close:
        print('parse error: bracket')
        return None, None

    return decl[open + 1:close], decl[close+1:]

def parse_array_size(decl):
    total = 1
    while True:
        expr, decl = parse_array(decl)
        if expr:
            total *= eval(expr)
        else: break
        if not decl: break

    # print(s)
    return total

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
            arraysize = info[f'{fieldname}_len'] if arraysize == 0 else arraysize
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

def write_file(dir, filename, data, log=True):
    # dir = 'patched'

    if not os.path.isdir(dir):
        os.makedirs(dir, exist_ok=True)

    fd = open(f'{dir}/{filename}', 'wb')
    fd.write(data)
    fd.close()

    if log: print(f'file written: {dir}/{filename}')


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
            # tris.append((i0+ofs, i2+ofs, i1+ofs))

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

        # vtxs.append([x,y,z,s,t,flags])
        # vtxs.append((x*sc,y*sc,z*sc))
        vtxs.append((x*sc, z*sc, y*sc, s, t, color)) #invert-yz

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

def clear_collection(collection):
    meshes = set()
    for obj in collection.objects:
        if obj.type == 'MESH':
            meshes.add(obj.data)
        # Delete the object
        bpy.data.objects.remove(obj)

    for mesh in meshes:
        bpy.data.meshes.remove(mesh)

def clear_scene():
    view_layer = bpy.context.view_layer
    clear_collection(view_layer.active_layer_collection.collection)
    # if name not in bpy.data.collections: return
    # collection = bpy.data.collections[name]

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


def activeMesh():
    obj = bpy.context.view_layer.objects.active
    if not obj: return None
    return obj.data

def select(item, idx):
    mesh = activeMesh()
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
