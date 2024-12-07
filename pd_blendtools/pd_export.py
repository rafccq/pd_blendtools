import bmesh

import pd_utils as pdu
from pdmodel import PDModel
import mtxpalette as mtxp
from pd_materials import *
import log_util as log
from gbi import *


logger = log.log_get(__name__)
log.log_config(logger, log.LOG_FILE_EXPORT)


# col is a tuple (r,g,b,a) with each element in the range [0:1]
def color_to_bytes(col):
    return [ci.to_bytes(1, 'big') for ci in col]

def normal_to_bytes(norm):
    return [ni.to_bytes(1, 'big', signed=True) for ni in norm]

def coord_to_bytes(coord):
    return [round(ci).to_bytes(2, 'big', signed=True) for ci in coord]

def uv_to_bytes(uv, texsize):
    return [round(32*uvi*ti).to_bytes(2,'big',signed=True) for (uvi, ti) in zip(uv, texsize)]

# returns an array of (v.position, v.color/normal, v.uv_coords, v.mtx)
# normals are mapped from -1.0:1.0 to -128:127 (s8)
# colors are mapped from 0.0:1.0 to 0:255 (u8)
def vtx_data(mesh, bm):
    layers = bm.loops.layers

    uv_layer = layers.uv.active
    layer_col = layers.color["vtxcolor"]
    has_mtx = 'matrices' in layers.color
    layer_mtx = layers.color["matrices"] if has_mtx else None

    if has_mtx:
        unassigned = pdu.get_vtx_unassigned_mtxs(bm)
        if len(unassigned) > 0:
            title = 'Not all vertices are assigned a matrix'
            pdu.msg_box(title, "Use 'Matrices > Select Unassigned' to check")
            raise RuntimeError(title)

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
        colornorms = {} # face index -> color or normal coords

        mat_idx = loops[0].face.material_index
        mat = mesh.materials[mat_idx]

        has_lighting = material_has_lighting(mat)

        maprange = lambda e: int(127.5 * (e + 1) - 128)  # maps -1.0:1.0 to -128:127
        for loop in loops:
            if has_lighting:
                normal = mesh.loops[loop.index].normal.to_tuple()
                normal = tuple([round(maprange(vi), 3) for vi in normal] + [0,1]) # extra '1' element to indicate normal
                colornorms[loop.face.index] = normal
            else:
                c = loops[0][layer_col] # for now, we always use the color from the first loop
                ct = tuple([round(ci*255) for ci in c] + [0]) # '0' to indicate color
                colornorms[loop.face.index] = ct

        mtx = None
        if has_mtx:
            mtxcol = loops[0][layer_mtx]
            mtx = mtxp.color2mtx(mtxcol)

        co = v.co
        data = ((co.x, co.y, co.z), colornorms, uvs, mtx)
        vtxdata.append(data)

    return vtxdata

