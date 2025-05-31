from typeinfo import TypeInfo, field_info

class DataBlock:
    def __init__(self, name, addr, data = None):
        self.name = name
        self.addr = addr
        self.write_addr = None
        self.fields = {}
        self.field_infos = {}
        self.bytes = data

    # create a new empty block (all fields set to zero)
    @staticmethod
    def New(decl_name):
        datablock = DataBlock(decl_name, 0)
        decl = TypeInfo.get_decl(decl_name)
        for typename in decl:
            info = field_info(typename)
            # print(info)
            if info['is_struct']:
                if info['is_array']:
                    n = info['array_size']
                    array = [DataBlock.New(info['typename']) for _ in range(n)]
                    datablock.add_field(info, array)
                else:
                    datablock.add_field(info, DataBlock.New(info['typename']))
            elif info['is_array']:
                datablock.add_field(info, [0] * info['array_size'])
            else:
                datablock.add_field(info, 0)

        return datablock

    def add_field(self, info, value):
        self.fields[info['fieldname']] = value
        self.field_infos[info['fieldname']] = info

    # updates the value of 'field' and also serialize it to dataout
    def update(self, dataout, field, value, signed=False):
        self[field] = value
        info = self.field_infos[field]
        typename = info['typename']

        size = TypeInfo.sizeof(typename)
        offset = TypeInfo.offsetof(self.name, field)
        addr = self.write_addr + offset

        if info['is_array']:
            for val in value:
                dataout[addr:addr + size] = val.to_bytes(size, 'big', signed=signed) # TODO config
                addr += size
        else:
            dataout[addr:addr + size] = value.to_bytes(size, 'big', signed=signed)

    def __getitem__(self, key):
        return self.fields[key]

    def __setitem__(self, key, value):
        self.fields[key] = value

    def __repr__(self):
        return str(self.fields)

