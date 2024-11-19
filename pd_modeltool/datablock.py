from bytereader import *

def offsetof(decl, field):
    return 0

class DataBlock:
    def __init__(self, name, addr, data = None):
        self.name = name
        self.addr = addr
        self.write_addr = None
        self.fields = {}
        self.field_types = {}
        self.field_offsets = {}
        self.bytes = data

    def add_field(self, typename, fieldname, value):
        self.fields[fieldname] = value
        self.field_types[fieldname] = typename

        # get the offset of the last field, if the map isn't empty
        ofs = 0
        if self.field_offsets:
            d_ofs, d_type = self.field_offsets, self.field_types

            k, last_ofs = _, d_ofs[k] = d_ofs.popitem()
            k, last_type = _, d_type[k] = d_type.popitem()

            last_size = TypeInfo.sizeof(last_type)
            ofs = last_size + last_ofs

        # if type(value) is list: # TODO handle array, is currently broken
        #     size *= len(value)

        self.field_offsets[fieldname] = ofs

    # updates the value of 'field' and also serialize it to dataout
    def update(self, dataout, field, value):
        self[field] = value
        typename = self.field_types[field]

        size = TypeInfo.sizeof(typename)
        offset = TypeInfo.offsetof(self.name, field)
        addr = self.write_addr + offset

        dataout[addr:addr + size] = value.to_bytes(size, 'big') # TODO config

    def __getitem__(self, key):
        return self.fields[key]

    def __setitem__(self, key, value):
        self.fields[key] = value

