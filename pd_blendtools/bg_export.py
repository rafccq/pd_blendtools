from collections import deque
import math

import bpy

import pd_utils as pdu
import bg_utils as bgu
import pd_mtx as mtx
import pd_materials as pdm
import pd_export as pde
from bytereader import *
from decl_bgfile import decl_portalvertices
from typeinfo import TypeInfo


def export_rooms(rd, dataout):
    start = len(dataout)

    R_inv = mtx.rot_blender_inv()
    coll = bpy.data.collections['Rooms']

    dummyroom = DataBlock.New('bgroom')
    rd.write_block(dataout, dummyroom)

    rooms = [dummyroom]
    for bl_room in coll.objects:
        if bl_room.pd_obj.type != pdprops.PD_OBJTYPE_ROOM: continue

        data = DataBlock.New('bgroom')
        rooms.append(data)
        print(bl_room.name, data)

        roompos = R_inv @ bl_room.matrix_world.translation
        pos = data['pos']
        pos['x'], pos['y'], pos['z'] = bgu.coord_as_s32(roompos)
        data['br_light_min'] = 0x80
        data['br_light_max'] = 0xff
        rd.write_block(dataout, data)

    endmarker = DataBlock.New('bgroom')
    rd.write_block(dataout, endmarker)
    rooms.append(endmarker)

    rd.write_block(dataout, dummyroom)
    add_padding(dataout, 8)

    return start, rooms

def export_lights(rd, dataout):
    start = len(dataout)
    add_padding(dataout, 8)
    return 0

def export_bgcmds(rd, dataout):
    start = len(dataout)
    cmd = DataBlock.New('bgcmd')
    cmd['len'] = 1
    rd.write_block(dataout, cmd)
    return start

def export_portals(rd, dataout):
    start = len(dataout)

    coll = bpy.data.collections['Portals']
    R_inv = mtx.rot_blender_inv()

    portalvertices = []
    for idx, bl_portal in enumerate(coll.objects):
        pd_portal = bl_portal.pd_portal

        data = DataBlock.New('bgportal')

        pd_room1, pd_room2 = pd_portal.room1.pd_room, pd_portal.room2.pd_room
        data['verticesoffset'] = idx + 1
        data['roomnum1'] = pd_room1.roomnum
        data['roomnum2'] = pd_room2.roomnum

        rd.write_block(dataout, data)

        verts = bgu.verts_world(bl_portal, R_inv)
        portalvertices.append(verts)

    endmarker = DataBlock.New('bgportal')
    rd.write_block(dataout, endmarker)

    export_portalvertices(rd, dataout, portalvertices)
    return start

def export_portalvertices(rd, dataout, portalvertices):
    # print('N portals', f'{len(portalvertices):02X}')
    # for verts in portalvertices:
    for idx, verts in enumerate(portalvertices):
        count = len(verts)
        TypeInfo.register('portalvertices', decl_portalvertices, False, varmap={'N': count})
        data = DataBlock.New('portalvertices')
        data['count'] = count
        for i, v in enumerate(verts):
            pv = data['vertices'][i]
            pv['x'], pv['y'], pv['z'] = bgu.coord_as_s32(v, round)

        rd.write_block(dataout, data)

    add_padding(dataout, 8)

def get_roomblocks(bl_room):
    layer_sort = lambda node: sorted(list(node.children), key = lambda e: e.pd_room.layer)

    blocks = []
    children = layer_sort(bl_room)
    stack = deque([c for c in reversed(children)])

    def set_links(nodes, parent):
        if len(nodes) == 0: return

        layer = lambda idx: nodes[idx].pd_room.layer
        for i in range(0, len(nodes)):
            nodes[i]['prev'] = nodes[i-1].name if i > 0 and layer(i) == layer(i-1) else ''
            nodes[i]['parent'] = ''

        nodes[0]['parent'] = parent

    set_links(children, '')

    while len(stack):
        current = stack.pop()

        blocks.append(current)
        children = list(current.children)
        for c in reversed(children):
            stack.append(c)

        set_links(children, current.name)

    return blocks

