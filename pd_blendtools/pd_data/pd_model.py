import struct
from collections import namedtuple

from data.bytereader import ByteReader
from .decl_model import *
from utils import pd_utils as pdu
from data.typeinfo import TypeInfo

NODETYPE_CHRINFO      = 0x01
NODETYPE_POSITION     = 0x02
NODETYPE_GUNDL        = 0x04
NODETYPE_DISTANCE     = 0x08
NODETYPE_BBOX         = 0x0a
NODETYPE_CHRGUNFIRE   = 0x0c
NODETYPE_POSITIONHELD = 0x15
NODETYPE_STARGUNFIRE  = 0x16
NODETYPE_HEADSPOT     = 0x17
NODETYPE_DL           = 0x18

def unmask(addr):
    return addr & 0x00ffffff if addr & 0x5000000 else addr

Bbox = namedtuple('Bbox', 'xmin xmax ymin ymax zmin zmax')

class PD_ModelFile:
    def __init__(self, modeldata, skipDLdata=False):
        self.modeldata = modeldata
        self.skipDLdata = skipDLdata
        self.rd = ByteReader(modeldata)

        self.modeldef = None
        self.modelparts = None
        self.nodes = {}
        self.rodatas = []
        self.texconfigs = []
        self.texdata = {}

        self.vertices = {}
        self.colors = {}

        self._has_embedded_tex = False

        self._read()

    def _read(self):
        rd = self.rd
        self.modeldef = rd.read_block('modeldef')

        root = self.modeldef['rootnode']
        self.rootnode = self.read_node(unmask(root))
        self.read_modelparts()
        self.read_rodata()
        self.read_tex_configs()

        # we only store the translation part of the matrix here
        self.matrices = {}
        self.build_matrices()

    def get_parent_mtx(self, parentaddr):
        if not parentaddr: return None

        addr = parentaddr

        while addr in self.nodes:
            node = self.nodes[addr]
            nodetype = node['type'] & 0xff
            rodata = self.find_rodata(node['rodata'])

            if nodetype == NODETYPE_POSITION:
                mtxindex = rodata['mtxindexes'][0]
                return self.matrices[mtxindex]
            elif nodetype in [NODETYPE_POSITION, NODETYPE_POSITIONHELD]:
                mtxindex = rodata['mtxindex']
                return self.matrices[mtxindex]

            addr = unmask(node['parent'])

        return None

    def build_matrices(self):
        def setup_mtx(model, node, idx, depth, **kwargs):
            nodetype = node['type'] & 0xff
            if nodetype not in [NODETYPE_CHRINFO, NODETYPE_POSITION, NODETYPE_POSITIONHELD]: return

            rodata = model.find_rodata(node['rodata'])

            x = y = z = 0
            if nodetype in [NODETYPE_POSITION, NODETYPE_POSITIONHELD]:
                pos = rodata['pos']
                # note: this is for external use so we use little-endian
                x = struct.unpack('f', pos['x'].to_bytes(4, 'little'))[0]
                y = struct.unpack('f', pos['y'].to_bytes(4, 'little'))[0]
                z = struct.unpack('f', pos['z'].to_bytes(4, 'little'))[0]

            parentaddr = unmask(node['parent'])
            parentmtx = model.get_parent_mtx(parentaddr)
            if parentmtx:
                x += parentmtx[0]
                y += parentmtx[1]
                z += parentmtx[2]

            if nodetype == NODETYPE_POSITION:
                # pos nodes have 3 mtx indices
                for i in range(3):
                    mtxindex = rodata['mtxindexes'][i]
                    if mtxindex != 0xffff:
                        model.matrices[mtxindex] = (x, y, z)
            else:
                mtxindex = rodata['mtxindex']
                model.matrices[mtxindex] = (x, y, z)

        self.traverse(setup_mtx)

    def traverse(self, callback, **kwargs):
        node = self.rootnode
        depth = 0
        idx = 0
        while node:
            callback(self, node, idx, depth, **kwargs)

            idx += 1

            child = unmask(node['child'])
            if child:
                node = self.nodes[child]
                depth += 1
            else:
                while node:
                    nextaddr = unmask(node['next'])
                    if nextaddr:
                        node = self.nodes[nextaddr]
                        break

                    parent = unmask(node['parent'])
                    node = self.nodes[parent] if parent else None
                    if node: depth -= 1

    def write(self):
        rd = self.rd
        dataout = bytearray()

        rd.write_block(dataout, self.modeldef)
        rd.write_block(dataout, self.modelparts)

        for texconf in self.texconfigs:
            rd.write_block(dataout, texconf, pad=4)

        for node in self.nodes.values():
            rd.write_block(dataout, node, pad=4)

        for texdata in self.texdata.values():
            rd.write_block_raw(dataout, texdata)

        idx = 0
        for rodata in self.rodatas:
            nodetype = rodata['_node_type_']

            if nodetype in [NODETYPE_GUNDL, NODETYPE_STARGUNFIRE, NODETYPE_DL]:
                rodata['vertices'] = len(dataout) | 0x05000000
                vertices = self.vertices[idx]
                colors = self.colors[idx]

                rd.write_block_raw(dataout, vertices, pad=8)
                rd.write_block_raw(dataout, colors, pad=8)

            rd.ref = len(dataout)
            rd.write_block(dataout, rodata, pad=8)
            idx += 1

        texaddrs = {blk.addr: blk.write_addr for blk in self.texdata.values()}

        # manually patch the texconfig pointers
        m = 0x05000000
        for texconfig in self.texconfigs:
            addr = texconfig.write_addr
            texnum = texconfig['texturenum']
            if not texnum & m: continue

            texnum_new = texaddrs[texnum & ~m] + (texnum & m)
            dataout[addr:addr+4] = texnum_new.to_bytes(4, DEST_BO)
            # log(texconfig, f'addr: tex {texnum:08X} texnew {texnum_new:08X}')

        nodes = list(self.nodes.values())
        for node, rodata in zip(nodes, self.rodatas):
            node.update(dataout, 'rodata', rodata.write_addr | 0x05000000)

        return dataout

    def replace_gdl(self, dataout, gdlbytes, idx, field):
        if not gdlbytes: return

        rodata = self.rodatas[idx]
        nodetype = rodata['_node_type_']
        if nodetype not in [NODETYPE_GUNDL, NODETYPE_STARGUNFIRE, NODETYPE_DL]:
            raise Exception(f'Invalid rodata type to replace GDL: {nodetype}')

        rd = self.rd
        gdlblock = rd.create_block(gdlbytes)
        rd.write_block_raw(dataout, gdlblock)
        rodata.update(dataout, field, gdlblock.write_addr | 0x05000000)

    def read_node(self, rootaddr):
        # log(f'read_node: {rootaddr:08X}')
        rd = self.rd
        rd.set_cursor(rootaddr)
        node = rd.read_block('modelnode')
        self.nodes[rootaddr] = node

        # read 'child' nodes
        child = unmask(node['child'])
        if child != 0 and child not in self.nodes:
            self.read_node(child)

        # read 'next' nodes
        next = unmask(node['next'])
        while next != 0 and next not in self.nodes:
            nextnode = self.read_node(next)
            next = unmask(nextnode['next'])

        return node

    def read_modelparts(self):
        rd = self.rd
        n = self.modeldef['numparts']
        TypeInfo.register('parts', decl_parts, varmap={'N': n})
        addr = unmask(self.modeldef['parts'])
        rd.set_cursor(addr)
        self.modelparts = rd.read_block('parts')

    def read_rodata(self):
        rd = self.rd
        idx = 0
        for k, node in self.nodes.items():
            rodata_addr = node['rodata']
            nodetype = node['type'] & 0xff
            rodata_name = rodata_decls[nodetype]

            rd.set_cursor(unmask(rodata_addr))
            rodata = rd.read_block(rodata_name)
            rodata['_node_type_'] = nodetype
            self.rodatas.append(rodata)
            rodatagdl_map = {
                NODETYPE_GUNDL: ['opagdl', 'xlugdl'],
                NODETYPE_STARGUNFIRE: ['gdl'],
                NODETYPE_DL: ['opagdl', 'xlugdl']
            }
            if nodetype in rodatagdl_map:
                self.read_vertices(rodata, nodetype, idx)

            idx += 1

    def read_vertices(self, rodata, nodetype, idx):
        rd = self.rd

        numvertices = rodata['numvertices'] if nodetype in [NODETYPE_GUNDL, NODETYPE_DL] else rodata['unk00'] * 4

        if numvertices:
            vtxsize = 12
            start = rodata['vertices']
            end = pdu.ALIGN8(unmask(start) + numvertices * vtxsize)
            self.vertices[idx] = rd.read_block_raw(unmask(start), end)
            col_start = pdu.ALIGN8(unmask(end))
            col_end = rodata.addr

            # save colors at the same address as the vertices
            colors = self.colors[idx] = rd.read_block_raw(col_start, col_end)
            rodata['colors'] = colors#
        else:
            self.vertices[idx] = rd.create_block(bytearray())
            self.colors[idx] = rodata['colors'] = rd.create_block(bytearray())

    def read_tex_configs(self):
        rd = self.rd
        addr = unmask(self.modeldef['texconfigs'])
        rd.set_cursor(addr)

        embeddedtex = False
        for i in range(0, self.modeldef['numtexconfigs']):
            texconfig = rd.read_block('texconfig')
            self.texconfigs.append(texconfig)

            texnum = texconfig['texturenum']
            if texnum & 0x05000000: embeddedtex = True

        if embeddedtex:
            self.read_texdata()

    def has_embedded_tex(self):
        return self._has_embedded_tex

    def read_texdata(self):
        self._has_embedded_tex = True
        rd = self.rd
        n = len(self.texconfigs)
        texaddrs = [texconf['texturenum'] for texconf in self.texconfigs]
        texaddrs.append(None)

        for i in range(0, n):
            addr = texaddrs[i]
            next = texaddrs[i+1]

            end = unmask(next) if next else next
            texdata = rd.read_block_raw(unmask(addr), end)
            self.texdata[addr] = texdata

    def data(self, ptr):
        return self.modeldata[ptr & 0xffffff:]

    def find_rodata(self, addr):
        addr = unmask(addr)
        for ro in self.rodatas:
            if ro.addr == addr: return ro

        return None

    def replace_vtxdata(self, idx, vtxdata):
        rodata = self.rodatas[idx]
        nodetype = rodata['_node_type_']

        if nodetype not in [NODETYPE_GUNDL, NODETYPE_STARGUNFIRE, NODETYPE_DL]:
            raise Exception(f'invalid node type: {nodetype} idx {idx}')

        vtxblock = self.vertices[idx]
        vtxblock.bytes = vtxdata

        numvtx = len(vtxdata) // 12

        # update rodata numvertices
        if nodetype in [NODETYPE_GUNDL, NODETYPE_DL]:
            rodata['numvertices'] = numvtx
        else:
            rodata['unk00'] = numvtx >> 2

    def replace_colordata(self, idx, colordata):
        rodata = self.rodatas[idx]
        nodetype = rodata['_node_type_']

        if nodetype not in [NODETYPE_GUNDL, NODETYPE_STARGUNFIRE, NODETYPE_DL]:
            raise RuntimeError(f'invalid node type: {nodetype}')

        colorblock = self.colors[idx]
        colorblock.bytes = colordata

    def find_bbox(self):
        for ro in self.rodatas:
            nodetype = ro['_node_type_']
            if nodetype == NODETYPE_BBOX:
                coords = [pdu.f32(ro[e]) for e in ['xmin', 'xmax', 'ymin', 'ymax', 'zmin', 'zmax']]
                bbox = Bbox(*coords)
                return bbox

        return None


def read(path, filename, skipDLdata=False):
    modeldata = pdu.read_file(f'{path}/{filename}')
    modeldata = pdu.decompress(modeldata)
    return PD_ModelFile(modeldata, skipDLdata)
