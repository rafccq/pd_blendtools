import bpy
import bmesh
import logging

import pd_utils as pdu
from pdmodel import PDModel


logger = logging.getLogger(__name__)
logger.handlers.clear()
logger.setLevel(logging.DEBUG)

fh = logging.FileHandler('D:/Mega/PD/pd_blend/pd_guns.log')
fh.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
ch.setLevel(logging.ERROR)

formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s', datefmt='%Y%m%d %H:%M:%S')
fh.setFormatter(formatter)
ch.setFormatter(formatter)

logger.addHandler(fh)
logger.addHandler(ch)


from pd_materials import *

# col: tuple (r,g,b,a) in the range [0:1]
def color_to_bytes(col):
    return [ci.to_bytes(1, 'big') for ci in col]

def normal_to_bytes(norm):
    return [ni.to_bytes(1, 'big', signed=True) for ni in norm]

def coord_to_bytes(coord):
    return [round(ci).to_bytes(2, 'big', signed=True) for ci in coord]

def uv_to_bytes(uv, texsize):
    return [round(32*uvi*ti).to_bytes(2,'big',signed=True) for (uvi, ti) in zip(uv, texsize)]

# will return an array of (v.position, v.color/normal, v.uv_coords)
# normals are mapped from -1.0:1.0 to -128:127 (s8)
# colors are mapped from 0.0:1.0 to 0:255 (u8)
def vtx_data(mesh, bm):
    uv_layer = bm.loops.layers.uv.active
    color_layer = bm.loops.layers.color["vtxcolor"]

    normals = [(0,0,0)] * len(mesh.vertices)

    # retrieve the normals
    for loop in mesh.loops:
        idx = loop.vertex_index
        n = normals[idx]
        if n[0] != 0 and n[1] != 0 and n[2] != 0: continue
        normals[idx] = loop.normal

    vtxdata = []
    for idx,v in enumerate(bm.verts):
        loops = v.link_loops

        if len(loops) == 0:
            print(f'v {v.index} SKIPPED (no geometry)')
            continue

        # face index -> uv coords
        uvs = {l.face.index: (l[uv_layer].uv[0], l[uv_layer].uv[1]) for l in loops}

        mat_idx = loops[0].face.material_index
        mat = mesh.materials[mat_idx]

        has_lighting = material_has_lighting(mat)
        if has_lighting:
            vn = normals[idx]
            maprange = lambda e: int(127.5 * (e+1) - 128) # maps -1.0:1.0 to -128:127
            vni = tuple([maprange(vi) for vi in vn] + [0,1]) # extra '1' element to indicate normal
            colornorm = vni
        else:
            c = loops[0][color_layer] # for now we always use the color from the first loop
            ct = tuple([round(ci*255) for ci in c] + [0]) # '0' to indicate color
            colornorm = ct

        co = v.co
        data = ((co.x, co.y, co.z), colornorm, uvs)
        vtxdata.append(data)

    return vtxdata

