import struct
import logging
import math

import bpy
import bmesh
from bpy import context as ctx
from bpy.props import StringProperty, IntProperty, PointerProperty
from bpy.types import PropertyGroup, Object, Panel
from mathutils import Euler, Vector, Matrix

import pd_utils as pdu
import pd_materials as pdm
import nodes.pd_shadernodes as pdn
from pd_materials import *
from pdmodel import unmask, PDModel
from gbi import *
import export as exp
import texload as tex

logger = logging.getLogger(__name__)
logger.handlers.clear()
logger.setLevel(logging.DEBUG)

fh = logging.FileHandler('D:/Mega/PD/pd_blend/pd_guns.log')
fh.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
# ch.setLevel(logging.DEBUG)
ch.setLevel(logging.ERROR)

formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s', datefmt='%Y%m%d %H:%M:%S')
fh.setFormatter(formatter)
ch.setFormatter(formatter)

logger.addHandler(fh)
logger.addHandler(ch)

def createCollectionIfNone(name):
    if name not in bpy.data.collections:
        collection = bpy.data.collections.new(name)
        ctx.scene.collection.children.link(collection)

def createMesh(mesh, tex_configs, idx, sub_idx):
    mesh_data = bpy.data.meshes.new('mesh_data')

    verts = mesh.verts
    faces = mesh.tris
    tri2tex = mesh.tri2tex

    verts_xyz = [v.pos for v in verts]
    mesh_data.from_pydata(verts_xyz, [], faces)
    # mesh_data.validate(verbose=True)

    # suffix = f'[{sub_idx}]-M{mtxindex:02X}' if sub_idx >= 0 else f'-M{mtxindex:02X}'
    suffix = f'[{sub_idx}]' if sub_idx >= 0 else ''
    suffix += '.XLU' if mesh.layer == MeshLayer.XLU else ''
    name = f'{idx:02X}.Mesh{suffix}'

    obj = bpy.data.objects.new(name, mesh_data)
    obj.pdmodel_props.name = name
    obj.pdmodel_props.idx = idx
    obj.pdmodel_props.sub_idx = sub_idx
    obj.pdmodel_props.mtx = mesh.mtxindex
    obj.pdmodel_props.layer = mesh.layer

    collection = pdu.active_collection()
    collection.objects.link(obj)

    logger.debug(f'[CREATEMESH {idx:02X}] {name}')

    normals = []
    colors = []

    for i, v in enumerate(verts):
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
            # normals.append(n)
            # for k in range(0,3): c[k] *= 255
            c = [float(ci/255) for ci in normcolor]
            # colors.append((c[0],c[1],c[2],1))
            colors.append((1,1,1,1))

        # c = normcolor
        # txtnorm = '' if hascolors else ' (N)'
        # txtnorm += '' if hascolors else ' (' + ''.join([f'{ni:<6.3f} ' for ni in normals[i]]) + ')'
        txtidx = f' [{v.color_idx}]'
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
    color_layer = bm.loops.layers.color.new("vtxcolor")
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
            use_alpha = matsetup.smode == 1 or pdm.tex_has_alpha(tc['format'], tc['depth'])
            mat = pdm.material_new(matsetup, use_alpha)
            obj.data.materials.append(mat)
        else:
            mat = bpy.data.materials[matname]

        face.material_index = mat_idx

        # setup the verts uv data and colors
        for loop in face.loops:
            vert = verts[loop.vert.index]
            uv_sc = (1 / (32 * tc['width']), 1 / (32 * tc['height']))
            uv = (vert.uv[0] * uv_sc[0], vert.uv[1] * uv_sc[1])
            loop[uv_layer].uv = uv
            loop[color_layer] = colors[loop.vert.index]

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

def createObj(idx, pos, root_obj):
    pos = Vector(pos)
    name = posNodeName(idx)

    obj = pdu.new_empty_obj(name, dsize=50, link=False)
    obj['pdid'] = idx

    view_layer = bpy.context.view_layer
    collection = view_layer.active_layer_collection.collection

    obj.location = pos
    obj.parent = root_obj

    # bpy.context.collection.objects.link(obj)
    # bpy.data.collections['Joints'].objects.link(obj)
    collection.objects.link(obj)
    # bpy.context.view_layer.update()

