import os
from math import pi

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
import romdata as rom
from filenums import ModelStates
import template_mesh as tmesh
import pd_blendprops as pdprops
import nodes.nodeutils as ndu


M_BADPI = 3.141092641

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
        else:
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

def obj_load_model(romdata, modelnum):
    filenum = ModelStates[modelnum].filenum

    modelname = romdata.filenames[filenum]
    # print(f'loadmodel {modelname}')
    return mdi.import_model(romdata, modelname, link=False)

def blender_align(obj):
    rot_mat = Euler((pi/2, 0, pi/2)).to_matrix().to_4x4()
    obj.matrix_world = rot_mat @ obj.matrix_world

def set_bbox(dst_bbox, src_bbox):
    bbox = [src_bbox.xmin, src_bbox.xmax, src_bbox.ymin, src_bbox.ymax, src_bbox.zmin, src_bbox.zmax]
    for i, val in enumerate(bbox):
        dst_bbox[i] = val

def door_setprops(bl_door, prop, pad, bbox):
    bl_door.pd_obj.type = pdprops.PD_PROP_DOOR

    pd_door = bl_door.pd_door
    pd_prop = bl_door.pd_prop

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

    pd_prop.padnum = prop['base']['pad']

    pd_prop.pad_pos = pad.pos

    set_bbox(pd_prop.model_bbox, bbox)
    set_bbox(pd_prop.pad_bbox, pad.bbox)
    set_bbox(pd_prop.pad_bbox_p, pad.bbox)

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
    print(f"{padnum:02X} {prop['base']['modelnum']:04X}")
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
    door_setprops(bl_door, prop, pad, bbox)

    return bl_door

def setup_create_obj(prop, romdata, paddata):
    padnum = prop['pad']
    if padnum == 0xffff:
        print(f"TMP: skipping obj with no pad {prop['modelnum']:04X}")
        return None

    modelnum = prop['modelnum']
    OBJNAMES = {
        0x01: 'door',
        0x14: 'multi ammo crate',
        0x2a: 'glass',
        0x2f: 'tinted glass',
        0x30: 'lift',
    }

    bl_obj, model = obj_load_model(romdata, modelnum)

    proptype = prop['type']
    name = OBJNAMES[proptype] if proptype in OBJNAMES else 'object'
    if proptype in [OBJTYPE_TINTEDGLASS, OBJTYPE_GLASS]:
        for mat in bl_obj.data.materials:
            pdm.mat_remove_links(mat, 'p_bsdf', ['Base Color', 'Alpha'])
            s = .12
            pdm.mat_set_basecolor(mat, (s, s, s, 1))

    bl_obj.name = f'{name} {padnum:02X}'
    bl_obj['modelnum'] = f'{modelnum:04X}'
    bl_obj['pad'] = f'{padnum:04X}'
    pd_prop = bl_obj.pd_prop

    pdu.add_to_collection(bl_obj, 'Props')

    fields = PADFIELD_POS | PADFIELD_LOOK | PADFIELD_UP | PADFIELD_NORMAL | PADFIELD_BBOX
    pad = paddata.pad_unpack(padnum, fields)
    flags = prop['flags']
    hasbbox = paddata.pad_hasbbox(padnum)

    modelscale = ModelStates[modelnum].scale
    pd_prop.modelscale = modelscale
    pd_prop.extrascale = prop['extrascale']
    pd_prop.flags = prop['flags']

    modelscale *= prop['extrascale'] / (256 * 4096)

    bbox = model.find_bbox()
    set_bbox(bl_obj.pd_prop.model_bbox, bbox)
    sx, sy, sz = obj_getscale(modelscale, pad.bbox, bbox, flags)

    rotation = None
    scale = pdp.Vec3(sx, sy, sz)

    if flags & OBJFLAG_00000002: # logic from func0f06ab60
        rotation = (pi * 1.5, M_BADPI, 0)

    # print(f'{padnum:02X} {bl_obj.name}')
    center = pad.pos

    if hasbbox:
        cx, cy, cz = pdp.pad_center(pad)
        cx += (pad.bbox.ymin - pad.bbox.ymax) * 0.5 * pad.up.x
        cy += (pad.bbox.ymin - pad.bbox.ymax) * 0.5 * pad.up.y
        cz += (pad.bbox.ymin - pad.bbox.ymax) * 0.5 * pad.up.z
        center = pdp.Vec3(cx, cy, cz)

    obj_setup_mtx(bl_obj, Vector(pad.look), Vector(pad.up), center, rotation, scale, flags, bbox)
    blender_align(bl_obj)

    set_bbox(pd_prop.model_bbox, bbox)
    if hasbbox:
        set_bbox(pd_prop.pad_bbox, pad.bbox)
        set_bbox(pd_prop.pad_bbox_p, pad.bbox)

    return bl_obj

