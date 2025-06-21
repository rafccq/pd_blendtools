import os
import time
from math import pi
from collections import namedtuple
import glob
from functools import cache

import bpy
from mathutils import Vector, Euler, Matrix

import pd_materials as pdm
from pd_setupfile import PD_SetupFile
import pd_padsfile as pdp
from decl_setupfile import *
from decl_padsfile import *
from typeinfo import TypeInfo
import pd_utils as pdu
import model_import as mdi
from filenums import ModelStates
import template_mesh as tmesh
import pd_blendprops as pdprops
import nodes.nodeutils as ndu


M_BADPI = 3.141092641

# these objects have a 'base' struct preceding the obj data
obj_types1 = [
    OBJTYPE_DOOR,
    OBJTYPE_MULTIAMMOCRATE,
    OBJTYPE_GLASS,
    OBJTYPE_LIFT,
    OBJTYPE_HOVERPROP,
    OBJTYPE_HOVERCAR,
    OBJTYPE_HOVERBIKE,
    OBJTYPE_AMMOCRATE,
    OBJTYPE_AUTOGUN,
    OBJTYPE_TINTEDGLASS,
    OBJTYPE_WEAPON,
]

obj_types2 = [
    OBJTYPE_BASIC,
    OBJTYPE_ALARM,
    OBJTYPE_DEBRIS,
    OBJTYPE_GASBOTTLE,
    OBJTYPE_29,
    OBJTYPE_SAFE,
]


def register():
    TypeInfo.register_all(setupfile_decls)
    TypeInfo.register_all(padsfile_decls)
    mdi.register()

def obj_setup_mtx(obj, look, up, pos, rotation=None, scale=None, flags=None, bbox=None):
    side = up.cross(look).normalized()
    up = look.cross(side).normalized()

    M = Matrix([
        [side.x, up.x, look.x, 0],
        [side.y, up.y, look.y, 0],
        [side.z, up.z, look.z, 0],
        [0, 0, 0, 1]
    ])

    T = Matrix.Identity(4)
    if scale:
        sx = Matrix.Scale(scale.x, 4, (1.0, 0.0, 0.0))
        sy = Matrix.Scale(scale.y, 4, (0.0, 1.0, 0.0))
        sz = Matrix.Scale(scale.z, 4, (0.0, 0.0, 1.0))
        T = T @ sx @ sy @ sz

    if rotation:
        rot_mat = Euler(rotation).to_matrix().to_4x4()
        T = T @ rot_mat

    newpos = pos
    if flags is not None:
        if flags & OBJFLAG_00000002:
            newpos = tuple([pos[i] - T[i][2] * bbox.zmin for i in range(3)])
            # print(f'  OBJFLAG_00000002')
        elif bbox is not None:
            ymin, ymax = bbox.ymin, bbox.ymax
            if flags & OBJFLAG_UPSIDEDOWN:
                rot = Euler((0, 0, M_BADPI)).to_matrix().to_4x4()
                T = T @ rot
                newpos = tuple([pos[i] - T[i][1] * ymax for i in range(3)])
                # print(f'  OBJFLAG_UPSIDEDOWN')
            elif flags & OBJFLAG_00000008:
                TMP = M @ T
                newpos = tuple([pos[i] - TMP[i][1] * ymin for i in range(3)])
                # print(f'  OBJFLAG_00000008 {pos} {newpos} {ymin} {bbox}')

    obj.matrix_world = M @ T
    obj.matrix_world.translation = newpos

    # print(f'  newpos {newpos}')


def obj_load_model(romdata, modelnum):
    scn = bpy.context.scene

    filenum = ModelStates[modelnum].filenum

    modelname = romdata.filenames[filenum]
    load_external = scn.level_external_models and modelname in scn['external_models']

    if load_external:
        filename = f'{scn.external_models_dir}/{modelname}'
        return mdi.import_model(romdata, single_mesh=True, filename=filename)
    else:
        return mdi.import_model(romdata, single_mesh=True, modelname=modelname)

def blender_align(obj):
    rot_mat = Euler((pi/2, 0, pi/2)).to_matrix().to_4x4()
    obj.matrix_world = rot_mat @ obj.matrix_world

