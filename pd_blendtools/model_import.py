import struct
from collections import namedtuple

import bpy
import bmesh
from mathutils import Euler, Vector, Matrix

import pd_materials as pdm
import pd_utils as pdu
from pd_materials import *
from pdmodel import unmask, PDModel
from gbi import *
import texload as tex
import mtxpalette as mtxp
import log_util as log
from decl_model import *
from typeinfo import TypeInfo

logger = log.log_get(__name__)
log.log_config(logger, log.LOG_FILE_IMPORT)

PDMeshData = namedtuple('PDMeshData',
                        'opagdl xlugdl ptr_vtx ptr_col vtxdata coldata matrices')
def create_mesh(mesh, tex_configs, meshidx, sub_idx):
    mesh_data = bpy.data.meshes.new('mesh_data')

    verts = mesh.verts
    faces = mesh.tris
    tri2tex = mesh.tri2tex

    verts_xyz = [v.pos for v in verts]
    mesh_data.from_pydata(verts_xyz, [], faces)
    # mesh_data.validate(verbose=True)

    suffix = f'[{sub_idx}]' if sub_idx >= 0 else ''
    suffix += '.XLU' if mesh.layer == MeshLayer.XLU else ''
    name = f'{meshidx:02X}.Mesh{suffix}'

    obj = bpy.data.objects.new(name, mesh_data)
    obj.pd_model.layer = mesh.layer

    logger.debug(f'[CREATEMESH {meshidx:02X}] {name}')

    normals = []
    colors = []
    colors_mtx = []

    for i, v in enumerate(verts):
        if mesh.has_mtx:
            col_mtx = mtxp.mtx2color(v.mtxidx)
            colors_mtx.append(col_mtx)

            # add to the vertex group 'mtx'
            mtx = f'{v.mtxidx:02X}'
            vgroups = obj.vertex_groups
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
    uv_layer = bm.loops.layers.uv.verify()
    layer_color = bm.loops.layers.color.new("vtxcolor")

    layer_mtx = bm.loops.layers.color.new("matrices") if mesh.has_mtx else None

    for idx, face in enumerate(bm.faces):
        matsetup = tri2tex[face.index]
        matsetup.optimize_cmds()

        # logger.debug(f'face {idx} mat {matsetup.id()}')
        tc = tex_configs[matsetup.texnum]

        matname = matsetup.id()
        mat_idx = obj.data.materials.find(matname)
        # material does not exist, create a new one
        if mat_idx < 0:
            mat_idx = len(obj.data.materials)
            fmt = tex.TexFormatGbiMapping[tc['format']]
            use_alpha = matsetup.smode == 1 or pdm.tex_has_alpha(fmt, tc['depth'])
            mat = pdm.material_new(matsetup, use_alpha)
            obj.data.materials.append(mat)

        face.material_index = mat_idx

        # sets up the verts uv data, colors and matrices
        for loop in face.loops:
            vert = verts[loop.vert.index]
            uv_sc = (1 / (32 * tc['width']), 1 / (32 * tc['height']))
            uv = (vert.uv[0] * uv_sc[0], vert.uv[1] * uv_sc[1])
            loop[uv_layer].uv = uv
            loop[layer_color] = colors[loop.vert.index]

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

    return obj

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

from enum import IntEnum
class MeshLayer(IntEnum):
    OPA = 0
    XLU = 1

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

def collect_sub_meshes(pdmeshdata, idx, apply_mtx):
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
    dbg = 1

    mesh = ImportMeshData(MeshLayer.OPA)
    meshes = [mesh] # stores all meshes, from both opa and xlu layers
    mtxindex = -1
    model_mtxs = set()

    trinum = 0

    mat_setup = PDMaterialSetup(idx)
    gdlnum = 0
    nverts = 0

    if dbg:
        # logger.debug(f'[COLLECTMESH {idx:02X}] ptr_vtx {ptr_vtx:04X} ptr_col {col_start:04X} nvtx {len(verts)}')
        logger.debug(f'[COLLECTMESH {idx:02X}] nvtx {len(verts)}')
        # n = min(nvtx, 300)
        for i in range(0, nvtx):
            v = verts[i]
            logger.debug(f' v_{i} {v}')

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
                mesh = ImportMeshData(MeshLayer.XLU, has_mtx=mesh.has_mtx)
                # ... so we need to copy them over to new xlu mesh
                mesh.add_vertices(vtxs)
                meshes.append(mesh)
                trinum = 0
                continue
            else:
                break

        cmdint = int.from_bytes(cmd, bo)
        w1 = cmdint & 0xffffffff

        if dbg: logger.debug(f'{cmdint:016X} {pdu.GDLcodes[cmd[0]]}')

        if op == G_TRI4:
            tris = pdu.read_tri4(cmd, 0)

            mat_setup.applied = True

            for tri in tris:
                if dbg: logger.debug(f'tri {trinum} {tri} tex {mat_setup.texnum:04X}')
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

                if dbg: logger.debug(f'  {i} col {coloridx} ({c[0]:02X} {c[1]:02X} {c[2]:02X} {c[3]:02X}) mtx {mtxindex}')

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
                mat_setup = PDMaterialSetup(idx, mat_setup)
            mat_setup.add_cmd(cmd)

        addr += 8

    return meshes, model_mtxs

