import os
import struct
import logging

import bpy
import bmesh
from bpy import context as ctx
from mathutils import Euler, Vector, Matrix

import pd_utils as pdu
import pdmodel
import pd_materials as pdm
from pdmodel import unmask


logging.basicConfig(filename='D:/Mega/PD/pd_blend/pd_guns.log',
    level=logging.DEBUG,
    format="{asctime}[{levelname}] {message}",
    style="{",
    datefmt="%Y-%m-%d %H:%M",
    filemode='w+')
logger = logging.getLogger(__name__)
logger.handlers.clear()
logger.propagate = False
logger.setLevel(logging.DEBUG)
# logger.addHandler(logging.StreamHandler())
logger.addHandler(logging.FileHandler('D:/Mega/PD/pd_blend/pd_guns.log'))
# logging.basicConfig(filename='D:/Mega/PD/pd_blend/pd_guns.log', encoding='utf-8', level=logging.DEBUG, filemode='w')

def createCollectionIfNone(name):
    if name not in bpy.data.collections:
        collection = bpy.data.collections.new(name)
        ctx.scene.collection.children.link(collection)

def createMesh(verts, faces, colors, idx, sub_idx, tri2tex, mtxindex, tex_configs):
    mesh_data = bpy.data.meshes.new('mesh_data')

    # verts_xyz = [(v[0], v[1], v[2]) for v in verts]
    verts_xyz = [v.pos for v in verts]
    mesh_data.from_pydata(verts_xyz, [], faces)

    suffix = f'[{sub_idx}]-M{mtxindex:02X}' if sub_idx >= 0 else f'-M{mtxindex:02X}'
    name = f'{idx:02X}.Mesh{suffix}'
    obj = bpy.data.objects.new(name, mesh_data)
    bpy.data.collections['Meshes'].objects.link(obj)

    layer_vtxcol = mesh_data.vertex_colors
    logger.debug(f'MESH {name} vtxcol {layer_vtxcol} len {len(layer_vtxcol)}')

    # setup vertex normals
    hasnormals = len(verts) and verts[0].hasnormal # assuming is either all norm or all color
    hascolors = not hasnormals
    normals = []

    colattr = None
    if hascolors:
        colattr = obj.data.color_attributes.new(
            name='vtxcolor',
            type='FLOAT_COLOR',
            domain='POINT',
        )

    for idx, v in enumerate(verts):
        normcolor = v.color # either a normal or color
        if normcolor is None: continue

        if hascolors:
            r = normcolor[0]/255.0
            g = normcolor[1]/255.0
            b = normcolor[2]/255.0
            a = normcolor[3]/255.0
            logger.debug(f'  {r:.2f} {g:.2f} {b:.2f}')
            colattr.data[idx].color = [r, g, b, a]
        else:
            s = 2.2
            n = Vector((normcolor[0], normcolor[2], normcolor[1])).normalized()
            n.x *= s; n.y *= s; n.z *= s
            normals.append(n)

    me = obj.data

    bpy.context.view_layer.objects.active = obj

    bpy.ops.object.mode_set(mode = 'EDIT')
    bm = bmesh.from_edit_mesh(me)
    bm.faces.ensure_lookup_table()
    bm.verts.ensure_lookup_table()

    # setup UVs and materials
    uv_layer = bm.loops.layers.uv.verify()
    for idx, face in enumerate(bm.faces):
        texnum, smode, geom_mode = tri2tex[face.index]
        tc = tex_configs[texnum]

        matname = pdm.mat_name(texnum, smode, geom_mode)
        mat_idx = obj.data.materials.find(matname)
        if mat_idx < 0:
            mat_idx = len(obj.data.materials)
            use_alpha = smode == 1 or pdm.tex_has_alpha(tc['format'], tc['depth'])
            mat = pdm.material_new(texnum, smode, use_alpha, geom_mode)
            obj.data.materials.append(mat)

        face.material_index = mat_idx

        # setup the verts uv data
        for loop in face.loops:
            vert = verts[loop.vert.index]
            uv_sc = (1 / (32 * tc['width']), 1 / (32 * tc['height']))
            uv = (vert.uv[0] * uv_sc[0], vert.uv[1] * uv_sc[1])
            loop[uv_layer].uv = uv

    bmesh.update_edit_mesh(me)
    bm.free()

    bpy.ops.object.mode_set(mode = 'OBJECT')

def readModel(modelName):
    print('-'*32)
    blend_dir = os.path.dirname(bpy.data.filepath)
    model = pdmodel.read(f'{blend_dir}/files', modelName)
    idx = 0
    for addr, node in model.nodes.items():
        nodetype = node['type']
        # print(f'{idx:02x} node t {nodetype} [{addr:04X}]')
        idx += 1

    print('num gdls: ', len(model.gdls))
    
    return model