def set_bbox(dst_bbox, src_bbox):
    bbox = [src_bbox.xmin, src_bbox.xmax, src_bbox.ymin, src_bbox.ymax, src_bbox.zmin, src_bbox.zmax]
    for i, val in enumerate(bbox):
        dst_bbox[i] = val

def init_door(bl_door, prop, pad, bbox):
    bl_door.pd_obj.type = pdprops.PD_PROP_DOOR

    pd_door = bl_door.pd_door
    pd_prop = bl_door.pd_prop
    pd_pad = pd_prop.pad

    # base obj props
    pd_prop.modelnum = prop['base']['modelnum']
    pd_prop.extrascale = prop['base']['extrascale']
    pd_prop.maxdamage = prop['base']['maxdamage']
    pd_prop.floorcol = prop['base']['floorcol']

    pdu.flags_unpack(pd_prop.flags1, prop['base']['flags'], [e[1] for e in pdprops.OBJ_FLAGS1])
    pdu.flags_unpack(pd_prop.flags2, prop['base']['flags2'], [e[1] for e in pdprops.OBJ_FLAGS2])
    pdu.flags_unpack(pd_prop.flags3, prop['base']['flags3'], [e[1] for e in pdprops.OBJ_FLAGS3])

    # door props
    door_type = ndu.item_from_value(pdprops.DOORTYPES, prop['doortype'])
    pd_door.door_type = ndu.make_id(door_type)
    sound_type = ndu.item_from_value(pdprops.DOOR_SOUNDTYPES, prop['soundtype'])
    pd_door.sound_type = ndu.make_id(sound_type)

    pd_door.maxfrac = prop['maxfrac']/65536
    pd_door.perimfrac = prop['perimfrac']/65536
    pd_door.accel = prop['accel']/65536000
    pd_door.decel = prop['decel']/65536000
    pd_door.maxspeed = prop['maxspeed']/65536
    pd_door.autoclosetime = prop['autoclosetime']/65536

    pd_door.laserfade = prop['laserfade']

    pd_pad.padnum = prop['base']['pad']
    pd_pad.pos = pad.pos
    pd_pad.room = pdp.pad_room(pad)
    pd_pad.lift = pdp.pad_lift(pad)
    pd_pad.hasbbox = True # assuming doors always have a bbox (TODO verify)
    set_bbox(pd_pad.model_bbox, bbox)
    set_bbox(pd_pad.bbox, pad.bbox)
    set_bbox(pd_pad.bbox_p, pad.bbox)

    doorflags = prop['doorflags']
    for idx, flag in enumerate(pdprops.DOOR_FLAGS):
        pd_door.door_flags[idx] = bool(doorflags & flag[1])

    keyflags = prop['keyflags']
    for idx, flag in enumerate(pdprops.DOOR_KEYFLAGS):
        pd_door.key_flags[idx] = bool(keyflags & flag[1])

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

def setup_create_door(prop, romdata, paddata):
    padnum = prop['base']['pad']
    # print(f"{padnum:02X} {prop['base']['modelnum']:04X}")
    bl_door, model = obj_load_model(romdata, prop['base']['modelnum'])
    bl_door.name = f'door {padnum:02X}'

    pdu.add_to_collection(bl_door, 'Props')
    padnum = prop['base']['pad']

    fields = PADFIELD_POS | PADFIELD_LOOK | PADFIELD_UP | PADFIELD_NORMAL | PADFIELD_BBOX
    pad = paddata.pad_unpack(padnum, fields)
    hasbbox = paddata.pad_hasbbox(padnum)

    # print(f'prop {prop} pad {padnum:02X} pad {pad} fnum: {filenum:04X} fname {romdata.filenames[filenum]}')

    bbox = model.find_bbox()

    sx = (pad.bbox.ymax - pad.bbox.ymin) / (bbox.xmax - bbox.xmin)
    sy = (pad.bbox.zmax - pad.bbox.zmin) / (bbox.ymax - bbox.ymin)
    sz = (pad.bbox.xmax - pad.bbox.xmin) / (bbox.zmax - bbox.zmin)

    if sx <= 0.000001 or sy <= 0.000001 or sz <= 0.000001:
        sx = sy = sz = 1

    bl_door['pd_padnum'] = f'{padnum:02X}'

    center = pdp.pad_center(pad) if hasbbox else pad.pos
    rotation = (pi/2, 0, pi/2)
    obj_setup_mtx(bl_door, Vector(pad.look), Vector(pad.up), center, rotation)

    blender_align(bl_door)
    bl_door.scale = (sx, sy, sz)
    init_door(bl_door, prop, pad, bbox)
    bl_door.pd_prop.pad.padnum = padnum # TODO TMP

    return bl_door