def create_model_mesh(idx, meshdata, sc, tex_configs, apply_mtx):
    subMeshes, model_mtxs = collect_sub_meshes(meshdata, idx, apply_mtx)
    n_submeshes = len(subMeshes)
    mesh_objs = []
    for sub_idx, meshdata in enumerate(subMeshes):
        if len(meshdata.verts) == 0: continue

        sub_idx = sub_idx if n_submeshes > 1 else -1
        mesh_obj = create_mesh(meshdata, tex_configs, idx, sub_idx)
        mesh_obj.data['matrices'] = list(model_mtxs)
        mesh_objs.append(mesh_obj)
        logger.debug(f'ntri {len(meshdata.tris)} nverts {len(meshdata.verts)}')

    return mesh_objs

def create_model_meshes(model, sc, apply_mtx):
    tex_configs = {}
    for tc in model.texconfigs:
        texnum = tc['texturenum']
        tex_configs[texnum] = tc

    idx = 0
    mesh_objs = []
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
                model.data(rodata['xlugdl']) if rodata['xlugdl'] else None, # xlu_gdl
                ptr_vtx,
                ptr_col,
                model.data(ptr_vtx),
                model.data(ptr_col),
                model.matrices
            )

            mesh_obj = create_model_mesh(idx, meshdata, sc, tex_configs, apply_mtx)
            mesh_objs += mesh_obj
        idx += 1

    return mesh_objs

def import_model(romdata, model_name, link=True):
    logger.debug(f'import model {model_name}')
    model = loadmodel(romdata, model_name)

    sc = 1

    # create joints
    # joints_obj = pdu.new_empty_obj('Joints', model_obj)
    # model.traverse(create_joint, root_obj=joints_obj)

    props_with_mtx = ['ProofgunZ', 'PgroundgunZ']
    name = model_name
    apply_mtx = name[0] != 'P' or name in props_with_mtx
    meshes = create_model_meshes(model, sc, apply_mtx)

    if len(meshes) > 1:
        model_obj = pdu.new_empty_obj(model_name, link=link)
        for mesh in meshes:
            mesh.parent = model_obj
    else:
        model_obj = meshes[0]
        model_obj.name = model_name

    model_obj.pd_model.name = model_name

    return model_obj, model

def loadimages_embedded(model):
    imglib = bpy.data.images

    addon_path = pdu.addon_path()
    tex_path = f'{addon_path}/tex'

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

def loadimages(romdata, texnums):
    imglib = bpy.data.images

    addon_path = pdu.addon_path()
    tex_path = f'{addon_path}/tex'

    for texnum in texnums:
        if texnum & 0x05000000: continue

        imgname = f'{texnum & 0xffffff:04X}.png'

        if imgname not in imglib:
            texdata = romdata.texturedata(texnum)
            texture = tex.tex_load(texdata, tex_path, imgname)
            teximg = texture.image
            img = imglib.load(f'{tex_path}/{imgname}')
            img['texinfo'] = {
                'width': teximg.width,
                'height': teximg.height,
                'format': teximg.format,
                'depth': teximg.depth,
            }

def loadmodel(romdata, modelname):
    modeldata = romdata.filedata(modelname)
    model = PDModel(modeldata)

    loadimages(romdata, [tc['texturenum'] for tc in model.texconfigs])
    if model.has_embedded_tex():
        loadimages_embedded(model)

    return model

def clear_materials():
    imglib = bpy.data.images
    for img in imglib:
        imglib.remove(img)

    matlib = bpy.data.materials
    for mat in matlib:
        if mat.name.startswith('Mat-') or mat.name.startswith('PD_'):
            matlib.remove(mat)

from bpy.app.handlers import persistent

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
