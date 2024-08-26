import os
import struct
import logging

import bpy
from bpy import context as ctx
from mathutils import Euler, Vector, Matrix

import pd_utils as pdu
import pdmodel
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
    collection = None
    if name not in bpy.data.collections:
        collection = bpy.data.collections.new(name)
        ctx.scene.collection.children.link(collection)
    else:
        collection = bpy.data.collections[name]
    
def createMesh(verts, faces, idx, sub_idx, pos, mtxindex):
    mesh_data = bpy.data.meshes.new('mesh_data')
    mesh_data.from_pydata(verts, [], faces)

    # pos = getPositionFromMtxIndex(model, mesh.mtxindex)

    suffix = f'[{sub_idx}]-M{mtxindex:02X}' if sub_idx >= 0 else f'-M{mtxindex:02X}'
    # suffix = f'[{sub_idx}]' if sub_idx >= 0 else ''
    obj = bpy.data.objects.new(f'{idx:02X}.Mesh{suffix}', mesh_data)
    # obj.location = pos
    bpy.data.collections['Meshes'].objects.link(obj)
    # obj.select_set(True)
    # bpy.context.view_layer.objects.active = obj

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
def traverse(model, node, depth):
    global nodeidx

    nodeidx += 1
    if not node: return

    sp = ' ' * depth*2
    nodetype = node['type']
    print(f'{sp} NODE {nodeidx:02X} t {nodetype:02X}' )
    child = pdmodel.unmask(node['child'])
    if child:
        traverse(model, model.nodes[child], depth+1)

    nextaddr = pdmodel.unmask(node['next'])
    if nextaddr:
        traverse(model, model.nodes[nextaddr], depth)

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

def createModelJoints(model, sc):
    # traverse(model, model.rootnode, 0)
    traverse2(model)
    idx = 0
    for ro in model.rodatas:
        if ro['_node_type_'] == 2:
            # print(ro)
            pos = ro['pos']['f']
            x = struct.unpack('f', pos[0].to_bytes(4, 'little'))[0]
            y = struct.unpack('f', pos[1].to_bytes(4, 'little'))[0]
            z = struct.unpack('f', pos[2].to_bytes(4, 'little'))[0]

            # createJoint(idx, x*sc, z*sc, y*sc)
            createJoint(idx, x, z, y)
        idx += 1
def TMP_getrodata(model, addr):
    for ro in model.rodatas:
        if ro['_addr_'] == unmask(addr): return ro

    return None

def traverse2(model):
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
    
G_MTX  = 0x01
G_VTX  = 0x04
G_TRI4 = 0xb1
G_END  = 0xb8

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

    def vtx_from_buffer(self, vtx_buffer, n):
        if len(self.vtx_buffer): return

        logger.debug(f'>>> MESH {self.mtxindex:02X} add vtx: {n}')

        # self.vtx_buffer = vtx_buffer
        self.tri_index = len(self.verts)
        for i in range(0, n):
            self.verts.append(vtx_buffer[i].pos)
            self.vtx_buffer.append(vtx_buffer[i].pos)

    def add_tri(self, tri):
        # if self.mtxindex == 0x2a: loghger.debug(f'>>> TRIANGLE ON MESH 2A')
        ofs = self.tri_index
        t = (
            tri[0] + ofs,
            tri[1] + ofs,
            tri[2] + ofs
        )
        if self.dbg: logger.debug(f'  f {len(self.tris)} {t} tidx {ofs} M{self.mtxindex:02X}')
        self.tris.append(t)

    def clear_vtx_buffer(self):
        logger.debug(f'>>> MESH {self.mtxindex:02X} clearbuf')
        self.vtx_buffer.clear()