def create_joint(model, node, idx, depth, **kwargs):
    root_obj = kwargs['root_obj']
    node['_idx_'] = idx
    nodetype = node['type']

    if nodetype == 2:
        r = node['rodata']
        print(f'idx {idx:02X} ro {r:08X}')
        ro = model.find_rodata(node['rodata'])
        pos = ro['pos']['f']
        x = struct.unpack('f', pos[0].to_bytes(4, 'little'))[0]
        y = struct.unpack('f', pos[1].to_bytes(4, 'little'))[0]
        z = struct.unpack('f', pos[2].to_bytes(4, 'little'))[0]

        parentaddr = unmask(node['parent'])
        parentnode = model.nodes[parentaddr] if parentaddr else None
        parentidx = parentnode['_idx_'] if parentnode and parentnode['type'] == 2 else -1
        parentobj = root_obj

        if parentidx >= 0:
            parentname = posNodeName(parentidx)
            parentobj = pdu.active_collection().objects[parentname]

        createObj(idx, (x, z, y), parentobj)

def _t(v): return f'({v[0]:.2f}, {v[1]:.2f}, {v[2]:.2f})'

from enum import IntEnum
class MeshLayer(IntEnum):
    OPA = 0
    XLU = 1

class SubMesh:
    def __init__(self, mtxindex, layer):
        self.nverts = 0
        self.vtx_start = -1
        self.vtx_end = -1
        self.vtx_offset = -1
        self.mtxindex = mtxindex
        self.verts = []
        self.tris = []
        self.tri_index = 0
        self.current_mtx = (0,0,0)
        self.dbg = 0
        self.vtx_buffer = []
        self.tri2tex = {} # tri -> texnum
        self.layer = layer

    def vtx_from_buffer(self, vtx_buffer, n):
        if len(self.vtx_buffer): return

        logger.debug(f'>>> MESH {self.mtxindex:02X} add vtx: {n}')

        self.tri_index = len(self.verts)
        for i in range(0, n):
            v = vtx_buffer[i]
            self.verts.append(v)
            self.vtx_buffer.append(v.pos)

    def add_tri(self, tri, mat_setup):
        ofs = self.tri_index
        t = (
            tri[0] + ofs,
            tri[1] + ofs,
            tri[2] + ofs
        )

        if self.dbg: logger.debug(f'  f {len(self.tris)} {t} tidx {ofs} M{self.mtxindex:02X}')

        self.tris.append(t)

        facenum = len(self.tris) - 1
        self.tri2tex[facenum] = mat_setup

    def clear_vtx_buffer(self):
        self.vtx_buffer.clear()

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

def select_mesh(tri, vtx_buffer):
    v0 = vtx_buffer[tri[0]]
    v1 = vtx_buffer[tri[1]]
    v2 = vtx_buffer[tri[2]]

    # picks the entry with most verts in the group
    if v0.group_size > v1.group_size:
        return v0 if v0.group_size >= v2.group_size else v2
    else:
        return v1 if v1.group_size >= v2.group_size else v2

