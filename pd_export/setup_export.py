import bpy

from pd_import import setup_import as stpi
import pd_blendprops as pdprops
from utils import pd_utils as pdu
from pd_data.decl_setupfile import *
from data.bytestream import ByteStream, add_padding
from data.datablock import DataBlock
from data.typeinfo import TypeInfo

def export_intro(rd, dataout):
    lib = bpy.data.collections['Intro'].objects
    objects = [obj for obj in lib if pdu.pdtype(obj) == pdprops.PD_OBJTYPE_INTRO and not obj.hide_render]
    for bl_intro in objects:
        cmd = bl_intro.pd_obj.type & 0xff
        padnum = bl_intro.pd_prop.padnum

        numargs = cmd_size[cmd] - 1
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
            params[0] = bl_intro.pd_intro.case_setnum
            params[1] = padnum
        elif cmd == INTROCMD_CASERESPAWN:
            params[0] = bl_intro.pd_intro.case_setnum
            params[1] = padnum

        rd.write_block(dataout, block)

    rd.write(dataout, ENDMARKER_INTROCMD, 'u32')

def export(filename, compress):
    dataout = bytearray()
    bs = ByteStream(None)

    header = DataBlock.New('stagesetup')
    bs.write_block(dataout, header)

    ofs_props = len(dataout)
    export_objects(bs, dataout)

    ofs_intro = len(dataout)
    export_intro(bs, dataout)

    ofs_paths = export_paths(bs, dataout)
    ofs_ailists = export_ailists(bs, dataout)

    header.update(dataout, 'props', ofs_props)
    header.update(dataout, 'intro', ofs_intro)
    header.update(dataout, 'ailists', ofs_ailists)
    header.update(dataout, 'paths', ofs_paths)

    if compress:
        dataout = pdu.compress(dataout)

    pdu.write_file(filename, dataout)

def export_paths(bs, dataout):
    start = len(dataout)
    bs.write(dataout, 0, 's32') # end marker
    return start
    # write path blocks
    paths = []
    pathpads = []
    id = 0
    for bl_path in bpy.data.collections['Paths'].objects:
        if bl_path.pd_obj.type != pdprops.PD_OBJTYPE_PATH: continue

        block = DataBlock.New('path')
        block['id'] = id
        bs.write_block(dataout, block)

        paths.append(block)
        pads = [bl_pad for bl_pad in bl_path.children if bl_pad.pd_obj.type == pdprops.PD_OBJTYPE_PATHPAD]
        pathpads.append(pads)
        id += 1
    bs.write(dataout, 0, 's32') # end marker

    # write path pads
    ofs_pads = len(dataout)
    for block, pads in zip(paths, pathpads):
        block.update(dataout, 'pads', ofs_pads)
        for bl_pad in pads:
            bs.write(dataout, bl_pad.pd_prop.padnum, 's32')
        bs.write(dataout, -1, 's32')
        ofs_pads += len(dataout)

    return start

def add_list1000(bs, dataout):
    add_padding(dataout, 4)
    list1000_addr = len(dataout)

    list1000 = [0x01, 0x85, 0x01, 0x45, 0x01, 0x46, 0x00,
                0x05, 0xfd, 0x00, 0x00, 0x00, 0x04, 0x00]

    frame = bytes(list1000)
    block = DataBlock('', 0, frame)
    bs.write_block_raw(dataout, block)
    add_padding(dataout, 4)

    ofs = len(dataout)

    ailist_1000 = DataBlock.New('ailist')
    ailist_1000['list'] = list1000_addr
    ailist_1000['id'] = 0x1000
    bs.write_block(dataout, ailist_1000)
    return ofs

def export_ailists(bs, dataout):
    scn = bpy.context.scene
    ailists = scn.pd_ailists

    # first, write the lists bytes
    add_padding(dataout, 4)
    for li in ailists:
        li.addr = len(dataout)
        block = DataBlock('', 0, li.bytes)
        bs.write_block_raw(dataout, block)
        add_padding(dataout, 4)

    # the game will crash if there isn't at least one ailist
    ofs_ailists = len(dataout)

    if len(ailists) == 0:
        ofs_ailists = add_list1000(bs, dataout)

    # next, write the ailists structs (addrs and ids)
    for li in ailists:
        bs.write(dataout, li.addr, 'u32')
        bs.write(dataout, li.id, 'u32')

    # write the end marker
    end = DataBlock.New('ailist')
    bs.write_block(dataout, end)
    return ofs_ailists

