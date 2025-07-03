import bpy

from pd_import import setup_import as stpi
import pd_blendprops as pdprops
from utils import pd_utils as pdu
from pd_data.decl_setupfile import *
from data.bytestream import ByteStream
from data.datablock import DataBlock
from data.typeinfo import TypeInfo

def export_intro(rd, dataout):
    objects = [obj for obj in bpy.data.collections['Intro'].objects if pdu.pdtype(obj) == pdprops.PD_OBJTYPE_INTRO]
    for bl_intro in objects:
        cmd = bl_intro.pd_obj.type & 0xff
        padnum = bl_intro.pd_prop.padnum

        numargs = cmd_size[cmd] - 1
        # print('  cmd', cmd, 'n', numargs)
        TypeInfo.register('intro', decl_intro_cmd, varmap={'N': numargs})

        block = DataBlock.New('intro')
        params = block['params']
        block['cmd'] = cmd
        if cmd == INTROCMD_SPAWN:
            params[0] = padnum
            params[1] = 0
        elif cmd == INTROCMD_HILL:
            params[0] = padnum
        elif cmd == INTROCMD_CASE:
            # params[1] = setnum # TODO add set
            params[1] = padnum
        elif cmd == INTROCMD_CASERESPAWN:
            # params[1] = setnum # TODO add set
            params[1] = padnum

        rd.write_block(dataout, block)

    rd.write(dataout, ENDMARKER_INTROCMD, 'u32')

def export(filename, compress):
    dataout = bytearray()
    rd = ByteStream(None)

    header = DataBlock.New('stagesetup')
    rd.write_block(dataout, header)

    ofs_props = len(dataout)
    export_objects(rd, dataout)

    ofs_intro = len(dataout)
    export_intro(rd, dataout)

    header.update(dataout, 'props', ofs_props)
    header.update(dataout, 'intro', ofs_intro)

    if compress:
        dataout = pdu.compress(dataout)

    pdu.write_file(filename, dataout)

def export_objects(rd, dataout):
    ObjCount = {}
    blockmap = {}
    objects = [obj for obj in bpy.data.collections['Props'].objects if pdu.pdtype(obj) == pdprops.PD_OBJTYPE_PROP]

    # insert the lift interlinks in the object list, so they're exported as objects
    for idx, bl_obj in enumerate(objects):
        objtype = bl_obj.pd_obj.type & 0xff
        if objtype != OBJTYPE_LIFT: continue

        pd_lift = bl_obj.pd_lift
        interlinks = pd_lift.interlinks
        for ofs, interlink in enumerate(interlinks):
            objects.insert(idx + ofs + 1, interlink)

    for idx, bl_obj in enumerate(objects):
        bl_obj['setup_index'] = idx
        objtype = bl_obj.pd_obj.type & 0xff
        type1 = objtype in stpi.OBJ_TYPES1
        type2 = objtype in stpi.OBJ_TYPES2

        objname = OBJ_NAMES[objtype]
        count = ObjCount[objtype] if objtype in ObjCount else 0
        ObjCount[objtype] = count + 1

        # print(f'{idx+1:03d} {bl_obj.name:<20} {pdu.pdtype(bl_obj):04X} {count} {objtype:02X}', 'p', f'{bl_obj.pd_prop.padnum:02X}')

        block = DataBlock.New(objtype)
        set_props(bl_obj, block)
        rd.write_block(dataout, block)
        blockmap[bl_obj.name] = block

    setup_fix_refs(dataout, blockmap, objects)
    rd.write(dataout, OBJTYPE_END, 'u32')

def set_props(bl_obj, block):
    objtype = bl_obj.pd_obj.type & 0xff
    type1 = objtype in stpi.OBJ_TYPES1
    type2 = objtype in stpi.OBJ_TYPES2

    setup_funcs = {
        OBJTYPE_DOOR: setup_door,
        OBJTYPE_MULTIAMMOCRATE: setup_multiammocrate,
        OBJTYPE_TINTEDGLASS: setup_tintedglass,
        OBJTYPE_WEAPON: setup_weapon,
        OBJTYPE_LIFT: setup_lift,
        OBJTYPE_LINKLIFTDOOR: setup_linkliftdoor,
    }

    if type1 or type2:
        base = block['base'] if type1 else block
        setup_baseobj(bl_obj, base)

    if objtype in setup_funcs:
        setup_funcs[objtype](bl_obj, block)

def setup_baseobj(bl_obj, base):
    pd_prop = bl_obj.pd_prop

    base['type'] = bl_obj.pd_obj.type & 0xff
    base['pad'] = pd_prop.padnum
    base['modelnum'] = pd_prop.modelnum
    base['extrascale'] = pd_prop.extrascale
    base['maxdamage'] = pd_prop.maxdamage
    base['floorcol'] = pd_prop.floorcol
    base['flags']  = pdu.flags_pack(pd_prop.flags1, [e[1] for e in pdprops.OBJ_FLAGS1])
    base['flags2'] = pdu.flags_pack(pd_prop.flags2, [e[1] for e in pdprops.OBJ_FLAGS2])
    base['flags3'] = pdu.flags_pack(pd_prop.flags3, [e[1] for e in pdprops.OBJ_FLAGS3])

