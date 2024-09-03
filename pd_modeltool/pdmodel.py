from bytereader import *
from decl_model import *


def unmask(addr):
    return addr & 0x00ffffff if addr & 0x5000000 else addr

def log(*args):
    if enableLog:
        print(''.join(args))

def printdict(d, indent=4):
    if enableLog:
        print_dict(d, indent=indent)

class PDModel:
    def __init__(self, modeldata, srcBO = 'big', destBO = 'little'):
        self.modeldata = modeldata
        self.rd = ByteReader(modeldata, srcBO, destBO, 0x00ffffff)
        self.srcBO = srcBO
        # self.rd = ByteReader(modeldata, srcBO, destBO)

        for name, decl in model_decls.items():
            self.rd.declare(name, decl)

        self.modeldef = None
        self.modelparts = None
        self.nodes = {}
        self.rodatas = []
        self.texconfigs = []
        self.texdatas = []

        self.gdladdrs = []
        # self.gdladdrs2 = []
        self.gdls = []
        # self.gdls2 = []
        self.vertices = {}
        self.colors = {}

        self.firstgdl = 0
        self.lastgdl = 0

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
        self.read_gdls()

    def traverse(self, callback, **kwargs):
        node = self.rootnode
        depth = 0
        idx = 0
        # parentnode = None
        while node:
            # node['_idx_'] = idx
            nodetype = node['type']

            callback(self, node, idx, depth, **kwargs)

            sp = ' ' * depth * 2
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

        log(f'>patch modeldef [{len(dataout):04X}]')
        rd.write_block(dataout, 'modeldef', self.modeldef)

        log(f'>patch parts [{len(dataout):04X}]')
        rd.write_block(dataout, 'parts', self.modelparts, pad=4)

        __addr = self.modelparts['write_addr']
        # print_bin('parts', dataout, __addr, -1, 4, 4)

        for texconf in self.texconfigs:
            log(f'>patch texconfig [{len(dataout):04X}]')
            rd.write_block(dataout, 'texconfig', texconf, pad=4)

        for k, node in self.nodes.items():
            log(f'>patch modelnode [{len(dataout):04X}]')
            rd.write_block(dataout, 'modelnode', node, pad=4)

        for texdata in self.texdatas:
            addr = texdata['_addr_']
            # log(f'texdata: {addr:08X}')
            log(f'>patch texdata [{len(dataout):04X}]')
            rd.write_block_raw(dataout, texdata)
            log(f'.TEX {len(dataout):08X}')

        # rd.add_padding(dataout, 8)

        for rodata in self.rodatas:
            type = rodata['_node_type_']

            numvertices = 0
            if type in [0x04, 0x18]:
                numvertices = rodata['numvertices']
            elif type == 0x16:
                numvertices = rodata['unk00'] * 4

            if numvertices:
                addr = rodata['vertices']
                # addr = rodata['vertices'] & 0xffffff
                # log(f'>patch rodata VTX addr {addr:04X}')
                vertices = self.vertices[addr]
                colors = self.colors[addr]

                v = vertices['bytes']
                log(f'>patch rodata VTX len {len(v)}')
                # print_bin('^VTX', v, 0, 64, 2, 6)
                rd.write_block_raw(dataout, vertices, pad=8)
                # log(f'COL {len(dataout):04X}')
                v = colors['bytes']
                log(f'>patch COL [{len(v)}]')
                rd.write_block_raw(dataout, colors, pad=8)

            log(f'>patch {rodata_decls[type]} [{len(dataout):04X}]')
            rd.ref = len(dataout)
            rd.write_block(dataout, rodata_decls[type], rodata, pad=8)

        gdladdrs = []
        for gdlinfo in self.gdls:
            gdldata = gdlinfo[0]
            node = gdlinfo[1]
            gdladdrs.append((len(dataout), node))
            log(f'>patch GDL [{len(dataout):04X}]')
            rd.write_block_raw(dataout, gdldata, pad=4)

        gdladdrs.append((len(dataout),0))
        n = len(gdladdrs) - 1
        baseptrs_map = {}
        for i in range(0, n):
            node = gdladdrs[i][1]
            if node not in baseptrs_map: baseptrs_map[node] = {}
            # rd.patch_gdl_pointers(dataout, gdladdrs[i][0], gdladdrs[i+1][0], baseptrs_map[node])
            rd.patch_gdl_pointers(dataout, gdladdrs[i][0], gdladdrs[i+1][0], baseptrs_map[node])
            # rd.patch_gdl_pointers(dataout, gdladdrs[i][0], gdladdrs[i+1][0], baseptrs_map)
            # log('-'*32)

        texaddrs = { blk['_addr_']: blk['write_addr'] for blk in self.texdatas }

        # for texdata in self.texdatas:
        #     addr, addr_new = texdata['_addr_'], texdata['write_addr']
        #     log(f'TEXDATA {addr:08X} -> {addr_new:08X}')

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
        # rd.patch_pointers(dataout)
        rd.patch_pointers(dataout, 0x05000000)

        # log('PTR MAP')
        # for k, ptr in sorted(rd.pointers_map.items()): log(f'{k:08X} -> {ptr:08X}')
        # log('PTR LOC')
        # for p in rd.pointers:
        #     map = rd.pointers_map
        #     v = rd.pointers_map[p] if p in map or (p | 0x05000000) in map else -1
        #     v = f'{v:08X}' if v >= 0 else '----'
        #     log(f'{p:08X} ({v})')

        return dataout
        # n = len(dataout)
        # print_bin(f'modeldef: {n:04X} ({n}) bytes', dataout, 0, n, group_size=4)

        # rd.patch_pointers(self.dataout)

    def read_node(self, rootaddr):
        log(f'read_node: {rootaddr:08X}')
        rd = self.rd
        rd.set_cursor(rootaddr)
        node = rd.read_block('modelnode')
        self.nodes[rootaddr] = node
        rd.print_dict(node, decl_modelnode, pad=16, numspaces=4)
        # printdict(node)
        log('-'*32)

        # read 'child' nodes
        child = unmask(node['child'])
        if child != 0 and child not in self.nodes:
            childnode = self.read_node(child)

        # read 'prev' nodes
        prev = unmask(node['prev'])
        # while prev != 0 and prev not in self.nodes:
        #     prevnode = self.read_node(prev)
        #     prev = unmask(prevnode['prev'])

        # read 'next' nodes
        next = unmask(node['next'])
        while next != 0 and next not in self.nodes:
            nextnode = self.read_node(next)
            next = unmask(nextnode['next'])

        return node

    def read_modelparts(self):
        # global decl_parts
        rd = self.rd
        # n = str(self.modeldef['numparts'])
        n = self.modeldef['numparts']
        # decl_parts = list(map(lambda e: e.replace('N', n), decl_parts))
        rd.declare('parts', decl_parts, vars={'N': n})
        addr = unmask(self.modeldef['parts'])
        rd.set_cursor(addr)
        self.modelparts = rd.read_block('parts')
        # printdict(self.modelparts)
        # for part in block_parts['parts']:
        #     log(f'{part:08X}')
        # rd.print_dict(block_parts, decl_parts, pad=16, numspaces=2)
        # log(self.modeldef)

    def read_rodata(self):
        rd = self.rd
        for k, node in self.nodes.items():
            gdladdrs = []
            node_addr = node['_addr_']
            rodata_addr = node['rodata']
            type = node['type'] & 0xff
            rodata_name = rodata_decls[type]
            # log(f'{node_addr:04X} t {type:02X} {rodata_name}')
            log(f'{node_addr:04X} t {type:02X} {rodata_name} {rodata_addr:08X}')

            rd.set_cursor(unmask(rodata_addr))
            rodata = rd.read_block(rodata_name)
            rodata['_node_type_'] = type
            self.rodatas.append(rodata)
            rd.print_dict(rodata, rd.decl_map[rodata_name], pad=16, numspaces=4, showdec=True)
            # log(rodata)
            rodatagdl_map = {
                0x04: ['opagdl', 'xlugdl'],
                0x16: ['gdl'],
                0x18: ['opagdl', 'xlugdl']
            }
            if type in rodatagdl_map:
                self.read_vertices(rodata, type)
                for name in rodatagdl_map[type]:
                    if name not in rodata:
                        print(f'warning: gdl \'{name}\' not found in rodata {type:02X}')
                        continue
                    addr = rodata[name] & 0xfffffffffffffffe
                    # if addr: self.gdladdrs.append(addr)

                    # we need to save 'k' here to later identify GDLs from the same node
                    if addr: self.gdladdrs.append((addr, k))
                    # if addr: self.gdladdrs.append((addr, node_addr))

                # self.gdladdrs2.append(gdladdrs)
            # log(''*12)

    def read_vertices(self, rodata, type):
        rd = self.rd
        log(f'VERTICES [{rd.cursor:04X}]')
        printdict(rodata)
        numvertices = rodata['numvertices'] if type in [0x04, 0x18] else rodata['unk00'] * 4
        # numvertices = rodata['numvertices'] if 'numvertices' in rodata else None
        if numvertices:
            vtxsize = 12
            start = rodata['vertices']
            # start = rodata['vertices'] & 0xffffff
            end = ALIGN8(unmask(start) + numvertices * vtxsize)
            endnoalign = (unmask(start) + numvertices * vtxsize)
            self.vertices[start] = rd.read_block_raw(unmask(start), end)
            v = self.vertices[start]['bytes']
            log(f'.VTX   start {unmask(start):04X} end {end:04X} endnoalign {endnoalign:04X} len {len(v)} num {numvertices}')
            if enableLog: print_bin('^VTX', v, 0, 12*12, 2, 6)

            # col_start = loc(end)
            # col_start = ALIGN8(loc(end))
            col_start = ALIGN8(unmask(end))
            col_end = rodata['_addr_']

            # a = colors['_addr_']
            # save colors at the same address as the vertices
            colors = self.colors[start] = rd.read_block_raw(col_start, col_end)
            rodata['colors'] = colors
            c = colors['bytes']
            log(f'.COLORS start {col_start:04X} len {len(c):04X} ({len(c)})')
            if enableLog: print_bin('^COLORS', c, 0, 12*12, 4, 3)

            # there are no direct pointers to the colors block (its implicit since it follows vtxs)
            # so we need to add it manually here, to things can be patched later, pain in the ass
            rd.pointers_map[col_start] = 0
            # log(f'  s {start:08X} e {end-1:08X} col_end {col_end:08X}')
            # print_bin('col', colors['bytes'], 0, 64, 4)

    def read_gdls(self):
        # global SRC_BO

        rd = self.rd
        gdladdrs = self.gdladdrs
        gdladdrs.sort()
        lastgdl = gdladdrs[-1][0]

        log('.GDLs')
        # print(self.gdladdrs2)
        # for gdl in self.gdladdrs2:
        #     print(gdl)

        for idx, gdlinfo in enumerate(gdladdrs):
            addr = gdlinfo[0]
            node = gdlinfo[1]

            start = addr
            end = gdladdrs[idx+1][0] if addr != lastgdl else len(rd.data) # end of the file
            rd.set_cursor(unmask(addr))
            # self.gdls[addr] = rd.read_block_raw(loc(start), loc(end))
            gdldata = rd.read_block_raw(unmask(start), unmask(end))
            log(f'.gdldata {unmask(start):04X}:{unmask(end):04X}')

            if enableLog:
                if sz['pointer'] == 8: printGDL(gdldata['bytes'], 2, 'little')
                # else: printGDL_x86(gdldata['bytes'], 2, 'little')
                else: printGDL_x86(gdldata['bytes'], 2, self.srcBO)

            # self.gdls.append(gdldata)
            self.gdls.append((gdldata, node))

    def read_tex_configs(self):
        rd = self.rd
        addr = unmask(self.modeldef['texconfigs'])
        rd.set_cursor(addr)

        embeddedtex = False
        msg = ''
        for i in range(0, self.modeldef['numtexconfigs']):
            texconfig = rd.read_block('texconfig')
            self.texconfigs.append(texconfig)

            texnum = texconfig['texturenum']
            tc_addr = texconfig['_addr_']
            if texnum & 0x05000000: embeddedtex = True
            # print_dict2(texconfig, decl_texconfig, sz, pad=16, numspaces=2)
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

def read(path, filename):
    modeldata = read_file(f'{path}/{filename}')
    modeldata = decompress(modeldata)
    return PDModel(modeldata)