def export_objects(rd, dataout):
    ObjCount = {}
    blockmap = {}
    lib = bpy.data.collections['Props'].objects
    objects = [obj for obj in lib if pdu.pdtype(obj) == pdprops.PD_OBJTYPE_PROP and not obj.hide_render]
    # remove multi-ammo crates from the list
    objects = [obj for obj in objects if obj.pd_obj.type != pdprops.PD_PROP_MULTIAMMOCRATE]

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

        objname = OBJ_NAMES[objtype]
        count = ObjCount[objtype] if objtype in ObjCount else 0
        ObjCount[objtype] = count + 1

        # print(f'{idx+1:03d} {bl_obj.name:<20} {pdu.pdtype(bl_obj):04X} {count} {objtype:02X}', 'p', f'{bl_obj.pd_prop.padnum:02X}')

        block = DataBlock.New(objtype)
        set_props(bl_obj, block)
        rd.write_block(dataout, block)
        blockmap[bl_obj.name] = block

        # insert the ammo crates linked to this weapon after it in the list
        ofs = 1
        if bl_obj.pd_obj.type == pdprops.PD_PROP_WEAPON:
            for child in bl_obj.children:
                if child.pd_obj.type != pdprops.PD_PROP_MULTIAMMOCRATE: continue
                objects.insert(idx + ofs, child)
                ofs += 1

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
        OBJTYPE_FAN: setup_fan,
        OBJTYPE_HOVERCAR: setup_hovercar,
        OBJTYPE_TAG: setup_tag,
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

def setup_fan(bl_obj, block):
    pd_fan = bl_obj.pd_fan

    block['yaccel'] = round(pd_fan.yaccel * 0x10000)
    block['ymaxspeed'] = round(pd_fan.ymaxspeed * 0x10000)
    block['on'] = 1
    block['base']['hidden2'] = 0x80

def setup_hovercar(bl_obj, block):
    pd_hovercar = bl_obj.pd_hovercar
    block['ailist'] = pd_hovercar.ailist

def setup_tag(bl_obj, block):
    pd_tag = bl_obj.pd_tag
    block['header']['type'] = OBJTYPE_TAG
    block['tagnum'] = pd_tag.tagnum

def setup_fix_refs(dataout, blockmap, objects):
    # print('---- REFS ----')
    for bl_obj in objects:
        objtype = bl_obj.pd_obj.type & 0xff
        if bl_obj.name not in blockmap: continue

        block = blockmap[bl_obj.name]

        if objtype == OBJTYPE_DOOR:
            pd_door = bl_obj.pd_door
            sibling = pd_door.sibling
            if sibling == None: continue

            door_idx = bl_obj['setup_index']
            sibling_idx = sibling['setup_index']
            diff = sibling_idx - door_idx

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

            block.update(dataout, 'doors', doors_ofs, signed=True)
        elif objtype == OBJTYPE_LINKLIFTDOOR:
            lift = bl_obj.controlled
            door = bl_obj.controller

            if lift is None:
                print(f'WARNING: interlink {bl_obj.name} has no controller object')
                continue

            if door is None:
                print(f'WARNING: interlink {bl_obj.name} has no controlled object')
                continue

            index = bl_obj['setup_index']
            lift_idx = lift['setup_index']
            door_idx = door['setup_index']
            lift_ofs = lift_idx - index
            door_ofs = door_idx - index
            block.update(dataout, 'lift', lift_ofs, signed=True)
            block.update(dataout, 'door', door_ofs, signed=True)
        elif objtype == OBJTYPE_TAG:
            tagged = bl_obj.pd_tag.obj

            if tagged is None:
                print(f'WARNING: Tag {bl_obj.name} has no object')
                continue

            index = bl_obj['setup_index']
            tagged_idx = tagged['setup_index']
            tagged_ofs = tagged_idx - index
            block.update(dataout, 'cmdoffset', tagged_ofs, signed=True)

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
