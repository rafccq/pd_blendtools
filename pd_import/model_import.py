import struct
import os
from collections import namedtuple
import glob
from enum import IntEnum

import bpy
import bmesh
from bpy.app.handlers import persistent
from mathutils import Vector

from pd_data.pd_model import unmask, PD_ModelFile
from pd_data.gbi import *
from pd_data.decl_model import *
from data.typeinfo import TypeInfo
from pd_data import texload as tex
from ui import mtxpalette as mtxp
from utils import (
    pd_utils as pdu,
    log_util as logu,
)
from materials import pd_materials as pdm
import pd_blendprops as pdprops

from fast64.f3d import f3d_material as f3dm


def update_log():
    logu.log_config(logger, logu.LOG_FILE_IMPORT)


logger = logu.log_get(__name__)
update_log()


class MeshLayer(IntEnum):
    OPA = 0
    XLU = 1


ASSET_TYPE_BG = 'BG'
ASSET_TYPE_OBJ = 'OBJ'
ASSET_TYPE_MODEL = 'MODEL'

PDMeshData = namedtuple('PDMeshData',
                        'opagdl xlugdl ptr_vtx ptr_col vtxdata coldata matrices')

def create_mesh(mesh, tex_configs, name, matcache, asset_type):
    mesh_data = bpy.data.meshes.new('mesh_data')

    verts = mesh.verts
    faces = mesh.tris
    tri2tex = mesh.tri2tex

    verts_xyz = [v.pos for v in verts]
    mesh_data.from_pydata(verts_xyz, [], faces)
    # mesh_data.validate(verbose=True)

    bl_obj = bpy.data.objects.new(name, mesh_data)

    logger.debug(f'[CREATEMESH] {name}')

    normals = []
    colors = []
    colors_mtx = []

    for i, v in enumerate(verts):
        if mesh.has_mtx:
            col_mtx = mtxp.mtx2color(v.mtxidx)
            colors_mtx.append(col_mtx)

            # add to the vertex group 'mtx'
            mtx = f'{v.mtxidx:02X}'
            vgroups = bl_obj.vertex_groups
            group = vgroups[mtx] if mtx in vgroups else vgroups.new(name=mtx)
            group.add([i], 0, 'REPLACE')

        normcolor = v.color # either a normal or color
        if normcolor is None: continue

        hascolors = not v.hasnormal

        if hascolors:
            colors.append(tuple([ci/255.0 for ci in normcolor]))
            normals.append((0,0,0))
        else:
            vn = tuple([int.from_bytes(normcolor[i:i+1], 'big', signed=True) for i in range(0,3)])
            n = Vector((vn[0], vn[1], vn[2]))
            normals.append(n.normalized())
            colors.append(tuple([ci/255.0 for ci in normcolor]))

        # c = normcolor
        # txtnorm = '' if hascolors else ' (N)'
        # txtnorm += '' if hascolors else ' (' + ''.join([f'{ni:<6.3f} ' for ni in normals[i]]) + ')'
        # txtidx = f' [{v.color_idx}]'
        # if idx == 0x27: print(f'vc {i:03d} ({c[0]:02X} {c[1]:02X} {c[2]:02X} {c[3]:02X}){txtnorm}{txtidx}')

    mesh_data.normals_split_custom_set_from_vertices(normals)
    mesh_data.update()

    me = mesh_data

    bm = bmesh.new()
    bm.from_mesh(me)

    bm.faces.ensure_lookup_table()
    bm.verts.ensure_lookup_table()

    # setup UVs and materials
    layer_uv = bm.loops.layers.uv.new("UVMap")
    layer_col = bm.loops.layers.color.new("Col")
    layeralpha = bm.loops.layers.color.new("Alpha")
    layer_mtx = bm.loops.layers.color.new("matrices") if mesh.has_mtx else None

    for idx, face in enumerate(bm.faces):
        matsetup = tri2tex[face.index]

        # logger.debug(f'face {idx} mat {matsetup.id()}')
        tc = None
        if matsetup.texnum in tex_configs:
            tc = tex_configs[matsetup.texnum]
        else:
            print(f'WARNING: No config found for tex {matsetup.texnum:04X}')

        n_mats = len(bl_obj.data.materials)
        matname = f'{name}_Mat{n_mats}_{matsetup.texnum:04X}'
        mathash = matsetup.hash()

        use_alpha = False
        if tc:
            fmt = tex.TexFormatGbiMapping[tc['format']]
            use_alpha = pdm.tex_has_alpha(fmt, tc['depth'])

        if mathash not in matcache:
            if should_use_f3d(matsetup, asset_type):
                matname += ' (F3D)'
                mat = pdm.material_create_f3d(bl_obj, matsetup, matname)
            else:
                mat = pdm.material_new(matsetup, use_alpha, matname)

            mat.hashed = mathash
            matcache[mathash] = mat.name
        else:
            matname = matcache[mathash]
            mat = bpy.data.materials[matname]

        if not pdm.mat_find_by_hash(bl_obj, mathash):
            bl_obj.data.materials.append(mat)

        mat_idx = bl_obj.data.materials.find(mat.name)
        face.material_index = mat_idx

        # sets up the verts uv data, colors and matrices
        for loop in face.loops:
            vert = verts[loop.vert.index]

            uv_sc = (1, 1)
            if tc:
                uv_sc = (1 / (32 * tc['width']), 1 / (32 * tc['height']))

            uv = (vert.uv[0] * uv_sc[0], vert.uv[1] * uv_sc[1])
            loop[layer_uv].uv = uv
            loop[layer_col] = colors[loop.vert.index]

            if mesh.has_mtx:
                loop[layer_mtx] = colors_mtx[loop.vert.index]

    # remove unused vertices
    verts_unused = []
    for idx,v in enumerate(bm.verts):
        if len(v.link_loops) == 0:
            logger.debug(f'v {v.index} (NO GEOMETRY)')
            verts_unused.append(v)

    for v in verts_unused:
        bm.verts.remove(v)

    bm.to_mesh(me)
    bm.free()

    return bl_obj

