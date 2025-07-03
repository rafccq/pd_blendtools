import bpy
from mathutils import Euler, Vector, Matrix

from utils import (
    pd_utils as pdu,
    bg_utils as bgu,
    setup_utils as stu
)
from pd_blendprops import WAYPOINT_EDGEVALUES
from pd_data.decl_padsfile import decl_padsfileheader
from data.bytereader import ByteReader, add_padding
from data.datablock import DataBlock
from data.typeinfo import TypeInfo
import pd_blendprops as pdprops
import pd_mtx as mtx
from pd_data import pd_padsfile as pdp, decl_setupfile as dst

ux = Vector((1, 0, 0))
uy = Vector((0, 1, 0))
uz = Vector((0, 0, 1))

M_BADPI = mtx.M_BADPI

def vec_alignment(v):
    if pdu.vec_comp(v, ux):
        return 'X', ''
    elif pdu.vec_comp(v, -ux):
        return 'X', 'INV'
    elif pdu.vec_comp(v, uy):
        return 'Y', ''
    elif pdu.vec_comp(v, -uy):
        return 'Y', 'INV'
    elif pdu.vec_comp(v, uz):
        return 'Z', ''
    elif pdu.vec_comp(v, -uz):
        return 'Z', 'INV'

    return '', ''

ALIGN_FLAGS = {
    'UP_X'  : pdp.PADFLAG_UPALIGNTOX,
    'UP_Y'  : pdp.PADFLAG_UPALIGNTOY,
    'UP_Z'  : pdp.PADFLAG_UPALIGNTOZ,
    'LOOK_X': pdp.PADFLAG_LOOKALIGNTOX,
    'LOOK_Y': pdp.PADFLAG_LOOKALIGNTOY,
    'LOOK_Z': pdp.PADFLAG_LOOKALIGNTOZ,
}

def pad_flags(up, look):
    flags = 0
    axis, inv = vec_alignment(up)
    if axis:
        flags |= ALIGN_FLAGS[f'UP_{axis}']
        flags |= pdp.PADFLAG_UPALIGNINVERT if inv else 0
        # print(f'    UP_{axis} {inv}')

    axis, inv = vec_alignment(look)
    if axis:
        flags |= ALIGN_FLAGS[f'LOOK_{axis}']
        flags |= pdp.PADFLAG_LOOKALIGNINVERT if inv else 0
        # print(f'    LOOK_{axis} {inv}')

    return flags

def pad_inv_center(pad, pdtype):
    if pdtype != pdprops.PD_PROP_DOOR:
        pad.pos.x -= (pad.bbox.ymin - pad.bbox.ymax) * 0.5 * pad.up.x
        pad.pos.y -= (pad.bbox.ymin - pad.bbox.ymax) * 0.5 * pad.up.y
        pad.pos.z -= (pad.bbox.ymin - pad.bbox.ymax) * 0.5 * pad.up.z

    invx = pad.pos.x - (
            (pad.bbox.xmin + pad.bbox.xmax) * pad.normal.x +
            (pad.bbox.ymin + pad.bbox.ymax) * pad.up.x +
            (pad.bbox.zmin + pad.bbox.zmax) * pad.look.x) * 0.5

    invy = pad.pos.y - (
            (pad.bbox.xmin + pad.bbox.xmax) * pad.normal.y +
            (pad.bbox.ymin + pad.bbox.ymax) * pad.up.y +
            (pad.bbox.zmin + pad.bbox.zmax) * pad.look.y) * 0.5

    invz = pad.pos.z - (
            (pad.bbox.xmin + pad.bbox.xmax) * pad.normal.z +
            (pad.bbox.ymin + pad.bbox.ymax) * pad.up.z +
            (pad.bbox.zmin + pad.bbox.zmax) * pad.look.z) * 0.5

    return Vector((invx, invy, invz))

def pad_inv_pos(objpos, look, up, flags=None, scale=None, rotation=None, bbox=None):
    side = up.cross(look).normalized()
    up = look.cross(side).normalized()

    # if dbg: print('s', side, 'u', up)

    T = Matrix.Identity(4)
    if scale:
        sx = Matrix.Scale(scale.x, 4, (1.0, 0.0, 0.0))
        sy = Matrix.Scale(scale.y, 4, (0.0, 1.0, 0.0))
        sz = Matrix.Scale(scale.z, 4, (0.0, 0.0, 1.0))
        T = T @ sx @ sy @ sz

    M = Matrix([
        [side.x, up.x, look.x, 0],
        [side.y, up.y, look.y, 0],
        [side.z, up.z, look.z, 0],
        [0, 0, 0, 1]
    ])

    T = rotation @ T if rotation else T

    pos = objpos
    if flags is not None:
        if flags & dst.OBJFLAG_00000002:
            pos = tuple([objpos[i] + T[i][2] * bbox.zmin for i in range(3)])
        elif bbox is not None:
            ymin, ymax = bbox.ymin, bbox.ymax
            if flags & dst.OBJFLAG_UPSIDEDOWN:
                rot = Euler((0, 0, -M_BADPI)).to_matrix().to_4x4()
                T = T @ rot
                pos = tuple([objpos[i] + T[i][1] * ymax for i in range(3)])
            elif flags & dst.OBJFLAG_00000008:
                MT = M @ T
                pos = tuple([objpos[i] + MT[i][1] * ymin for i in range(3)])

    return Vector(pos)

