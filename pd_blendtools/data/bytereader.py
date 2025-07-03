from .datablock import DataBlock
from .typeinfo import TypeInfo, field_info


enableLog = False

class ByteReader:
    def __init__(self, data, src_BO = 'big', dest_BO = 'big'):
        self.data = data
        self.buffer = None
        self.cursor = 0
        self.fd = ''
        self.ref = 0
        self.src_BO = src_BO
        self.dest_BO = dest_BO

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
            block.add_field(info, val)

        return block

    def read_block_raw(self, start, end=None):
        data = self.data[start:end] if end is not None else self.data[start:]
        return DataBlock('', start, data)

    @staticmethod
    def create_block(data):
        return DataBlock('', 0, data)

    def read(self, decl, endmarker = None):
        info = field_info(decl)

        typename = info['typename']
        is_struct = info['is_struct']
        is_array = info['is_array']

        read_func = self.read_block if is_struct else self.read_primitive

        if is_array:
            dataout = []
            self.read_array(dataout, info, endmarker)
            return dataout, info
        else:
            return read_func(typename), info

    def read_array(self, dataout, info, endmarker):
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
                val = read_func(typename)
                dataout.append(val)

    def read_primitive(self, typename):
        size = TypeInfo.sizeof(typename)

        addr = self.cursor
        self.cursor += size

        val = self.data[addr:addr+size]
        return int.from_bytes(val, self.src_BO)

    def peek(self, typename, n = 1):
        size = TypeInfo.sizeof(typename)
        addr = self.cursor
        values = []

        for i in range(n):
            val = self.data[addr:addr+size]
            values.append(int.from_bytes(val, self.src_BO))
            addr += size

        return values if n > 1 else values[0]

    def write(self, dataout, val, typename):
        nbytes = TypeInfo.sizeof(typename)
        __addr = len(dataout)
        __addrrel = __addr - self.ref
        __v = val
        signed = typename in ['s8', 's16', 's32', 's64']
        val = val.to_bytes(nbytes, self.dest_BO, signed=signed)

        dataout += bytearray(val)

    def write_block(self, dataout, block, pad=0, reread_arraysize=False):
        block.write_addr = len(dataout)

        decl_name = block.name
        decl = TypeInfo.get_decl(decl_name)
        for field in decl:
            info = field_info(field)

            typename = info['typename']
            fieldname = info['fieldname']
            is_pointer = info['is_pointer']
            is_struct = info['is_struct']
            is_array = info['is_array']
            array_size = info['array_size']

            if is_array:
                array_size = array_size if reread_arraysize else len(block[fieldname])
                for i in range(0, array_size):
                    memdata = block[fieldname][i]
                    if is_struct:
                        self.write_block(dataout, memdata)
                    else:
                        self.fd = f'{fieldname}[{i}]'
                        self.write(dataout, memdata, typename)
            elif is_struct and not is_pointer:
                self.write_block(dataout, block[fieldname])
            else:
                self.fd = fieldname
                self.write(dataout, block[fieldname], typename)

        add_padding(dataout, pad)

    def write_block_list(self, dataout, decl, blocklist, endmarker=None, pad=0, dbg=0):
        for block in blocklist:
            self.write_block(dataout, block)

        if endmarker is not None:
            self.write(dataout, endmarker[1], endmarker[0])

        add_padding(dataout, pad)

    @staticmethod
    def write_block_raw(dataout, block, pad=0):
        block.write_addr = len(dataout)
        dataout += block.bytes
        add_padding(dataout, pad)

def add_padding(dataout, pad):
    if pad == 0: return

    size = len(dataout)
    alignedsize = (size + (pad-1)) & ~(pad - 1)
    diff = alignedsize - size

    if diff > 0:
        dataout += bytearray(diff)