def should_use_f3d(matsetup, asset_type):
    if asset_type == ASSET_TYPE_MODEL: return True

    OFS_ENVMAP = 0
    OFS_TRANSLUCENT = 1
    OFS_OTHER = 2

    scn = bpy.context.scene
    ofs = 0 if asset_type == ASSET_TYPE_BG else 3
    settings = scn.import_settings.packed
    bit_set = lambda pos: settings & (1 << (pos + ofs))

    if bit_set(OFS_ENVMAP) and matsetup.has_envmap(): return True
    if bit_set(OFS_TRANSLUCENT) and matsetup.mat_is_translucent(): return True
    return bit_set(OFS_OTHER) != 0


def posNodeName(idx): return f'{idx:02X}.Position'

def create_joint(model, node, idx, depth, **kwargs):
    root_obj = kwargs['root_obj']
    node['_idx_'] = idx
    nodetype = node['type'] & 0xff

    if nodetype == 2:
        r = node['rodata']
        ro = model.find_rodata(node['rodata'])
        pos = ro['pos']
        # note: this is for external use so we use little-ending
        x = struct.unpack('f', pos['x'].to_bytes(4, 'little'))[0]
        y = struct.unpack('f', pos['y'].to_bytes(4, 'little'))[0]
        z = struct.unpack('f', pos['z'].to_bytes(4, 'little'))[0]

        parentaddr = unmask(node['parent'])
        parentnode = model.nodes[parentaddr] if parentaddr else None
        parentidx = parentnode['_idx_'] if parentnode and parentnode['type'] & 0xff == 2 else -1
        parentobj = root_obj

        if parentidx >= 0:
            parentname = posNodeName(parentidx)
            parentobj = pdu.active_collection().objects[parentname]

        joint_obj = pdu.new_obj(posNodeName(idx), parentobj)
        joint_obj.location = (x, y, z)