class TriBatch:
    def __init__(self):
        self.tris = []
        self.vtxmap = {} # (v_global, uv) -> v_relative
        self.ntris = 0
        self.mat = -1
        self.colors = []
        self.color_indices = []
        self.vtxdata = [] # (position, color/normal, uv coords)

        self.vtx_offset = 0
        self.vtx_start = 0
        self.color_offset = 0
        self.color_start = 0

    def add_tri(self, face, verts, vtxdata):
        tri = []
        for v in verts:
            uv = vtxdata[v][2][face]
            vtxuv = (v, uv)

            if vtxuv in self.vtxmap:
                tri.append(self.vtxmap[vtxuv])
                continue

            self.vtxmap[vtxuv] = len(self.vtxmap)
            tri.append(self.vtxmap[vtxuv])

            vdata = vtxdata[v]
            self.vtxdata.append((vdata[0], vdata[1], uv))

        self.tris.append(tuple([vi for vi in tri]))
        self.ntris += 1

    def has_vert(self, vtxuv):
        return vtxuv in self.vtxmap

    def nverts(self):
        return len(self.vtxmap)

    def build_color_indices(self):
        verts = self.vtxmap.values()
        self.colors, self.color_indices = color_indices(self.vtxdata, verts)

    def vtx_bytes(self, mtx, texsize):
        if not self.colors: self.build_color_indices()

        vtxdata = bytearray()
        for v, vdata in enumerate(self.vtxdata):
            # print(f'---- {v} nv {len(self.vtxdata)} nci {len(self.color_indices)} ----')
            pos = vdata[0]
            pos = (pos[0] - mtx[0], pos[1] - mtx[1], pos[2] - mtx[2])
            uvcoord = vdata[2]

            # pos flag col_idx s t
            vtxbytes = []
            vtxbytes += coord_to_bytes(pos)
            vtxbytes += [b'\x00'] # flag
            vtxbytes += [self.color_indices[v].to_bytes(1, 'big')]
            vtxbytes += uv_to_bytes(uvcoord, texsize)

            for b in vtxbytes: vtxdata += b

        return vtxdata

    def color_bytes(self):
        if not self.colors: self.build_color_indices()

        colordata = bytearray()
        for c in self.colors:
            to_bytes = normal_to_bytes if c[4] == 1 else color_to_bytes
            colnorm = to_bytes(c[0:4])
            for ci in colnorm:
                colordata += ci

        return colordata

def color_indices(vtxdata, verts):
    colors, col_indices = [], []
    # vtx: (x,y,z) f col_idx (u,v)
    # col: 4 bytes: (r, g, b, a) or (nx, ny, nz, 0)
    for v in verts:
        colornorm = vtxdata[v][1]
        if colornorm in colors:
            col_idx = 4 * colors.index(colornorm)
        else:
            col_idx = 4 * len(colors)
            colors.append(colornorm)

        if col_idx >= 256:
            msg = 'Color index exceeds 256'
            print(msg)
            raise Exception(msg)

        col_indices.append(col_idx)

    return colors, col_indices

def create_tri_batches(mesh, bm, vtxdata):
    prevmat = -1
    tri_batches = [TriBatch()]

    MAX_VERTS = 64
    for face, tri in enumerate(bm.faces):
        cur_batch = tri_batches[-1]

        mat = tri.material_index
        if cur_batch.mat < 0: cur_batch.mat = mat
        mat_changed = mat != prevmat and prevmat >= 0

        verts = [v.index for v in tri.verts]
        nverts = cur_batch.nverts()
        uvs = tuple([vtxdata[v][2][face] for v in verts])
        nverts += sum([1 if not cur_batch.has_vert((v, uv)) else 0 for v, uv in zip(verts, uvs)])

        # creates a new batch
        txtnewbatch = ''
        if nverts > MAX_VERTS or mat_changed:
            txtnewbatch = 'NEWBATCH'
            cur_batch = TriBatch()
            tri_batches.append(cur_batch)
            cur_batch.mat = mat

        logger.debug(f'f {face:<3} nv {nverts} {txtnewbatch} {mesh.materials[mat].name} MAX {MAX_VERTS} newmat {mat_changed}')

        cur_batch.add_tri(face, verts, vtxdata)

        if mat_changed or prevmat < 0:
            m = mesh.materials[mat]
            MAX_VERTS = 64 if material_has_lighting(m) else 128

        prevmat = mat

    return tri_batches

class ExportMeshData:
    def __init__(self, name, idx, mtx, layer, meshdata):
        self.name = name
        self.idx = idx
        self.mtx = mtx
        self.layer = layer
        self.meshdata = meshdata
        self.batches = []

    def create_batches(self):
        logger.debug(f'MESH {self.name} M{self.mtx:02X}')
        print(f'MESH {self.name} M{self.mtx:02X}')
        mesh = self.meshdata

        bm = bmesh.new()
        bm.from_mesh(mesh)

        bm.faces.ensure_lookup_table()
        bm.verts.ensure_lookup_table()

        vtxdata = vtx_data(mesh, bm)
        batches = create_tri_batches(mesh, bm, vtxdata)

        for batch in batches: batch.build_color_indices()
        print_batches(mesh, batches)
        bm.free()

        self.batches = batches