class TriBatch:
    def __init__(self):
        self.tris = [] # list of 3-tuples (relative vtx indices)
        self.vtxmap = {} # (v_global, uv) -> v_relative
        self.ntris = 0
        self.mat = -1
        self.colors = []
        self.vtxmtxs = {} # vtx (relative) -> mtx
        self.mtxs = []
        self.color_indices = []
        self.vtxdata = [] # (position, color/normal, uv coords)
        self.vtxbin_sizes = {}

        self.vtx_offset = 0
        self.vtx_start = 0
        self.color_offset = 0
        self.color_start = 0

    def add_tri(self, face, verts, vtxdata):
        tri = []
        for v in verts:
            uv = vtxdata[v][2][face]
            colornorm = vtxdata[v][1][face]
            vtx_key = (v, uv, colornorm)

            if vtx_key in self.vtxmap:
                tri.append(self.vtxmap[vtx_key])
                continue

            vidx = len(self.vtxmap)
            vdata = vtxdata[v]
            mtx = vdata[3]

            self.vtxmap[vtx_key] = vidx
            tri.append(vidx)

            if mtx is not None:
                if vidx not in self.vtxmtxs:
                    self.vtxmtxs[vidx] = mtx

                if mtx not in self.mtxs:
                    self.mtxs.append(mtx)

            self.vtxdata.append((vdata[0], colornorm, uv))

        self.tris.append(tuple([vi for vi in tri]))
        self.ntris += 1

    def has_vert(self, vtxuv):
        return vtxuv in self.vtxmap

    def nverts(self):
        return len(self.vtxmap)

    def build_color_indices(self):
        verts = self.vtxmap.values()
        self.colors, self.color_indices = color_indices(self.vtxdata, verts)

    def reorder_verts_by_mtx(self):
        if not self.vtxmtxs: return

        # put each vtx in a bin according to its matrix
        vtxbins = {} # mtx -> [v0, v1...]
        for v in self.vtxmap.values():
            mtx = self.vtxmtxs[v]
            if mtx not in vtxbins: vtxbins[mtx] = []
            vtxbins[mtx].append(v)

        # create a mapping from the old idx to the new, after flattening all the bins
        # and the offsets for each bin
        vtxmapping = {} # old vtxidx -> new
        idx, ofs = 0, 0
        for mtx, vbin in vtxbins.items():
            self.vtxbin_sizes[mtx] = len(vbin)
            ofs += len(vbin)
            for v in vbin:
                vtxmapping[v] = idx
                idx += 1

        # update the vtx indices in each triangle
        for idx, tri in enumerate(self.tris):
            newtri = [0]*3
            for vidx, v in enumerate(tri):
                newtri[vidx] = vtxmapping[v]
            self.tris[idx] = tuple(newtri)

        # update the matrices and vtxdata maps
        mtxs = {}
        vtxdata = [None] * len(self.vtxdata)
        colorindices = [None] * len(self.vtxdata)
        for v_old, v_new in vtxmapping.items():
            mtxs[v_new] = self.vtxmtxs[v_old]
            vtxdata[v_new] = self.vtxdata[v_old]
            colorindices[v_new] = self.color_indices[v_old]

        self.vtxmtxs = mtxs
        self.vtxdata = vtxdata
        self.color_indices = colorindices

    def vtx_bytes(self, model, texsize):
        if not self.colors: self.build_color_indices()
        vtxdata = bytearray()
        for v, vdata in enumerate(self.vtxdata):
            mtx = model.matrices[self.vtxmtxs[v]] if self.vtxmtxs else (0,0,0)
            vpos = vdata[0]
            vpos = (vpos[0] - mtx[0], vpos[1] - mtx[1], vpos[2] - mtx[2])
            uvcoord = vdata[2]

            # pos flag col_idx s t
            vtxbytes = []
            vtxbytes += coord_to_bytes(vpos)
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
            raise RuntimeError(msg)

        col_indices.append(col_idx)

    return colors, col_indices

def create_tri_batches(mesh, bm, vtxdata):
    prevmat = -1
    tri_batches = [TriBatch()]

    MAX_VERTS = 16
    for face, tri in enumerate(bm.faces):
        cur_batch = tri_batches[-1]

        mat = tri.material_index
        if cur_batch.mat < 0: cur_batch.mat = mat
        mat_changed = mat != prevmat and prevmat >= 0

        verts = [v.index for v in tri.verts]
        nverts = cur_batch.nverts()
        colnorms = tuple([vtxdata[v][1][face] for v in verts])
        uvs = tuple([vtxdata[v][2][face] for v in verts])
        nverts += sum([1 if not cur_batch.has_vert((v, uv, cn)) else 0 for v, uv, cn in zip(verts, uvs, colnorms)])

        # creates a new batch
        txtnewbatch = ''
        if nverts > MAX_VERTS or mat_changed:
            txtnewbatch = 'NEWBATCH'
            cur_batch = TriBatch()
            tri_batches.append(cur_batch)
            cur_batch.mat = mat

        logger.debug(f'f {face:<3} nv {nverts} {txtnewbatch} {mesh.materials[mat].name} MAX {MAX_VERTS} newmat {mat_changed}')

        cur_batch.add_tri(face, verts, vtxdata)

        prevmat = mat

    return tri_batches