nodeidx = -1
def _traverse(model, node, depth):
    global nodeidx

    nodeidx += 1
    if not node: return

    sp = ' ' * depth*2
    nodetype = node['type']
    print(f'{sp} NODE {nodeidx:02X} t {nodetype:02X}' )
    child = pdmodel.unmask(node['child'])
    if child:
        _traverse(model, model.nodes[child], depth + 1)

    nextaddr = pdmodel.unmask(node['next'])
    if nextaddr:
        _traverse(model, model.nodes[nextaddr], depth)

def posNodeName(idx): return f'{idx:02X}.Position'

def createObj(idx, pos, parentidx):
    pos = Vector(pos)
    name = posNodeName(idx)
    obj = bpy.data.objects.new(name=name, object_data=None)
    obj.empty_display_type = "PLAIN_AXES"
    obj.empty_display_size = 50

    if parentidx < 0:
        location = pos
        rotation = Euler((0, 0,0))
        scale = Vector((1, 1, 1))
        T = Matrix.Translation(location)
        R = rotation.to_matrix().to_4x4()
        S = Matrix.Diagonal(scale.to_4d())
        M = T @ R @ S
        # obj.matrix_world = M
        # obj.matrix_world = Matrix.Translation(pos)
        obj.location = pos
    else:
        name = posNodeName(parentidx)
        parent = bpy.data.collections['Joints'].objects[name]
        obj.parent = parent
        # obj.matrix_world = Matrix.Translation(pos)
        # obj.location = pos + parent.location
        obj.location = pos

    # bpy.context.collection.objects.link(obj)
    bpy.data.collections['Joints'].objects.link(obj)
    # bpy.context.view_layer.update()

def TMP_getrodata(model, addr):
    for ro in model.rodatas:
        if ro['_addr_'] == unmask(addr): return ro

    return None

def traverse(model):
    node = model.rootnode
    depth = 0
    idx = 0
    # parentnode = None
    while node:
        node['_idx_'] = idx
        nodetype = node['type']

        if nodetype == 2:
            r = node['rodata']
            print(f'idx {idx:02X} ro {r:08X}')
            ro = TMP_getrodata(model, node['rodata'])
            pos = ro['pos']['f']
            x = struct.unpack('f', pos[0].to_bytes(4, 'little'))[0]
            y = struct.unpack('f', pos[1].to_bytes(4, 'little'))[0]
            z = struct.unpack('f', pos[2].to_bytes(4, 'little'))[0]

            parentaddr = unmask(node['parent'])
            parentnode = model.nodes[parentaddr] if parentaddr else None
            parentidx = parentnode['_idx_'] if parentnode and parentnode['type'] == 2 else -1
            createObj(idx, (x, z, y), parentidx)

        sp = ' ' * depth * 2
        print(f'{sp} NODE {idx:02X} t {nodetype:02X}')
        idx += 1

        child = pdmodel.unmask(node['child'])
        if child:
            node = model.nodes[child]
            depth += 1
        else:
            while node:
                nextaddr = pdmodel.unmask(node['next'])
                if nextaddr:
                    node = model.nodes[nextaddr]
                    break

                parent = pdmodel.unmask(node['parent'])
                node = model.nodes[parent] if parent else None
                if node: depth -= 1

def createJoint(idx, x, y, z):
    #    r = rnd.randint(1, 1000)
    joint = bpy.data.objects.new(name=f'{idx:02X}.Joint', object_data=None)
    joint.empty_display_type = "PLAIN_AXES"
    joint.empty_display_size = 200
    joint.location = (x, y, z)
    # joint.scale = (20, 20, 20)
    bpy.data.collections['Joints'].objects.link(joint)
    
G_MTX               = 0x01
G_VTX               = 0x04
G_COL               = 0x07
G_TRI4              = 0xb1
G_SETGEOMETRYMODE   = 0xb7
G_CLEARGEOMETRYMODE = 0xb6
G_PDTEX             = 0xc0
G_END               = 0xb8

# G_LIGHTING    = 0x00020000
# G_TEXTURE_GEN = 0x00040000

