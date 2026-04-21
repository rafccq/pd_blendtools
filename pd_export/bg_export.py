from collections import deque
import math
import datetime

import bpy

from utils import (
    pd_utils as pdu,
    bg_utils as bgu
)
from . import model_export as mde
from pd_data.decl_bgfile import decl_portalvertices
import data.typeinfo as tpi
from data.datablock import DataBlock
from data.bytestream import ByteStream, add_padding
import pd_mtx as mtx
from materials import pd_materials as pdm
import pd_blendprops as pdprops


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

        roompos = R_inv @ bl_room.matrix_world.translation
        pos = data['pos']
        pos['x'], pos['y'], pos['z'] = bgu.coord_as_u32(roompos)
        data['br_light_min'] = 0x80
        data['br_light_max'] = 0xff
        rd.write_block(dataout, data)

    endmarker = DataBlock.New('bgroom')
    rd.write_block(dataout, endmarker)
    rooms.append(endmarker)

    rd.write_block(dataout, dummyroom)

    return start, rooms

def export_lights(rd, dataout):
    start = len(dataout)
    return 0

def export_bgcmds(rd, dataout):
    start = len(dataout)

    scn = bpy.context.scene

    for cmd in scn.pd_bgcmds:
        data = DataBlock.New('bgcmd')
        data['type'] = cmd['type']
        data['len'] = cmd['len']
        data['param'] = cmd['param']
        rd.write_block(dataout, data)

    endmarker = DataBlock.New('bgcmd')
    endmarker['len'] = 1
    rd.write_block(dataout, endmarker)

    return start

def export_portals(rd, dataout):
    start = len(dataout)

    coll = bpy.data.collections['Portals']
    R_inv = mtx.rot_blender_inv()

    portalvertices = []
    idx = 0
    for bl_portal in coll.objects:
        pd_portal = bl_portal.pd_portal

        data = DataBlock.New('bgportal')

        if not pd_portal.room1 or not pd_portal.room2:
            print(f'WARNING missing room in {bl_portal.name}')
            continue

        if bl_portal.hide_render:
            print(f'SKIPPED {bl_portal.name}')
            continue

        pd_room1, pd_room2 = pd_portal.room1.pd_room, pd_portal.room2.pd_room
        data['verticesoffset'] = idx + 1
        data['roomnum1'] = pd_room1.roomnum
        data['roomnum2'] = pd_room2.roomnum

        rd.write_block(dataout, data)

        verts = bgu.verts_world(bl_portal, R_inv)
        portalvertices.append(verts)
        idx += 1

    endmarker = DataBlock.New('bgportal')
    rd.write_block(dataout, endmarker)

    export_portalvertices(rd, dataout, portalvertices)
    return start

def export_portalvertices(rd, dataout, portalvertices):
    # for verts in portalvertices:
    for idx, verts in enumerate(portalvertices):
        count = len(verts)
        tpi.TypeInfo.register('portalvertices', decl_portalvertices, False, varmap={'N': count})
        data = DataBlock.New('portalvertices')
        data['count'] = count
        for i, v in enumerate(verts):
            pv = data['vertices'][i]
            pv['x'], pv['y'], pv['z'] = bgu.coord_as_u32(v, round)

        rd.write_block(dataout, data)

    if len(portalvertices) == 0:
        tpi.TypeInfo.register('portalvertices', decl_portalvertices, False, varmap={'N': 0})

    endmarker = DataBlock.New('portalvertices')
    rd.write_block(dataout, endmarker)

def get_roomblocks(bl_room):
    blocks = []

    children = pdu.get_children(bl_room)
    for child in children:
        child['prev'] = ''
        child['parent'] = ''

    def traverse(block):
        if not block: return

        stack = [block]
        while len(stack):
            current = stack.pop()
            blocks.append(current)

            pd_roomblock = current.pd_room
            next = pd_roomblock.next
            if next:
                next['prev'] = current.name
                stack.append(next)

            child = pd_roomblock.child
            if child:
                child['parent'] = current.name
                stack.append(child)

    pd_room = bl_room.pd_room
    traverse(pd_room.first_opa)
    traverse(pd_room.first_xlu)

    return blocks