def obj_make_opaque(bl_obj):
    def edit_mat(obj):
        if not obj.data: return
        for mat in obj.data.materials:
            pdm.mat_remove_links(mat, 'p_bsdf', ['Base Color', 'Alpha'])
            s = .12
            pdm.mat_set_basecolor(mat, (s, s, s, 1))

    edit_mat(bl_obj)
    for child in bl_obj.children: edit_mat(child)

def setup_create_obj(prop, romdata, pad):
    if not pad:
        print(f"TMP: skipping obj with no pad {prop['modelnum']:04X}")
        return None, None

    modelnum = prop['modelnum']
    OBJNAMES = {
        0x01: 'door',
        0x08: 'weapon',
        0x14: 'multi ammo crate',
        0x2a: 'glass',
        0x2f: 'tinted glass',
        0x30: 'lift',
    }

    proptype = prop['type']
    padnum = prop['pad']
    if proptype == OBJTYPE_WEAPON:
        bl_obj = tmesh.create_mesh(f'weapon {padnum:02X}', 'weapon')
        model = None
        bl_obj.show_wire = True
    else:
        bl_obj, model = obj_load_model(romdata, modelnum)

    pdu.add_to_collection(bl_obj, 'Props')

    name = OBJNAMES[proptype] if proptype in OBJNAMES else 'object'
    if proptype in [OBJTYPE_TINTEDGLASS, OBJTYPE_GLASS]:
        obj_make_opaque(bl_obj)

    bl_obj.name = f'{name} {padnum:02X}'
    bl_obj['modelnum'] = f'{modelnum:04X}'
    bl_obj['pad'] = f'{padnum:04X}'
    pd_prop = bl_obj.pd_prop
    pd_pad = pd_prop.pad

    pd_pad.padnum = padnum
    pd_prop.modelnum = modelnum

    scn = bpy.context.scene

    # fields = PADFIELD_POS | PADFIELD_LOOK | PADFIELD_UP | PADFIELD_NORMAL | PADFIELD_BBOX
    # pad = paddata.pad_unpack(padnum, fields)
    flags = prop['flags']
    # hasbbox = paddata.pad_hasbbox(padnum)
    hasbbox = pdp.pad_hasbbox(pad)

    modelscale = ModelStates[modelnum].scale if modelnum < len(ModelStates) else 0x1000
    pd_prop.modelscale = modelscale
    pd_prop.extrascale = prop['extrascale']
    pd_prop.maxdamage = prop['maxdamage']
    pd_prop.floorcol = prop['floorcol']
    pdu.flags_unpack(pd_prop.flags1, prop['flags'], [e[1] for e in pdprops.OBJ_FLAGS1])
    pdu.flags_unpack(pd_prop.flags2, prop['flags2'], [e[1] for e in pdprops.OBJ_FLAGS2])
    pdu.flags_unpack(pd_prop.flags3, prop['flags3'], [e[1] for e in pdprops.OBJ_FLAGS3])

    pd_prop.flags1_packed = f"{prop['flags']:08X}"
    pd_prop.flags2_packed = f"{prop['flags2']:08X}"
    pd_prop.flags3_packed = f"{prop['flags3']:08X}"

    pad_setprops(bl_obj, pad, padnum)

    modelscale *= prop['extrascale'] / (256 * 4096)

    rotation = None
    s = modelscale
    scale = pdp.Vec3(s, s, s) if proptype != OBJTYPE_WEAPON else pdp.Vec3(24, 24, 24)

    if flags & OBJFLAG_00000002: # logic from func0f06ab60
        rotation = (pi * 1.5, M_BADPI, 0)

    center = pad.pos

    # print(f'{bl_obj.name} pad {padnum} c {center} bbox {hasbbox}')

    bbox = None
    if hasbbox:
        bbox = model.find_bbox()
        set_bbox(pd_pad.model_bbox, bbox)
        sx, sy, sz = obj_getscale(modelscale, pad.bbox, bbox, flags)
        scale = pdp.Vec3(sx, sy, sz)

        cx, cy, cz = pdp.pad_center(pad)
        cx += (pad.bbox.ymin - pad.bbox.ymax) * 0.5 * pad.up.x
        cy += (pad.bbox.ymin - pad.bbox.ymax) * 0.5 * pad.up.y
        cz += (pad.bbox.ymin - pad.bbox.ymax) * 0.5 * pad.up.z
        center = pdp.Vec3(cx, cy, cz)

        # print(f'  c {center}')

    obj_setup_mtx(bl_obj, Vector(pad.look), Vector(pad.up), center, rotation, scale, flags, bbox)
    blender_align(bl_obj)

    if hasbbox:
        set_bbox(pd_pad.model_bbox, bbox)
        set_bbox(pd_pad.bbox, pad.bbox)
        set_bbox(pd_pad.bbox_p, pad.bbox)

    bl_obj.pd_obj.type = pdprops.PD_OBJTYPE_PROP | proptype
    return bl_obj, model