def _t(v): return f'({v[0]:.2f}, {v[1]:.2f}, {v[2]:.2f})'
class SubMesh:
    def __init__(self ):
        self.nverts = 0
        self.vtx_start = -1
        self.vtx_end = -1
        self.vtx_offset = -1
        self.mtxindex = 0
        self.verts = []
        self.tris = []
        self.tri_index = 0
        self.current_mtx = (0,0,0)
        self.dbg = 0
        self.vtx_buffer = []
        self.tri2tex = {} # tri -> texnum

    def vtx_from_buffer(self, vtx_buffer, n):
        if len(self.vtx_buffer): return

        logger.debug(f'>>> MESH {self.mtxindex:02X} add vtx: {n}')

        self.tri_index = len(self.verts)
        for i in range(0, n):
            v = vtx_buffer[i]
            self.verts.append(v)
            self.vtx_buffer.append(v.pos)

    def add_tri(self, tri, texnum, smode, geom_mode):
        ofs = self.tri_index
        t = (
            tri[0] + ofs,
            tri[1] + ofs,
            tri[2] + ofs
        )
        if self.dbg: logger.debug(f'  f {len(self.tris)} {t} tidx {ofs} M{self.mtxindex:02X}')
        self.tris.append(t)

        if texnum:
            facenum = len(self.tris) - 1
            self.tri2tex[facenum] = (texnum, smode, geom_mode)

    def clear_vtx_buffer(self):
        self.vtx_buffer.clear()

class VtxBufferEntry:
    def __init__(self, pos=(0,0,0), uv=(0,0), color=None, group_size=0, mtxidx=-1, hasnormal=False):
        self.pos = pos
        self.uv = uv
        self.color = color
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

def collectSubMeshes(model, ro_gundl, idx):
    ptr_opagdl = ro_gundl['opagdl']

    ptr_vtx = ro_gundl['vertices']&0xffffff
    vtxbytes = model.data(ptr_vtx)
    nvtx = ro_gundl['numvertices']
    ptr_col = pdu.align(ptr_vtx + nvtx*12, 8)
    col_start = ptr_col

    sc = 1
    verts = pdu.read_vtxs(vtxbytes, nvtx, sc)

    gdl = model.data(ptr_opagdl)
    addr = 0
    bo='big'
    dbg = idx == 0x3

    matrixmesh_map = {} # matrix idx -> mesh
    mtxindex = -1

    vtx_buffer = [VtxBufferEntry()]*128
    vtx_buf_size = 0

    current_tex = 0
    smode = 0
    geom_mode = 0

    gdlnum = 0

    if dbg:
        # n = min(nvtx, 300)
        for i in range(0, nvtx):
            v = verts[i]
            logger.debug(f' v_{i} {v}')

    if dbg: logger.debug(f'[CREATEMESH {idx:02X}] ptr_vtx {ptr_vtx:04X} ptr_col {ptr_col:04X} nvtx {len(verts)}')

    while True:
        cmd = gdl[addr:addr+8]
        op = cmd[0]

        if op == G_END:
            ptr_xlugdl = ro_gundl['xlugdl']
            if ptr_xlugdl and gdlnum == 0:
                gdl = model.data(ptr_xlugdl)
                addr = 0
                current_tex = 0
                smode = 0
                geom_mode = 0
                gdlnum += 1
                continue
            else:
                break

        cmdint = int.from_bytes(cmd, bo)
        w0 = (cmdint & 0xffffffff00000000) >> 32
        w1 = cmdint & 0xffffffff

        if dbg: logger.debug(f'{cmdint:016X} {pdu.GDLcodes[cmd[0]]}')

        if op == G_TRI4:
            tris = pdu.read_tri4(cmd, 0)

            for tri in tris:
                v = select_mesh(tri, vtx_buffer)
                if dbg: logger.debug(f'tri {tri} tex {current_tex:04X}')
                mesh = matrixmesh_map[v.mtxidx]
                mesh.vtx_from_buffer(vtx_buffer, vtx_buf_size)
                mesh.add_tri(tri, current_tex, smode, geom_mode)
        elif op == G_VTX:
            nverts = ((cmd[1] & 0xf0) >> 4) + 1
            vtx_idx = cmd[1] & 0xf
            vtx_ofs = int.from_bytes(cmd[5:8], bo)

            vstart = (vtx_ofs - ptr_vtx) // 12
            vtx_buf_size = vtx_idx + nverts
            pos = getPositionFromMtxIndex(model, mtxindex) if mtxindex >= 0 else (0,0,0)

            logger.debug(f'  vstart {vstart} n {nverts} vidx {vtx_idx:01X} vbufsize {vtx_buf_size} col_offset {(col_start-ptr_col)>>2}')

            col_data = model.data(col_start)
            for i, v in enumerate(verts[vstart:vstart+nverts]):
                vpos = (v[0] + pos[0], v[1] + pos[1], v[2] + pos[2])
                uv = (v[3], v[4])
                coloridx = v[5]
                color = col_data[coloridx:coloridx+4]
                if dbg: logger.debug(f'  {i} {coloridx}')
                vtx_buffer[vtx_idx+i] = VtxBufferEntry(vpos, uv, color, nverts, mtxindex)

            matrixmesh_map[mtxindex].clear_vtx_buffer()
        elif op == G_COL:
            col_start = (cmdint & 0xffffff)
        elif op == G_MTX:
            mtxindex = (cmdint & 0xffffff) // 0x40
            logger.debug(f'  MTX {mtxindex:04X}')

            if mtxindex not in matrixmesh_map:
                currentSubMesh = matrixmesh_map[mtxindex] = SubMesh()
                currentSubMesh.mtxindex = mtxindex
                currentSubMesh.dbg = dbg
        elif op == G_PDTEX:
            current_tex = cmdint & 0xffff
            smode = (w0 >> 22) & 3
        elif op == G_SETGEOMETRYMODE:
            geom_mode = w1
        elif op == G_CLEARGEOMETRYMODE:
            geom_mode = 0

        addr += 8

    return list(filter(lambda e: len(e.tris), matrixmesh_map.values()))

