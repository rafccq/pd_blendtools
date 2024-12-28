import os
from math import pi

import bpy
from mathutils import Vector, Euler, Matrix

import pd_materials as pdm
from pd_setupfile import PD_SetupFile
from pd_padsfile import PD_PadsFile, Vec3
from decl_setupfile import *
from decl_padsfile import *
from typeinfo import TypeInfo
import pd_utils as pdu
import pd_import as pdi
import romdata as rom
from filenums import ModelStates
import template_mesh as tmesh


M_BADPI = 3.141092641

def register():
    TypeInfo.register_all(setupfile_decls)
    TypeInfo.register_all(padsfile_decls)
    pdi.register()

def obj_setup_mtx(obj, pad, pos, rotation=None, scale=None, flags=None, bbox=None):
    look = Vector(pad.look)
    up = Vector(pad.up)

    side = up.cross(look).normalized()
    up = look.cross(side).normalized()

    M = Matrix([
        [side.x, up.x, look.x, 0],
        [side.y, up.y, look.y, 0],
        [side.z, up.z, look.z, 0],
        [0,0,0,1]
    ])

    T = Matrix.Identity(4)
    if scale:
        # print(f'scale {obj.name} {scale}')
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
                print('  OBJFLAG_UPSIDEDOWN on')
                rot = Euler((0, 0, M_BADPI)).to_matrix().to_4x4()
                T = T @ rot
                newpos = tuple([pos[i] - T[i][1] * ymax for i in range(3)])
            elif flags & OBJFLAG_00000008:
                TMP = M @ T
                newpos = tuple([pos[i] - TMP[i][1] * ymin for i in range(3)])
            else:
                # Row 0
                curval = T[1][0]
                if curval < 0.0: curval = -curval

                row = 0
                isnegative = T[1][row] < 0.0
                maxval = curval

                # Row 1
                curval = T[1][1]

                if curval < 0.0: curval = -curval

                if curval > maxval:
                    row = 1
                    isnegative = T[1][row] < 0.0
                    maxval = curval

                # Row 2
                curval = T[1][2]

                if curval < 0.0: curval = -curval

                if curval > maxval:
                    row = 2
                    isnegative = T[1][row] < 0.0
                    maxval = curval

                pmin, pmax = bbox.ymin, bbox.ymax
                if row == 0:
                    pmin = bbox.xmin
                    pmax = bbox.xmax
                elif row == 2:
                    pmin = bbox.zmin
                    pmax = bbox.zmax

                if isnegative:
                    tmp = pmin
                    pmin = pmax
                    pmax = tmp

                newpos = tuple([pos[i] - T[i][row] * pmin for i in range(3)])

    obj.matrix_world = M @ T
    obj.matrix_world.translation = newpos

def obj_load_model(romdata, modelnum):
    filenum = ModelStates[modelnum].filenum

    modelname = romdata.filenames[filenum]
    return pdi.import_model(romdata, modelname, link=False)

def blender_align(obj):
    rot_mat = Euler((pi/2, 0, pi/2)).to_matrix().to_4x4()
    obj.matrix_world = rot_mat @ obj.matrix_world

def setup_create_door(prop, romdata, paddata):
    padnum = prop['base']['pad']
    print(f"{padnum:02X} {prop['base']['modelnum']:04X}")
    model_obj, model = obj_load_model(romdata, prop['base']['modelnum'])

    pdu.add_to_collection(model_obj, 'Props')
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

    # sc = max(sx, sy, sz)
    # sc *= pdu.f32(model.modeldef['scale'])
    model_obj['pd_padnum'] = f'{padnum:02X}'

    center = PD_PadsFile.pad_center(pad) if hasbbox else pad.pos
    rotation = (pi/2, 0, pi/2)
    obj_setup_mtx(model_obj, pad, center, rotation)

    blender_align(model_obj)
    model_obj.scale = (sx, sy, sz)