@cache
def get_setupdata(romdata):
    scn = bpy.context.scene

    if scn.import_src_setup == 'ROM':
        setupdata = romdata.filedata(scn.rom_setups)
    else:
        setupdata = pdu.read_file(scn.file_setup)

    if scn.import_src_pads == 'ROM':
        padsdata = romdata.filedata(f'bgdata/{scn.rom_pads}')
    else:
        padsdata = pdu.read_file(scn.file_pads)

    pdsetup = PD_SetupFile(setupdata)
    pdpads = pdp.PD_PadsFile(padsdata)

    return pdsetup, pdpads

def setup_import(romdata, all_props, objnum, duration):
    scn = bpy.context.scene

    if objnum == 0 and scn.level_external_models:
        path = scn.external_models_dir
        ext_models = []
        for filename in glob.iglob(f'{path}/P*'):
            filename = os.path.basename(filename).split('.')[0]
            ext_models.append(filename)
        scn['external_models'] = ext_models

    pdsetup, pdpads = get_setupdata(romdata)

    t = time.time()
    if objnum == 0:
        import_intro(pdsetup.introcmds, pdpads)
        import_waypoints(pdpads)
        import_coverpads(pdpads)
        print(f'LOAD_SETUP_INTRO {time.time() - t:2.1f}')

    return import_objects(romdata, pdsetup, pdpads, all_props, objnum, duration)

def import_objects(romdata, setupdata, paddata, all_props, objnum, duration):
    wm = bpy.context.window_manager
    stepmsg = pdu.msg_import_step(wm)

    dt = 0
    nobjs = len(setupdata.props)

    while dt < duration and objnum < nobjs:
        t_start = time.time()
        wm.progress = objnum / nobjs
        wm.progress_msg = f'{stepmsg}Loading Object {objnum}/{nobjs}...'

        prop = setupdata.props[objnum]

        proptype = prop['_type_']
        # name = OBJ_NAMES[proptype]
        type1 = proptype in obj_types1
        type2 = proptype in obj_types2

        # print(f'{idx} TYPE {proptype:02X}')
        if proptype == OBJTYPE_DOOR:
            # print(f"DOOR p {b['pad']:04X} m {b['modelnum']:04X}")
            bl_door = setup_create_door(prop, romdata, paddata)
            all_props.append(bl_door)
        elif type1 or type2:
            obj = prop['base'] if type1 else prop

            # print(f"OBJ1 p {obj['pad']:04X} m {obj['modelnum']:04X}")
            fields = PADFIELD_POS | PADFIELD_LOOK | PADFIELD_UP | PADFIELD_NORMAL | PADFIELD_BBOX
            pad = paddata.pad_unpack(obj['pad'], fields)
            bl_prop, model = setup_create_obj(obj, romdata, pad)
            if not bl_prop:
                all_props.append(None)
                dt += time.time() - t_start
                objnum += 1
                continue

            if proptype == OBJTYPE_LIFT:
                # pad = paddata.pad_unpack(padnum, PADFIELD_POS | PADFIELD_BBOX)
                init_lift(bl_prop, prop, paddata, model)
            elif proptype == OBJTYPE_TINTEDGLASS:
                init_tintedglass(bl_prop, prop)
            elif proptype == OBJTYPE_WEAPON:
                init_weapon(bl_prop, prop)

            all_props.append(bl_prop)
        else:
            # to make sure both lists have the same size
            all_props.append(None)

        dt += time.time() - t_start
        objnum += 1

    done = objnum == nobjs
    if done:
        setup_fix_refs(all_props, setupdata.props)

    return done, objnum

