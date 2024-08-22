from pd_utils import *

sz = {
    'pointer': 4,
    'u8': 1,
    's8': 1,
    's16': 2,
    'u16': 2,
    's32': 4,
    'u32': 4,
    'f32': 4,
    's64': 8,
    'f64': 8,
    'u64': 8,
}

SRC_BO = 'big'
# SRC_BO = 'little'
DEST_BO = 'little'
# DEST_BO = 'big'

enableLog = False
# enableLog = True

OUT_PTR_SIZE = 8

class ByteReader:
    def __init__(self, data, srcBO = 'big', destBO = 'little', mask=0xffffffff):
        global SRC_BO, DEST_BO
        SRC_BO = srcBO
        DEST_BO = destBO

        self.data = data
        self.buffer = None
        self.cursor = 0
        self.x64pointers = True
        self.offset = 0
        self.read_struct_table = {}
        self.struct_funcs = {}
        self.union_funcs = {}
        self.decl_map = {}
        self.pointers_map = {}
        self.pointers = []
        self.ofs = 0
        self.ofs_w = 0
        self.fd = ''
        self.ref = 0
        self.mask = mask


    def set_data(self, data):
        self.data = data
        self.cursor = 0

    def declare(self, name, declaration, vars = None):
        if vars:
            # replace variables in the declaration. Example: 'u8 val[N]' -> 'u8 val[5]'
            # where vars = {'N': 5}
            decl = declaration.copy()
            n = len(decl)
            pairs = [(idx, key) for idx in range(n) for key in vars.keys()]
            for (idx, key) in pairs: decl[idx] = decl[idx].replace(key, str(vars[key]))

            self.decl_map[name] = decl
            return

        prop_name = setup_props_names[name] if name in setup_props_names else name

        # show_struct = True
        show_struct = False
        if show_struct: print(f'struct {prop_name} {{')

        if name != "portalvertices":
            declaration = self.add_decl_pads(declaration)
        self.decl_map[name] = declaration

        if show_struct and name != "portalvertices":
            struct_sz, _ = self.struct_size(name)
            print(f'}} [{struct_sz:02x}]')

    def struct_size(self, name):
        if name == 'portalvertices': return
        # print(f'  struct size: {name}')
        struct = self.decl_map[name]
        # print(struct)
        size = 0
        max_sz = 0

        for decl in struct:
            info = field_info(decl)
            # print(info['typename'], info['fieldname'])
            # print(info)
            if info['is_struct']:
                name = info['typename']
                struct_sz, type_sz = self.struct_size(info['typename'])
                size += struct_sz
                max_sz = max(max_sz, type_sz)
                continue

            type_sz = sz['pointer'] if info['is_pointer'] else sz[info['typename']]
            max_sz = max(max_sz, type_sz)
            if info['is_array']:
                size += type_sz * info['array_size']
            else:
                size += type_sz

        return size, max_sz

    def add_decl_pads(self, decls):
        # log = True
        log = False

        cur_offset = 0
        new_decl = []

        pad_n = 0
        max_sz = 0

        for decl in decls:
            info = field_info(decl)
            # print(info)

            if info['is_cmd']: continue

            if info['is_struct']:
                name = info['typename']
                fieldname = info['fieldname']
                if log: print(f'/*{cur_offset:02x}*/ struct {name} {fieldname}')
                struct_sz, type_sz = self.struct_size(info['typename'])
                cur_offset += struct_sz
                max_sz = max(max_sz, type_sz)
                new_decl.append(decl)
                continue

            type_sz = sz['pointer'] if info['is_pointer'] else sz[info['typename']]
            max_sz = max(max_sz, type_sz)

            # add pads if needed
            # pad_sz = cur_offset % type_sz
            pad_sz = align(cur_offset, type_sz) - cur_offset
            if type_sz > 1 and pad_sz > 0:
                new_decl.append(f'u8 __pad{pad_n}__[{pad_sz}]')
                if log: print(f'/*{cur_offset:02x}*/ u8 __pad__[{pad_sz}]')
                cur_offset += pad_sz
                pad_n += 1

            if log: print(f'/*{cur_offset:02x}*/ {decl}')
            new_decl.append(decl)

            arr = info['is_array']
            cur_offset += type_sz * info['array_size'] if arr else type_sz

        remaining = cur_offset % max_sz
        if max_sz > 1 and remaining > 0:
            pad_sz = max_sz - remaining
            new_decl.append(f'u8 __pad{pad_n}__[{pad_sz}]')
            if log: print(f'/*{cur_offset:02x}*/ u8 __pad__[{pad_sz}] (max={max_sz}, cur_ofs={cur_offset:03x})')

        return new_decl

    def declare_union(self, name, func):
        self.union_funcs[name] = func

    def register_struct_func(self, name, func):
        self.struct_funcs[name] = func

    def set_buffer(self, buffer:bytearray):
        self.buffer = buffer

    def set_cursor(self, cursor):
        self.cursor = cursor

    def read_block(self, decl, endmarker = None, addpointers=True):
        byname = type(decl) is not list
        if byname and decl not in self.decl_map:
            print(f'attempt to read a block not declared: {decl}')
            return None

        decl = self.decl_map[decl] if byname else decl
        block = {'_addr_': self.cursor}
        for typename in decl:
            val, name = self.read(typename, block, endmarker, addpointers)
            block[name] = val

        return block

    def read_block_raw(self, start, end=None):
        # print(f'read block: {start:08X} {end: 08X}')
        # print(f'read block: {start:08X} {end: 08X} {self.data[start:end]}')
        return {
            '_addr_': start & 0x00ffffff,
            'bytes': self.data[start:end] if end is not None else self.data[start:]
        }

    def read(self, decl, block, endmarker = None, addpointers=True):
        info = field_info(decl)

        if info['is_cmd']:
            cmd = info['cmd']
            param = info['cmd_param']

            if cmd == 'union':
                union_func = self.union_funcs[param]
                # print(f'union: {param} func {union_func}')
                union_decl = union_func(block, 'read')
                return self.read_block(union_decl, addpointers), param

        # print(info)

        typename = info['typename']
        fieldname = info['fieldname']
        is_pointer = info['is_pointer']
        is_struct = info['is_struct']
        is_array = info['is_array']
        array_size = info['array_size']

        # to read structs, use the registered reader function from the table
        read_func = self.read_block if is_struct else self.read_primitive

        # if is_struct: print(f'{fieldname}:')

        if is_array:
            dataout = []
            self.read_array(dataout, info, endmarker, addpointers)
            block[f'{fieldname}_len'] = len(dataout)
            info[f'{fieldname}_len'] = len(dataout)
            return dataout, fieldname
        else:
            return read_func(typename, addpointers=addpointers), fieldname

    def read_array(self, dataout, info, endmarker, addpointers=True):
        fieldname = info['fieldname']
        typename = info['typename']
        array_size = info['array_size']
        is_struct = info['is_struct']

        read_func = self.read_block if is_struct else self.read_primitive

        if array_size == 0:
            if not endmarker: return
            markertype = endmarker[0]
            markervalue = endmarker[1]
            marker = self.peek(markertype)
            while marker != markervalue:
                val = read_func(typename, addpointers)
                dataout.append(val)
                marker = self.peek(markertype)

            marker = self.read_primitive(markertype)
            if 'includelast' in endmarker:
                dataout.append(marker)
        else:
            for i in range(0, array_size):
                # if is_struct: print(f'{fieldname}[{i}]:')
                val = read_func(typename, addpointers)
                dataout.append(val)

    def read_primitive(self, typename, addpointers=True):
        is_pointer = '*' in typename

        if not is_pointer and typename not in sz:
            raise Exception(f'type {typename} not registered')

        s = sz['pointer'] if is_pointer else sz[typename]

        addr = self.cursor
        self.cursor += s

        val = self.data[addr:addr+s]
        intval = int.from_bytes(val, SRC_BO)

        # pointer: save into the map, to be patched later, the value itself doesnt matter now
        if addpointers and is_pointer and intval != 0:
            # print(f'    register pointer: {intval&0x00ffffff + self.ofs:08X} ({typename}) intv {intval&0x00ffffff:08x} ofs {self.ofs:08X}')
            # addr = (intval&0x00ffffff) + (self.ofs&0xff000000)
            # addr = intval & self.ptr_mask # TODO
            addr = intval
            # self.pointers_map[intval&0x00ffffff + self.ofs] = 0
            self.pointers_map[addr & self.mask] = 0

        return intval

    def peek(self, typename, n = 1):
        is_pointer = '*' in typename

        if not is_pointer and typename not in sz:
            raise Exception(f'type {typename} not registered')

        s = sz['pointer'] if is_pointer else sz[typename]

        addr = self.cursor

        values = []
        for i in range(n):
            val = self.data[addr:addr+s]
            values.append(int.from_bytes(val, SRC_BO))
            v = int.from_bytes(val, SRC_BO)
            # print(f'peek{i}: {v:01X}')
            addr += s;

        return values if n > 1 else values[0]

    def write(self, dataout, val, typename):
        is_pointer = '*' in typename

        if is_pointer:
            addr = len(dataout)
            # if enableLog: print(f'  add pointer loc: {addr:08X} ({typename})')
            # if len(dataout) in self.pointers:
            #     log(f'>debug loc {addr:08X} t {typename}');
            self.pointers.append(len(dataout))

        nbytes = OUT_PTR_SIZE if is_pointer else sz[typename]
        # nbytes = 4 if is_pointer else sz[typename]
        __addr = len(dataout)
        __addrrel = __addr - self.ref
        __v = val
        val = val.to_bytes(nbytes, DEST_BO)

        fmt = '0' + str(nbytes*2) + 'X'
        # print(f'  write {val}')
        dataout += bytearray(val)

        # s = f'{typename} '.join([f'{val[k]:02X}' for k in range(0, nbytes)]) + f' [{__addr:08X}]'
        fd = self.fd.ljust(16) if self.fd else ''
        val = ''.join([f'{val[k]:02X}' for k in range(0, nbytes)])
        s = f'  {typename.ljust(12)} {fd} ' + val.ljust(16) + f' [{__addr:04X}] [{__addrrel:04X}]'
        # if enableLog: print(s)

    def add_padding(self, dataout, pad, name=None):
        if pad == 0: return

        if pad not in [4, 8, 16]:
            name = f'for decl {name}' if name else ''
            print(f'invalid pad value {name}: {pad}, ignoring pad')
            return

        # print(f'    >padding {pad}')
        size = len(dataout)
        alignedsize = (size + (pad-1)) & ~(pad - 1)
        diff = alignedsize - size

        if diff > 0:
            dataout += bytearray(diff)

    def write_block(self, dataout, decl, block, pad=0, reread_arraysize=False):
        blockaddr = block['_addr_']
        blockaddr_new = len(dataout)
        block['write_addr'] = blockaddr_new
        # print(f'blk {decl}: {blockaddr:08X} (+{self.ofs:08X}) {blockaddr + self.ofs:08X}')
        # print('write block:', json.dumps(block, indent=4))

        # save the new block address in the self.pointers_map
        addr = (blockaddr + self.ofs)
        if addr in self.pointers_map:
            # print(f'  ptr: {addr:08X} -> {blockaddr_new + self.ofs_w:08X} ({decl})')
            self.pointers_map[addr] = blockaddr_new + self.ofs_w

        byname = type(decl) is not list
        if byname and decl not in self.decl_map:
            print(f'attempt to read a block not declared: {decl}')
            return None

        decl = self.decl_map[decl] if byname else decl
        # for field in self.decl_map[name]:
        for field in decl:
            info = field_info(field)
            # print(info)

            if info['is_cmd']:
                cmd = info['cmd']
                param = info['cmd_param']

                if cmd == 'union':
                    union_func = self.union_funcs[param]
                    # print(f'union: {param} func {union_func}')
                    union_decl = union_func(block, 'write')
                    # print(f'union: {union_decl}')
                    # print(json.dumps(block, indent=4))
                    self.write_block(dataout, union_decl, block[param], reread_arraysize=True)
                    continue

            typename = info['typename']
            fieldname = info['fieldname']
            is_pointer = info['is_pointer']
            is_struct = info['is_struct']
            is_array = info['is_array']
            array_size = info['array_size']

            if is_array:
                # if not array_size: array_size = block[f'{fieldname}_len']
                array_size = array_size if reread_arraysize else block[f'{fieldname}_len']
                # print(f'arrsz {array_size} field \'{field}\'')
                # print(block)
                for i in range(0, array_size):
                    memdata = block[fieldname][i]
                    if is_struct:
                        self.write_block(dataout, typename, memdata)
                    else:
                        self.fd = f'{fieldname}[{i}]'
                        self.write(dataout, memdata, typename)
            elif is_struct and not is_pointer:
                # print(f'struct: {fieldname}')
                self.write_block(dataout, typename, block[fieldname])
            else:
                self.fd = fieldname
                # print(fieldname, ':', decl)
                self.write(dataout, block[fieldname], typename)

        name = decl if decl is str else ''
        self.add_padding(dataout, pad, name)

    def write_block_list(self, dataout, decl, blocklist, endmarker=None, pad=0, dbg=0):
        for block in blocklist:
            # print(block)
            if dbg==1:
                # print_dict2(block, self.decl_map[decl], sz, pad=12)
                # self.print_dict(block, decl, pad=12, showdec=True, numspaces=4)
                print(f'write {decl} [{len(dataout):04X}]')
                self.print_dict(block, decl, pad=5, numspaces=2)
                addr = block['_addr_']
                # print(f'addr:{addr:08X}', json.dumps(block, indent=4))
            self.write_block(dataout, decl, block)

        if endmarker is not None:
            # endmarker: (typename, value) eg ('s32', 0xffffffff)
            self.write(dataout, endmarker[1], endmarker[0])

        self.add_padding(dataout, pad, decl)

    def write_block_raw(self, dataout, block, pad=0):
        blockaddr_old = block['_addr_'] + self.ofs
        block['write_addr'] = len(dataout)
        # print(f'blk: {blockaddr_old:08X} [{len(dataout):04X}]')
        # print(block)

        # save the new block address in the map
        if blockaddr_old in self.pointers_map:
            blockaddr_new = len(dataout) + self.ofs_w
            # print(f'  ptr: {blockaddr_old:08X} -> {blockaddr_new:08X}')
            self.pointers_map[blockaddr_old] = blockaddr_new

        dataout += block['bytes']
        self.add_padding(dataout, pad)

    # def add_pointer(self, ptr):
    #     self.pointers_map[ptr] = 0

    def patch_pointers(self, data, mask):
        ptrsz = 8
        # print(f'{len(self.pointers)} pointers')

        # mask = 0x05000000
        for addr in self.pointers:
            ptrvalue = int.from_bytes(data[addr:addr+ptrsz], byteorder=DEST_BO)
            if ptrvalue == 0: continue

            # ptrnew = 0xcadebeef
            # print(f'[{addr:08X}] {ptrvalue:08X} -> {ptrnew:08X}')
            ptrmasked = ptrvalue & ~mask
            ptrnew = self.pointers_map[ptrmasked] + (ptrvalue & mask) + 0*self.ofs_w if ptrmasked in self.pointers_map else None
            # print(f'[{addr:08X}] {ptrvalue:08X}')
            if not ptrnew:
                # print(f'warning: pointer {ptrvalue & ~mask:08X} at addr {addr:08X} not found, skipping...')
                continue

            if ptrnew == 0xffffffff:
                # if enableLog: print(f'warning: ptr {ptrvalue:08X} [{addr:04X}] marked to be patched but not updated]')
                continue

            # if enableLog: print(f'[{addr:08X}] {ptrvalue:08X} -> {ptrnew:08X} diff {ptrnew - ptrvalue}')
            # print(f'\t -> {ptrnew:08X}')
            data[addr:addr+ptrsz] = ptrnew.to_bytes(ptrsz, byteorder=DEST_BO)

    def patch_gdl_pointers(self, dataout, start, end = None, base_ptr = None):
        addr = start
        vtx = 0
        base_ptr = {} if not base_ptr else base_ptr
        m = 0xff000000
        while addr < end if end else True:
            cmd = dataout[addr:addr+8]
            opcode = cmd[0]

            if not end and opcode == G_ENDDL: break

            val = int.from_bytes(cmd, 'big')
            w0 = int.from_bytes(cmd[4:8], 'big')
            msg = ''
            # print(f'  >GDL {val:016X}: w0:{w0:08X} {GDLcodes[cmd[0]]}')
            seg = (w0 & m) >> 24
            if is_cmd_ptr(opcode) and seg == 5:
                # w0 &= 0x00ffffff
                w = w0 & ~m
                # print(f'key {w:08X} ({w})')
                newptr = self.pointers_map[w] if w in self.pointers_map else 0

                if opcode in [0x04, 0x07]: # VTX and COL commands
                    if opcode not in base_ptr: base_ptr[opcode] = w
                    base = base_ptr[opcode]
                    base_new = self.pointers_map[base]
                    # try:
                    #     base_new = self.pointers_map[base]
                    # except Exception as e:
                    #     print('ERROR, ptr_map:', self.pointers_map)
                    #     for k,v in self.pointers_map.items():
                    #         print(f'  {k:08X} {v:08X}')
                    #     raise e
                    offset = w - base
                    newptr = base_new + offset

                if newptr:
                    newptr += w0 & m
                    dataout[addr+4:addr+8] = newptr.to_bytes(4, 'big')
                msg = f': >GDLpatch {w0:04X} -> {newptr:08X}'
            # print(f'{val:016X}: w0:{w0:08X} {GDLcodes[cmd[0]]} {msg}')
            addr += 8

    def skip(self, nbytes):
        for i in range(nbytes):
            self.read('u8', 'skip')

    def skip_dwords(self, n):
        for i in range(n):
            self.read('s32', 'skip')

    def skip_words(self, n):
        for i in range(n):
            self.read('s16', 'skip')

    def print_dict(self, block, decl, showdec=False, pad=0, numspaces=0):
        if not enableLog: return

        byname = type(decl) is not list
        if byname and decl not in self.decl_map:
            print(f'attempt to read a block not declared: {decl}')
            return None

        decl = self.decl_map[decl] if byname else decl
        for field in decl:
            info = field_info(field)
            # print(info)
            if info['is_cmd'] and info['cmd'] == 'union':
                param = info['cmd_param']

                union_func = self.union_funcs[param]
                # print(f'union: {param} func {union_func}')
                # op = 'read' if sz['pointer'] == 4 else 'write'
                union_decl = union_func(block, 'read')
                # print(f'union: {union_decl}')
                # print(json.dumps(block, indent=4))

                self.print_dict(block[param], union_decl, showdec, pad, numspaces + 2)
                # return self.write_block(dataout, union_decl, block[param])
                continue

            typename = info['typename']
            fieldname = info['fieldname']
            is_struct = info['is_struct']
            is_pointer = info['is_pointer']
            is_array = info['is_array']

            if fieldname.startswith('__pad') and fieldname.endswith('__'): continue

            if is_struct and not is_pointer and not is_array:
                # print(f'{spaces}{fieldname}:')
                self.print_dict(block[fieldname], typename, showdec, pad, numspaces) # + 2
                continue

            if info['is_array']:
                arraysize = info['array_size']
                arraysize = block[f'{fieldname}_len'] if arraysize == 0 else arraysize
                # arraysize = info
                for i in range(0, arraysize):
                    spaces = ' ' * numspaces if numspaces > 0 else ''
                    if is_struct:
                        if enableLog: print(f'{spaces}{fieldname}[{i}]:')
                        self.print_dict(block[fieldname][i], typename, showdec, pad, numspaces) # + 2)
                        continue

                    # size = sz['pointer'] if info['is_pointer'] else sz[typename]
                    size = 4 if info['is_pointer'] else sz[typename]
                    fmt = '0' + str(size*2) + 'X'
                    # name = f'{fieldname}[{i}]'.ljust(pad)
                    name = f'{fieldname}[{i}]'
                    val = block[fieldname][i]
                    valfiltered = val if val < 65536 else '-'
                    dec = f' ({valfiltered})' if showdec else ''
                    # print(f'{spaces}{name}: {block[fieldname][i]:{fmt}}{dec}')
                    # print(f'{spaces}{name}:    0x{block[fieldname][i]:{fmt}}{dec}')
                    print(f'{spaces}{name}: {block[fieldname][i]:{fmt}}{dec}')
                continue

            size = sz['pointer'] if info['is_pointer'] else sz[typename]
            name = fieldname.ljust(pad)
            fmt = '0' + str(size*2) + 'X'

            val = block[fieldname]
            # valfiltered = val if val < 65536 else '-'
            # dec = f' ({valfiltered})' if showdec else ''
            # print(f'{spaces}{name}: {val:{fmt}}{dec}')
            # print(f'{spaces}{name}:    0x{val:{fmt}}{dec}')
            self.print(val, typename, fieldname, showdec, pad, numspaces)

    def print(self, val, typename, fieldname, showdec = False, pad=0, numspaces=0):
        if not enableLog: return
        if fieldname.startswith('_') and fieldname.endswith('_') and 'pad' in fieldname: return

        is_pointer = '*' in typename
        # size = sz['pointer'] if is_pointer else sz[typename]
        size = 4 if is_pointer else sz[typename]
        name = fieldname.ljust(pad)
        # name = fieldname
        fmt = '0' + str(size*2) + 'X'

        valfiltered = val if val < 65536 else '-'
        dec = f' ({valfiltered})' if showdec else ''
        spaces = ' ' * numspaces if numspaces > 0 else ''
        # print(f'{spaces}{name}:    0x{val:{fmt}}{dec} [0x{self.cursor:04X}]')
        # print(f'{spaces}{name}:    0x{val:{fmt}}{dec}')
        # print(f'{spaces}{name}: {val:{fmt}}{dec} [0x{self.cursor:04X}]')
        print(f'{spaces}{name}: {val:{fmt}}{dec}')