def setup_door(bl_obj, block):
    pd_door = bl_obj.pd_door

    block['doortype'] = pdprops.DOORTYPES_VALUES[pd_door.door_type]
    block['soundtype'] = pdprops.DOOR_SOUNDTYPES_VALUES[pd_door.sound_type]
    block['maxfrac'] = round(pd_door.maxfrac * 65536)
    block['perimfrac'] = round(pd_door.perimfrac * 65536)
    block['accel'] = round(pd_door.accel * 65536000)
    block['decel'] = round(pd_door.decel * 65536000)
    block['maxspeed'] = round(pd_door.maxspeed * 65536)
    block['autoclosetime'] = round(pd_door.autoclosetime * 65536)

    block['laserfade'] = pd_door.laserfade

    block['doorflags'] = pdu.flags_pack(pd_door.door_flags, [e[1] for e in pdprops.DOOR_FLAGS])
    block['keyflags'] = pdu.flags_pack(pd_door.key_flags, [e[1] for e in pdprops.DOOR_KEYFLAGS])

def setup_lift(bl_obj, block):
    pd_lift = bl_obj.pd_lift
    block['accel'] = round(pd_lift.accel * 65536)
    block['maxspeed'] = round(pd_lift.maxspeed * 65536)
    block['soundtype'] = pd_lift.sound

    pads = [-1]*4
    if pd_lift.stop1: pads[0] = pd_lift.stop1.pd_prop.padnum
    if pd_lift.stop2: pads[1] = pd_lift.stop2.pd_prop.padnum
    if pd_lift.stop3: pads[2] = pd_lift.stop3.pd_prop.padnum
    if pd_lift.stop4: pads[3] = pd_lift.stop4.pd_prop.padnum
    block['pads'] = pads

def setup_objheader(bl_obj, block):
    header = block['header']
    header['type'] = bl_obj.pd_obj.type & 0xff

def setup_linkliftdoor(interlink, block):
    setup_objheader(interlink, block)
    block['door'] = 0
    block['lift'] = 0
    block['stopnum'] = interlink.stopnum - 1

def setup_fix_refs(dataout, blockmap, objects):
    # print('---- REFS ----')
    for bl_obj in objects:
        objtype = bl_obj.pd_obj.type & 0xff
        if objtype == OBJTYPE_DOOR:
            pd_door = bl_obj.pd_door
            sibling = pd_door.sibling
            if sibling == None: continue

            door_idx = bl_obj['setup_index']
            sibling_idx = sibling['setup_index']
            diff = sibling_idx - door_idx

            block = blockmap[bl_obj.name]
            block.update(dataout, 'sibling', diff, signed=True)
            # print(f'{bl_obj.name}: {diff}')
        elif objtype == OBJTYPE_LIFT:
            pd_lift = bl_obj.pd_lift
            lift_idx = bl_obj['setup_index']
            doors = [pd_lift.door1, pd_lift.door2, pd_lift.door3, pd_lift.door4]
            doors_ofs = [0] * len(doors)

            for idx, door in enumerate(doors):
                if door == None: continue

                door_idx = door['setup_index']
                diff = door_idx - lift_idx
                doors_ofs[idx] = diff

                # print(f'{door.name} (lift): {diff}')

            block = blockmap[bl_obj.name]
            block.update(dataout, 'doors', doors_ofs, signed=True)
        elif objtype == OBJTYPE_LINKLIFTDOOR:
            lift = bl_obj.controlled
            door = bl_obj.controller

            if lift is None:
                print(f'WARNING: interlink {bl_obj.name} has no controller object')

            if door is None:
                print(f'WARNING: interlink {bl_obj.name} has no controlled object')

            block = blockmap[bl_obj.name]

            index = bl_obj['setup_index']
            lift_idx = lift['setup_index']
            door_idx = door['setup_index']
            lift_ofs = lift_idx - index
            door_ofs = door_idx - index
            block.update(dataout, 'lift', lift_ofs, signed=True)
            block.update(dataout, 'door', door_ofs, signed=True)

    # print('------------------')

def setup_multiammocrate(_bl_obj, block):
    slots = block['slots']
    for slot in slots:
        slot['modelnum'] = 0xffff

def setup_tintedglass(bl_obj, block):
    pd_tintedglass = bl_obj.pd_tintedglass

    block['xludist'] = pd_tintedglass.xludist
    block['opadist'] = pd_tintedglass.opadist
    block['portalnum'] = -1

def setup_weapon(bl_obj, block):
    pd_weapon = bl_obj.pd_weapon

    block['weaponnum'] = pd_weapon['weaponnum']
    block['dualweaponnum'] = -1
    block['timer240'] = -1