def getPositionFromMtxIndex(model, mtxindex):
    for addr, node in model.nodes.items():
        if node['type'] == 2:
            idx = node['_idx_']
            ro = TMP_getrodata(model, node['rodata'])
            # print('idx', f'{idx:02X}', ro, 'q ', mtxindex)
            if ro['mtxindexes'][0] == mtxindex:
                name = posNodeName(idx)
                obj = bpy.data.collections['Joints'].objects[name]
                logger.debug(f'  found MTX {mtxindex:02X} in {name}: {obj.matrix_world.translation}')
                return obj.matrix_world.translation
    return None


def createModelMesh(idx, model, ro_gundl, sc, tex_configs):
    # logger.debug(f'createModelMesh {idx:02X}')

    subMeshes = collectSubMeshes(model, ro_gundl, idx)
    colors = ro_gundl['colors']['bytes']
    n_submeshes = len(subMeshes)
    logger.debug(f'idx {idx:02X} n {n_submeshes}')
    for sub_idx, mesh in enumerate(subMeshes):
        tris = mesh.tris
        sub_idx = sub_idx if n_submeshes > 1 else -1
        # pos = getPositionFromMtxIndex(model, mesh.mtxindex)
        createMesh(mesh.verts, tris, colors, idx, sub_idx, mesh.tri2tex, mesh.mtxindex, tex_configs)
        logger.debug(f'  n {len(tris)} nvtx {len(mesh.verts)}')

def createModelMeshes(model, sc):
    tex_configs = {}
    for tc in model.texconfigs:
        texnum = tc['texturenum']
        width = tc['width']
        height = tc['height']

        tex_configs[texnum] = tc
        print(f'tex {texnum:04X} w {width:02X} h {height:02X}')

    logger.debug('createModelMeshes')
    idx = 0
    for ro in model.rodatas:
        if ro['_node_type_'] == 4:
        # if ro['_node_type_'] == 4 and idx == 3:
#            print(ro)
            createModelMesh(idx, model, ro, sc, tex_configs)
        idx += 1

def clearLog():
    f = open('D:/Mega/PD/pd_blend/pd_guns.log', 'r+')
    f.truncate(0)

def clearScene():
    pdu.clearCollection('Meshes')
    pdu.clearCollection('Joints')
    # materials_clear()

def main():
    clearLog() # TMP
    clearScene()
    createCollectionIfNone('Meshes')
    createCollectionIfNone('Joints')
    modelName = 'Gk7avengerZ'
    modelName = 'GdysuperdragonZ'
    modelName = 'GdydragonZ'
    # modelName = 'Gleegun1Z'
    # modelName = 'Gfalcon2Z'
    # modelName = 'GcrossbowZ'
    # modelName = 'Gdy357Z'
    # modelName = 'GdydevastatorZ'
    # modelName = 'GdyrocketZ'
    # modelName = 'GsniperrifleZ'
    # modelName = 'Gm16Z'
    # modelName = 'GshotgunZ'
    # modelName = 'GpcgunZ'
    # modelName = 'GdruggunZ'
    # modelName = 'GmaianpistolZ'
    # modelName = 'GskminigunZ'
    # modelName = 'Gz2020Z'
    # modelName = 'Gcmp150Z'
    # modelName = 'PchrdragonZ'
    model = readModel(modelName)

    sc = 0.01
    sc = 1
    traverse(model)
    bpy.context.view_layer.update()
    createModelMeshes(model, sc)

