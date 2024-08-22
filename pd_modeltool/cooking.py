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
    # style="{",
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

    suffix = f'[{sub_idx}]-M{mtxindex:02X}' if sub_idx >= 0 else ''
    obj = bpy.data.objects.new(f'{idx:02X}.Mesh{suffix}', mesh_data)
    obj.location = pos
    bpy.data.collections['Meshes'].objects.link(obj)
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj

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

class SubMesh:
    def __init__(self ):
        self.nverts = 0
        self.vtx_start = -1
        self.vtx_end = -1
        self.vtx_offset = -1
        self.mtxindex = 0
        self.tris = []

    def setVtxOffset(self, vtx_offset):
        if self.vtx_offset < 0:
            self.vtx_offset = vtx_offset
            
    def setVtxStart(self, vtx_start):
        if self.vtx_start < 0:
            self.vtx_start = vtx_start

    def setVtxEnd(self, vtx_end):
        self.vtx_end = vtx_end
        

def collectSubMeshes(model, ro_gundl, idx):
    ptr_opagdl = ro_gundl['opagdl']
    ptr_vtx = ro_gundl['vertices']&0xffffff
    gdl = model.data(ptr_opagdl)
    addr = 0
    vtx_offset = 0
    tris = []
    bo='big'
    dbg = idx == 0x3
    # dbg = 0

    subMeshes = []
    currentSubMesh = SubMesh()
    # if dbg: logger.debug(f'ptr_vtx {ptr_vtx:04X}')
    currentSubMesh.setVtxOffset(ptr_vtx)

    vtx_idx = 0
    nverts = 0
    ntris = 0
    prev = None
    while True:
        # dbg = idx == 0x3 and len(subMeshes) == 3
        cmd = gdl[addr:addr+8]
        op = cmd[0]

        if op == G_END: 
            if len(currentSubMesh.tris): 
                subMeshes.append(currentSubMesh)
                if dbg: logger.debug(f'  submesh {len(subMeshes)-1:02X} ntris {len(currentSubMesh.tris)} nvtx {currentSubMesh.nverts}')
            break
    
        cmdint = int.from_bytes(cmd, bo)
        
        if dbg: logger.debug(f'{cmdint:016X} {pdu.GDLcodes[cmd[0]]}')
        
        if op == G_TRI4:
            # ofs = (vtx_offset - currentSubMesh.vtx_offset)//12 - vtx_idx
            ofs = (vtx_offset - currentSubMesh.vtx_offset)//12
            # if vtx_idx:
            #     ofs = vtx_idx
            tris = pdu.read_tri4(cmd, ofs)
            s = ntris
            ntris += len(tris)
            currentSubMesh.tris += tris
            if dbg: logger.debug(f'  {s}-{ntris-1} ofs {ofs+vtx_idx*0:04X} {vtx_idx:02X} tris {pdu.read_tri4(cmd, 0)}')
            msg = ''
            if dbg:
                vtxs_raw = model.data(currentSubMesh.vtx_offset)
                logger.debug(f'  nverts {currentSubMesh.nverts}')
                verts = pdu.read_vtxs(vtxs_raw, currentSubMesh.nverts+1, 1)
                for idx, t in enumerate(tris):
                    if dbg: logger.debug(f'  t {t}')
                    v0 = verts[t[0]]
                    v1 = verts[t[1]]
                    v2 = verts[t[2]]
                    logger.debug(f'  v0 {v0} v1 {v1} v2 {v2}')
                    # logger.debug(f'  t {t}')
                if dbg: logger.debug(f'  verts {msg}')