class ExportMeshData:
    def __init__(self, name, idx, layer, meshdata):
        self.name = name
        self.idx = idx
        self.layer = layer
        self.meshdata = meshdata
        self.batches = []

    def create_batches(self, model):
        logger.debug(f'MESH {self.name}')
        mesh = self.meshdata

        bm = bmesh.new()
        bm.from_mesh(mesh)

        bm.faces.ensure_lookup_table()
        bm.verts.ensure_lookup_table()

        vtxdata = vtx_data(mesh, bm)
        batches = create_tri_batches(mesh, bm, vtxdata)

        for idx, batch in enumerate(batches):
            logger.debug(f'batch {idx} building color indices')
            batch.build_color_indices()
            batch.reorder_verts_by_mtx()

        print_batches(mesh, batches, model)
        bm.free()

        self.batches = batches


def build_meshmap(obj):
    meshmap = {} # idx -> list of meshes
    for obj in obj.children:
        if obj.type != 'MESH': continue

        idx = obj.pdmodel_props.idx
        layer = obj.pdmodel_props.layer

        if idx not in meshmap: meshmap[idx] = []

        meshinfo = ExportMeshData(obj.name, idx, layer, obj.data)
        meshmap[idx].append(meshinfo)

    return meshmap

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

    geobits = 0
    for idx, batch in enumerate(mesh.batches):
        mat = materials[batch.mat]
        mat_cmds, geobits = material_cmds(mat, geobits)

        geobits |= geobits
        for cmd in mat_cmds:
            gdlbytes += bytearray.fromhex(cmd)

        gdlbytes += cmd_G_COL(len(batch.colors), batch.color_start + batch.color_offset)

        vtx_ofs = batch.vtx_start + batch.vtx_offset
        vidx = 0

        nverts = batch.nverts()
        for mtx in batch.mtxs:
            nverts = batch.vtxbin_sizes[mtx]

            gdlbytes += cmd_G_MTX(mtx)
            gdlbytes += cmd_G_VTX(nverts, vtx_ofs, vidx)

            vtx_ofs += nverts * 12
            vidx += nverts

        # handle meshes with no matrix
        if not batch.mtxs:
            gdlbytes += cmd_G_VTX(nverts, vtx_ofs, vidx)
            vtx_ofs += nverts * 12

        # flush triangles
        trigroup = []
        for tri in batch.tris:
            trigroup.append(tri)
            if len(trigroup) == 4:
                gdlbytes += cmd_G_TRI4(trigroup)
                trigroup.clear()

        # flush remaining tris
        if len(trigroup) > 0:
            gdlbytes += cmd_G_TRI4(trigroup)

    if geobits != 0:
        gdlbytes += cmd_G_CLEARGEOMETRY(geobits)

    return gdlbytes

def loadmodel(romdata, modelname):
    modeldata = romdata.modeldata(modelname)
    return PDModel(modeldata)