def export_roomGDL(roomblocks):
    gfxdata = []
    textures = set()
    bbox = bgu.Bbox()

    for block in roomblocks:
        pd_roomblock = block.pd_room
        mesh = pde.ExportMeshData(block.name, pd_roomblock.layer, block.data)
        mesh.create_batches()
        mesh.batches.sort(key=lambda b: b.mat)

        materials = mesh.meshdata.materials

        vtxdata = bytearray()
        colordata = bytearray()

        for batch in mesh.batches:
            batch.vtx_offset = len(vtxdata)
            batch.color_offset = len(colordata)
            batch.color_start = 0

            mat = materials[batch.mat]
            image = pdm.material_get_teximage(mat)
            textures.add(image)

            texsize = (1, 1)
            if image:
                texsize = image.size
            else:
                print(f'WARNING: material has no texture. Mesh{mesh.name} mat {mat.name}')

            vtxdata += batch.vtx_bytes(texsize, bbox=bbox)
            colordata += batch.color_bytes()

        nverts = len(block.data.vertices)
        gdlbytes = pde.mesh_to_gdl(mesh, 0, nverts, 0xe, 0xd, env_enabled=True)
        gfxdata.append((vtxdata, colordata, gdlbytes))

    return gfxdata, textures, bbox

def export_roomgfxdata(rd, bl_room, ofs_room):
    # print('[ROOMGFXDATA]', bl_room.name, f'ofs {ofs_room:08X}')
    bl_blocks = get_roomblocks(bl_room)
    blockmap = {}

    dataout = bytearray()
    header = DataBlock.New('roomgfxdata')
    header['lightsindex'] = -1
    rd.write_block(dataout, header)

    blocks_dl = []
    blocks_bsp = []

    ptr_opa = 0
    ptr_xlu = 0

    # write room blocks
    for bl_block in bl_blocks:
        pd_room = bl_block.pd_room

        block = DataBlock.New('roomblock')
        blockmap[bl_block.name] = block

        ofs_block = len(dataout) + ofs_room

        if pd_room.blocktype == pdprops.BLOCKTYPE_DL:
            block['type'] = 0
            blocks_dl.append(bl_block)
        else:
            block['type'] = 1
            blocks_bsp.append(bl_block)

        rd.write_block(dataout, block)

        if bl_block['prev']:
            prev = blockmap[bl_block['prev']]
            prev.update(dataout, 'next', ofs_block)

        if bl_block['parent']:
            parent = blockmap[bl_block['parent']]
            parent.update(dataout, 'gdl|child', ofs_block)

        if ptr_opa == 0 and pd_room.layer == 'opa':
            ptr_opa = ofs_block
        if ptr_xlu == 0 and pd_room.layer == 'xlu':
            ptr_xlu = ofs_block

    header.update(dataout, 'opablocks', ptr_opa)
    header.update(dataout, 'xlublocks', ptr_xlu)

    R_inv = mtx.rot_blender_inv()

    # write coords (from bsp blocks)
    for bl_block in blocks_bsp:
        pd_room = bl_block.pd_room
        bsp_pos = R_inv @ pd_room.bsp_pos
        bsp_normal = R_inv @ pd_room.bsp_normal

        block_pos = DataBlock.New('coord')
        block_normal = DataBlock.New('coord')
        ofs_coord = len(dataout) + ofs_room

        block_pos['x'], block_pos['y'], block_pos['z'] = bgu.coord_as_s32(bsp_pos)
        block_normal['x'], block_normal['y'], block_normal['z'] = bgu.coord_as_s32(bsp_normal)

        rd.write_block(dataout, block_pos)
        rd.write_block(dataout, block_normal)

        block = blockmap[bl_block.name]
        block.update(dataout, 'vertices|coord1', ofs_coord)

    add_padding(dataout, 8)

    ptr_verts = ofs_room + len(dataout)
    header.update(dataout, 'vertices', ptr_verts)

    gfxdata, textures, bbox = export_roomGDL(blocks_dl)

    def write_data(idx, field, update_ptr=None):
        datalist = [e[idx] for e in gfxdata]
        for bl_block, data in zip(blocks_dl, datalist):
            ofs = len(dataout) + ofs_room
            datblock = rd.create_block(data)
            rd.write_block_raw(dataout, datblock)
            block = blockmap[bl_block.name]
            block.update(dataout, field, ofs)

        add_padding(dataout, 8)

        if update_ptr:
            ptr = ofs_room + len(dataout)
            header.update(dataout, update_ptr, ptr)

    # write verts, colours and GDL data
    write_data(0, 'vertices|coord1', update_ptr='colours')
    write_data(1, 'colours')
    write_data(2, 'gdl|child')

    add_padding(dataout, 4)

    return dataout, textures, bbox