def pad_initial_pos(bl_obj):
    pd_prop = bl_obj.pd_prop
    pd_pad = pd_prop.pad

    objtype = bl_obj.pd_obj.type
    is_intro = pdu.pdtype(bl_obj) == pdprops.PD_OBJTYPE_INTRO

    B = mtx.rot_blender_inv()
    M = B @ bl_obj.matrix_world

    if is_intro:
        M = bl_obj.matrix_world.copy()
        T = M.translation
        M = M @ mtx.rot_introinv()
        M.translation = T
        M = B @ M

    objpos = M.translation

    pad_bbox = pdp.Bbox(*pd_pad.bbox)
    model_bbox = pdp.Bbox(*pd_pad.model_bbox)
    modelscale = pd_prop.modelscale * pd_prop.extrascale / (256 * 4096)
    flags = pdu.flags_pack(pd_prop.flags1, [e[1] for e in pdprops.OBJ_FLAGS1])
    sx, sy, sz = stu.obj_getscale(modelscale, pad_bbox, model_bbox, flags)

    # invert the rotation caused by FLAG00000002
    R = mtx.rot_FLAG00000002inv() if flags & dst.OBJFLAG_00000002 else Matrix.Identity(4)
    if flags & dst.OBJFLAG_UPSIDEDOWN:
        R = R @ mtx.rot_FLAGUPSIDEDONWinv()

    # doors have an extra rotation
    R = R @ mtx.rot_doorinv() if objtype == pdprops.PD_PROP_DOOR else R

    normal, up, look = mtx.mtx_basis(M @ R)
    sc = Vector((sx, sy, sz))
    pos = pad_inv_pos(objpos, look, up, flags, sc, R, model_bbox)
    pad = pdp.Pad(pos, look, up, normal, pad_bbox, None)
    pos = pad_inv_center(pad, objtype) if pd_pad.hasbbox else pos

    return pos, up.normalized(), look.normalized()

def export_pad(bl_obj, padnum, dataout):
    rd = ByteReader(None)

    pd_prop = bl_obj.pd_prop
    pd_pad = pd_prop.pad

    flags = pdu.flags_pack(pd_pad.flags, [e[1] for e in pdprops.OBJ_FLAGS1])

    padpos, up, look = pad_initial_pos(bl_obj)
    padflags = pad_flags(up, look)
    if pd_pad.hasbbox: padflags |= pdp.PADFLAG_HASBBOXDATA
    flags |= padflags
    flags |= pdp.PADFLAG_INTPOS

    header = pdp.pad_makeheader(flags, pd_pad.room, pd_pad.lift)
    rd.write(dataout, header, 'u32')
    size = TypeInfo.sizeof('u32')

    f = round
    rd.write(dataout, f(padpos.x), 's16')
    rd.write(dataout, f(padpos.y), 's16')
    rd.write(dataout, f(padpos.z), 's16')
    rd.write(dataout, 0, 's16')

    size += 3 * TypeInfo.sizeof('s16')

    # print(f'pad {padnum:02X} h {header:08X}  bbox {pd_pad.hasbbox} {bl_obj.name}')

    f = lambda e: round(e, 4)

    if not (padflags & (pdp.PADFLAG_UPALIGNTOX | pdp.PADFLAG_UPALIGNTOY | pdp.PADFLAG_UPALIGNTOZ)):
        conv = lambda e: round(e, 4)
        ux = bgu.as_u32(conv(up.x))
        uy = bgu.as_u32(conv(up.y))
        uz = bgu.as_u32(conv(up.z))
        # print(f'  ux     : {ux:08X}({f(up.x):.4f})')
        # print(f'  uy     : {uy:08X}({f(up.y):.4f})')
        # print(f'  uz     : {uz:08X}({f(up.z):.4f})')
        rd.write(dataout, ux, 'u32')
        rd.write(dataout, uy, 'u32')
        rd.write(dataout, uz, 'u32')

        size += 3 * TypeInfo.sizeof('u32')

    if not (padflags & (pdp.PADFLAG_LOOKALIGNTOX | pdp.PADFLAG_LOOKALIGNTOY | pdp.PADFLAG_LOOKALIGNTOZ)):
        lx = bgu.as_u32(look.x)
        ly = bgu.as_u32(look.y)
        lz = bgu.as_u32(look.z)
        # print(f'  lx     : {lx:08X}({f(look.x):.4f})')
        # print(f'  ly     : {ly:08X}({f(look.y):.4f})')
        # print(f'  lz     : {lz:08X}({f(look.z):.4f})')
        rd.write(dataout, lx, 'u32')
        rd.write(dataout, ly, 'u32')
        rd.write(dataout, lz, 'u32')

        size += 3 * TypeInfo.sizeof('u32')

    if padflags & pdp.PADFLAG_HASBBOXDATA:
        bbox = pdp.Bbox(*pd_pad.bbox)
        xmin = bgu.as_u32(bbox.xmin)
        xmax = bgu.as_u32(bbox.xmax)
        ymin = bgu.as_u32(bbox.ymin)
        ymax = bgu.as_u32(bbox.ymax)
        zmin = bgu.as_u32(bbox.zmin)
        zmax = bgu.as_u32(bbox.zmax)
        vals = [xmin, xmax, ymin, ymax, zmin, zmax]
        for v in vals: rd.write(dataout, f(v), 'u32')
        # print(f'  xmin  : {xmin:08X}({bbox.xmin:.4f})')
        # print(f'  xmax  : {xmax:08X}({bbox.xmax:.4f})')
        # print(f'  ymin  : {ymin:08X}({bbox.ymin:.4f})')
        # print(f'  ymax  : {ymax:08X}({bbox.ymax:.4f})')
        # print(f'  zmin  : {zmin:08X}({bbox.zmin:.4f})')
        # print(f'  zmax  : {zmax:08X}({bbox.zmax:.4f})')

        size += 6 * TypeInfo.sizeof('u32')

    add_padding(dataout, 4)
    return pdu.align(size, 4)