# from cooking import MeshLayer
def build_meshmap(obj):
    meshmap = {} # idx -> list of meshes
    for obj in obj.children:
        if obj.type != 'MESH': continue

        idx = obj.pdmodel_props.idx
        mtx = obj.pdmodel_props.mtx
        layer = obj.pdmodel_props.layer

        if idx not in meshmap: meshmap[idx] = []

        meshinfo = ExportMeshData(obj.name, idx, mtx, layer, obj.data)
        meshmap[idx].append(meshinfo)

    return meshmap

def cmd_G_COL(count, offset):
    offset |= 0x05000000
    cmd = bytearray([0x07, 0x00])
    cmd += count.to_bytes(2, 'big')
    cmd += offset.to_bytes(4, 'big')
    return cmd

def cmd_G_VTX(count, offset):
    offset |= 0x05000000
    cmd = bytearray([0x04, 0x00])
    cmd += (count*12).to_bytes(2, 'big')
    cmd += offset.to_bytes(4, 'big')
    return cmd

def cmd_G_MTX(mtx):
    offset = 0x03000000 | (mtx * 64)
    cmd = bytearray([0x01, 0x02, 0x000, 0x40])
    cmd += offset.to_bytes(4, 'big')
    return cmd

def cmd_G_TRI(tri):
    cmd = bytearray([0xbf, 0x00, 0x00, 0x00, 0x00])
    if len(tri) != 3:
        print(f'WARNING: invalid tri: {tri}')
    cmd += bytearray([v for v in tri])
    return cmd

def cmd_G_RDPPIPESYNC():
    return bytearray.fromhex('E700000000000000')

def cmd_G_END():
    return bytearray.fromhex('B800000000000000')

def meshes_to_gdl(meshes, vtx_start, nverts):
    if not meshes: return None

    color_start = pdu.align(vtx_start + nverts * 12, 8)

    gdlbytes = cmd_G_RDPPIPESYNC()

    for mesh in meshes:
        for batch in mesh.batches:
            batch.vtx_start = vtx_start
            batch.color_start = color_start

        gdlbytes += create_gdl(mesh)

    gdlbytes += cmd_G_END()
    return gdlbytes

def create_gdl(mesh: ExportMeshData):
    gdlbytes = bytearray()
    materials = mesh.meshdata.materials

    gdlbytes += cmd_G_MTX(mesh.mtx)

    for idx, batch in enumerate(mesh.batches):
        mat = materials[batch.mat]
        mat_cmds = material_cmds(mat)
        for cmd in mat_cmds:
            gdlbytes += bytearray.fromhex(cmd)

        gdlbytes += cmd_G_COL(len(batch.colors), batch.color_start + batch.color_offset)
        gdlbytes += cmd_G_VTX(batch.nverts(), batch.vtx_start + batch.vtx_offset)

        for tri in batch.tris:
            gdlbytes += cmd_G_TRI([v for v in tri])

    return gdlbytes

def loadmodel(romdata, modelname):
    modeldata = romdata.modeldata(modelname)
    return PDModel(modeldata)