def collectSubMeshes(model, rodata, idx):
    ptr_opagdl = rodata['opagdl']

    nodetype = rodata['_node_type_']
    ptr_vtx = rodata['vertices'] & 0xffffff
    vtxbytes = model.data(ptr_vtx)
    nvtx = rodata['numvertices']
    col_start = 0 if nodetype in [0x04, 0x18] else pdu.align(ptr_vtx + nvtx*12, 8)

    sc = 1
    verts = pdu.read_vtxs(vtxbytes, nvtx, sc)

    gdl = model.data(ptr_opagdl)
    addr = 0
    bo='big'
    dbg = idx == 0x3
    dbg = 1

    matrixmesh_map = {} # matrix idx -> mesh
    mtxindex = -1

    vtx_buffer = [VtxBufferEntry()]*128
    vtx_buf_size = 0

    mat_setup = PDMaterialSetup(idx)
    gdlnum = 0
    col_ofs = 0

    if dbg:
        # n = min(nvtx, 300)
        for i in range(0, nvtx):
            v = verts[i]
            logger.debug(f' v_{i} {v}')

    if dbg: logger.debug(f'[COLLECTMESH {idx:02X}] ptr_vtx {ptr_vtx:04X} ptr_col {col_start:04X} nvtx {len(verts)}')

    # these commands change the material setup
    MAT_CMDS = [
        G_SetOtherMode_L, G_SetOtherMode_H, G_SETCOMBINE,
        G_SETGEOMETRYMODE, G_CLEARGEOMETRYMODE,
        G_TEXTURE, G_PDTEX
    ]

    layer = MeshLayer.OPA

    while True:
        cmd = bytearray(gdl[addr:addr+8])
        op = cmd[0]

        if op == G_END:
            ptr_xlugdl = rodata['xlugdl']
            if ptr_xlugdl and gdlnum == 0:
                gdl = model.data(ptr_xlugdl)
                addr = 0
                gdlnum += 1
                layer = MeshLayer.XLU
                matrixmesh_map[(mtxindex, layer)] = SubMesh(mtxindex, layer)
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
                v = select_mesh(tri, vtx_buffer)
                if dbg: logger.debug(f'tri {tri} tex {mat_setup.texnum:04X}')

                mesh = matrixmesh_map[(v.mtxidx, layer)]
                mesh.vtx_from_buffer(vtx_buffer, vtx_buf_size)
                mesh.add_tri(tri, mat_setup)
        elif op == G_VTX:
            nverts = ((cmd[1] & 0xf0) >> 4) + 1
            vtx_idx = cmd[1] & 0xf
            vtx_ofs = int.from_bytes(cmd[5:8], bo)

            vtx_segmented = (w1 & 0x05000000) == 0x05000000
            vstart = (vtx_ofs - ptr_vtx)//12 if vtx_segmented else vtx_ofs//12
            vtx_buf_size = vtx_idx + nverts
            pos = model.matrices[mtxindex] if mtxindex >= 0 else (0,0,0)

            logger.debug(f'  vstart {vstart} n {nverts} vidx {vtx_idx:01X} vbufsize {vtx_buf_size} col_offset {(col_ofs-col_start)>>2} seg {vtx_segmented:08X} mtx {mtxindex}')

            col_data = model.data(col_start + col_ofs)
            for i, v in enumerate(verts[vstart:vstart+nverts]):
                vpos = (v[0] + pos[0], v[1] + pos[1], v[2] + pos[2])

                uv = (v[3], v[4])
                coloridx = v[5]
                c = color = col_data[coloridx:coloridx+4]
                if dbg: logger.debug(f'  {i} col {coloridx} ({c[0]:02X} {c[1]:02X} {c[2]:02X} {c[3]:02X}) mtx {mtxindex}')
                hasnormal = mat_setup.has_normal()
                vtx_buffer[vtx_idx+i] = VtxBufferEntry(vpos, uv, color, coloridx, nverts, mtxindex, hasnormal)

            matrixmesh_map[(mtxindex, layer)].clear_vtx_buffer()
        elif op == G_COL:
            col_ofs = (cmdint & 0xffffff)
        elif op == G_MTX:
            mtxindex = (cmdint & 0xffffff) // 0x40
            logger.debug(f'  MTX {mtxindex:04X}')

            if (mtxindex, layer) not in matrixmesh_map:
                cur_mesh = matrixmesh_map[(mtxindex, layer)] = SubMesh(mtxindex, layer)
                cur_mesh.dbg = dbg
        elif op in MAT_CMDS:
            if mat_setup.applied:
                mat_setup = PDMaterialSetup(idx, mat_setup)
            mat_setup.add_cmd(cmd)

        addr += 8

    print(f'mesh {idx:02X} {mat_setup.applied}')

    return list(filter(lambda e: len(e.tris), matrixmesh_map.values()))

def createModelMesh(idx, model, rodata, sc, tex_configs, parent_obj):
    subMeshes = collectSubMeshes(model, rodata, idx)
    n_submeshes = len(subMeshes)
    logger.debug(f'idx {idx:02X} n {n_submeshes}')
    for sub_idx, meshdata in enumerate(subMeshes):
        logger.debug(f'  submesh {sub_idx:02X}')
        sub_idx = sub_idx if n_submeshes > 1 else -1
        mesh_obj = createMesh(meshdata, tex_configs, idx, sub_idx)
        mesh_obj.parent = parent_obj
        logger.debug(f'  nt {len(meshdata.tris)} nv {len(meshdata.verts)}')

def createModelMeshes(model, sc, model_obj):
    tex_configs = {}
    for tc in model.texconfigs:
        texnum = tc['texturenum']
        tex_configs[texnum] = tc
        # print(f'tex {texnum:04X} w {width:02X} h {height:02X}')

    idx = 0
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

            print(f'createModelMesh {idx:02X} t {nodetype:02X}')
            createModelMesh(idx, model, rodata, sc, tex_configs, model_obj)
        idx += 1

def register():
    bpy.utils.register_class(PDModelPropertyGroup)
    bpy.utils.register_class(OBJECT_PT_custom_panel)
    Object.pdmodel_props = PointerProperty(type=PDModelPropertyGroup)
    pdn.register()