def setup_import(lvname, mp = False):
    blend_dir = os.path.dirname(bpy.data.filepath)
    romdata = rom.load(f'{blend_dir}/pd.ntsc-final.z64')

    mp = 'mp_' if mp else ''
    name = lvname.replace('bg_', '')
    filename = f'U{mp}setup{name}Z'
    setupdata = romdata.filedata(filename)
    setupdata = PD_SetupFile(setupdata)

    filename = f'bgdata/{lvname}_padsZ'
    paddata = romdata.filedata(filename)
    paddata = pdp.PD_PadsFile(paddata)

    import_objects(romdata, setupdata, paddata)
    import_intro(setupdata.introcmds, paddata)
    import_waypoints(paddata)

# these objects have a 'base' struct preceding the obj data
obj_types1 = [
    OBJTYPE_MULTIAMMOCRATE,
    OBJTYPE_GLASS,
    OBJTYPE_LIFT,
    OBJTYPE_HOVERPROP,
    OBJTYPE_HOVERCAR,
    OBJTYPE_HOVERBIKE,
    OBJTYPE_AMMOCRATE,
    OBJTYPE_AUTOGUN,
    OBJTYPE_TINTEDGLASS,
]

obj_types2 = [
    OBJTYPE_BASIC,
    OBJTYPE_ALARM,
    OBJTYPE_DEBRIS,
    OBJTYPE_GASBOTTLE,
    OBJTYPE_29,
    OBJTYPE_SAFE,
]

def import_objects(romdata, setupdata, paddata):
    all_props = []
    for idx, prop in enumerate(setupdata.props):
        proptype = prop['_type_']
        # name = OBJ_NAMES[proptype]
        type1 = proptype in obj_types1
        type2 = proptype in obj_types2

        # print(f'TYPE {proptype:02X}')
        if proptype == OBJTYPE_DOOR:
            # print(f"DOOR p {b['pad']:04X} m {b['modelnum']:04X}")
            bl_door = setup_create_door(prop, romdata, paddata)
            all_props.append(bl_door)
        elif type1 or type2:
            obj = prop['base'] if type1 else prop
            #     print(f"OBJ1 p {b['pad']:04X} m {b['modelnum']:04X}")
            bl_prop = setup_create_obj(obj, romdata, paddata)
            if not bl_prop:
                all_props.append(None)
                continue
            objtype = pdprops.PD_OBJTYPE_PROP | proptype
            bl_prop.pd_obj.type = objtype
            if proptype == OBJTYPE_LIFT:
                # TODO setup obj common props
                pd_prop = bl_prop.pd_prop
                pdu.flags_unpack(pd_prop.flags1, obj['flags'], [e[1] for e in pdprops.flags1])
                pdu.flags_unpack(pd_prop.flags2, obj['flags2'], [e[1] for e in pdprops.flags2])
                pdu.flags_unpack(pd_prop.flags3, obj['flags3'], [e[1] for e in pdprops.flags3])

                pd_prop.flags1_packed = f"{obj['flags']:08X}"
                pd_prop.flags2_packed = f"{obj['flags2']:08X}"
                pd_prop.flags3_packed = f"{obj['flags3']:08X}"

                bl_prop.pd_lift.accel = prop['accel'] / 0x10000
                bl_prop.pd_lift.maxspeed = prop['maxspeed'] / 0x10000
                bl_prop.pd_prop.padnum = obj['pad']
                # ## Create lift stops
                for idxpad, pad_stop in enumerate(prop['pads']):
                    padnum = pdu.s16(pad_stop)
                    if padnum < 0: continue
                    pad = paddata.pad_unpack(padnum, PADFIELD_POS | PADFIELD_BBOX)
                    name = f'{bl_prop.name} stop{idxpad} P-{padnum:02X}'
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

            all_props.append(bl_prop)
        else:
            # to make sure both lists have the same size
            all_props.append(None)

    setup_fix_refs(all_props, setupdata.props)

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

    door_ofs = pdu.s32(prop['door'])
    if door_ofs != 0:
        door_prop = setup_props[idx + door_ofs]
        door_pad = door_prop['base']['pad']
        bl_door = pad2obj[door_pad]
        interlink.controller = bl_door

    interlink.stopnum = prop['stopnum'] + 1

def setup_fix_refs(all_props, setup_props):
    pad2obj = {prop.pd_prop.padnum: prop for prop in all_props if prop}
    for idx, bl_prop in enumerate(all_props):
        prop = setup_props[idx]
        proptype = prop['_type_']
        if proptype == OBJTYPE_DOOR:
            door_setsibling(bl_prop, prop, setup_props, pad2obj, idx)
        elif proptype == OBJTYPE_LIFT:
            lift_setdoor(bl_prop, prop, setup_props, pad2obj, idx)
        elif proptype == OBJTYPE_LINKLIFTDOOR:
            lift_setinterlink(prop, setup_props, pad2obj, idx)

