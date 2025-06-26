import bpy
from mathutils import Matrix, Vector, Euler

from decl_setupfile import *
from pd_mtx import M_BADPI
import pd_blendprops as pdprops
import model_import as mdi
from model_info import ModelStates
import romdata as rom
from model_info import ModelNames


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

def check_flags(packedflags, *flags):
    flagsval = 0
    for flag in flags:
        flagsval |= flag

    return packedflags & flagsval

def obj_hasmodel(pd_obj):
    return pd_obj.type in [
        pdprops.OBJTYPE_BASIC,
        pdprops.OBJTYPE_DOOR,
        pdprops.OBJTYPE_GLASS,
        pdprops.OBJTYPE_TINTEDGLASS,
        pdprops.OBJTYPE_LIFT,
        pdprops.OBJTYPE_MULTIAMMOCRATE,
    ]

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

def change_model(bl_obj, modelnum):
    if not bl_obj: return

    pd_prop = bl_obj.pd_prop

    if pd_prop.modelnum == modelnum: return

    romdata = rom.load()
    new_obj, _ = obj_load_model(romdata, modelnum)
    mesh = bl_obj.data
    mesh.clear_geometry()
    mesh.materials.clear()

    bl_obj.data = new_obj.data
    bpy.data.objects.remove(new_obj, do_unlink=True)
    bpy.data.meshes.remove(mesh, do_unlink=True)
    pd_prop.modelnum = modelnum
    pd_prop.modelname = ModelNames[modelnum]
