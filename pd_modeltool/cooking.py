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

    def setMtx(self, mtx):
        self.current_mtx = mtx

    def setVtxOffset(self, vtx_offset):
        if self.vtx_offset < 0:
            self.vtx_offset = vtx_offset
            
    def setVtxStart(self, vtx_start):
        if self.vtx_start < 0:
            self.vtx_start = vtx_start

    def setVtxEnd(self, vtx_end):
        self.vtx_end = vtx_end

    def addTri(self, tri, ofs):
        ofs += self.tri_index
        t = (
            tri[0] + ofs,
            tri[1] + ofs,
            tri[2] + ofs
        )
        if self.dbg: logger.debug(f'  f {len(self.tris)} {t} tidx {ofs} M{self.mtxindex:02X}')
        self.tris.append(t)

    def addTris(self, tris):
        ofs = self.tri_index
        for t in tris:
            t = (
                t[0] + ofs,
                t[1] + ofs,
                t[2] + ofs
            )
            self.tris.append(t)
            if self.dbg:
                logger.debug(f'  t {t}')
                v0 = self.verts[t[0]]
                v1 = self.verts[t[1]]
                v2 = self.verts[t[2]]
                logger.debug(f'  v0 {_t(v0)} v1 {_t(v1)} v2 {_t(v2)}')

    def addVtx(self, vert, mtx):
        current_nverts = len(self.verts)
        # if current_nverts:
        #     self.tri_index = current_nverts

        vtx = (
            vert[0] + mtx[0],
            vert[1] + mtx[1],
            vert[2] + mtx[2],
        )
        self.verts.append(vtx)

    def addVtxs(self, verts, n, idx):
        current_nverts = len(self.verts)
        # if current_nverts and idx == 0:
        if current_nverts:
            self.tri_index = current_nverts

        diff = idx - current_nverts
        if diff > 0:
            logger.debug(f'  ADD_ZERO {diff}')
            # if idx == 0: self.tri_index += diff
            # for i in range(0, diff): self.verts.append((0,0,0))

        pos = self.current_mtx
        # pos = (0,0,0)
        if self.dbg: logger.debug(f'  mtx {pos}')
        for i in range(0, n):
            v = verts[i]
            vtx = (
                v[0] + pos[0],
                v[1] + pos[1],
                v[2] + pos[2],
            )
            self.verts.append(vtx)

        logger.debug(f'  addvtx ofs {self.vtx_offset:04X} n {n} nvtx {len(verts)} curlen {len(self.verts)} tri_idx {self.tri_index}')

    def _addVtxs(self, verts, n, idx):
        current_nverts = len(self.verts)
        if current_nverts and idx == 0:
        # if current_nverts:
            self.tri_index = current_nverts

        diff = idx - current_nverts
        if diff > 0:
            logger.debug(f'  ADD_ZERO {diff}')
            if idx == 0: self.tri_index += diff
            for i in range(0, diff): self.verts.append((0,0,0))

        pos = self.current_mtx
        # pos = (0,0,0)
        if self.dbg: logger.debug(f'  mtx {pos}')
        for i in range(0, n):
            v = verts[i]
            vtx = (
                v[0] + pos[0],
                v[1] + pos[1],
                v[2] + pos[2],
            )
            self.verts.append(vtx)

        logger.debug(f'  addvtx ofs {self.vtx_offset:04X} n {n} nvtx {len(verts)} curlen {len(self.verts)} tri_idx {self.tri_index}')