def import_intro(introcmds, paddata):
    for cmd in introcmds:
        if cmd['cmd'] == INTROCMD_SPAWN:
            padnum = cmd['params'][0]
            print('SPAWN', f"pad: {padnum:02X}")
            pad = paddata.pad_unpack(padnum, PADFIELD_POS | PADFIELD_LOOK | PADFIELD_UP)
            create_intro_obj('Spawn', pad, padnum)
        elif cmd['cmd'] == INTROCMD_HILL:
            padnum = cmd['params'][0]
            print('HILL', f"pad: {padnum:02X}")
            pad = paddata.pad_unpack(padnum, PADFIELD_POS | PADFIELD_LOOK | PADFIELD_UP)
            create_intro_obj('Hill', pad, padnum, 20)
        elif cmd['cmd'] == INTROCMD_CASE:
            padnum = cmd['params'][1]
            print('CASE', f"pad: {padnum:02X}")
            pad = paddata.pad_unpack(padnum, PADFIELD_POS | PADFIELD_LOOK | PADFIELD_UP)
            create_intro_obj('Case', pad, padnum)
        elif cmd['cmd'] == INTROCMD_CASERESPAWN:
            padnum = cmd['params'][1]
            print('CASERESPAWN', f"pad: {padnum:02X}")
            pad = paddata.pad_unpack(padnum, PADFIELD_POS | PADFIELD_LOOK | PADFIELD_UP)
            create_intro_obj('CaseRespawn', pad, padnum)

def create_intro_obj(name, pad, padnum, sc=16):
    meshname = name.lower()
    name = f'{name}_{padnum:02X}'
    spawn_obj = tmesh.create_mesh(name, meshname)
    spawn_obj.show_wire = True
    collection = pdu.new_collection('Intro')
    collection.objects.link(spawn_obj)
    obj_setup_mtx(spawn_obj, Vector(pad.look), Vector(pad.up), pad.pos, scale = pdp.Vec3(sc, sc, sc))
    blender_align(spawn_obj)
    spawn_obj.rotation_euler[0] -= pi/2
    spawn_obj.rotation_euler[2] -= pi/2


def import_waypoints(paddata):
    scn = bpy.context.scene

    waypoints = paddata.waypoints

    scn['waypoints'] = {}
    groups = []
    for i, wp in enumerate(waypoints):
        padnum = wp['padnum']
        if padnum == 0xffffffff: break

        groupnum = wp['groupnum']

        groupname = pdu.group_name(groupnum)
        if groupnum not in groups:
            bl_group = pdu.new_empty_obj(groupname, dsize=0, link=False)
            pdu.add_to_collection(bl_group, 'Waypoints')
            groups.append(groupnum)
        else:
            bl_group = bpy.data.objects[groupname]

        pad = paddata.pad_unpack(padnum, PADFIELD_POS)
        bl_waypoint = create_waypoint(padnum, pad.pos, bl_group)

        pd_waypoint = bl_waypoint.pd_waypoint
        pd_waypoint.padnum = padnum
        pd_waypoint.groupnum = groupnum
        pd_waypoint.group_enum = groupname
        pd_neighbours = pd_waypoint.neighbours_coll
        for idx, block in enumerate(wp['neighbours_list']):
            neighbour = block['value']
            if neighbour == 0xffffffff: break

            neighbour_wp = waypoints[neighbour&0xff]
            neighbour_item = pd_neighbours.add()
            neighbour_item.name = pdu.waypoint_name(neighbour_wp['padnum'])
            neighbour_item.groupnum = neighbour_wp['groupnum']
            neighbour_item.padnum = neighbour_wp['padnum']

            idxs = { 0: 0, 0x4000: 1, 0x8000: 2, }
            edgeidx = idxs[neighbour & 0xff00]
            edge = pdprops.WAYPOINT_EDGETYPES[edgeidx][0]
            neighbour_item.edgetype = edge

def create_waypoint(padnum, pos, bl_group, rotate=True):
    objname = pdu.waypoint_name(padnum)
    bl_waypoint = tmesh.create_mesh(objname, 'cube')
    bl_waypoint.parent = bl_group

    bl_waypoint.color = (0.0, 0.8, 0.0, 1.0)
    if len(bl_waypoint.data.materials) == 0:
        wp_material = pdm.waypoint_material()
        bl_waypoint.data.materials.append(wp_material)

    bl_waypoint.pd_obj.type = pdprops.PD_OBJTYPE_WAYPOINT
    bl_waypoint.pd_obj.name = objname
    pdu.add_to_collection(bl_waypoint, 'Waypoints')

    bl_waypoint.matrix_world.translation = pos

    if rotate:
        blender_align(bl_waypoint)

    bl_waypoint.scale = (7, 7, 7)

    scn = bpy.context.scene
    waypoints = scn['waypoints']
    waypoints[str(padnum)] = bl_waypoint
    return bl_waypoint