class PDModelPropertyGroup(PropertyGroup):
    name: StringProperty(name='name', default='', options={'LIBRARY_EDITABLE'})
    idx: IntProperty(name='idx', default=0, options={'LIBRARY_EDITABLE'})
    mtx: IntProperty(name='mtx', default=0, options={'LIBRARY_EDITABLE'})
    sub_idx: IntProperty(name='sub_idx', default=0, options={'LIBRARY_EDITABLE'})
    layer: IntProperty(name='layer', default=0, options={'LIBRARY_EDITABLE'})

class OBJECT_PT_custom_panel(Panel):
    bl_label = 'PD Model'
    bl_idname = 'OBJECT_PT_custom_panel'
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "object"

    @classmethod
    def poll(cls, context):
        return context.object and context.object.type == 'MESH'

    def draw(self, context):
        layout = self.layout
        obj = context.object

        box = layout.box()
        box.prop(obj.pdmodel_props, 'name', icon='LOCKED', text='')
        box.label(text=f'Index: {obj.pdmodel_props.idx:02X}', icon='LOCKED')

        if obj.pdmodel_props.sub_idx >= 0:
            box.label(text=f'Sub Index: {obj.pdmodel_props.sub_idx:02X}', icon='LOCKED')

        box.label(text=f'Matrix: {obj.pdmodel_props.mtx:02X}', icon='LOCKED')
        txtlayer = 'opa' if obj.pdmodel_props.layer == MeshLayer.OPA else 'xlu'
        box.label(text=f'Layer: {txtlayer}', icon='LOCKED')
        box.enabled = False

def unreg():
    bpy.utils.unregister_class(PDModelPropertyGroup)
    bpy.utils.unregister_class(OBJECT_PT_custom_panel)
    del Object.pdmodel_props

def clearLog():
    f = open('D:/Mega/PD/pd_blend/pd_guns.log', 'r+')
    f.seek(0)
    f.truncate(0)

def main():
    # pdn.unregister()
    # pdn.register()
    # unreg()

    clearLog()

    bpy.utils.register_class(PDModelPropertyGroup)
    bpy.utils.register_class(OBJECT_PT_custom_panel)
    Object.pdmodel_props = PointerProperty(type=PDModelPropertyGroup)
    # pdn.register()

    logger.debug('clearScene()')
    pdu.clear_scene()

    model_name = 'Gfalcon2Z'
    # model_name = 'Gleegun1Z'
    # model_name = 'Gdy357Z'
    # model_name = 'Gcmp150Z'
    # model_name = 'Gk7avengerZ'
    # model_name = 'GdydragonZ'
    # model_name = 'GpcgunZ'
    # model_name = 'GdysuperdragonZ'
    model_name = 'GcrossbowZ'
    # model_name = 'GdydevastatorZ'
    model_name = 'GdyrocketZ'
    # model_name = 'GsniperrifleZ'
    # model_name = 'Gm16Z'
    # model_name = 'GshotgunZ'
    # model_name = 'GdruggunZ'
    # model_name = 'GmaianpistolZ'
    # model_name = 'GskminigunZ'
    # model_name = 'Gz2020Z'
    # model_name = 'PchrdragonZ'
    # model_name = 'Pchrdy357Z'
    # model_name = 'CdjbondZ'
    # model_name = 'CskedarZ'
    # model_name = 'PchrautogunZ'

    romdata = pdu.loadrom()
    model = loadmodel(romdata, model_name)

    model_obj = pdu.new_empty_obj(model_name)

    sc = 0.01
    sc = 1
    # model.traverse(create_joint, root_obj=model_obj)
    createModelMeshes(model, sc, model_obj)
    model_obj.rotation_euler[0] = math.radians(90)
    model_obj.rotation_euler[2] = math.radians(90)

def export(name):
    exp.export_model(name)

def loadimages(romdata, model):
    imglib = bpy.data.images

    for tc in model.texconfigs:
        texnum = tc['texturenum']
        imgname = f'{texnum:04X}.png'

        if imgname not in imglib:
            texdata = romdata.texturedata(texnum)
            tex.tex_load(texdata, 'D:/Mega/PD/pd_blend/tex', imgname) # TODO TEX FOLDER
            imglib.load(f'{TEX_FOLDER}/{imgname}')

def loadmodel(romdata, modelname):
    modeldata = romdata.modeldata(modelname)
    # pdu.write_file('D:/Mega/PD/pd_blend/modelbin', f'{modelname}.bin', modeldata)
    model = PDModel(modeldata)
    loadimages(romdata, model)
    return model