def export_waypoints(dataout, waypoints):
    rd = ByteReader(None)

    wp_blocks = []
    for idx, bl_waypoint in enumerate(waypoints):
        pd_waypoint = bl_waypoint.pd_waypoint
        pd_prop = bl_waypoint.pd_prop
        pd_waypoint.idx = idx
        # print(bl_waypoint.name, pd_waypoint.groupnum)

        block = DataBlock.New('waypoint')
        block['padnum'] = pd_prop.padnum
        block['groupnum'] = pd_waypoint.groupnum
        wp_blocks.append(block)
        rd.write_block(dataout, block)

    wp_end = DataBlock.New('waypoint')
    wp_end['padnum'] = -1
    rd.write_block(dataout, wp_end)

    # write neighbours
    id2idx = {wp.pd_waypoint.id: wp.pd_waypoint.idx for wp in waypoints}
    # for wp in waypoints:
    #     print(f'{wp.name} id {wp.pd_waypoint.id:02X} pad {wp.pd_prop.pad.padnum:04X} idx {wp.pd_waypoint.idx:02X}')

    for idx, bl_waypoint in enumerate(waypoints):
        pd_waypoint = bl_waypoint.pd_waypoint
        # print(bl_waypoint.name, f'{pd_waypoint.groupnum:02X}')
        # print(f'WP #{idx:02X} neighbours {len(dataout):08X}')
        wp_blocks[idx].update(dataout, 'neighbours', len(dataout))
        for neighbour in pd_waypoint.neighbours_coll:
            edge = neighbour.edgetype
            edgevalue = pdprops.WAYPOINT_EDGEVALUES[edge] << 8
            edgevalue |= id2idx[neighbour.id]
            rd.write(dataout, edgevalue, 'u32')
            # print(f'  {edgevalue:08X}')

        rd.write(dataout, 0xffffffff, 'u32')

    add_padding(dataout, 4)