def init_lift(bl_prop, prop, paddata, model):
    bl_prop.pd_lift.accel = prop['accel'] / 0x10000
    bl_prop.pd_lift.maxspeed = prop['maxspeed'] / 0x10000
    # ## Create lift stops
    for idxpad, pad_stop in enumerate(prop['pads']):
        padnum = pdu.s16(pad_stop)
        if padnum < 0: continue

        pad = paddata.pad_unpack(padnum, PADFIELD_POS | PADFIELD_BBOX)
        name = f'{bl_prop.name} stop{idxpad} (P{padnum:02X})'
        bl_stop = pdu.new_empty_obj(name, bl_prop, dsize=50, dtype='CIRCLE', link=False)
        bl_stop.pd_obj.type = pdprops.PD_PROP_LIFT_STOP
        bl_stop.matrix_world.translation = pad.pos
        pdu.add_to_collection(bl_stop, 'Props')
        blender_align(bl_stop)
        if idxpad == 0:
            bl_prop.pd_lift.stop1 = bl_stop
        elif idxpad == 1:
            bl_prop.pd_lift.stop2 = bl_stop
        elif idxpad == 2:
            bl_prop.pd_lift.stop3 = bl_stop
        elif idxpad == 3:
            bl_prop.pd_lift.stop4 = bl_stop

        # copy pad info
        bbox = model.find_bbox()
        pd_pad = bl_stop.pd_prop.pad
        pd_pad.pos = pad.pos
        pd_pad.room = pdp.pad_room(pad)
        pd_pad.lift = pdp.pad_lift(pad)
        pd_pad.hasbbox = True
        set_bbox(pd_pad.model_bbox, bbox)
        set_bbox(pd_pad.bbox, pad.bbox)

def door_setsibling(bl_door, prop, setup_props, pad2obj, idx):
    sibling_ofs = pdu.s32(prop['sibling'])
    if sibling_ofs == 0: return

    sibling = setup_props[idx + sibling_ofs]
    sibling_pad = sibling['base']['pad']
    bl_door.pd_door.sibling = pad2obj[sibling_pad]

def lift_setdoor(bl_lift, prop, setup_props, pad2obj, idx):
    for dooridx, ofs in enumerate(prop['doors']):
        if ofs == 0: continue

        pad = setup_props[idx + ofs]['base']['pad']
        door = pad2obj[pad]
        if dooridx == 0:
            bl_lift.pd_lift.door1 = door
        elif dooridx == 1:
            bl_lift.pd_lift.door2 = door
        elif dooridx == 2:
            bl_lift.pd_lift.door3 = door
        elif dooridx == 3:
            bl_lift.pd_lift.door4 = door

def lift_setinterlink(prop, setup_props, pad2obj, idx):
    lift_ofs = pdu.s32(prop['lift'])
    if lift_ofs == 0: return

    lift_prop = setup_props[idx + lift_ofs]
    lift_pad = lift_prop['base']['pad']
    bl_lift = pad2obj[lift_pad]
    pd_interlinks = bl_lift.pd_lift.interlinks
    interlink = pd_interlinks.add()
    interlink.name = f'{bl_lift.name} Interlink {len(pd_interlinks)}'
    interlink.controlled = bl_lift
    interlink.pd_obj.type = OBJTYPE_LINKLIFTDOOR | pdprops.PD_OBJTYPE_PROP

    door_ofs = pdu.s32(prop['door'])
    if door_ofs != 0:
        door_prop = setup_props[idx + door_ofs]
        door_pad = door_prop['base']['pad']
        bl_door = pad2obj[door_pad]
        interlink.controller = bl_door

    interlink.stopnum = prop['stopnum'] + 1

