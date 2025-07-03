import time

from data.bytestream import ByteStream
from .decl_bgfile import *
from data.typeinfo import TypeInfo
from utils import pd_utils as pdu


ROOMBLOCKTYPE_LEAF = 0
ROOMBLOCKTYPE_PARENT = 1


class PD_BGFile:
    def __init__(self, bgdata):
        self.bgdata = bgdata
        self.bs = ByteStream(bgdata)

        self.gfxdata = {}

        self.textures = []
        self.rooms = []
        self.lights = []
        self.bgcmds = []
        self.portals = []
        self.portalvertices = []
        self.bboxes = []
        self.gfxdatalen = {}
        self.blocks = {}

        self._read()

    def _read(self):
        self.load_filedata()
        self.read_primarydata()
        self.read_section2()
        self.read_section3()
        self.read_gfxdata()

    def load_filedata(self):
        bs = self.bs

        # header
        primarydatasize = bs.read_primitive('u32')
        section1compsize = bs.read_primitive('u32')
        primcompsize = bs.read_primitive('u32')

        self.offsetgfxdata = primarydatasize - primcompsize - 0xc

        self.primarydata = pdu.decompress(self.bgdata[0xc:0xc + primcompsize])

        # load section 2
        section2start = section1compsize + 0xc
        bs.set_cursor(section2start)
        section2inflatedsize = bs.read_primitive('u16')
        section2compsize = bs.read_primitive('u16')
        section2end = section2start + section2compsize + 4

        self.section2 = pdu.decompress(self.bgdata[section2start + 4:section2end])

        self.numtextures = (section2inflatedsize & 0x7fff) >> 1

        # load section 3
        section3start = section2start + section2compsize + 4
        bs.set_cursor(section3start)
        section3inflatedsize = bs.read_primitive('u16')
        section3compsize = bs.read_primitive('u16')
        section3end = section3start + section3compsize + 4
        self.section3 = pdu.decompress(self.bgdata[section3start + 4:section3end])

    def read_primarydata(self):
        bs = self.bs
        bs.set_data(self.primarydata)

        header = bs.read_block('primarydata')
        self.primdata_header = header

        self.read_bgrooms(header)
        self.read_lights()
        self.read_bgcmds()
        self.read_bgportals(header)

        # save the section that contains light data
        offset = header['lightfile'] - 0x0f000000
        self.lightdata = bs.read_block_raw(offset)

    def read_bgrooms(self, header):
        bs = self.bs

        bs.set_cursor(header['rooms'] - 0x0f000000)
        room0 = bs.read_block('bgroom')
        self.rooms.append(room0)
        n = 0
        while True:
            room = bs.read_block('bgroom')
            roomid = room['unk00']
            if roomid == 0:
                self.rooms.append(room)
                break
            n += 1
            room['id'] = roomid
            room['roomnum'] = n
            self.rooms.append(room)

        self.numrooms = n

    def read_lights(self):
        bs = self.bs

        header = self.primdata_header
        start = header['lightfile'] - 0xf000000

        if start < 0: return

        bs.set_cursor(start)
        end = header['portals'] - 0xf000000 # x64
        n = 0
        while bs.cursor + 32 < end:
            light = bs.read_block('light')
            self.lights.append(light)
            n += 1

    def read_bgcmds(self):
        bs = self.bs

        start = self.primdata_header['bgcmds'] - 0x0f000000
        bs.set_cursor(start)

        n = 0
        while True:
            bgcmd = bs.read_block('bgcmd')
            type = bgcmd['type']
            self.bgcmds.append(bgcmd)

            if type == 0: break
            n += 1

    def read_bgportals(self, header):
        bs = self.bs

        start = header['portals']
        bs.set_cursor(start - 0x0f000000)
        n = 0
        while True:
            portal = bs.read_block('bgportal')
            self.portals.append(portal)

            verts = portal['verticesoffset']

            if verts == 0: break
            n += 1

        self.read_bgportalvertices()

    def read_bgportalvertices(self):
        bs = self.bs

        c = pdu.align(bs.cursor, 4)
        bs.set_cursor(c)
        for n, portal in enumerate(self.portals):
            count = bs.peek('u8')
            TypeInfo.register('portalvertices', decl_portalvertices, False, varmap={'N': count})
            vtx = bs.read_block('portalvertices')
            self.portalvertices.append(vtx)

    def read_section2(self):
        bs = self.bs
        bs.set_data(self.section2)
        for i in range(0, self.numtextures):
            tex = bs.read_primitive('u16')
            self.textures.append(tex)

    def read_section3(self):
        bs = self.bs
        bs.set_data(self.section3)

        for r in range(1, self.numrooms):
            bbox = bs.read_block('bbox')
            self.bboxes.append(bbox)

        for r in range(1, self.numrooms):
            datalen = bs.read_primitive('u16')
            self.rooms[r]['gfxdatalen'] = datalen

        lightindex = 0
        totalights = 0
        for r in range(1, self.numrooms):
            numlights = bs.read_primitive('u8')
            self.rooms[r]['numlights'] = numlights

            if numlights > 0:
                self.rooms[r]['lightindex'] = lightindex
                lightindex += numlights
            else:
                self.rooms[r]['lightindex'] = -1

            totalights += numlights

    def read_gfxdata(self):
        for r in range(1, self.numrooms):
            self.load_roomgfxdata(r)

    def load_roomgfxdata(self, roomnum):
        start = self.rooms[roomnum]['id']
        next = self.rooms[roomnum+1]['id']
        complen = (self.rooms[roomnum+1]['id'] - start + 0xf) & ~0xf
        gfxdatalen = self.rooms[roomnum]['gfxdatalen'] * 0x10 + 0x100
        gfxdatalencomp = self.rooms[roomnum]['gfxdatalen']

        if start < 0 or gfxdatalen < complen:
            print(f'no gfx data for room {roomnum:04X}')

        start -= 0x0f000000
        start -= self.offsetgfxdata

        self.gfxdata[roomnum] = pdu.decompress(self.bgdata[start:start + complen])
        self.rooms[roomnum]['prevgfxdatalen'] = len(self.gfxdata)
        self.read_roomgfxdata(roomnum)

    def read_roomgfxdata(self, roomnum):
        bs = self.bs
        room = self.rooms[roomnum]
        roomid = room['id']

        bs.set_data(self.gfxdata[roomnum])
        gfxdata = bs.read_block('roomgfxdata')
        room['gfxdata'] = gfxdata

        verts_addr = gfxdata['vertices']
        colors_addr = gfxdata['colours']
        opa = gfxdata['opablocks']
        xlu = gfxdata['xlublocks']

        self.offset = roomid
        gdls = self.read_roomblocks(verts_addr, roomnum, roomid)
        vtxs = self.read_vertices(verts_addr - roomid, colors_addr - roomid)

        t = time.time()
        firstgdl = gdls[0] if len (gdls) > 0 else -1
        colors = self.read_colors(colors_addr - roomid, firstgdl - roomid)

        room['vtx'] = vtxs
        room['colors'] = colors

        # read GDLs
        room['_gdldata'] = {}
        ngdl = len(gdls)

        # make each address relative to the room id
        gdls = list(map(lambda e: e - roomid, gdls))
        gdls.append(None) # add the end marker
        for i in range(0, ngdl):
            start = gdls[i]
            end = gdls[i + 1]
            gdldata = bs.read_block_raw(start, end)
            room['_gdldata'][start] = gdldata

    def read_roomblocks(self, end, roomnum, roomid):
        bs = self.bs

        room = self.rooms[roomnum]
        offset = room['id']
        bs.ofs = offset
        end -= offset

        blocks = {}

        gdls = []
        n = 0
        blocksize = 4 * TypeInfo.sizeof('u8') + 4 * TypeInfo.sizeof('pointer')
        while (bs.cursor + blocksize) <= end:
            blockaddr = bs.cursor + offset
            roomblock = bs.read_block('roomblock')

            type = roomblock['type']
            verts = roomblock['vertices|coord1']
            verts -= offset
            if type == ROOMBLOCKTYPE_PARENT and verts < end:
                end = verts

            if type == ROOMBLOCKTYPE_PARENT:
                cu = bs.cursor
                addr = roomblock['vertices|coord1']
                bs.set_cursor(addr - roomid)
                coord0 = bs.read_block('coord')
                coord1 = bs.read_block('coord')
                
                roomblock['coord_0'] = coord0
                roomblock['coord_1'] = coord1
                bs.set_cursor(cu)

            if type == ROOMBLOCKTYPE_LEAF:
                gdl = roomblock['gdl|child']
                if gdl != 0: gdls.append(gdl)

            blocks[blockaddr] = roomblock
            n += 1

        room['roomblocks'] = blocks
        bs.ofs = 0
        return gdls

    def read_vertices(self, start, end):
        if start == 0: return None

        bs = self.bs

        vtx = bs.read_block_raw(start, end)
        data = vtx.bytes

        addr = 0
        end = len(data)
        while addr < end:
            x = int.from_bytes(data[addr:addr+2], 'big')
            y = int.from_bytes(data[addr+2:addr+4], 'big')
            z = int.from_bytes(data[addr+4:addr+6], 'big')

            f = int.from_bytes(data[addr+6:addr+7], 'big')
            c = int.from_bytes(data[addr+7:addr+8], 'big')

            s = int.from_bytes(data[addr+8:addr+10], 'big')
            t = int.from_bytes(data[addr+10:addr+12], 'big')

            addr += 12

        vtxs = []
        n = 0
        return vtx

    def read_colors(self, start, end):
        if start <= 0: return None

        bs = self.bs

        colors = bs.read_block_raw(start, end)
        data = colors.bytes

        addr = 0
        end = len(data)
        n = 0
        while addr < end:
            col = int.from_bytes(data[addr:addr+4], 'big')
            addr += 4
            n += 1

        return colors
