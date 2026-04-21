import bpy
from mathutils import Vector, Matrix, Euler

from pd_data.decl_setupfile import *
from . import pd_utils as pdu
from pd_mtx import M_BADPI
from pd_data.model_info import ModelStates, ModelNames
import pd_blendprops as pdprops
from pd_import import model_import as mdi
from pd_data import romdata as rom, pd_padsfile as pdp


def obj_setup_mtx(obj, look, up, pos, rotation=None, scale=None, flags=None, bbox=None):
    conv = pdu.pos_to_lhs

    look = conv(-look)
    up = conv(up)

    side = look.cross(up).normalized()
    up = side.cross(look).normalized()

    M = Matrix([
        [side.x, look.x, up.x, 0],
        [side.y, look.y, up.y, 0],
        [side.z, look.z, up.z, 0],
        [0, 0, 0, 1]
    ])

    T = Matrix.Identity(4)
    if rotation:
        Rx = Matrix.Rotation(rotation[0], 4, 'X')
        Ry = Matrix.Rotation(rotation[1], 4, 'Y')
        Rz = Matrix.Rotation(-rotation[2], 4, 'Z')
        rot_lh = Rz @ Ry @ Rx

        # convert to right-handed by applying the same coord change as conv
        # conv: (x, y, z) -> (x, -z, y), which is a -90d rotation around X
        C = Matrix([
            [1, 0, 0, 0],
            [0, 0, 1, 0],
            [0, -1, 0, 0],
            [0, 0, 0, 1]
        ])
        rot_rh = C @ rot_lh @ C.inverted()

        T = T @ rot_rh

    if scale:
        sx = Matrix.Scale(scale.x, 4, (1.0, 0.0, 0.0))
        sy = Matrix.Scale(scale.z, 4, (0.0, 1.0, 0.0))
        sz = Matrix.Scale(scale.y, 4, (0.0, 0.0, 1.0))
        T = T @ sx @ sy @ sz

    newpos = pos
    if flags is not None:
        if flags & OBJFLAG_00000002:
            newpos = tuple([pos[i] - T[i][2] * bbox.zmin for i in range(3)])
        elif bbox is not None:
            ymin, ymax = bbox.ymin, bbox.ymax
            if flags & OBJFLAG_UPSIDEDOWN:
                rot = Euler((0, 0, M_BADPI)).to_matrix().to_4x4()
                T = T @ rot
                newpos = tuple([pos[i] - T[i][1] * ymax for i in range(3)])
            elif flags & OBJFLAG_00000008:
                TMP = M @ T
                newpos = tuple([pos[i] - TMP[i][1] * ymin for i in range(3)])

    obj.matrix_world = M @ T
    obj.matrix_world.translation = newpos
    pdu.obj_pos_to_lhs(obj)

def obj_getscale(modelscale, padbbox, bbox, flags):
    sx = sy = sz = 1.0

    flag40 = OBJFLAG_YTOPADBOUNDS

    if flags & OBJFLAG_XTOPADBOUNDS:
        if bbox.xmin < bbox.xmax:
            if flags & OBJFLAG_00000002:
                sx = (padbbox.xmax - padbbox.xmin) / ((bbox.xmax - bbox.xmin) * modelscale)
            else:
                sx = (padbbox.xmax - padbbox.xmin) / ((bbox.xmax - bbox.xmin) * modelscale)

    if flags & flag40:
        if bbox.ymin < bbox.ymax:
            if flags & OBJFLAG_00000002:
                sz = (padbbox.zmax - padbbox.zmin) / ((bbox.ymax - bbox.ymin) * modelscale)
            else:
                sy = (padbbox.ymax - padbbox.ymin) / ((bbox.ymax - bbox.ymin) * modelscale)

    if flags & OBJFLAG_ZTOPADBOUNDS:
        if bbox.zmin < bbox.zmax:
            if flags & OBJFLAG_00000002:
                sy = (padbbox.ymax - padbbox.ymin) / ((bbox.zmax - bbox.zmin) * modelscale)
            else:
                sz = (padbbox.zmax - padbbox.zmin) / ((bbox.zmax - bbox.zmin) * modelscale)

    maxscale = max(sx, sy, sz)

    if (flags & OBJFLAG_XTOPADBOUNDS) == 0:
        if flags & OBJFLAG_00000002 and bbox.xmax == bbox.xmin:
            sx = maxscale
        elif bbox.xmax == bbox.xmin:
            sx = maxscale

    if (flags & flag40) == 0:
        if flags & OBJFLAG_00000002 and bbox.ymax == bbox.ymin:
            sz = maxscale
        elif bbox.ymax == bbox.ymin:
            sy = maxscale

    if (flags & OBJFLAG_ZTOPADBOUNDS) == 0:
        if flags & OBJFLAG_00000002:
            if bbox.zmax == bbox.zmin:
                sy = maxscale
        elif bbox.zmax == bbox.zmin:
            sz = maxscale

    sx /= maxscale
    sy /= maxscale
    sz /= maxscale

    if sx <= 0.000001 or sy <= 0.000001 or sz <= 0.000001:
        sx = sy = sz = 1

    m = modelscale * maxscale
    return m*sx, m*sy, m*sz