def export_section1(out_gfxdatalens, out_bboxes, out_textures):
    primarydata = bytearray()
    rd = ByteReader(primarydata)

    header = DataBlock.New('primarydata')
    rd.write_block(primarydata, header)

    # export sub sections and save the offsets
    ofs_rooms, rooms = export_rooms(rd, primarydata)
    ofs_lights = export_lights(rd, primarydata)
    ofs_cmds = export_bgcmds(rd, primarydata)
    ofs_portals = export_portals(rd, primarydata)

    # update header
    headers = [('rooms', ofs_rooms), ('portals', ofs_portals),
               ('bgcmds', ofs_cmds), ('lightfile', ofs_lights)]
    for hdr, ofs in headers:
        if ofs == 0: continue
        header.update(primarydata, hdr, ofs + 0x0f000000)

    primsize = len(primarydata)

    #### patch all gfx data
    gfxdata = bytearray()

    ofs_room = primsize + 0x0f000000
    coll = bpy.data.collections['Rooms']
    idx = 1
    for bl_room in coll.objects:
        if bl_room.pd_obj.type != pdprops.PD_OBJTYPE_ROOM: continue

        roomgfxdata, textures, bbox = export_roomgfxdata(rd, bl_room, ofs_room)
        comp = pdu.compress(roomgfxdata)
        complen = pdu.align(len(comp), 4)

        rooms[idx].update(primarydata, 'unk00', ofs_room)

        ofs_room += complen
        gfxdata += comp
        add_padding(gfxdata, 4)

        out_gfxdatalens.append(len(roomgfxdata))
        out_textures |= textures
        out_bboxes.append(bbox)

        idx += 1

    rooms[idx].update(primarydata, 'unk00', ofs_room)

    # compress the data and write the headers
    primarydata_comp = compress(primarydata)
    primcompsize = len(primarydata_comp)

    section1 = primarydata_comp + gfxdata
    section1size = len(section1)

    header = bytearray()
    rd.write(header, primsize, 'u32')
    rd.write(header, section1size, 'u32')
    rd.write(header, primcompsize, 'u32')

    # print('nrooms', len(rooms))
    # print('primsize    ', f'{primsize:04X}')
    # print('section1size', f'{section1size:04X}')
    # print('primcompsize', f'{primcompsize:04X}')

    # print('sz(room)', TypeInfo.sizeof('bgroom'))
    # print('sz(portal)', TypeInfo.sizeof('bgportal'))
    # print('sz(roomgfxdata)', TypeInfo.sizeof('roomgfxdata'))
    # print('sz(roomblock)', TypeInfo.sizeof('roomblock'))

    return header + section1

def export_section2(textures):
    dataout = bytearray()
    rd = ByteReader(dataout)

    for tex in textures:
        name = tex.name
        name = name[:name.index('.')]
        texnum = int(f'{name}', 16)
        rd.write(dataout, texnum, 's16')

    return pack_section(dataout, mask=0x7fff)

def export_section3(gfxdatalens, bboxes, lights_per_room):
    dataout = bytearray()
    rd = ByteReader(dataout)

    #### bboxes
    for bbox in bboxes:
        block = DataBlock.New('bbox')
        block['min_x'] = math.floor(bbox.xmin)
        block['min_y'] = math.floor(bbox.ymin)
        block['min_z'] = math.floor(bbox.zmin)
        block['max_x'] = math.floor(bbox.xmax)
        block['max_y'] = math.floor(bbox.ymax)
        block['max_z'] = math.floor(bbox.zmax)
        rd.write_block(dataout, block)

    #### gfxdatalen
    for gfxdatalen in gfxdatalens:
        rd.write(dataout, gfxdatalen//0x10, 'u16')

    #### lights/room
    for numlights in lights_per_room:
        rd.write(dataout, numlights, 'u8')

    return pack_section(dataout, 0x7fff)

def pack_section(dataout, mask = 1):
    compdata = compress(dataout)
    sec2len = len(dataout)
    compsec2len = len(compdata)

    header = bytearray()
    header += (sec2len & mask).to_bytes(2, byteorder=DEST_BO)
    header += compsec2len.to_bytes(2, byteorder=DEST_BO)
    header += compdata

    return header

def export(filename):
    textures = set()
    gfxdatalens = []
    bboxes = []
    section1 = export_section1(gfxdatalens, bboxes, textures)
    section2 = export_section2(textures)
    section3 = export_section3(gfxdatalens, bboxes, [0] * len(gfxdatalens))

    bgdata = section1 + section2 + section3
    pdu.write_file(filename, bgdata)
