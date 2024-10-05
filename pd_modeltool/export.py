import bpy
import bmesh
import logging


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
    return bytearray([round(255*ci) for ci in col])

def normal_to_bytes(norm):
    # conv range [-1:1] to [-128:127]
    maprange = lambda v: int(127.5 * (v+1) - 128)
    return [maprange(ni).to_bytes(1, 'big', signed=True) for ni in norm]

def coord_to_bytes(coord):
    return [round(ci).to_bytes(2, 'big', signed=True) for ci in coord]

def uv_to_bytes(uv, texsize):
    return [round(32*uvi*ti).to_bytes(2,'big',signed=True) for (uvi, ti) in zip(uv, texsize)]

# returns an array of (v.position, v.color/normal, v.uv_coords)
# normals are mapped from -1.0:1.0 to -128:127 (s8)
# colors are mapped from 0:1.0 to 0:255 (u8)
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
        loop = v.link_loops

        if len(loop) == 0:
            print(f'v {v.index} SKIPPED (no geometry)')
            continue

        loopdata = loop[0][uv_layer]
        uv = loopdata.uv

        mat_idx = loop[0].face.material_index
        mat = mesh.materials[mat_idx]

        has_lighting = material_has_lighting(mat)
        if has_lighting:
            vn = normals[idx]
            maprange = lambda e: int(127.5 * (e+1) - 128) # maps -1.0:1.0 to -128:127
            vni = tuple([maprange(vi) for vi in vn] + [0,1]) # extra '1' element to indicate normal
            colornorm = vni
        else:
            c = loop[0][color_layer]
            ct = tuple([round(ci*255) for ci in c] + [0]) # '0' to indicate color
            colornorm = ct

        data = (v.co, colornorm, uv)
        vtxdata.append(data)

    return vtxdata

class TriBatch:
    def __init__(self):
        self.tris = []
        self.vtxmap = {}
        self.ntris = 0
        self.nverts = 0
        self.mat = -1
        self.colors = []
        self.col_indices = []

    def add_tri(self, verts):
        self.tris.append(tuple([vi for vi in verts]))
        self.ntris += 1

        for v in verts:
            if v in self.vtxmap: continue
            self.vtxmap[v] = self.nverts
            self.nverts += 1

    def has_vert(self, v):
        return v in self.vtxmap

    def setup_colors(self, vtxdata):
        verts = self.vtxmap.keys()
        overflow = color_indices(vtxdata, verts, self.colors, self.col_indices)
        if overflow:
            msg = 'Color index exceeds 256'
            print(msg)
            raise Exception(msg)

def color_indices(vtxdata, verts, colors, col_indices):
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
            return True

        col_indices.append(col_idx)

    return False

def export_tris(mesh, bm):
    prevmat = -1
    tri_batches = [TriBatch()]

    MAX_VERTS = 64
    f = 0
    for tri in bm.faces:
        cur_batch = tri_batches[-1]

        mat = tri.material_index
        if cur_batch.mat < 0: cur_batch.mat = mat
        mat_changed = mat != prevmat and prevmat >= 0

        verts = [v.index for v in tri.verts]
        nverts = cur_batch.nverts
        nverts += sum([1 if not cur_batch.has_vert(v) else 0 for v in verts])

        # creates a new batch
        txtnewbatch = ''
        if nverts > MAX_VERTS or mat_changed:
            txtnewbatch = ' NEWBATCH'
            cur_batch = TriBatch()
            tri_batches.append(cur_batch)
            cur_batch.mat = mat

        # print(f'f {f:<3} nv {nverts}{txtnewbatch} {mesh.materials[mat].name} MAX {MAX_VERTS} newmat {mat_changed}')
        logger.debug(f'f {f:<3} nv {nverts}{txtnewbatch} {mesh.materials[mat].name} MAX {MAX_VERTS} newmat {mat_changed}')
        f += 1

        cur_batch.add_tri(verts)

        if mat_changed or prevmat < 0:
            m = mesh.materials[mat]
            MAX_VERTS = 64 if material_has_lighting(m) else 128

        prevmat = mat

    return tri_batches

def export_mesh(mesh_obj):
    logger.debug(f'MESH {mesh_obj.pdmodel_props.name} M{mesh_obj.pdmodel_props.mtx:02X}')
    bpy.context.view_layer.objects.active = mesh_obj
    mesh = mesh_obj.data

    bm = bmesh.new()
    bm.from_mesh(mesh)

    bm.faces.ensure_lookup_table()
    bm.verts.ensure_lookup_table()

    uv_layer = bm.loops.layers.uv.active
    color_layer = bm.loops.layers.color["vtxcolor"]

    mtxidx = mesh_obj.pdmodel_props.mtx
    binvtx = bytearray()

    vtxdata = vtx_data(mesh, bm)
    batches = export_tris(mesh, bm)
    for batch in batches: batch.setup_colors(vtxdata)
    print_batches(mesh, batches)

    bm.free()

def build_meshmap(obj):
    meshmap = {} # idx -> list of meshes
    for c in obj.children:
        if c.type != 'MESH': continue
        idx = c.pdmodel_props.idx
        if idx not in meshmap: meshmap[idx] = []
        meshmap[idx].append(c)

    return meshmap

def export_model(name):
    obj = bpy.data.objects[name]
    objmap = build_meshmap(obj)
    logger.debug(f'exportModel: {name}')
    for idx, meshes in objmap.items():
        for mesh in meshes:
            name = mesh.pdmodel_props.name
            mtx = mesh.pdmodel_props.mtx
            ln = '-'*32
            logger.debug(f'{ln} {name}-M{mtx:2X} {ln}')
            export_mesh(mesh)

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
                     f'nv {batch.nverts} nt {batch.ntris} '
                     f'ncols {len(batch.colors)} {newmat}{txtnorm}')

        for tri in batch.tris:
            tglob = [v for v in tri]
            trel = [batch.vtxmap[v] for v in tri]

            # s=''.join([f'{v}-' for v in trel])
            # print(s.rstrip('-'))
            cidxs = [batch.col_indices[v] for v in trel]
            colors = [batch.colors[ci//4] for ci in cidxs]

            txtcol = ''

            for col in colors:
                if col[4]: # normal
                    # s = ''.join([f'{col[i].hex().upper()} ' for i in range(0, 3)])
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