def collectSubMeshes(model, ro_gundl, idx):
    # [:6] M24
    # [6:] M21
    # (5,24) (6,21)
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
    # dbg = 1
    # dbg = 0

    matrixmesh_map = {} # matrix idx -> mesh
    tris2matrix = {} # idx -> mtx where idx is the max tri idx using mtx
    mtxindex = -1

    if dbg:
        n = min(nvtx, 300)
        for i in range(0, n):
            v = verts[i]
            logger.debug(f' v_{i} {v}')

    subMeshes = []
    currentSubMesh = SubMesh()
    if dbg: logger.debug(f'[CREATEMESH {idx:02X}] ptr_vtx {ptr_vtx:04X} nvtx {len(verts)}')
    currentSubMesh.setVtxOffset(ptr_vtx)

    # vtx_offset = 0
    vtx_idx = 0
    ntris = 0
    prevmtx = 0
    while True:
        currentSubMesh.dbg = dbg
        cmd = gdl[addr:addr+8]
        op = cmd[0]

        if op == G_END:
            # if len(currentSubMesh.tris):
            #     subMeshes.append(currentSubMesh)
            #     if dbg: logger.debug(f'SUBMESH {len(subMeshes)-1:02X} ntris {len(currentSubMesh.tris)} nvtx {currentSubMesh.nverts} -----------^')
            break

        cmdint = int.from_bytes(cmd, bo)

        if dbg: logger.debug(f'{cmdint:016X} {pdu.GDLcodes[cmd[0]]}')

        if op == G_TRI4:
            tris, min_idxs = pdu.read_tri4(cmd, 0)

            # [(0, 1, 2), (3, 4, 5), (6, 7, 8), (6, 8, 9)]
            # [0, 3, 6, 6]
            # (5, 24), (15, 21)
            dbgmsg = ''
            for tri, min_idx in zip(tris, min_idxs):
                mtx = next((info[1] for info in tris2matrix.values() if min_idx <= info[0]), None)
                currentSubMesh = matrixmesh_map[mtx]
                ofs = -vtx_idx if min_idx >= vtx_idx else 0
                currentSubMesh.addTri(tri, ofs)

                dbgmsg += f'{tri}/{mtx:02X} '

            ntris += len(tris)
            if dbg:
                logger.debug(f'  ofs {vtx_ofs:04X} vidx {vtx_idx:02X} tris [{dbgmsg}]')
                logger.debug(f'  trimap {tris2matrix.items()}')
        elif op == G_VTX:
            nverts = ((cmd[1] & 0xf0) >> 4) + 1
            vtx_idx = cmd[1] & 0xf
            vtx_ofs = int.from_bytes(cmd[5:8], bo)

            vstart = (vtx_ofs - ptr_vtx) // 12
            if nverts > 1:
                currentSubMesh = matrixmesh_map[mtxindex]
                logger.debug(f'  vstart {vstart} n {nverts} vidx {vtx_idx:01X}')
                currentSubMesh.addVtxs(verts[vstart:], nverts, vtx_idx)
                tris2matrix[vtx_idx] = (nverts + vtx_idx-1, mtxindex)
            else:
                # mtx = getPositionFromMtxIndex(model, prevmtx)
                mtx = getPositionFromMtxIndex(model, mtxindex)
                currentSubMesh = matrixmesh_map[prevmtx]
                currentSubMesh.addVtx(verts[vstart], mtx)

        elif op == G_MTX:
            prevmtx = mtxindex
            mtxindex = (cmdint & 0xffffff) // 0x40
            logger.debug(f'  MTX {mtxindex:04X}')

            if mtxindex not in matrixmesh_map:
                currentSubMesh = matrixmesh_map[mtxindex] = SubMesh()
                currentSubMesh.setMtx(getPositionFromMtxIndex(model, mtxindex))
                currentSubMesh.mtxindex = mtxindex

        addr += 8

    return list(matrixmesh_map.values())