def init_tintedglass(bl_prop, prop):
    pd_tintedglass = bl_prop.pd_tintedglass
    pd_tintedglass.opadist = prop['opadist']
    pd_tintedglass.xludist = prop['xludist']

def init_weapon(bl_prop, prop):
    pd_weapon = bl_prop.pd_weapon
    pd_weapon.weaponnum = prop['weaponnum']

def setup_fix_refs(all_props, setup_props):
    pad2obj = {prop.pd_prop.pad.padnum: prop for prop in all_props if prop}
    for idx, bl_prop in enumerate(all_props):
        prop = setup_props[idx]
        proptype = prop['_type_']
        if proptype == OBJTYPE_DOOR:
            door_setsibling(bl_prop, prop, setup_props, pad2obj, idx)
        elif proptype == OBJTYPE_LIFT:
            lift_setdoor(bl_prop, prop, setup_props, pad2obj, idx)
        elif proptype == OBJTYPE_LINKLIFTDOOR:
            lift_setinterlink(prop, setup_props, pad2obj, idx)

IntroCfg = namedtuple('IntroCfg', 'padidx name pdtype')
def import_intro(introcmds, paddata):
    intro_cfg = {
        INTROCMD_SPAWN:         IntroCfg(0, 'Spawn', pdprops.PD_INTRO_SPAWN),
        INTROCMD_HILL:          IntroCfg(0, 'Hill', pdprops.PD_INTRO_HILL),
        INTROCMD_CASE:          IntroCfg(1, 'Case', pdprops.PD_INTRO_CASE),
        INTROCMD_CASERESPAWN:   IntroCfg(1, 'CaseRespawn', pdprops.PD_INTRO_CASERESPAWN),
    }
    for cmd in introcmds:
        key = cmd['cmd']

        if key not in intro_cfg: continue

        cfg = intro_cfg[key]
        padnum = cmd['params'][cfg.padidx]
        name = cfg.name
        pdtype = cfg.pdtype
        pad = paddata.pad_unpack(padnum, PADFIELD_POS | PADFIELD_LOOK | PADFIELD_UP)
        create_intro_obj(name, pad, padnum, pdtype)

def create_intro_obj(name, pad, padnum, objtype, sc=16):
    meshname = name.lower()
    name = f'{name}_{padnum:02X}'
    intro_obj = tmesh.create_mesh(name, meshname)
    intro_obj.show_wire = True
    collection = pdu.new_collection('Intro')
    collection.objects.link(intro_obj)
    obj_setup_mtx(intro_obj, Vector(pad.look), Vector(pad.up), pad.pos, scale = pdp.Vec3(sc, sc, sc))
    blender_align(intro_obj)
    intro_obj.rotation_euler[0] -= pi/2
    intro_obj.rotation_euler[2] -= pi/2

    intro_obj.pd_obj.type = objtype
    pad_setprops(intro_obj, pad, padnum)


def pad_setprops(bl_obj, pad, padnum):
    pd_pad = bl_obj.pd_prop.pad
    pd_pad.padnum = padnum
    pd_pad.hasbbox = pdp.pad_hasbbox(pad)
    pd_pad.room = pdp.pad_room(pad)
    pd_pad.lift = pdp.pad_lift(pad)
    padflags = pdp.pad_flags(pad)

    # we need to clear these flags because they will be automatically set on export
    padflags &= ~PADFLAG_UPALIGNTOX
    padflags &= ~PADFLAG_UPALIGNTOY
    padflags &= ~PADFLAG_UPALIGNTOZ
    padflags &= ~PADFLAG_LOOKALIGNTOX
    padflags &= ~PADFLAG_LOOKALIGNTOY
    padflags &= ~PADFLAG_LOOKALIGNTOZ

    pdu.flags_unpack(pd_pad.flags, padflags, [e[1] for e in pdprops.pad_flags])

