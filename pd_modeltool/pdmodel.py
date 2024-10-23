from bytereader import *
from decl_model import *


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

        for name, decl in model_decls.items():
            self.rd.declare(name, decl)

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
        rd.print_dict(self.modeldef, 'modeldef', pad=16, numspaces=4)

        root = self.modeldef['rootnode']
        self.rootnode = self.read_node(unmask(root))
        self.read_modelparts()
        self.read_rodata()
        self.read_tex_configs()

        # we only represent the translation part of the matrix here
        self.matrices = [(0,0,0)] * self.modeldef['nummatrices']
        self.build_matrices()

    def build_matrices(self):
        def setup_mtx(model, node, idx, depth, **kwargs):
            nodetype = node['type']
            if nodetype not in [0x2, 0x15]: return

            # rodata = node['rodata']
            rodata = model.find_rodata(node['rodata'])

            pos = rodata['pos']['f']
            x = struct.unpack('f', pos[0].to_bytes(4, 'little'))[0]
            y = struct.unpack('f', pos[1].to_bytes(4, 'little'))[0]
            z = struct.unpack('f', pos[2].to_bytes(4, 'little'))[0]

            parentaddr = unmask(node['parent'])
            parentnode = model.nodes[parentaddr] if parentaddr else None
            # if parentnode and nodetype == 0x2: # and parentnode['type'] == 0x2:
            if parentnode and parentnode['type'] in [0x2, 0x15]:
                parentrodata = model.find_rodata(parentnode['rodata'])
                mtxindex = parentrodata['mtxindexes'][0] if parentnode['type'] == 0x2 else parentrodata['mtxindex']
                parentmtx = model.matrices[mtxindex]
                x += parentmtx[0]
                y += parentmtx[1]
                z += parentmtx[2]

            mtxindex = rodata['mtxindexes'][0] if nodetype == 0x2 else rodata['mtxindex']
            model.matrices[mtxindex] = (x, y, z)

            sp = ' ' * depth * 2
            print(f'{sp} NODE {idx:02X} t {nodetype:02X} mtx {mtxindex:02X} ({x:.3f}, {y:.3f}, {z:.3f})')
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

    def patch(self):
        rd = self.rd
        dataout = bytearray()

        rd.write_block(dataout, 'modeldef', self.modeldef)
        rd.write_block(dataout, 'parts', self.modelparts, pad=4)

        for texconf in self.texconfigs:
            rd.write_block(dataout, 'texconfig', texconf, pad=4)

        for k, node in self.nodes.items():
            rd.write_block(dataout, 'modelnode', node, pad=4)

        for texdata in self.texdatas:
            rd.write_block_raw(dataout, texdata)
            log(f'.TEX {len(dataout):08X}')

        idx = 0
        for rodata in self.rodatas:
            type = rodata['_node_type_']

            # if numvertices:
            if type in [0x04, 0x16, 0x18]:
                rodata['vertices'] = len(dataout) | 0x05000000
                vertices = self.vertices[idx]
                colors = self.colors[idx]

                rd.write_block_raw(dataout, vertices, pad=8)
                rd.write_block_raw(dataout, colors, pad=8)

            rd.ref = len(dataout)
            rd.write_block(dataout, rodata_decls[type], rodata, pad=8)
            idx += 1

        texaddrs = { blk['_addr_']: blk['write_addr'] for blk in self.texdatas }

        # we have to manually patch the texconfig pointers, because nothing points to them (except the first)
        m = 0x05000000
        for texconfig in self.texconfigs:
            addr = texconfig['write_addr']
            texnum = texconfig['texturenum']
            if not texnum & m: continue

            texnum_new = texaddrs[texnum & ~m] + (texnum & m)
            # log(texconfig, f'addr: tex {texnum:08X} texnew {texnum_new:08X}')
            dataout[addr:addr+8] = texnum_new.to_bytes(8, DEST_BO)
            # log(texconfig, f'addr: tex {texnum:08X} texnew {texnum_new:08X}')

        log(f'>patchpointers [{len(dataout):04X}]')
        rd.patch_pointers(dataout, 0x05000000)

        return dataout

    def replace_gdl(self, dataout, gdlbytes, idx, layer):
        if not gdlbytes: return

        rodata = self.rodatas[idx]
        nodetype = rodata['_node_type_']
        if nodetype not in [0x04, 0x16, 0x18]:
            raise Exception(f'Invalid rodata type to replace GDL: {nodetype}')

        rd = self.rd
        # print(f'REPLACE_GDL {idx:02X} len {len(gdlbytes)} {layer}')
        prev_addr = rodata[layer] & 0xffffff
        gdlblock = rd.create_block(prev_addr, gdlbytes)
        rd.write_block_raw(dataout, gdlblock)

        gdl_addr = gdlblock['write_addr']
        offset = 4 if layer == 'xlugdl' else 0
        ptr_addr = rodata['write_addr'] + offset
        # print(f'  {idx:02X} GDL prev {prev_addr:08X} new {gdl_addr:08X} ptr {ptr_addr:08X}')
        dataout[ptr_addr: ptr_addr + 4] = gdl_addr.to_bytes(4, 'big')

    def read_node(self, rootaddr):
        log(f'read_node: {rootaddr:08X}')
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
        rd.declare('parts', decl_parts, vars={'N': n})
        addr = unmask(self.modeldef['parts'])
        rd.set_cursor(addr)
        self.modelparts = rd.read_block('parts')

    def read_rodata(self):
        rd = self.rd
        idx = 0
        for k, node in self.nodes.items():
            node_addr = node['_addr_']
            rodata_addr = node['rodata']
            type = node['type'] & 0xff
            rodata_name = rodata_decls[type]
            log(f'{node_addr:04X} t {type:02X} {rodata_name} {rodata_addr:08X}')

            rd.set_cursor(unmask(rodata_addr))
            rodata = rd.read_block(rodata_name)
            rodata['_node_type_'] = type
            self.rodatas.append(rodata)
            rd.print_dict(rodata, rd.decl_map[rodata_name], pad=16, numspaces=4, showdec=True)
            rodatagdl_map = {
                0x04: ['opagdl', 'xlugdl'],
                0x16: ['gdl'],
                0x18: ['opagdl', 'xlugdl']
            }
            if type in rodatagdl_map:
                self.read_vertices(rodata, type, idx)

            idx += 1

            # log(''*12)

    def read_vertices(self, rodata, type, idx):
        rd = self.rd
        log(f'VERTICES [{rd.cursor:04X}]')

        numvertices = rodata['numvertices'] if type in [0x04, 0x18] else rodata['unk00'] * 4

        if numvertices:
            vtxsize = 12
            start = rodata['vertices']
            end = ALIGN8(unmask(start) + numvertices * vtxsize)
            endnoalign = (unmask(start) + numvertices * vtxsize)
            self.vertices[idx] = rd.read_block_raw(unmask(start), end)
            v = self.vertices[idx]['bytes']
            log(f'.VTX   start {unmask(start):04X} end {end:04X} endnoalign {endnoalign:04X} len {len(v)} num {numvertices}')
            if enableLog: print_bin('^VTX', v, 0, 12*12, 2, 6)

            col_start = ALIGN8(unmask(end))
            col_end = rodata['_addr_']

            # save colors at the same address as the vertices
            colors = self.colors[idx] = rd.read_block_raw(col_start, col_end)
            rodata['colors'] = colors
            c = colors['bytes']
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
            tc_addr = texconfig['_addr_']
            if texnum & 0x05000000: embeddedtex = True
            log(f'{tc_addr:04X} texconfig {i}')
            rd.print_dict(texconfig, rd.decl_map['texconfig'], pad=16, numspaces=4, showdec=True)

        if embeddedtex:
            self.read_texdata()

    def read_texdata(self):
        rd = self.rd
        n = len(self.texconfigs)
        texaddrs = [texconf['texturenum'] for texconf in self.texconfigs]
        texaddrs.append(self.rodatas[0]['_addr_'])

        for i in range(0, n):
            addr = texaddrs[i]
            next = texaddrs[i+1]

            texdata = rd.read_block_raw(unmask(addr), unmask(next))
            self.texdatas.append(texdata)
            log(f'^TEX {addr:08X}:{next:08X}')
            print_bin(f'texdata_{i}', self.texdatas[0]['bytes'], 0, 16*10, 4, 4)

    def data(self, ptr):
        return self.modeldata[ptr&0xffffff:]

        # print_bin('texdata_0', self.texdatas[0]['bytes'], 0, -1, group_size=4)

    def find_rodata(self, addr):
        addr = unmask(addr)
        for ro in self.rodatas:
            if ro['_addr_'] == addr: return ro

        return None

    def replace_vtxdata(self, idx, vtxdata):
        rodata = self.rodatas[idx]
        nodetype = rodata['_node_type_']

        if nodetype not in [0x04, 0x16, 0x18]:
            raise Exception(f'invalid node type: {nodetype} idx {idx}')

        vtxblock = self.vertices[idx]
        vtxblock['bytes'] = vtxdata

        numvtx = len(vtxdata) // 12

        # update rodata numvertices
        if nodetype in [0x04, 0x18]:
            rodata['numvertices'] = numvtx
        elif nodetype in [0x16]:
            rodata['unk00'] = numvtx >> 2

    def replace_colordata(self, idx, colordata):
        rodata = self.rodatas[idx]
        nodetype = rodata['_node_type_']

        if nodetype not in [0x04, 0x16, 0x18]:
            raise Exception(f'invalid node type: {type}')

        colorblock = self.colors[idx]
        colorblock['bytes'] = colordata

def read(path, filename, skipDLdata=False):
    modeldata = read_file(f'{path}/{filename}')
    modeldata = decompress(modeldata)
    return PDModel(modeldata, skipDLdata)