def _collectSubMeshes(model, ro_gundl, idx):
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
    # dbg = 1
    # dbg = 0

    if dbg:
        n = min(nvtx, 1000)
        for i in range(0, n):
            v = verts[i]
            logger.debug(f' v_{i} {v}')

    subMeshes = []
    currentSubMesh = SubMesh()
    if dbg: logger.debug(f'[CREATEMESH {idx:02X}] ptr_vtx {ptr_vtx:04X} nvtx {len(verts)}')
    currentSubMesh.setVtxOffset(ptr_vtx)

    prev = 0
    nverts = 0
    vtx_offset = 0
    vtx_idx = 0
    ntris = 0
    while True:
        currentSubMesh.dbg = dbg
        cmd = gdl[addr:addr+8]
        op = cmd[0]

        if op == G_END: 
            if len(currentSubMesh.tris): 
                subMeshes.append(currentSubMesh)
                if dbg: logger.debug(f'SUBMESH {len(subMeshes)-1:02X} ntris {len(currentSubMesh.tris)} nvtx {currentSubMesh.nverts} -----------^')
            break
    
        cmdint = int.from_bytes(cmd, bo)
        
        if dbg: logger.debug(f'{cmdint:016X} {pdu.GDLcodes[cmd[0]]}')
        
        if op == G_TRI4:
            vtx_ofs = (vtx_offset - currentSubMesh.vtx_offset)//12
            tris, _ = pdu.read_tri4(cmd, 0)
            s = ntris
            ntris += len(tris)
            if dbg: logger.debug(f'  {s}-{ntris-1} ofs {vtx_ofs+vtx_idx*0:04X} {vtx_idx:02X} tris {pdu.read_tri4(cmd, 0)}')
            currentSubMesh.addTris(tris)
        elif op == G_VTX:
            nverts = ((cmd[1] & 0xf0) >> 4) + 1
            vtx_idx = cmd[1] & 0xf

            ofs = int.from_bytes(cmd[5:8], bo)
            if vtx_idx == 0:
                vtx_offset = ofs

            currentSubMesh.setVtxOffset(vtx_offset)
            vstart = (ofs - ptr_vtx) // 12
            logger.debug(f'  vstart {vstart} n {nverts} vidx {vtx_idx:01X}')
            currentSubMesh._addVtxs(verts[vstart:], nverts, vtx_idx)
        elif op == G_MTX:
            mtxindex = (cmdint & 0xffffff) // 0x40
            logger.debug(f'  MTX {mtxindex:04X}')
            if len(currentSubMesh.tris):
                # close this mesh..
                ntris = 0
                subMeshes.append(currentSubMesh)
                if dbg: logger.debug(f'(SUBMESH {len(subMeshes)-1:02X}) ntris {len(currentSubMesh.tris)} nvtx {currentSubMesh.nverts} -----------^')

                # .. and start new submesh
                prevmtx_idx = currentSubMesh.mtxindex
                currentSubMesh = SubMesh()
                if prev[0] == G_VTX:
                    if dbg: logger.debug(f'  set vtx_ofs {vtx_offset:04X}')

                    currentSubMesh.setVtxOffset(vtx_offset)

                    currentSubMesh.setMtx(getPositionFromMtxIndex(model, prevmtx_idx))
                    currentSubMesh.mtxindex = prevmtx_idx

                    vstart = (vtx_offset - ptr_vtx) // 12
                    logger.debug(f'  (from prev) vstart {vstart} n {nverts} vidx {vtx_idx:01X}')
                    currentSubMesh.addVtxs(verts[vstart:], nverts, vtx_idx)

            if currentSubMesh.mtxindex >= 0:
                currentSubMesh.setMtx(getPositionFromMtxIndex(model, mtxindex))
                currentSubMesh.mtxindex = mtxindex

        addr += 8
        prev = cmd

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
                logger.debug(f'  found MTX {mtxindex:02X} in {name}: {obj.matrix_world.translation}')
                return obj.matrix_world.translation
    return None

def createModelMesh(idx, model, ro_gundl, sc):
    # logger.debug(f'createModelMesh {idx:02X}')
    ptr_vtx = ro_gundl['vertices']
    vtxs = model.vertices[ptr_vtx]['bytes']
#    ptr_vtx &= 0xffffff
#    print(f'ptr_vtx {ptr_vtx:08X}')

#    #pdu.print_bin('^VTX', vtxs, 0, -1, 2, 6)

#    tris = collectTris(ro_gundl)
    nvtx = ro_gundl['numvertices']
    # verts = pdu.read_vtxs(vtxs, nvtx, sc)

    subMeshes = _collectSubMeshes(model, ro_gundl, idx)
    n_submeshes = len(subMeshes)
    logger.debug(f'idx {idx:02X} n {n_submeshes}')
    for sub_idx, mesh in enumerate(subMeshes):
#        prefix = f'{idx:02X}[{sub_idx}]'
#         s = mesh.vtx_start
#         e = mesh.vtx_start + mesh.nverts
        # e = len(verts)
        # vtxs = verts[s:e]
        tris = mesh.tris
        sub_idx = sub_idx if n_submeshes > 1 else -1
        pos = getPositionFromMtxIndex(model, mesh.mtxindex)
        createMesh(mesh.verts, tris, idx, sub_idx, pos, mesh.mtxindex)
        logger.debug(f'  n {len(tris)} nvtx {len(mesh.verts)}')

def createModelMeshes(model, sc):
    logger.debug('createModelMeshes')
    idx = 0
    for ro in model.rodatas:
        if ro['_node_type_'] == 4:
        # if ro['_node_type_'] == 4 and idx == 5:
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
    # modelName = 'Gfalcon2Z'
    # modelName = 'GcrossbowZ'
    # modelName = 'Gdy357Z'
    # modelName = 'GdydevastatorZ'
    # modelName = 'GsniperrifleZ'
    # modelName = 'Gm16Z'
    # modelName = 'GshotgunZ'
    modelName = 'GpcgunZ'
    # modelName = 'PchrdragonZ'
    model = readModel(modelName)

    sc = 0.01
    sc = 1
    traverse2(model)
    bpy.context.view_layer.update()
    createModelMeshes(model, sc)
    # createModelJoints(model, sc)