def import_waypoints(paddata):
    scn = bpy.context.scene

    waypoints = paddata.waypoints

    scn['waypoints'] = {}
    groups = []
    for idx, wp in enumerate(waypoints):
        padnum = wp['padnum']
        if padnum == 0xffffffff: break

        groupnum = wp['groupnum']

        groupname = pdu.group_name(groupnum)
        if groupnum not in groups:
            bl_group = pdu.new_empty_obj(groupname, dsize=0, link=False)
            bl_group.pd_obj.type = pdprops.PD_OBJTYPE_WAYGROUP
            pdu.add_to_collection(bl_group, 'Waypoints')
            groups.append(groupnum)

        pad = paddata.pad_unpack(padnum, PADFIELD_POS | PADFIELD_UP | PADFIELD_LOOK)
        bl_waypoint = create_waypoint(idx, pad.pos, groupnum, pad)

        pd_waypoint = bl_waypoint.pd_waypoint
        bl_waypoint.pd_prop.pad.padnum = padnum  # TODO TMP

        pad_setprops(bl_waypoint, pad, padnum)

        pd_neighbours = pd_waypoint.neighbours_coll
        for block in wp['neighbours_list']:
            neighbour = block['value']
            if neighbour == 0xffffffff: break

            neighbour_wp = waypoints[neighbour & 0x3fff]
            neighbour_item = pd_neighbours.add()
            neighbour_item.name = pdu.waypoint_name(neighbour_wp['padnum'])
            neighbour_item.groupnum = neighbour_wp['groupnum']
            neighbour_item.id = neighbour & 0x3fff

            idxs = { 0: 0, 0x4000: 1, 0x8000: 2, }
            edgeidx = idxs[neighbour & 0xc000]
            edge = pdprops.WAYPOINT_EDGETYPES[edgeidx][0]
            neighbour_item.edgetype = edge

def create_waypoint(pad_id, pos, groupnum, pad=None):
    objname = pdu.waypoint_name(pad_id)
    groupname = pdu.group_name(groupnum)
    bl_group = bpy.data.objects[groupname]
    bl_waypoint = tmesh.create_mesh(objname, 'cube')
    bl_waypoint.parent = bl_group

    pd_waypoint = bl_waypoint.pd_waypoint
    pd_waypoint.id = pad_id
    pd_waypoint.groupnum = groupnum
    pd_waypoint.group_enum = groupname

    bl_waypoint.color = (0.0, 0.8, 0.0, 1.0)
    if len(bl_waypoint.data.materials) == 0:
        wp_material = pdm.waypoint_material()
        bl_waypoint.data.materials.append(wp_material)

    bl_waypoint.pd_obj.type = pdprops.PD_OBJTYPE_WAYPOINT
    bl_waypoint.pd_obj.name = objname
    pdu.add_to_collection(bl_waypoint, 'Waypoints')

    bl_waypoint.matrix_world.translation = pos

    if pad:
        obj_setup_mtx(bl_waypoint, Vector(pad.look), Vector(pad.up), pad.pos, scale=pdp.Vec3(7,7,7))
        blender_align(bl_waypoint)
    else:
        bl_waypoint.scale = (7, 7, 7)

    scn = bpy.context.scene
    waypoints = scn['waypoints']
    waypoints[str(pad_id)] = bl_waypoint
    return bl_waypoint

def import_coverpads(paddata):
    for idx, cover in enumerate(paddata.covers):
        create_coverpad(cover, idx)

def create_coverpad(cover, idx):
    objname = f'cover_{idx:02X}'
    bl_cover = tmesh.create_mesh(objname, 'cube', copy=True)

    # pd_cover = bl_cover.cover

    bl_cover.color = (0.8, 0.0, 0.0, 1.0)
    if len(bl_cover.data.materials) == 0:
        cover_mat = pdm.cover_material()
        bl_cover.data.materials.append(cover_mat)

    bl_cover.pd_obj.type = pdprops.PD_OBJTYPE_COVER
    bl_cover.pd_obj.name = objname
    pdu.add_to_collection(bl_cover, 'Cover Pads')

    pos = [pdu.f32(cover['pos'][key]) for key in ['x', 'y', 'z']]
    look = [pdu.f32(cover['look'][key]) for key in ['x', 'y', 'z']]
    up = (0, 1, 0)

    obj_setup_mtx(bl_cover, Vector(look), Vector(up), pos, scale=pdp.Vec3(7,7,7))
    blender_align(bl_cover)

    return bl_cover