def export_waygroups(dataout):
    EDGEVALUES = WAYPOINT_EDGEVALUES

    rd = ByteReader(None)

    groups = [obj for obj in bpy.data.collections['Waypoints'].objects if obj.parent is None]

    wg_blocks = []
    groups_waypoints = []
    groups_neighbours = []

    for _ in enumerate(groups):
        block = DataBlock.New('waygroup')
        wg_blocks.append(block)
        rd.write_block(dataout, block)

    wg_end = DataBlock.New('waypoint')
    wg_end['neighbours'] = 0
    rd.write_block(dataout, wg_end)

    for groupnum, bl_group in enumerate(groups):
        neighbours = set()
        waypoints = []
        for wp in bl_group.children:
            pd_waypoint = wp.pd_waypoint
            waypoints.append(pd_waypoint.idx)

            for nb in pd_waypoint.neighbours_coll:
                # standard (STD) edges have total priority over the other edge types
                nb_group = nb.groupnum
                if nb_group != groupnum:
                    if nb.edgetype == 'STD':
                        # remove other edges from the set if existent
                        neighbours.discard(EDGEVALUES['OWF'] << 8 | nb_group)
                        neighbours.discard(EDGEVALUES['OWB'] << 8 | nb_group)
                        neighbours.add(nb.groupnum)
                    elif nb_group not in neighbours:
                        neighbours.add(nb_group | EDGEVALUES[nb.edgetype] << 8)

        groups_neighbours.append(neighbours)
        groups_waypoints.append(waypoints)
        # str_nb = ''.join(str([f'{g:04X}'for g in groups_neighbours[groupnum]]))
        # print(f'group {groupnum:02X}: {str_nb}')

    # export waypoints
    for groupnum, block in enumerate(wg_blocks):
        block.update(dataout, 'waypoints', len(dataout))
        waypoints = groups_waypoints[groupnum]
        for wp in waypoints:
            rd.write(dataout, wp, 's32')
        rd.write(dataout, 0xffffffff, 'u32')

    add_padding(dataout, 4)

    # export neighbours
    for groupnum, block in enumerate(wg_blocks):
        block.update(dataout, 'neighbours', len(dataout))
        neighbours = groups_neighbours[groupnum]
        for wp in neighbours:
            rd.write(dataout, wp, 's32')
        rd.write(dataout, 0xffffffff, 'u32')

def export_covers(dataout):
    rd = ByteReader(None)

    covers = [obj for obj in bpy.data.collections['Cover Pads'].objects if pdu.pdtype(obj) == pdprops.PD_OBJTYPE_COVER]

    for bl_cover in covers:
        block = DataBlock.New('cover')
        B = mtx.rot_blender_inv()
        M = B @ bl_cover.matrix_world

        pos = M.translation
        _, _, look = mtx.mtx_basis(M)

        bpos = block['pos']
        blook = block['look']

        bpos['x'], bpos['y'], bpos['z'] = bgu.coord_as_u32(pos)
        blook['x'], blook['y'], blook['z'] = bgu.coord_as_u32(look)

        rd.write_block(dataout, block)

def add_lift_stops(props):
    def add_stop(stop, idx):
        nonlocal ofs
        if stop is not None:
            props.insert(idx + ofs + 1, stop)
            ofs += 1

    for idx, prop in enumerate(props):
        if prop.pd_obj.type == pdprops.PD_PROP_LIFT:
            pd_lift = prop.pd_lift

            ofs = 0
            add_stop(pd_lift.stop1, idx)
            add_stop(pd_lift.stop2, idx)
            add_stop(pd_lift.stop3, idx)
            add_stop(pd_lift.stop4, idx)

def export(filename, compress):
    get_objs = lambda coll, objtype: [prop for prop in bpy.data.collections[coll].objects if pdu.pdtype(prop) == objtype]

    props = get_objs('Props', pdprops.PD_OBJTYPE_PROP)
    intros = get_objs('Intro', pdprops.PD_OBJTYPE_INTRO)
    waypoints = get_objs('Waypoints', pdprops.PD_OBJTYPE_WAYPOINT)

    add_lift_stops(props)

    dataout = bytearray()
    rd = ByteReader(None)

    all_objs = props + intros + waypoints
    all_objs.sort(key = lambda e: e.pd_prop.pad.padnum)

    for idx, bl_obj in enumerate(all_objs):
        bl_obj.pd_prop.padnum = idx

    # print('---- OBJS ----')
    # for idx, bl_obj in enumerate(all_objs):
    #     print(f'{bl_obj.name:<20} pad {bl_obj.pd_prop.pad.padnum:02X} idx {idx:02X}')
    # print('--------------')

    numpads = len(all_objs)
    numcovers = len(bpy.data.collections['Cover Pads'].objects)
    TypeInfo.register('padsfileheader', decl_padsfileheader, varmap={'N': numpads})

    header = DataBlock.New('padsfileheader')
    header['numpads'] = numpads
    header['numcovers'] = numcovers

    rd.write_block(dataout, header)

    add_padding(dataout, 4)

    ofs = len(dataout)
    pad_offsets = []
    for bl_obj in all_objs:
        pad_offsets.append(ofs)
        idx = bl_obj.pd_prop.padnum
        ofs += export_pad(bl_obj, idx, dataout)

    add_padding(dataout, 4)

    ofs_waypoints = len(dataout)
    export_waypoints(dataout, waypoints)

    ofs_waygroups = len(dataout)
    export_waygroups(dataout)

    ofs_covers = len(dataout)
    export_covers(dataout)

    header.update(dataout, 'padoffsets', pad_offsets)
    header.update(dataout, 'waypointsoffset', ofs_waypoints)
    header.update(dataout, 'waygroupsoffset', ofs_waygroups)
    header.update(dataout, 'coversoffset', ofs_covers)

    if compress:
        dataout = pdu.compress(dataout)

    pdu.write_file(filename, dataout)