def setup_create_obj(obj, romdata, paddata):
    padnum = obj['pad']
    # print(f'{padnum:04X}')
    if padnum == 0xffff:
        print(f"TMP: skipping obj with no pad {obj['modelnum']:04X}")
        return

    modelnum = obj['modelnum']

    model_obj, model = obj_load_model(romdata, modelnum)

    if obj['type'] in [OBJTYPE_TINTEDGLASS, OBJTYPE_GLASS]:
        for child in model_obj.children:
            for mat in child.data.materials:
                pdm.mat_remove_links(mat, 'p_bsdf', ['Base Color', 'Alpha'])
                s = .12
                pdm.mat_set_basecolor(mat, (s, s, s, 1))

    model_obj['modelnum'] = f'{modelnum:04X}'
    model_obj['pad'] = f'{padnum:04X}'

    pdu.add_to_collection(model_obj, 'Props')

    fields = PADFIELD_POS | PADFIELD_LOOK | PADFIELD_UP | PADFIELD_NORMAL | PADFIELD_BBOX
    pad = paddata.pad_unpack(padnum, fields)
    flags = obj['flags']
    hasbbox = paddata.pad_hasbbox(padnum)

    center = pad.pos

    if hasbbox:
        cx, cy, cz = PD_PadsFile.pad_center(pad)
        cx += (pad.bbox.ymin - pad.bbox.ymax) * 0.5 * pad.up.x
        cy += (pad.bbox.ymin - pad.bbox.ymax) * 0.5 * pad.up.y
        cz += (pad.bbox.ymin - pad.bbox.ymax) * 0.5 * pad.up.z
        center = Vec3(cx, cy, cz)

    modelscale = ModelStates[modelnum].scale / 0x1000

    sx = sy = sz = 1.0
    modelscale *= obj['extrascale'] * (1.0 / 256.0)

    bbox = model.find_bbox()
    if hasbbox:
        # assuming here that models always have a bbox
        flag40 = OBJFLAG_YTOPADBOUNDS

        if flags & OBJFLAG_XTOPADBOUNDS:
            if bbox.xmin < bbox.xmax:
                if flags & OBJFLAG_00000002:
                    sx = (pad.bbox.xmax - pad.bbox.xmin) / ((bbox.xmax - bbox.xmin) * modelscale)
                else:
                    sx = (pad.bbox.xmax - pad.bbox.xmin) / ((bbox.xmax - bbox.xmin) * modelscale)

        if flags & flag40:
            if bbox.ymin < bbox.ymax:
                if flags & OBJFLAG_00000002:
                    sz = (pad.bbox.zmax - pad.bbox.zmin) / ((bbox.ymax - bbox.ymin) * modelscale)
                else:
                    sy = (pad.bbox.ymax - pad.bbox.ymin) / ((bbox.ymax - bbox.ymin) * modelscale)

        if flags & OBJFLAG_ZTOPADBOUNDS:
            if bbox.zmin < bbox.zmax:
                if flags & OBJFLAG_00000002:
                    sy = (pad.bbox.ymax - pad.bbox.ymin) / ((bbox.zmax - bbox.zmin) * modelscale)
                else:
                    sz = (pad.bbox.zmax - pad.bbox.zmin) / ((bbox.zmax - bbox.zmin) * modelscale)

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

        modelscale *= maxscale

    # print(f'prop {prop} pad {padnum:02X} pad {pad} fnum: {filenum:04X} fname {romdata.filenames[filenum]}')

    model_obj['pd_padnum'] = f'{padnum:02X}'

    rotation = None
    m = modelscale
    scale = Vec3(sx*m, sy*m, sz*m)

    if flags & OBJFLAG_00000002: # logic from func0f06ab60
        rotation = (pi * 1.5, M_BADPI, 0)

    print(f'{padnum:02X} {model_obj.name}')
    obj_setup_mtx(model_obj, pad, center, rotation, scale, flags, bbox)
    blender_align(model_obj)

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
    paddata = PD_PadsFile(paddata)

    import_objects(romdata, setupdata, paddata)
    import_intro(setupdata.introcmds, paddata)

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
    for idx, prop in enumerate(setupdata.props):
        isobj = 'base' in prop.fields
        proptype = prop['_type_']
        name = OBJ_NAMES[proptype]

        if proptype == OBJTYPE_DOOR:
            setup_create_door(prop, romdata, paddata)
        elif proptype in obj_types1:
            setup_create_obj(prop['base'], romdata, paddata)
        elif proptype in obj_types2:
            setup_create_obj(prop, romdata, paddata)

def import_intro(introcmds, paddata):
    for cmd in introcmds:
        if cmd['cmd'] == INTROCMD_SPAWN:
            padnum = cmd['params'][0]
            print('SPAWN', f"pad: {padnum:02X}")
            pad = paddata.pad_unpack(padnum, PADFIELD_POS | PADFIELD_LOOK | PADFIELD_UP)
            intro_obj('Spawn', pad, padnum)
        elif cmd['cmd'] == INTROCMD_HILL:
            padnum = cmd['params'][0]
            print('HILL', f"pad: {padnum:02X}")
            pad = paddata.pad_unpack(padnum, PADFIELD_POS | PADFIELD_LOOK | PADFIELD_UP)
            intro_obj('Hill', pad, padnum, 20)
        elif cmd['cmd'] == INTROCMD_CASE:
            padnum = cmd['params'][1]
            print('CASE', f"pad: {padnum:02X}")
            pad = paddata.pad_unpack(padnum, PADFIELD_POS | PADFIELD_LOOK | PADFIELD_UP)
            intro_obj('Case', pad, padnum)
        elif cmd['cmd'] == INTROCMD_CASERESPAWN:
            padnum = cmd['params'][1]
            print('CASERESPAWN', f"pad: {padnum:02X}")
            pad = paddata.pad_unpack(padnum, PADFIELD_POS | PADFIELD_LOOK | PADFIELD_UP)
            intro_obj('CaseRespawn', pad, padnum)

def intro_obj(name, pad, padnum, sc=16):
    meshname = name.lower()
    name = f'{name}_{padnum:02X}'
    spawn_obj = tmesh.create_mesh(name, meshname)
    spawn_obj.show_wire = True
    collection = pdu.new_collection('Intro')
    collection.objects.link(spawn_obj)
    # sc = 16
    obj_setup_mtx(spawn_obj, pad, pad.pos, scale = Vec3(sc, sc, sc))
    blender_align(spawn_obj)
    spawn_obj.rotation_euler[0] -= pi/2
    spawn_obj.rotation_euler[2] -= pi/2