def export_model(modelname):
    obj = bpy.data.objects[modelname]
    objmap = build_meshmap(obj)
    logger.debug(f'exportModel: {modelname}')

    romdata = pdu.loadrom()
    model = loadmodel(romdata, modelname)

    # objmap: idx -> list of meshes
    for idx, meshes in objmap.items():
        vtxdata = bytearray()
        colordata = bytearray()

        for mesh in meshes:
            meshname = mesh.name
            mtx = mesh.mtx
            ln = '-'*32
            logger.debug(f'{ln} {meshname}-M{mtx:2X} {ln}')
            mesh.create_batches()

            materials = mesh.meshdata.materials

            # aggregate vtxdata from all batches
            for batch in mesh.batches:
                batch.vtx_offset = len(vtxdata)
                batch.color_offset = len(colordata)

                mtx = model.matrices[mesh.mtx]
                mat = materials[batch.mat]
                image = material_get_teximage(mat)
                texsize = (1,1)
                if image: texsize = image.size
                else:
                    print(f'WARNING: material has no texture. Mesh{mesh.name} mat {mat.name}')

                vtxdata += batch.vtx_bytes(mtx, texsize)
                colordata += batch.color_bytes()

        model.replace_vtxdata(idx, vtxdata)
        model.replace_colordata(idx, colordata)

    # write all model data except GDLs, and patch pointers
    patched = model.patch()

    # create GDLs from the meshes
    for idx, meshes in objmap.items():
        rodata = model.rodatas[idx]
        nodetype = rodata['_node_type_']

        # split the list into 2 for opa and xlu layers (here we assume the list consists of contiguous opa/xlu meshes
        idx_xlu = pdu.index_where(meshes, lambda e: e.layer == 1, len(meshes)) # TODO Meshlayer enum
        meshes_opa = meshes[:idx_xlu]
        meshes_xlu = meshes[idx_xlu:]

        print(f'MESH {idx:02X} idx {idx_xlu} {len(meshes_opa)} {len(meshes_xlu)}')
        vtx_start = rodata['vertices']

        nverts = rodata['numvertices'] if nodetype in [0x04, 0x18] else rodata['unk00'] * 4
        gdlbytes_opa = meshes_to_gdl(meshes_opa, vtx_start, nverts)
        gdlbytes_xlu = meshes_to_gdl(meshes_xlu, vtx_start, nverts)

        opa = 'opagdl' if nodetype in [0x04, 0x18] else 'gdl'
        xlu = 'xlugdl'
        model.replace_gdl(patched, gdlbytes_opa, idx, opa)
        model.replace_gdl(patched, gdlbytes_xlu, idx, xlu)

    patched = pdu.compress(patched)
    pdu.write_file('D:/Mega/PD/pd_blend/modelbin', f'{modelname}', patched)

def print_batches(mesh, tri_batches):
    f = 0
    prevmat = -1
    for bidx, batch in enumerate(tri_batches):
        mat = batch.mat

        m = mesh.materials[mat]
        matname = m.name
        newmat = ' NEWMAT' if mat != prevmat else ''
        txtnorm = ' NORM' if material_has_lighting(m) else ''
        logger.debug(f'batch_{bidx} mat {mat} {matname} '
                     f'nv {batch.nverts()} nt {batch.ntris} '
                     f'ncols {len(batch.colors)} {newmat}{txtnorm}')

        for tri in batch.tris:
            vidxs = [k[0] for k in batch.vtxmap.keys()]
            tglob = [vidxs[v] for v in tri]
            trel = [v for v in tri]

            cidxs = [batch.color_indices[v] for v in trel]
            colors = [batch.colors[ci//4] for ci in cidxs]

            txtcol = ''

            for col in colors:
                if col[4]: # normal
                    bo = 'big'
                    s = ''.join([f'{col[i].to_bytes(1, bo, signed=True).hex().upper()} ' for i in range(0, 3)])
                else:
                    s = ''.join([f'{c:02X} ' for c in col])

                txtcol += f'({s.rstrip()}) '

            txtcol = txtcol.rstrip()
            txtcol += f' | [{cidxs[0]:<4} {cidxs[1]:<4} {cidxs[2]:<4}] '

            logger.debug(f'  {f:<3} ({trel[0]:<3} {trel[1]:<3} {trel[2]:<3}) '
                         f'({tglob[0]:<3} {tglob[1]:<3} {tglob[2]:<3}){txtcol}')
            f += 1