class ImportMeshData:
    def __init__(self, layer, has_mtx=False):
        self.nverts = 0
        self.verts = []
        self.tris = []
        self.tri_index = 0
        self.dbg = 0
        self.vtx_ofs = 0
        self.tri2tex = {} # tri -> texnum
        self.layer = layer
        # [0]: where the indexed vtxs starts, [1]: the gap size
        self.idx_correction = (0, 0)
        self.has_mtx = has_mtx

    def add_vertices(self, verts, idx = 0):
        # in some cases, indexed vertices have a gap, where the index is higher than the index
        # of the last vertex loaded, idx_correction is used to remove that gap
        self.idx_correction = (0, 0)

        diff = idx - (len(self.verts) - self.vtx_ofs)
        if idx == 0:
            self.vtx_ofs = len(self.verts)
        elif diff != 0:
            start = len(self.verts) - self.vtx_ofs
            self.idx_correction = (start, -diff)

        self.verts += verts

    def add_tri(self, tri, mat_setup):
        vofs = self.vtx_ofs
        iofs = self.idx_correction

        idx_correction = (
            iofs[1] if tri[0] > iofs[0] else 0,
            iofs[1] if tri[1] > iofs[0] else 0,
            iofs[1] if tri[2] > iofs[0] else 0,
        )

        t = (
            tri[0] + vofs + idx_correction[0],
            tri[1] + vofs + idx_correction[1],
            tri[2] + vofs + idx_correction[2],
        )

        if self.dbg: logger.debug(f'  f {len(self.tris)} {t} tidx {vofs}')

        self.tris.append(t)

        facenum = len(self.tris) - 1
        self.tri2tex[facenum] = mat_setup


class VtxBufferEntry:
    def __init__(self, pos=(0,0,0), uv=(0,0), color=None, color_idx=0, group_size=0, mtxidx=-1, hasnormal=False):
        self.pos = pos
        self.uv = uv
        self.color = color
        self.color_idx = color_idx
        self.group_size = group_size
        self.mtxidx = mtxidx
        self.meshes_loaded = []
        self.hasnormal = hasnormal

def gdl_read_data(pdmeshdata, idx, apply_mtx, layer=MeshLayer.OPA):
    ptr_vtx = pdmeshdata.ptr_vtx
    ptr_col = pdmeshdata.ptr_col
    vtxdata = pdmeshdata.vtxdata
    coldata = pdmeshdata.coldata
    nvtx = len(vtxdata) // 12

    col_ofs = 0

    sc = 1
    verts = pdu.read_vtxs(vtxdata, nvtx, sc)

    gdl = pdmeshdata.opagdl
    addr = 0
    bo='big'

    mesh_opa = ImportMeshData(layer)
    mesh_xlu = None
    mesh = mesh_opa
    mtxindex = -1
    model_mtxs = set()

    trinum = 0

    mat_setup = pdm.PDMaterialSetup()
    gdlnum = 0
    nverts = 0

    # these commands change the material setup
    MAT_CMDS = [
        G_SetOtherMode_L, G_SetOtherMode_H, G_SETCOMBINE,
        G_SETGEOMETRYMODE, G_CLEARGEOMETRYMODE,
        G_SETTIMG, G_TEXTURE, G_PDTEX
    ]

    while True:
        cmd = bytearray(gdl[addr:addr+8])
        op = cmd[0]

        if op == G_END:
            xlugdl = pdmeshdata.xlugdl
            if xlugdl and gdlnum == 0:
                gdl = xlugdl
                addr = 0
                gdlnum += 1
                # meshes in the xlu layer may use vertices loaded for the opa layer...
                vtxs = mesh.verts[-nverts:]
                mesh_xlu = ImportMeshData(MeshLayer.XLU, has_mtx=mesh.has_mtx)
                # ... so we need to copy them over to new xlu mesh
                mesh_xlu.add_vertices(vtxs)
                mesh = mesh_xlu
                trinum = 0
                continue
            else:
                break

        cmdint = int.from_bytes(cmd, bo)
        w1 = cmdint & 0xffffffff

        if op == G_TRI4:
            tris = pdu.read_tri4(cmd, 0)

            mat_setup.applied = True

            for tri in tris:
                mesh.add_tri(tri, mat_setup)
                trinum += 1
        elif op == G_VTX:
            nverts = ((cmd[1] & 0xf0) >> 4) + 1
            vtx_idx = cmd[1] & 0xf
            vtx_ofs = int.from_bytes(cmd[5:8], bo)

            segmented = (w1 & 0x05000000) == 0x05000000
            vstart = (vtx_ofs - ptr_vtx)//12 if segmented else vtx_ofs//12
            pos = pdmeshdata.matrices[mtxindex] if mtxindex >= 0 and apply_mtx else (0,0,0)

            logger.debug(f'  vstart {vstart} n {nverts} vidx {vtx_idx:01X} seg {segmented:08X} mtx {mtxindex}')

            col_addr = col_ofs - ptr_col if segmented else col_ofs
            col_data = coldata[col_addr:]
            vertlist = []
            for i, v in enumerate(verts[vstart:vstart+nverts]):
                vpos = (v[0] + pos[0], v[1] + pos[1], v[2] + pos[2])

                uv = (v[3], v[4])
                coloridx = v[5]
                c = color = col_data[coloridx:coloridx+4]

                hasnormal = mat_setup.has_envmap()
                vertlist.append(VtxBufferEntry(vpos, uv, color, coloridx, nverts, mtxindex, hasnormal))

            mesh.add_vertices(vertlist, vtx_idx)
        elif op == G_COL:
            col_ofs = (cmdint & 0xffffff)
        elif op == G_MTX:
            mtxindex = (cmdint & 0xffffff) // 0x40
            model_mtxs.add(mtxindex)
            mesh.has_mtx = True
        elif op in MAT_CMDS:
            if mat_setup.applied:
                mat_setup = mat_setup.copy()
            mat_setup.add_cmd(cmd)

        addr += 8

    return mesh_opa, mesh_xlu, model_mtxs

