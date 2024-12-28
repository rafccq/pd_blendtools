import os
from math import pi

import bpy
from mathutils import Euler, Vector, Matrix

from pd_bgfile import PatchBGFile as PDBGFile
from decl_bgfile import bgfile_decls
from typeinfo import TypeInfo
import pd_utils as pdu
import pd_import as pdi
import pd_materials as pdm
import tiles_import as tiles
import romdata as rom

def register():
    TypeInfo.register_all(bgfile_decls)

def bg_import(lvname, roomrange=None):
    bgdata, tex_configs = bg_load(lvname)

    # room1, room2 = 0x10, 0x37
    # roomrange = range(room1, room2)
    nrooms = len(bgdata.rooms) - 2
    roomrange = range(1, nrooms) if roomrange is None else roomrange
    # roomrange = range(1, len(bgdata.rooms)-1)

    for roomnum in roomrange:
        loadroom(bgdata, roomnum, tex_configs)

    # bg_loadportals(bgdata, room1, room2)
    # tiles.bg_loadtiles(lvname)

def bg_load(lvname, loadimgs = True):
    print(f'bgload {lvname}')

    blend_dir = os.path.dirname(bpy.data.filepath)
    romdata = rom.load(f'{blend_dir}/pd.ntsc-final.z64')

    filename = f'bgdata/{lvname}.seg'
    bgdata = romdata.filedata(filename)
    # pdu.print_bin(f'^{lvname.upper()}', bgdata, 0, 64)
    bgdata = PDBGFile(bgdata)

    print('nrooms', len(bgdata.rooms))
    print('load images')

    if loadimgs:
        pdi.loadimages(romdata, bgdata.textures)
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

def bg_loadportals(bgdata, room_first, room_last):
    portals = bgdata.portals
    portalvtxs = bgdata.portalvertices

    roomrange = range(room_first, room_last+1)
    for portalnum, portal in enumerate(portals):
        portalvtx = portalvtxs[portalnum]
        room1 = portal['roomnum1']
        room2 = portal['roomnum2']

        if room1 not in roomrange and room2 not in roomrange: continue
        verts = portalvtx['vertices']
        verts_bl = []
        for v in verts:
            x = pdu.f32(v['x'])
            y = pdu.f32(v['y'])
            z = pdu.f32(v['z'])

            M =  Matrix.Translation((x, y, z))
            R = Euler((pi / 2, 0, pi / 2)).to_matrix().to_4x4()
            M = R @ M
            t = M.translation
            verts_bl.append((round(t.x), round(t.y), round(t.z)))
            nx, ny, nz = verts_bl[-1]
            print(f'v {x} {y} {z} ({nx} {ny} {nz})')

        basename = f'portal_{portalnum:02X}'
        portalmesh = pdu.mesh_from_verts(verts_bl, f'{basename}_mesh')
        portalobj = bpy.data.objects.new(f'{basename}({room1:02X}-{room2:02X})', portalmesh)
        # portalobj.display_type = 'WIRE'
        portalobj.show_wire = True
        portalmat = pdm.portal_material()
        portalobj.color = (0, 0.8, 0.8, 0.4)
        portalobj.data.materials.append(portalmat)
        collection = pdu.active_collection()
        collection.objects.link(portalobj)

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
    roomid = room['id']
    pos = room['pos']

    x = pdu.f32(pos['x'])
    y = pdu.f32(pos['y'])
    z = pdu.f32(pos['z'])

    room_ptr_vtx = gfxdata['vertices']
    room_ptr_cols = gfxdata['colours']

    meshes = []
    for idx, block in enumerate(room['roomblocks']):
        if block['type'] != 0: continue

        ptr_gdl = block['gdl|child'] - roomid
        gdldata = room['_gdldata'][ptr_gdl].bytes
        # pdu.print_bin(f'^GDL', gdldata, 0, 64, 8, 1)

        vtxstart = (block['vertices|coord1'] - room_ptr_vtx)
        colstart = (block['colours'] - room_ptr_cols)

        # print(f"block_{idx} vstart {vtxstart:08X} colstart {colstart:08X} {room['id'] + block.addr:08X} gdl {block['gdl|child']:08X}")

        # vdata = room['vtx'].bytes[vtxstart:]
        # pdu.print_bin(f'^VTX', vdata, 0, 12*8, 2, 6)

        meshdata = pdi.PDMeshData(
            gdldata,
            None, # xlu_gdl
            None, # ptr_vtx
            None, # ptr_col
            room['vtx'].bytes[vtxstart:],
            room['colors'].bytes[colstart:],
            None
        )

        mesh, _ = pdi.collect_sub_meshes(meshdata, idx, False)
        meshes += mesh

    for idx, mesh in enumerate(meshes):
        room_obj = pdi.create_mesh(mesh, tex_configs, roomnum, idx)
        room_obj.matrix_world.translation.x = x
        room_obj.matrix_world.translation.y = y
        room_obj.matrix_world.translation.z = z

        for mat in room_obj.data.materials:
            if mat['has_envmap']:
                pdm.mat_show_vtxcolors(mat)

        # to blender coords
        rot_mat = Euler((pi/2, 0, pi/2)).to_matrix().to_4x4()
        room_obj.matrix_world = rot_mat @ room_obj.matrix_world
        pdu.add_to_collection(room_obj, 'Rooms')

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