#            print(f'{cmdint:08X} VTX {vtx_offset:04X} ntri {len(currentSubMesh.tris)}')
#            print(tris)
        elif op == G_VTX:
            nverts = int.from_bytes(cmd[2:4], bo) // 12
            vtx_idx = cmd[1] & 0xf
            # vtx_offset = int.from_bytes(cmd[5:8], bo) - ptr_vtx
            # vtx_offset = int.from_bytes(cmd[5:8], bo) - currentSubMesh.vtx_offset
            if vtx_idx == 0:
                vtx_offset = int.from_bytes(cmd[5:8], bo)
            # if dbg: logger.debug(f'  n {nverts} ofs {vtx_offset:04X} vtx_idx {vtx_idx}')
            setofs = currentSubMesh.vtx_offset < 0
            currentSubMesh.setVtxOffset(vtx_offset)
            # vtx_offset //= 12
            currentSubMesh.setVtxStart((vtx_offset - ptr_vtx)//12)
            ofs = int.from_bytes(cmd[5:8], bo)
            msg = f' [NEW_OFS]' if setofs else ''
            if dbg: logger.debug(f'  vtx_ofs {currentSubMesh.vtx_offset:04X} ofs {ofs:04X} n {nverts} vtx_idx {vtx_idx} {msg}')
            # currentSubMesh.setVtxStart(0)
            # currentSubMesh.setVtxEnd(vtx_offset//12 + nvtx)
            currentSubMesh.nverts += nverts
        elif op == G_MTX:
            # start new submesh
            if len(currentSubMesh.tris):
                # print(f'  newsubm {currentSubMesh.tris}')
                # logger.debug(currentSubMesh.tris)
                ntris = 0
                subMeshes.append(currentSubMesh)
                if dbg: logger.debug(f'  submesh {len(subMeshes)-1:02X} ntris {len(currentSubMesh.tris)} nvtx {currentSubMesh.nverts}')
                currentSubMesh = SubMesh()
                currentSubMesh.mtxindex = (cmdint & 0xfff) // 0x40  # TODO check idx mask is correct
                if prev[0] == G_VTX:
                    if dbg: logger.debug(f'  set vtx_ofs {vtx_offset:04X}')
                    currentSubMesh.setVtxOffset(vtx_offset)
                    currentSubMesh.nverts += nverts
            else:
                currentSubMesh.mtxindex = (cmdint & 0xfff) // 0x40  # TODO check idx mask is correct

            # if vtx_offset:
                #     if dbg: logger.debug(f'  submesh.vtx_offset {vtx_offset:02X}')
                #     currentSubMesh.setVtxOffset(vtx_offset)

            # currentSubMesh = SubMesh()
            # currentSubMesh.setVtxOffset(vtx_offset)

        addr += 8
        prev = cmd
        
#    print(subMeshes)
        
    return subMeshes

def getPositionFromMtxIndex(model, mtxindex):
    for addr, node in model.nodes.items():
        if node['type'] == 2:
            idx = node['_idx_']
            ro = TMP_getrodata(model, node['rodata'])
            # print('idx', f'{idx:02X}', ro, 'q ', mtxindex)
            if ro['mtxindexes'][0] == mtxindex:
                name = posNodeName(idx)
                obj = bpy.data.collections['Joints'].objects[name]
                return obj.location
    return None

def createModelMesh(idx, model, ro_gundl, sc):
    logger.debug(f'createModelMesh {idx:02X}')
    ptr_vtx = ro_gundl['vertices']
    vtxs = model.vertices[ptr_vtx]['bytes']
#    ptr_vtx &= 0xffffff
#    print(f'ptr_vtx {ptr_vtx:08X}')

#    #pdu.print_bin('^VTX', vtxs, 0, -1, 2, 6)

#    tris = collectTris(ro_gundl)
    nvtx = ro_gundl['numvertices']
    verts = pdu.read_vtxs(vtxs, nvtx, sc)
#    createMesh(idx, verts, tris)
#    print(tris)

    subMeshes = collectSubMeshes(model, ro_gundl, idx)
    n_submeshes = len(subMeshes)
    logger.debug(f'idx {idx:02X} n {n_submeshes}')
    for sub_idx, mesh in enumerate(subMeshes):
#        prefix = f'{idx:02X}[{sub_idx}]'
        s = mesh.vtx_start
        e = mesh.vtx_start + mesh.nverts
        # e = len(verts)
        vtxs = verts[s:e]
        tris = mesh.tris
        sub_idx = sub_idx if n_submeshes > 1 else -1
        pos = getPositionFromMtxIndex(model, mesh.mtxindex)
        createMesh(vtxs, tris, idx, sub_idx, pos, mesh.mtxindex)
        logger.debug(f'  n {len(tris)} vtx s {s} e {e}')

def createModelMeshes(model, sc):
    logger.debug('createModelMeshes')
    idx = 0
    for ro in model.rodatas:
        if ro['_node_type_'] == 4:
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
    modelName = 'Gk7avengerZ'
    modelName = 'Gleegun1Z'
    modelName = 'Gfalcon2Z'
    # modelName = 'GcrossbowZ'
    # modelName = 'Gdy357Z'
    # modelName = 'GdydevastatorZ'
    # modelName = 'GsniperrifleZ'
    # modelName = 'Gm16Z'
    # modelName = 'GshotgunZ'
    model = readModel(modelName)

    sc = 0.01
    sc = 1
    traverse2(model)
    createModelMeshes(model, sc)
    # createModelJoints(model, sc)

