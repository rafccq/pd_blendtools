import os
from math import pi

import bpy
from mathutils import Euler, Vector, Matrix

from pd_bgfile import PatchBGFile as PDBGFile, ROOMBLOCKTYPE_LEAF, ROOMBLOCKTYPE_PARENT
from decl_bgfile import bgfile_decls
from typeinfo import TypeInfo
import pd_utils as pdu
import bg_utils as bgu
import model_import as mdi
import pd_materials as pdm
import romdata as rom
import pd_blendprops as pdprops

def register():
    TypeInfo.register_all(bgfile_decls)

def bg_import(lvname, roomrange=None):
    scn = bpy.context.scene
    scn['rooms'] = {}

    bgdata, tex_configs = bg_load(lvname)

    # room1, room2 = 0x10, 0x37
    # roomrange = range(room1, room2)
    nrooms = len(bgdata.rooms) - 2
    roomrange = range(1, nrooms) if roomrange is None else roomrange
    # roomrange = range(1, len(bgdata.rooms)-1)

    for roomnum in roomrange:
        loadroom(bgdata, roomnum, tex_configs)

    bg_loadportals(bgdata, roomrange)

def bg_load(lvname, loadimgs = True):
    print(f'bgload {lvname}')

    blend_dir = os.path.dirname(bpy.data.filepath)
    romdata = rom.load(f'{blend_dir}/pd.ntsc-final.z64')

    filename = f'bgdata/{lvname}.seg'
    bgdata = romdata.filedata(filename)
    bgdata = PDBGFile(bgdata)

    print('nrooms', len(bgdata.rooms))
    print('load images')

    if loadimgs:
        mdi.loadimages(romdata, bgdata.textures)
    # for texnum in sorted(bgdata.textures):
    #     print(f'{texnum: 04X}')
    # print('done')

    tex_configs = {}
    for texnum in bgdata.textures:
        img = bpy.data.images[f'{texnum:04X}.png']
        tex_configs[texnum] = img['texinfo']

    bpy.context.scene['lvname'] = lvname

    return bgdata, tex_configs

def bg_loadroom(room):
    bg_loadrooms(room, room)

def loadportals(roomrange):
    blend_dir = os.path.dirname(bpy.data.filepath)
    romdata = rom.load(f'{blend_dir}/pd.ntsc-final.z64')
    filename = f'bgdata/bg_ame.seg'
    bgdata = romdata.filedata(filename)
    bgdata = PDBGFile(bgdata)
    bg_loadportals(bgdata, roomrange)

def bg_loadportals(bgdata, roomrange):
    portals = bgdata.portals
    portalvtxs = bgdata.portalvertices

    for portalnum, portal in enumerate(portals):
        portalvtx = portalvtxs[portalnum]
        room1 = portal['roomnum1']
        room2 = portal['roomnum2']

        if room1 not in roomrange and room2 not in roomrange:
            print(f'WARNING: Portal {portalnum} is invalid, room1: {room1} room2: {room2}')
            continue

        verts = portalvtx['vertices']
        verts_bl = []
        for v in verts:
            x = pdu.f32(v['x'])
            y = pdu.f32(v['y'])
            z = pdu.f32(v['z'])

            M =  Matrix.Translation((x, y, z))
            R = Euler((pi/2, 0, pi/2)).to_matrix().to_4x4()
            M = R @ M
            t = M.translation
            verts_bl.append((round(t.x), round(t.y), round(t.z)))
            nx, ny, nz = verts_bl[-1]
            print(f'v {x} {y} {z} ({nx} {ny} {nz})')

        basename = f'portal_{portalnum:02X}'
        portalmesh = pdu.mesh_from_verts(verts_bl, f'{basename}_mesh')
        bl_portal = bpy.data.objects.new(f'{basename}({room1:02X}-{room2:02X})', portalmesh)
        # bl_portal.display_type = 'WIRE'
        bgu.init_portal(bl_portal, basename)

        scn = bpy.context.scene
        rooms = scn['rooms']
        bl_portal.pd_portal.room1 = rooms[str(room1)]
        bl_portal.pd_portal.room2 = rooms[str(room2)]

