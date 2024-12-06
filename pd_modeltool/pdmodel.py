import struct

from bytereader import *
from decl_model import *

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

def log(*args):
    if enableLog:
        print(''.join(args))

class PDModel:
    def __init__(self, modeldata, skipDLdata=False):
        self.modeldata = modeldata
        self.skipDLdata = skipDLdata
        self.rd = ByteReader(modeldata, mask=0x00ffffff)

        self.modeldef = None
        self.modelparts = None
        self.nodes = {}
        self.rodatas = []
        self.texconfigs = []
        self.texdatas = []

        self.vertices = {}
        self.colors = {}

        self._read()

    def _read(self):
        rd = self.rd
        self.modeldef = rd.read_block('modeldef')
        log(f'modeldef:')
        # rd.print_dict(self.modeldef, 'modeldef', pad=16, numspaces=4)

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
        node = self.nodes[addr]

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

            pos = rodata['pos']
            # note: this is for external use so we use little-ending
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

            # sp = ' ' * depth * 2
            # print(f'{sp} NODE {idx:02X} t {nodetype:02X} mtx {mtxindex:02X} ({x:.3f}, {y:.3f}, {z:.3f})')
        #-------------------------------------
        self.traverse(setup_mtx)

    def traverse(self, callback, **kwargs):
        node = self.rootnode
        depth = 0
        idx = 0
        # parentnode = None
        while node:
            callback(self, node, idx, depth, **kwargs)

            # sp = ' ' * depth * 2
            # print(f'{sp} NODE {idx:02X} t {nodetype:02X}')
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

        rd.write_block(dataout, 'modeldef', self.modeldef)
        rd.write_block(dataout, 'parts', self.modelparts, pad=8)

        for texconf in self.texconfigs:
            rd.write_block(dataout, 'texconfig', texconf, pad=4)

        for node in self.nodes.values():
            rd.write_block(dataout, 'modelnode', node, pad=4)

        for texdata in self.texdatas:
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
            rd.write_block(dataout, rodata_decls[nodetype], rodata, pad=8)
            idx += 1

        texaddrs = { blk.addr: blk.write_addr for blk in self.texdatas }

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
        rd.print_dict(node, decl_modelnode, pad=16, numspaces=4)

        log('-'*32)

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
        TypeInfo.register('parts', decl_parts, _vars={'N': n})
        addr = unmask(self.modeldef['parts'])
        rd.set_cursor(addr)
        self.modelparts = rd.read_block('parts')

    def read_rodata(self):
        rd = self.rd
        idx = 0
        for k, node in self.nodes.items():
            node_addr = node.addr
            rodata_addr = node['rodata']
            nodetype = node['nodetype'] & 0xff
            rodata_name = rodata_decls[nodetype]
            log(f'{node_addr:04X} t {nodetype:02X} {rodata_name} {rodata_addr:08X}')

            rd.set_cursor(unmask(rodata_addr))
            rodata = rd.read_block(rodata_name)
            rodata['_node_type_'] = nodetype
            self.rodatas.append(rodata)
            # rd.print_dict(rodata, TypeInfo.get_decl(rodata_name), pad=16, numspaces=4, showdec=True)
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
        log(f'VERTICES [{rd.cursor:04X}]')

        numvertices = rodata['numvertices'] if nodetype in [NODETYPE_GUNDL, NODETYPE_DL] else rodata['unk00'] * 4

        if numvertices:
            vtxsize = 12
            start = rodata['vertices']
            end = ALIGN8(unmask(start) + numvertices * vtxsize)
            endnoalign = (unmask(start) + numvertices * vtxsize)
            self.vertices[idx] = rd.read_block_raw(unmask(start), end)
            v = self.vertices[idx].bytes
            log(f'.VTX   start {unmask(start):04X} end {end:04X} endnoalign {endnoalign:04X} len {len(v)} num {numvertices}')
            if enableLog: print_bin('^VTX', v, 0, 12*12, 2, 6)

            col_start = ALIGN8(unmask(end))
            col_end = rodata.addr

            # save colors at the same address as the vertices
            colors = self.colors[idx] = rd.read_block_raw(col_start, col_end)
            rodata['colors'] = colors
            c = colors.bytes
            log(f'.COLORS start {col_start:04X} len {len(c):04X} ({len(c)})')
            if enableLog: print_bin('^COLORS', c, 0, 12*12, 4, 3)

            # there are no direct pointers to the colors block (its implicit since it follows vtxs)
            # so we need to add it manually here, to things can be patched later, pain in the ass
            rd.pointers_map[col_start] = 0

    def read_tex_configs(self):
        rd = self.rd
        addr = unmask(self.modeldef['texconfigs'])
        rd.set_cursor(addr)

        embeddedtex = False
        for i in range(0, self.modeldef['numtexconfigs']):
            texconfig = rd.read_block('texconfig')
            self.texconfigs.append(texconfig)

            texnum = texconfig['texturenum']
            tc_addr = texconfig.addr
            if texnum & 0x05000000: embeddedtex = True
            log(f'{tc_addr:04X} texconfig {i}')
            rd.print_dict(texconfig, TypeInfo.get_decl('texconfig'), pad=16, numspaces=4, showdec=True)

        if embeddedtex:
            self.read_texdata()

    def read_texdata(self):
        rd = self.rd
        n = len(self.texconfigs)
        texaddrs = [texconf['texturenum'] for texconf in self.texconfigs]
        texaddrs.append(self.rodatas[0].addr)

        for i in range(0, n):
            addr = texaddrs[i]
            next = texaddrs[i+1]

            texdata = rd.read_block_raw(unmask(addr), unmask(next))
            self.texdatas.append(texdata)
            log(f'^TEX {addr:08X}:{next:08X}')
            print_bin(f'texdata_{i}', self.texdatas[0]['bytes'], 0, 16*10, 4, 4)

    def data(self, ptr):
        return self.modeldata[ptr & 0xffffff:]
        # print_bin('texdata_0', self.texdatas[0]['bytes'], 0, -1, group_size=4)

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

def read(path, filename, skipDLdata=False):
    modeldata = read_file(f'{path}/{filename}')
    modeldata = decompress(modeldata)
    return PDModel(modeldata, skipDLdata)