def prop_getscale(pd_prop):
    pad = pd_prop.pad
    pad_bbox = pdp.Bbox(*pad.bbox)
    model_bbox = pdp.Bbox(*pad.model_bbox)
    modelscale = pd_prop.modelscale * pd_prop.extrascale / (256 * 4096)
    flags = pdu.flags_pack(pd_prop.flags1, [e[1] for e in pdprops.OBJ_FLAGS1])
    return obj_getscale(modelscale, pad_bbox, model_bbox, flags)

def check_flags(packedflags, *flags):
    flagsval = 0
    for flag in flags:
        flagsval |= flag

    return packedflags & flagsval

def obj_hasmodel(type):
    return type in [
        pdprops.OBJTYPE_BASIC, 'standard',
        pdprops.OBJTYPE_DOOR, 'door',
        pdprops.OBJTYPE_GLASS, 'glass',
        pdprops.OBJTYPE_TINTEDGLASS, 'tinted glass',
        pdprops.OBJTYPE_LIFT, 'lift',
        pdprops.OBJTYPE_MULTIAMMOCRATE, 'multi-ammo crate',
        pdprops.OBJTYPE_FAN, 'fan',
        pdprops.OBJTYPE_HOVERCAR, 'hovercar',
    ]

def obj_load_model(romdata, modelnum):
    scn = bpy.context.scene

    filenum = ModelStates[modelnum].filenum
    modelname = romdata.filenames[filenum]
    load_external = scn.level_external_models and modelname in scn['external_models']

    matlib = bpy.data.materials
    matcache = { mat.hashed:mat.name for mat in matlib }

    if load_external:
        filename = f'{scn.external_models_dir}/{modelname}'
        return mdi.import_model(romdata, matcache, mdi.ASSET_TYPE_OBJ, filename=filename)
    else:
        return mdi.import_model(romdata, matcache, mdi.ASSET_TYPE_OBJ, modelname=modelname)

def change_model(bl_obj, modelnum, force=False):
    if not bl_obj: return

    pd_prop = bl_obj.pd_prop

    if pd_prop.modelnum == modelnum and not force: return

    romdata = rom.load()
    new_obj, model = obj_load_model(romdata, modelnum)
    mesh = bl_obj.data
    mesh.clear_geometry()
    mesh.materials.clear()

    bl_obj.data = new_obj.data
    bpy.data.objects.remove(new_obj, do_unlink=True)
    bpy.data.meshes.remove(mesh, do_unlink=True)
    pd_prop.modelnum = modelnum
    pd_prop.modelname = ModelNames[modelnum]

    # update the pad's model bbox
    pd_pad = pd_prop.pad
    bbox = model.find_bbox()
    set_bbox(pd_pad.model_bbox, bbox)

def set_bbox(dst_bbox, src_bbox):
    bbox = [src_bbox.xmin, src_bbox.xmax, src_bbox.zmin, src_bbox.zmax, src_bbox.ymin, src_bbox.ymax]
    for i, val in enumerate(bbox):
        dst_bbox[i] = val

def update_flagspacked(obj, propname, flags):
    flagsval = 0
    prop = obj[propname]
    for i, f in enumerate(prop): flagsval |= flags[i][1] if f else 0
    obj[f'{propname}_packed'] = f'{flagsval:08X}'

def update_flags(array, flags_packed):
    f = int(flags_packed, 16)
    n = len(array)
    for i in range(n):
        array[i] = f & 1
        f >>= 1

def wp_name(pad_id): return f'waypoint_{pad_id:02X}'

def wp_addneighbour(bl_waypoint, bl_neighbour):
    pd_waypoint = bl_waypoint.pd_waypoint
    pd_neighbour_wp = bl_neighbour.pd_waypoint

    pd_neighbours = pd_waypoint.neighbours_coll

    # check if the neighbour already exists
    for neighbour in pd_neighbours:
        if neighbour.id == pd_waypoint.id:
            return

    neighbour_item = pd_neighbours.add()
    neighbour_item.name = wp_name(pd_neighbour_wp.id)
    neighbour_item.groupnum = pd_neighbour_wp.groupnum
    neighbour_item.id = pd_neighbour_wp.id

    edge = pdprops.WAYPOINT_EDGETYPES[0][0]
    neighbour_item.edgetype = edge

def wp_nextid():
    wp_coll = bpy.data.collections['Waypoints']
    return 1 + max([wp.pd_waypoint.id for wp in wp_coll.objects], default=0)

def wp_remove_neighbour(pd_waypoint, id):
    neighbours_coll = pd_waypoint.neighbours_coll
    for idx, neighbour in enumerate(neighbours_coll):
        if neighbour.id == id:
            neighbours_coll.remove(idx)

            # check if the active neighbor is the last one...
            n_nbs = len(neighbours_coll)
            nb_idx = pd_waypoint.active_neighbour_idx
            # ... if so, update it
            if nb_idx >= n_nbs:
                pd_waypoint.active_neighbour_idx = n_nbs - 1
            return

def wp_newgroup():
    groupnum = wp_maxgroup()
    groupname = pdu.group_name(groupnum)
    bl_group = pdu.new_empty_obj(groupname, dsize=0, link=False)
    pdu.add_to_collection(bl_group, 'Waypoints')

    return groupnum, bl_group

def wp_maxgroup():
    n = 0
    wp_coll = bpy.data.collections['Waypoints']
    for group in wp_coll.objects:
        if group.parent is not None: continue
        n += 1

    return n