def create_model_mesh(idx, meshdata, tex_configs, apply_mtx, matcache):
    *gdldatas, model_mtxs = gdl_read_data(meshdata, idx, apply_mtx)
    n_submeshes = len(gdldatas)
    mesh_objs = []
    for sub_idx, gdldata in enumerate(gdldatas):
        if not gdldata: continue

        name = f'Node{idx:02X}'
        name += ' (xlu)' if gdldata.layer == MeshLayer.XLU else ''
        mesh_obj = create_mesh(gdldata, tex_configs, name, matcache)
        mesh_obj.pd_model.layer = gdldata.layer
        mesh_obj.pd_model.idx = idx
        mesh_obj.data['matrices'] = list(model_mtxs)
        mesh_objs.append(mesh_obj)
        logger.debug(f'ntri {len(gdldata.tris)} nverts {len(gdldata.verts)}')

    return mesh_objs

def mesh_merge(mesh_dst, mesh_src):
    mesh_dst.add_vertices(mesh_src.verts)
    for idx_tri, tri in enumerate(mesh_src.tris):
        mesh_dst.add_tri(tri, mesh_src.tri2tex[idx_tri])

def aggregate_mesh(finalmesh, idx, meshdata, apply_mtx):
    mesh_opa, mesh_xlu, _ = gdl_read_data(meshdata, idx, apply_mtx)

    if finalmesh:
        mesh_merge(finalmesh, mesh_opa)
    else:
        finalmesh = mesh_opa

    if mesh_xlu:
        mesh_merge(mesh_opa, mesh_xlu)

    return finalmesh

def create_model_meshes(model, name, apply_mtx, asset_type, matcache):
    tex_configs = {}
    for tc in model.texconfigs:
        texnum = tc['texturenum']
        tex_configs[texnum] = tc

    idx = 0
    mesh_objs = []
    single_mesh = asset_type == ASSET_TYPE_OBJ
    finalmesh = None
    for ro in model.rodatas:
        nodetype = ro['_node_type_']
        typeDL1 = nodetype in [0x4, 0x18]
        typeDL2 = nodetype == 0x16

        if typeDL1 or typeDL2:
            rodata = {k: ro[k] for k in ['vertices', 'colors', '_node_type_']}
            if typeDL1:
                for e in ['opagdl', 'xlugdl', 'numvertices']: rodata[e] = ro[e]
            if typeDL2:
                rodata['opagdl'] = ro['gdl']
                rodata['xlugdl'] = None
                rodata['numvertices'] = ro['unk00']*4

            ptr_vtx = rodata['vertices'] & 0xffffff
            ptr_col = pdu.align(ptr_vtx + rodata['numvertices']*12, 8)
            meshdata = PDMeshData(
                model.data(rodata['opagdl']),
                model.data(rodata['xlugdl']) if rodata['xlugdl'] else None,
                ptr_vtx,
                ptr_col,
                model.data(ptr_vtx),
                model.data(ptr_col),
                model.matrices
            )

            if single_mesh:
                finalmesh = aggregate_mesh(finalmesh, idx, meshdata, apply_mtx)
            else:
                mesh_obj = create_model_mesh(idx, meshdata, tex_configs, apply_mtx, matcache, asset_type)
                mesh_objs += mesh_obj

        idx += 1

    if single_mesh:
        mesh_obj = create_mesh(finalmesh, tex_configs, name, matcache, asset_type)
        mesh_objs = [mesh_obj]

    return mesh_objs