def export_model(model_obj, filename):
    log.log_clear(log.LOG_FILE_EXPORT)

    objmap = build_meshmap(model_obj)
    modelname = model_obj.pdmodel_props.name
    logger.debug(f'export model: {modelname}')

    romdata = pdu.loadrom()
    model = loadmodel(romdata, modelname)

    # objmap: idx -> list of meshes
    for idx, meshes in objmap.items():
        vtxdata = bytearray()
        colordata = bytearray()

        # create batches for each mesh and sort them by material
        for mesh in meshes: mesh.create_batches(model)
        for mesh in meshes: mesh.batches.sort(key = lambda b: b.mat)

        # aggregate vtxdata from all batches
        for mesh in meshes:
            meshname = mesh.name
            ln = '-'*32
            logger.debug(f'{ln} {meshname} {ln}')

            materials = mesh.meshdata.materials

            for batch in mesh.batches:
                batch.vtx_offset = len(vtxdata)
                batch.color_offset = len(colordata)

                mat = materials[batch.mat]
                image = material_get_teximage(mat)

                texsize = (1,1)
                if image: texsize = image.size
                else:
                    print(f'WARNING: material has no texture. Mesh{mesh.name} mat {mat.name}')

                vtxdata += batch.vtx_bytes(model, texsize)
                colordata += batch.color_bytes()

        model.replace_vtxdata(idx, vtxdata)
        model.replace_colordata(idx, colordata)

    # write all model data except GDLs
    modeldata = model.write()

    # create GDLs from the meshes and replace them in the model
    for idx, meshes in objmap.items():
        rodata = model.rodatas[idx]
        nodetype = rodata['_node_type_']

        # split the list into 2 for opa and xlu layers
        idx_xlu = pdu.index_where(meshes, lambda e: e.layer == 1, len(meshes)) # TODO Meshlayer enum
        meshes_opa = meshes[:idx_xlu]
        meshes_xlu = meshes[idx_xlu:]

        vtx_start = rodata['vertices']

        nverts = rodata['numvertices'] if nodetype in [0x04, 0x18] else rodata['unk00'] * 4
        gdlbytes_opa = meshes_to_gdl(meshes_opa, vtx_start, nverts)
        gdlbytes_xlu = meshes_to_gdl(meshes_xlu, vtx_start, nverts)

        opa = 'opagdl' if nodetype in [0x04, 0x18] else 'gdl'
        xlu = 'xlugdl'
        model.replace_gdl(modeldata, gdlbytes_opa, idx, opa)
        model.replace_gdl(modeldata, gdlbytes_xlu, idx, xlu)

    modeldata = pdu.compress(modeldata)
    pdu.write_file(filename, modeldata)

def print_batches(mesh, tri_batches, model):
    f = 0
    prevmat = -1
    # print(f'mesh {mesh.idx:02X} batches')
    for bidx, batch in enumerate(tri_batches):
        mat = batch.mat

        m = mesh.materials[mat]
        matname = m.name
        newmat = ' NEWMAT' if mat != prevmat else ''
        txtnorm = ' NORM' if material_has_lighting(m) else ''
        logger.debug(f'batch_{bidx} mat {mat} {matname} '
                     f'nv {batch.nverts()} nt {batch.ntris} '
                     f'ncols {len(batch.colors)} {newmat}{txtnorm}')

        for v, vdata in enumerate(batch.vtxdata):
            mtx = model.matrices[batch.vtxmtxs[v]] if batch.vtxmtxs else (0,0,0)
            p = vdata[0]
            x, y, z = p[0] - mtx[0], p[1] - mtx[1], p[2] - mtx[2]
            txtmtx = f'(MTX {batch.vtxmtxs[v]:02X})' if batch.vtxmtxs else ''
            logger.debug(f'v {v:<3} {x:>8.3f} {y:>8.3f} {z:>8.3f} {txtmtx}')

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
            # txtcol += f' | [{cidxs[0]:<4} {cidxs[1]:<4} {cidxs[2]:<4}] '

            txtmtx = ''
            if batch.vtxmtxs:
                for v in tri: txtmtx += f'{batch.vtxmtxs[v]:02X} '
                txtmtx = f'({txtmtx.rstrip()})'

            logger.debug(f'  {f:<3} ({trel[0]:<3} {trel[1]:<3} {trel[2]:<3}) '
                         f'({tglob[0]:<3} {tglob[1]:<3} {tglob[2]:<3}){txtcol} MTX {txtmtx}')
            f += 1