def bg_loadrooms(room_from, room_to):
    for name, decl in bgfile_decls.items():
        TypeInfo.register(name, decl)

    scn = bpy.context.scene
    lvname = scn['lvname']
    bgdata, tex_configs = bg_load(lvname, loadimgs=False)

    for roomnum in range(room_from, room_to+1):
        loadroom(bgdata, roomnum, tex_configs)

def loadroom(bgdata, roomnum, tex_configs):
    print(f'loadroom {roomnum:02X}')
    room = bgdata.rooms[roomnum]
    gfxdata = room['gfxdata']

    bl_room = pdu.new_obj(f'Room_{roomnum:02X}', link=False, dsize=0.0001)

    bl_room.pd_obj.name = bl_room.name
    bl_room.pd_obj.type = pdprops.PD_OBJTYPE_ROOM
    bl_room.pd_room.roomnum = roomnum
    bl_room.pd_room.room = bl_room

    pdu.add_to_collection(bl_room, 'Rooms')
    bl_room.matrix_world.translation = get_vec3(room['pos'])

    # to blender coords
    R = Euler((pi / 2, 0, pi / 2)).to_matrix().to_4x4()
    bl_room.matrix_world = R @ bl_room.matrix_world

    idx = bg_create_roomblocks(room, gfxdata['opablocks'], bl_room, bl_room, tex_configs, 'opa', 0)
    bg_create_roomblocks(room, gfxdata['xlublocks'], bl_room, bl_room, tex_configs, 'xlu', idx)

    bpy.context.scene['rooms'][str(roomnum)] = bl_room

def get_vec3(pos):
    x = pdu.f32(pos['x'])
    y = pdu.f32(pos['y'])
    z = pdu.f32(pos['z'])
    return x, y, z

def bg_create_roomblockDL(room, block, bl_room, rootobj, tex_configs, layer, idx):
    gfxdata = room['gfxdata']
    roomid = room['id']
    roomnum = room['roomnum']

    room_ptr_vtx = gfxdata['vertices']
    room_ptr_cols = gfxdata['colours']

    ptr_gdl = block['gdl|child'] - roomid
    gdldata = room['_gdldata'][ptr_gdl].bytes
    # pdu.print_bin(f'^GDL', gdldata, 0, 64, 8, 1)

    vtxstart = (block['vertices|coord1'] - room_ptr_vtx)
    colstart = (block['colours'] - room_ptr_cols)

    # print(f"block_{idx} vstart {vtxstart:08X} colstart {colstart:08X} {room['id'] + block.addr:08X} gdl {block['gdl|child']:08X}")

    meshdata = mdi.PDMeshData(
        gdldata,
        None,  # xlu_gdl
        None,  # ptr_vtx
        None,  # ptr_col
        room['vtx'].bytes[vtxstart:],
        room['colors'].bytes[colstart:],
        None
    )

    gdldata, _, _ = mdi.gdl_read_data(meshdata, idx, False)

    bl_roomblock = mdi.create_mesh(gdldata, tex_configs, roomnum, idx)
    bl_roomblock['addr'] = f'{block.addr:08X}'
    bl_roomblock.name = bgu.blockname(roomnum, idx, 'Display List', layer)
    bl_roomblock.parent = rootobj
    bl_roomblock.color = (0,0,0,1)
    pdu.add_to_collection(bl_roomblock, 'Rooms')
    bgu.roomblock_set_props(bl_roomblock, roomnum, bl_room, idx, layer, 'Display List')

    for mat in bl_roomblock.data.materials:
        if mat['has_envmap']:
            pdm.mat_show_vtxcolors(mat)