class VtxBufferEntry:
    def __init__(self, pos=(0,0,0), group_size=0, mtxidx=-1):
        self.pos = pos
        self.group_size = group_size
        self.mtxidx = mtxidx
        self.meshes_loaded = []

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
    sc = 1
    verts = pdu.read_vtxs(vtxbytes, nvtx, sc)

    gdl = model.data(ptr_opagdl)
    addr = 0
    bo='big'
    dbg = idx == 0x1

    matrixmesh_map = {} # matrix idx -> mesh
    mtxindex = -1

    vtx_buffer = [VtxBufferEntry()]*128
    vtx_buf_size = 0

    if dbg:
        n = min(nvtx, 300)
        for i in range(0, n):
            v = verts[i]
            logger.debug(f' v_{i} {v}')

    if dbg: logger.debug(f'[CREATEMESH {idx:02X}] ptr_vtx {ptr_vtx:04X} nvtx {len(verts)}')

    while True:
        cmd = gdl[addr:addr+8]
        op = cmd[0]

        if op == G_END: break

        cmdint = int.from_bytes(cmd, bo)

        if dbg: logger.debug(f'{cmdint:016X} {pdu.GDLcodes[cmd[0]]}')

        if op == G_TRI4:
            tris = pdu.read_tri4(cmd, 0)

            for tri in tris:
                v = select_mesh(tri, vtx_buffer)
                if dbg: logger.debug(tri)
                mesh = matrixmesh_map[v.mtxidx]
                # if len(mesh.vtx_buffer) == 0:
                mesh.vtx_from_buffer(vtx_buffer, vtx_buf_size)
                mesh.add_tri(tri)
        elif op == G_VTX:
            nverts = ((cmd[1] & 0xf0) >> 4) + 1
            vtx_idx = cmd[1] & 0xf
            vtx_ofs = int.from_bytes(cmd[5:8], bo)

            vstart = (vtx_ofs - ptr_vtx) // 12
            vtx_buf_size = vtx_idx + nverts
            pos = getPositionFromMtxIndex(model, mtxindex)

            logger.debug(f'  vstart {vstart} n {nverts} vidx {vtx_idx:01X} vbufsize {vtx_buf_size}')

            for i, v in enumerate(verts[vstart:vstart+nverts]):
                v = (v[0] + pos[0], v[1] + pos[1], v[2] + pos[2])
                vtx_buffer[vtx_idx+i] = VtxBufferEntry(v, nverts, mtxindex)

            matrixmesh_map[mtxindex].clear_vtx_buffer()
        elif op == G_MTX:
            mtxindex = (cmdint & 0xffffff) // 0x40
            logger.debug(f'  MTX {mtxindex:04X}')

            if mtxindex not in matrixmesh_map:
                currentSubMesh = matrixmesh_map[mtxindex] = SubMesh()
                currentSubMesh.mtxindex = mtxindex
                currentSubMesh.dbg = dbg

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
                # logger.debug(f'  found MTX {mtxindex:02X} in {name}: {obj.matrix_world.translation}')
                return obj.matrix_world.translation
    return None

def createModelMesh(idx, model, ro_gundl, sc):
    # logger.debug(f'createModelMesh {idx:02X}')

    # subMeshes = _collectSubMeshes(model, ro_gundl, idx)
    subMeshes = collectSubMeshes(model, ro_gundl, idx)
    n_submeshes = len(subMeshes)
    logger.debug(f'idx {idx:02X} n {n_submeshes}')
    for sub_idx, mesh in enumerate(subMeshes):
        tris = mesh.tris
        sub_idx = sub_idx if n_submeshes > 1 else -1
        pos = getPositionFromMtxIndex(model, mesh.mtxindex)
        createMesh(mesh.verts, tris, idx, sub_idx, pos, mesh.mtxindex)
        logger.debug(f'  n {len(tris)} nvtx {len(mesh.verts)}')

def createModelMeshes(model, sc):
    logger.debug('createModelMeshes')
    idx = 0
    for ro in model.rodatas:
        # if ro['_node_type_'] == 4:
        if ro['_node_type_'] == 4 and idx == 1:
#            print(ro)
            createModelMesh(idx, model, ro, sc)
        idx += 1

def clearLog():
    f = open('D:/Mega/PD/pd_blend/pd_guns.log', 'r+')
    f.truncate(0)

def clearScene():
    pdu.clearCollection('Meshes')
    pdu.clearCollection('Joints')

def main():
    clearLog() # TMP
    clearScene()
    createCollectionIfNone('Meshes')
    createCollectionIfNone('Joints')
    # modelName = 'Gk7avengerZ'
    modelName = 'Gleegun1Z'
    modelName = 'Gfalcon2Z'
    # modelName = 'GcrossbowZ'
    # modelName = 'Gdy357Z'
    # modelName = 'GdydevastatorZ'
    # modelName = 'GsniperrifleZ'
    # modelName = 'Gm16Z'
    # modelName = 'GshotgunZ'
    modelName = 'GpcgunZ'
    # modelName = 'GdruggunZ'
    # modelName = 'GmaianpistolZ'
    # modelName = 'GskminigunZ'
    # modelName = 'Gz2020Z'
    modelName = 'Gcmp150Z'
    # modelName = 'PchrdragonZ'
    model = readModel(modelName)

    sc = 0.01
    sc = 1
    traverse2(model)
    bpy.context.view_layer.update()
    createModelMeshes(model, sc)
    # createModelJoints(model, sc)

