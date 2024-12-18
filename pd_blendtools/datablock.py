from typeinfo import TypeInfo

class DataBlock:
    def __init__(self, name, addr, data = None):
        self.name = name
        self.addr = addr
        self.write_addr = None
        self.fields = {}
        self.field_infos = {}
        self.bytes = data

    def add_field(self, info, value):
        self.fields[info['fieldname']] = value
        self.field_infos[info['fieldname']] = info

    # updates the value of 'field' and also serialize it to dataout
    def update(self, dataout, field, value):
        self[field] = value
        info = self.field_infos[field]
        typename = info['typename']

        size = TypeInfo.sizeof(typename)
        offset = TypeInfo.offsetof(self.name, field)
        addr = self.write_addr + offset

        dataout[addr:addr + size] = value.to_bytes(size, 'big') # TODO config

    def __getitem__(self, key):
        return self.fields[key]

    def __setitem__(self, key, value):
        self.fields[key] = value

    def __repr__(self):
        return str(self.fields)