def bg_create_roomblocks(room, rootaddr, bl_room, rootobj, tex_configs, layer, idx):
    if rootaddr == 0: return idx

    roomblocks = room['roomblocks']
    rootblock = roomblocks[rootaddr]
    roomnum = room['roomnum']

    next_block = lambda addr: roomblocks[addr] if addr else None

    block = rootblock
    while block:
        blocktype = block['type']
        if blocktype == ROOMBLOCKTYPE_LEAF:
            bg_create_roomblockDL(room, block, bl_room, rootobj, tex_configs, layer, idx)
            block = next_block(block['next'])
        elif blocktype == ROOMBLOCKTYPE_PARENT:
            name = bgu.blockname(roomnum, idx, 'BSP', layer)
            bl_rootblock = pdu.new_obj(name, rootobj, link=False, dsize=0.0001)
            bl_rootblock['addr'] = f'{block.addr:08X}'
            bsp_pos = pdu.read_coord(block['coord_0'])
            bsp_normal = pdu.read_coord(block['coord_1'])
            pdu.add_to_collection(bl_rootblock, 'Rooms')
            bgu.roomblock_set_props(bl_rootblock, roomnum, bl_room, idx, layer, pdprops.BLOCKTYPE_BSP, bsp_pos, bsp_normal)

            idx = bg_create_roomblocks(room, block['gdl|child'], bl_room, bl_rootblock, tex_configs, layer, idx + 1)
            block = next_block(block['next'])

        idx += 1

    return idx

def _bg_loadlights():
    for name, decl in bgfile_decls.items(): #TMP
        TypeInfo.register(name, decl)

    lvname = bpy.context.scene['lvname']
    bgdata, _ = bg_load(lvname, False)
    bg_loadlights(bgdata)

def light_center(roompos, points):
    center = [roompos[0], roompos[1], roompos[2]]
    for p in points:
        center[0] += p[0]
        center[1] += p[1]
        center[2] += p[2]

    center[0] *= 0.25
    center[1] *= 0.25
    center[2] *= 0.25

    return Vector(center)

def bg_loadlights(bgdata):
    # lights = [bgdata.lights[i] for i in [0x2, 0xf]]
    # lights = [bgdata.lights[0x2]]
    lights = [0x2, 0xf]
    ln = '-'*40
    for i in lights:
        light = bgdata.lights[i]
        print(ln, f'light_{i:02X}')
        points = [light['bbox'][i] for i in range(4)]
        points = [p['s'] for p in points]
        for p in points: p[:] = map(pdu.s16, p)

        roomnum = light['roomnum']
        room = bgdata.rooms[roomnum]
        roompos = room['pos']
        roompos = [pdu.f32(roompos[e]) for e in ['x', 'y', 'z']]

        print(f'R{roomnum:02X}', roompos)
        print(points)
        p0, p1, p2, p3 = [points[i] for i in range(4)]

        v0 = Vector(p0)
        v1 = Vector(p1)
        v3 = Vector(p3)
        f = lambda d: pdu.s8(light[d])
        lightdir = Vector((f('dirx'), f('diry'), f('dirz'))).normalized()

        center = light_center(roompos, points)
        lightpos = center + Vector(roompos)
        lightpos += lightdir * 0.5

        # lightpos[:] = [lightpos[i] for i in [2,0,1]]
        verts = map(lambda p: Vector(p) - center, points)
        verts = map(lambda v: (v.z, v.x, v.y), verts)
        # rx, ry, rz = roompos
        # here we map xyz:zxy to account for Blender coordinate system
        # points[:] = map(lambda p: [p[2] + rz, p[0] + rx, p[1] + ry], points)
        # print(points)
        basename = f'light_{1}'
        lightmesh = pdu.mesh_from_verts(verts, f'{basename}_mesh')
        lightobj = bpy.data.objects.new(f'{basename}(R{roomnum:02X})', lightmesh)
        # lightobj.display_type = 'WIRE'
        lightobj.show_wire = True
        lightobj.location = (lightpos.z, lightpos.x, lightpos.y)
        # portalmat = pdm.portal_material()
        lightobj.color = (0, 0.8, 0.8, 0.4)
        # lightobj.data.materials.append(portalmat)
        collection = pdu.active_collection()
        collection.objects.link(lightobj)

def bg_portals_hide():
    scn = bpy.context.scene
    for obj in scn.objects:
        if obj.name.startswith('portal'):
            obj.hide_set(True)

def bg_portals_unhide():
    scn = bpy.context.scene
    for obj in scn.objects:
        if obj.name.startswith('portal'):
            obj.hide_set(False)
