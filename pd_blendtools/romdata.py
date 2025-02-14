import pd_utils as pdu
import pd_addonprefs as pdp


class Romdata:
    def __init__(self, filename):
        fd = open(filename, 'rb')
        self.rom = fd.read()
        fd.close()

        self.romid = 'ntsc-final'

        dataofs = self.section_ofs('data')
        self.data = pdu.decompress(self.rom[dataofs:])

        self.fileoffsets = {}
        self.filenames = []
        self.texoffsets = {}

        self.read_files()
        self.read_textures()

    def read_files(self):
        offsets_list = self.get_file_offsets()
        self.filenames = self.get_file_names(offsets_list[-1])

        for (index, offset) in enumerate(offsets_list):
            if index == 0:
                continue
            try:
                endoffset = offsets_list[index + 1]
            except:
                break

            name = self.filenames[index]
            self.fileoffsets[name] = (offset, endoffset)

    def filedata(self, modelname):
        ofs = self.fileoffsets[modelname]
        data = self.rom[ofs[0]:ofs[1]]
        return pdu.decompress(data) if data[0:2] == b'\x11\x73' else data

    def texturedata(self, texnum):
        ofs = self.texoffsets[texnum]
        return self.rom[ofs[0]:ofs[1]]

    def read_textures(self):
        base = self.section_ofs('textures')
        datalen = 0x294960 if self.romid == 'jpn-final' else 0x291d60
        tablepos = base + datalen
        index = 0
        while True:
            start = int.from_bytes(self.rom[tablepos+1:tablepos+4], 'big')
            end = int.from_bytes(self.rom[tablepos+9:tablepos+12], 'big')
            if int.from_bytes(self.rom[tablepos+12:tablepos+16], 'big') != 0:
                break
            self.texoffsets[index] = (base + start, base + end)
            index += 1
            tablepos += 8

    def get_file_offsets(self):
        i = self.section_ofs('files')
        offsets = []
        while True:
            offset = int.from_bytes(self.data[i:i+4], 'big')
            if offset == 0 and len(offsets):
                return offsets
            offsets.append(offset)
            i += 4

    def get_file_names(self, tableaddr):
        i = tableaddr
        names = []
        while True:
            offset = int.from_bytes(self.rom[i:i+4], 'big')
            if offset == 0 and len(names):
                return names
            names.append(self.read_name(tableaddr + offset))
            i += 4

    def read_name(self, address):
        nullpos = self.rom[address:].index(0)
        return str(self.rom[address:address + nullpos], 'utf-8')

    def section_ofs(self, section):
        romid = self.romid
        index = ['ntsc-final','pal-final','jpn-final'].index(romid)
        return section_offsets[section][index]

section_offsets = {
    #                 ntsc-final pal-final  jpn-final
    'files':         [0x28080,   0x28910,   0x28800,   ],
    'data':          [0x39850,   0x39850,   0x39850,   ],
    'mpconfigs':     [0x7d0a40,  0x7bc240,  0x7c00d0,  ],
    'textureconfig': [0x7eb270,  0x7d6a70,  0x7da900,  ],
    'textures':      [0x1d65f40, 0x1d5ca20, 0x1d61f90, ],
}

def load(filename=None):
    if not filename:
        filename = pdp.pref_get(pdp.PD_PREF_ROMPATH)
    return Romdata(filename)