def import_model(romdata, matcache, asset_type, modelname=None, filename=None):
    logger.debug(f'import model {modelname}')
    model = loadmodeldata(romdata, modelname=modelname, filename=filename)

    sc = 1

    # create joints
    # joints_obj = pdu.new_empty_obj('Joints', model_obj)
    # model.traverse(create_joint, root_obj=joints_obj)

    props_with_mtx = ['ProofgunZ', 'PgroundgunZ']
    name = modelname if modelname else os.path.basename(filename)
    apply_mtx = name[0] != 'P' or name in props_with_mtx
    meshes = create_model_meshes(model, name, apply_mtx, asset_type, matcache)

    if len(meshes) > 1:
        model_obj = pdu.new_empty_obj(name, link=False)
        for mesh in meshes:
            mesh.parent = model_obj
    else:
        model_obj = meshes[0]
        model_obj.name = name

    model_obj.pd_obj.type = pdprops.PD_OBJTYPE_MODEL
    model_obj.pd_model.name = name
    model_obj.pd_model.filename = filename if filename else ''

    return model_obj, model

def loadimages_embedded(model):
    imglib = bpy.data.images

    tex_path = pdu.tex_path()

    for tc in model.texconfigs:
        texnum = tc['texturenum']
        if not texnum & 0x05ffffff: continue
        pdtex = tex.PDTex()
        teximg = pdtex.image
        fmt, w, h, d = tc['format'], tc['width'], tc['height'], tc['depth']

        teximg.format = tex.tex_config_to_format(fmt, d)
        teximg.width = w
        teximg.height = h
        teximg.depth = d

        imgname = f'{texnum & 0xffffff:04X}.png'

        if imgname not in imglib:
            texdata = model.texdata[texnum].bytes
            tex.tex_set_pixels(teximg, texdata)
            tex.tex_write_image(tex_path, pdtex, imgname)
            img = imglib.load(f'{tex_path}/{imgname}')
            img['texinfo'] = {
                'width': teximg.width,
                'height': teximg.height,
                'format': teximg.format,
                'depth': teximg.depth,
            }

def loadimage(texdata, tex_path, texnum):
    imglib = bpy.data.images
    imgname = f'{texnum & 0xffffff:04X}.png'
    texture = tex.tex_load(texdata, tex_path, imgname)
    img = imglib.load(f'{tex_path}/{imgname}')

    teximg = texture.image
    img['texinfo'] = {
        'width': teximg.width,
        'height': teximg.height,
        'format': teximg.format,
        'depth': teximg.depth,
    }

def loadimages_external(path):
    tex_path = pdu.tex_path()

    for filename in glob.iglob(f'{path}/*.bin'):
        texdata = pdu.read_file(filename, autodecomp=False)
        filename = os.path.basename(filename).split('.')[0]
        texnum = int(filename, 16)
        loadimage(texdata, tex_path, texnum)

def loadimages(romdata, texnums):
    imglib = bpy.data.images
    tex_path = pdu.tex_path()

    for texnum in texnums:
        if texnum & 0x05000000 or texnum > 3503: continue #TODO temp hack

        imgname = f'{texnum & 0xffffff:04X}.png'

        if imgname not in imglib:
            if texnum <= 3503: #TODO temp hack
                texdata = romdata.texturedata(texnum)
                loadimage(texdata, tex_path, texnum)
            else:
                img = imglib.load(f'{tex_path}/{imgname}')

def loadmodeldata(romdata, modelname=None, filename=None):
    modeldata = pdu.read_file(filename) if filename else romdata.filedata(modelname)
    model = PD_ModelFile(modeldata)

    loadimages(romdata, [tc['texturenum'] for tc in model.texconfigs])
    if model.has_embedded_tex():
        loadimages_embedded(model)

    return model

@persistent
def on_update_graph(*args):
    pass
    # print('update', bpy.context.selected_objects)

def register_handlers():
    # bpy.app.handlers.depsgraph_update_post.append(on_update_graph)
    # bpy.app.handlers.depsgraph_update_pre.append(on_update_graph_pre)
    bpy.msgbus.subscribe_rna(
        key=(bpy.types.LayerObjects, "active"),
        owner=object(),
        args=tuple(),
        notify=on_update_graph,
    )

def register():
    TypeInfo.register_all(model_decls)
