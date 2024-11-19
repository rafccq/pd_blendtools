from datablock import DataBlock
from pd_utils import *
from typeinfo import *

SRC_BO = 'big'
# SRC_BO = 'little'
# DEST_BO = 'little'
DEST_BO = 'big'

enableLog = False
# enableLog = True

class ByteReader:
    def __init__(self, data, srcBO = 'big', destBO = 'big', mask=0xffffffff):
        global SRC_BO, DEST_BO
        SRC_BO = srcBO
        DEST_BO = destBO

        self.data = data
        self.buffer = None
        self.cursor = 0
        self.pointers_map = {}
        self.fd = ''
        self.ref = 0
        self.mask = mask

    def set_data(self, data):
        self.data = data
        self.cursor = 0

    def set_buffer(self, buffer:bytearray):
        self.buffer = buffer

    def set_cursor(self, cursor):
        self.cursor = cursor

    def read_block(self, decl_name, endmarker = None):
        decl = TypeInfo.decl_map[decl_name]
        block = DataBlock(decl_name, self.cursor)
        for typename in decl:
            val, info = self.read(typename, endmarker)
            name = info['fieldname']
            typename = info['typename']
            block.add_field(typename, name, val)

        return block

    def read_block_raw(self, start, end=None):
        data = self.data[start:end] if end is not None else self.data[start:]
        return DataBlock('', start, data)

    def create_block(self, addr, data):
        return { # TODO
            '_addr_': addr,
            'bytes': data
        }

    def read(self, decl, endmarker = None):
        info = field_info(decl)

        # print(info)

        typename = info['typename']
        is_struct = info['is_struct']
        is_array = info['is_array']

        read_func = self.read_block if is_struct else self.read_primitive

        if is_array:
            dataout = []
            self.read_array(dataout, info, endmarker) #TODO array size
            # block[f'{fieldname}_len'] = len(dataout)
            # info[f'{fieldname}_len'] = len(dataout)
            return dataout, info
        else:
            return read_func(typename), info

    def read_array(self, dataout, info, endmarker):
        # fieldname = info['fieldname']
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
                val = read_func(typename)
                dataout.append(val)
                marker = self.peek(markertype)

            marker = self.read_primitive(markertype)
            if 'includelast' in endmarker:
                dataout.append(marker)
        else:
            for i in range(0, array_size):
                # if is_struct: print(f'{fieldname}[{i}]:')
                val = read_func(typename)
                dataout.append(val)

    def read_primitive(self, typename):
        size = TypeInfo.sizeof(typename)

        addr = self.cursor
        self.cursor += size

        val = self.data[addr:addr+size]
        return int.from_bytes(val, SRC_BO)

    def peek(self, typename, n = 1):
        size = TypeInfo.sizeof(typename)
        addr = self.cursor
        values = []

        for i in range(n):
            val = self.data[addr:addr+size]
            values.append(int.from_bytes(val, SRC_BO))
            v = int.from_bytes(val, SRC_BO)
            # print(f'peek{i}: {v:01X}')
            addr += size

        return values if n > 1 else values[0]

    def write(self, dataout, val, typename):
        nbytes = TypeInfo.sizeof(typename)
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

    def write_block(self, dataout, decl, block, pad=0, reread_arraysize=False):
        block.write_addr = len(dataout)

        decl = TypeInfo.get_decl(decl)
        for field in decl:
            info = field_info(field)
            # print(info)

            typename = info['typename']
            fieldname = info['fieldname']
            is_pointer = info['is_pointer']
            is_struct = info['is_struct']
            is_array = info['is_array']
            array_size = info['array_size']

            if is_array:
                array_size = array_size if reread_arraysize else block[f'{fieldname}_len'] # TODO array size
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
        add_padding(dataout, pad, name)

    def write_block_list(self, dataout, decl, blocklist, endmarker=None, pad=0, dbg=0):
        for block in blocklist:
            # print(block)
            if dbg==1:
                # print_dict2(block, self.decl_map[decl], sz, pad=12)
                # self.print_dict(block, decl, pad=12, showdec=True, numspaces=4)
                # print(f'write {decl} [{len(dataout):04X}]')
                self.print_dict(block, decl, pad=5, numspaces=2)
                # addr = block.addr
                # print(f'addr:{addr:08X}', json.dumps(block, indent=4))
            self.write_block(dataout, decl, block)

        if endmarker is not None:
            # endmarker: (typename, value) eg ('s32', 0xffffffff)
            self.write(dataout, endmarker[1], endmarker[0])

        add_padding(dataout, pad, decl)

    def write_block_raw(self, dataout, block, pad=0):
        block.write_addr = len(dataout)
        dataout += block.bytes
        add_padding(dataout, pad)

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

    def print_dict(self, block, decl_name, showdec=False, pad=0, numspaces=0):
        if not enableLog: return

        decl = TypeInfo.get_decl(decl_name)
        for field in decl:
            info = field_info(field)

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

                    size = TypeInfo.sizeof(typename)
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

            size = TypeInfo.sizeof(typename)
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

        size = TypeInfo.sizeof(typename)
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

def add_padding(dataout, pad, name=None):
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