def export_roomGDL(roomblocks):
    gfxdata = []
    textures = set()
    bbox = bgu.Bbox()

    mde.update_log()

    ofs_vtx = 0
    for block in roomblocks:
        pd_roomblock = block.pd_room
        mesh = mde.ExportMeshData(block.name, pd_roomblock.layer, block.data)
        mesh.create_batches()
        mesh.batches.sort(key=lambda b: b.mat)

        materials = mesh.meshdata.materials

        vtxdata = bytearray()
        colordata = bytearray()

        nverts_batches = 0
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
                print(f'WARNING: material has no texture. Mesh {mesh.name} mat {mat.name}')

            texconfig = pdm.material_get_texconfig(mat)
            texscale = texconfig.tex_scale
            vtxdata += batch.vtx_bytes(texsize, texscale, bbox=bbox)
            colordata += batch.color_bytes()
            nverts_batches += batch.nverts()

        nverts = len(block.data.vertices)
        vtx_start = ofs_vtx if pd_roomblock.layer == 'xlu' else 0
        gdlbytes = mde.mesh_to_gdl(mesh, vtx_start, nverts, 0xe, 0xd)
        gfxdata.append((vtxdata, colordata, gdlbytes))
        ofs_vtx += nverts_batches * 12

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

        block_pos['x'], block_pos['y'], block_pos['z'] = bgu.coord_as_u32(bsp_pos)
        block_normal['x'], block_normal['y'], block_normal['z'] = bgu.coord_as_u32(bsp_normal)

        rd.write_block(dataout, block_pos)
        rd.write_block(dataout, block_normal)

        block = blockmap[bl_block.name]
        block.update(dataout, 'vertices|coord1', ofs_coord)

    add_padding(dataout, 8)

    ptr_verts = ofs_room + len(dataout)
    header.update(dataout, 'vertices', ptr_verts)

    gfxdata, textures, bbox = export_roomGDL(blocks_dl)

    # ---- write gfx data
    DAT_VTX = 0
    DAT_COLORS = 1
    DAT_GDL = 2
    def write_data(idx, field):
        datalist = [e[idx] for e in gfxdata]
        for bl_block, data in zip(blocks_dl, datalist):
            ofs = len(dataout) + ofs_room
            datblock = rd.create_block(data)
            rd.write_block_raw(dataout, datblock)
            block = blockmap[bl_block.name]
            block.update(dataout, field, ofs)

        add_padding(dataout, 8)
        return len(dataout)

    # write verts, colours and GDL data
    ofs_col = write_data(DAT_VTX, 'vertices|coord1')
    write_data(DAT_COLORS, 'colours')
    write_data(DAT_GDL, 'gdl|child')
    header.update(dataout, 'colours', ofs_col + ofs_room)

    # this weird quirk is needed for animated textures to work: xlu blocks vertices
    # must be the same as the header, the offset goes into the VTX command
    for bl_block in blocks_dl:
        pd_room = bl_block.pd_room
        if pd_room.layer != 'xlu': continue
        block = blockmap[bl_block.name]
        block.update(dataout, 'vertices|coord1', ptr_verts)

    add_padding(dataout, 4)

    return dataout, textures, bbox

def export_section1(out_gfxdatalens, out_bboxes, out_textures):
    primarydata = bytearray()
    rd = ByteStream(primarydata)

    header = DataBlock.New('primarydata')
    rd.write_block(primarydata, header)

    # export subsections and save the offsets
    ofs_rooms, rooms = export_rooms(rd, primarydata)
    ofs_lights = export_lights(rd, primarydata)
    ofs_portals = export_portals(rd, primarydata)
    ofs_cmds = export_bgcmds(rd, primarydata)

    # update header
    headers = [('rooms', ofs_rooms), ('portals', ofs_portals),
               ('bgcmds', ofs_cmds), ('lightfile', ofs_lights)]
    for hdr, ofs in headers:
        if ofs == 0: continue
        header.update(primarydata, hdr, ofs + 0x0f000000)

    primsize = len(primarydata)

    #### patch all gfx data
    gfxdata = bytearray()

    scn = bpy.context.scene
    if scn.remap_texids:
        pdm.create_texid_map(scn.texid_start)

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
    primarydata_comp = pdu.compress(primarydata)
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
    rd = ByteStream(dataout)

    scn = bpy.context.scene
    texmap = scn['map_texids']
    for tex in textures:
        name = tex.name
        texnum = texmap[name] if scn.remap_texids and name in texmap else int(pdu.filename(name), 16)
        rd.write(dataout, texnum, 's16')

    return pack_section(dataout, mask=0x7fff)

def export_section3(gfxdatalens, bboxes, lights_per_room):
    dataout = bytearray()
    rd = ByteStream(dataout)

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
        rd.write(dataout, int(gfxdatalen*2)//0x10, 'u16')

    #### lights/room
    for numlights in lights_per_room:
        rd.write(dataout, numlights, 'u8')

    return pack_section(dataout, 0x7fff)

def pack_section(dataout, mask = 1):
    compdata = pdu.compress(dataout)
    sec2len = len(dataout)
    compsec2len = len(compdata)

    header = bytearray()
    header += (sec2len & mask).to_bytes(2, byteorder='big')
    header += compsec2len.to_bytes(2, byteorder='big')
    header += compdata

    return header

def export(filename, _):
    textures = set()
    gfxdatalens = []
    bboxes = []
    section1 = export_section1(gfxdatalens, bboxes, textures)
    section2 = export_section2(textures)
    section3 = export_section3(gfxdatalens, bboxes, [0] * len(gfxdatalens))

    bgdata = section1 + section2 + section3

    filename = pdu.make_dir_bgdata(filename)
    pdu.write_file(filename, bgdata)

    now = datetime.datetime.now()
    print(f'BG export done at {now}')
