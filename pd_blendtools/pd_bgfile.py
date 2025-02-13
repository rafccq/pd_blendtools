import time

from bytereader import *
from decl_bgfile import *
from typeinfo import TypeInfo

debug_dir = './debug'

ROOMBLOCKTYPE_LEAF = 0
ROOMBLOCKTYPE_PARENT = 1


def log(*args):
    if enableLog:
        print(''.join(args))

def make_header(entries):
    header = bytearray()
    for entry in entries:
        size = TypeInfo.sizeof([entry[0]])
        header += entry[1].to_bytes(size, DEST_BO)

    return header

# adds a header with the size and compressed size, and return the compress the data
def pack(dataout, mask = 1):
    compdata = compress(dataout)
    sec2len = len(dataout)
    compsec2len = len(compdata)

    header = bytearray()
    header += (sec2len & mask).to_bytes(2, byteorder=DEST_BO)
    header += compsec2len.to_bytes(2, byteorder=DEST_BO)
    header += compdata

    return header

class PatchBGFile:
    def __init__(self, bgdata, srcBO = 'big', destBO = 'little'):
        self.bgdata = bgdata
        self.rd = ByteReader(bgdata, srcBO, destBO)

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

    def run(self, name, func):
        s = time.time()
        func()
        log(f'T_{name.ljust(10)}: {time.time() - s:2.5f}')

    def _read(self):
        self.run('filedata', self.load_filedata)
        self.run('primdata', self.read_primarydata)
        self.run('section2', self.read_section2)
        self.run('section3', self.read_section3)
        self.run('gfxdata', self.read_gfxdata)

    def load_filedata(self):
        rd = self.rd

        # header
        primarydatasize = rd.read_primitive('u32')
        section1compsize = rd.read_primitive('u32')
        primcompsize = rd.read_primitive('u32')

        self.offsetgfxdata = primarydatasize - primcompsize - 0xc
        log(f'offsetgfxdata:', f'{self.offsetgfxdata:08X}')

        self.primarydata = decompress(self.bgdata[0xc:0xc + primcompsize])

        # load section 2
        section2start = section1compsize + 0xc
        rd.set_cursor(section2start)
        # log(f'section2start: {section2start:04X}')
        section2inflatedsize = rd.read_primitive('u16')
        section2compsize = rd.read_primitive('u16')
        # section2end = section2start + ((section2compsize - 1) | 0xf) + 1
        section2end = section2start + section2compsize + 4

        log(f'primarydatasize:', f'{primarydatasize:08X}')
        log(f'section1compsize:', f'{section1compsize:08X}')
        log(f'primcompsize:', f'{primcompsize:08X}')
        log(f'section2inflatedsize:', f'{section2inflatedsize:04X}')
        log(f'section2compsize:', f'{section2compsize:04X}')

        log(f'will load section2 at {section2start+4:08X}')
        log(f'section2end: {section2end:08X}')
        # print_bin('primdata:', self.data, section2start+4, 64, 4)
        self.section2 = decompress(self.bgdata[section2start + 4:section2end])
        # print_bin('section2:', self.section2, 0, 64, 4)

        self.numtextures = (section2inflatedsize & 0x7fff) >> 1
        log(f'SECTION2: 0x{section2start:08x}')
        log(f'SECTION1_COMPSIZE: 0x{section1compsize:08X}')
        log(f'SECTION2_COMPSIZE: 0x{section2compsize:08X}')

        # load section 3
        section3start = section2start + section2compsize + 4
        rd.set_cursor(section3start)
        section3inflatedsize = rd.read_primitive('u16')
        section3compsize = rd.read_primitive('u16')
        section3end = section3start + section3compsize + 4
        self.section3 = decompress(self.bgdata[section3start + 4:section3end])
        log(f'SECTION3_COMPSIZE: 0x{section3compsize:08X}')
        log(f'section3inflatedsize:', f'{section3inflatedsize & 0x7fff:08X}')
        # log(f'section3inflatedsize:', f'{len(self.section3):04X}')
        log(f'NUM_TEX=0x{self.numtextures:02X}')

    def read_primarydata(self):
        log('{SECTION1.PRIMARYDATA}')

        rd = self.rd
        rd.set_data(self.primarydata)
        log(f'LEN(PRIMDATA) {len(self.primarydata):08X}')
        # write_file(debug_dir, f'{sys.argv[2]}_prim.bin', self.primarydata)

        header = rd.read_block('primarydata')
        self.primdata_header = header

        rd.print_dict(header, 'primarydata', pad=12, showdec=True, numspaces=4)

        self.read_bgrooms(header)
        self.read_lights()
        self.read_bgcmds()
        self.read_bgportals(header)

        # save the section that contains light data
        offset = header['lightfile'] - 0x0f000000
        # self.lightdata = self.primarydata[offset:]
        self.lightdata = rd.read_block_raw(offset)

        # print('>>LIGHTDATA')
        # print('  len=', len(self.lightdata.bytes))
        # print_bin('  lightdata', self.lightdata.bytes, 0, -1, 1, 16)

    def read_bgrooms(self, header):
        log('{PRIMARYDATA.ROOMS}:')
        rd = self.rd

        rd.set_cursor(header['rooms'] - 0x0f000000)
        # self.read_bgroom()
        # self.rooms[0] = {'id': len(self.primarydata)+0x0f000000}
        room0 = rd.read_block('bgroom')
        # self.rooms[0] = room0
        self.rooms.append(room0)
        # log(f'addr={rd.cursor:04X}')
        rd.print_dict(room0, 'bgroom', pad=15, showdec=True, numspaces=4)
        # self.rooms[0] = {}
        log(f'room #{0:02X}: {0:08X} ------------------------^')
        n = 0
        while True:
            room = rd.read_block('bgroom')
            rd.print_dict(room, 'bgroom', pad=15, showdec=True, numspaces=4)
            roomid = room['unk00']
            if roomid == 0:
                self.rooms.append(room)
                break
            # log(f'room #{n+1:02X}: {roomid:08X} ------------------------^')
            log(f'room #{n+1:02X}: {roomid:08X} ({rd.cursor:04X}) ------------------------^')
            n += 1
            room['id'] = roomid
            room['roomnum'] = n
            # self.rooms[n] = room
            self.rooms.append(room)

        self.numrooms = n

    def read_lights(self):
        rd = self.rd

        header = self.primdata_header
        start = header['lightfile'] - 0xf000000

        if start < 0: return

        rd.set_cursor(start)
        # end = header['bgcmds'] - 0xf000000
        end = header['portals'] - 0xf000000 # x64
        log(f'readlights: cursor={rd.cursor:08X}, end={end:08X}')
        n = 0
        while rd.cursor + 32 < end:
            log(f'light {n:04X}')
            # self.read_light()
            light = rd.read_block('light')
            self.lights.append(light)
            rd.print_dict(light, 'light', pad=15, showdec=True, numspaces=4)
            n += 1

    def read_bgcmds(self):
        rd = self.rd

        log(f'{{PRIMARYDATA.BGCMDS}}: {rd.cursor:08X}')

        # self.cursor = self.offset_bgcmds - 0x0f000000
        # offset = header['portals']
        start = self.primdata_header['bgcmds'] - 0x0f000000
        rd.set_cursor(start)

        n = 0
        while True:
            bgcmd = rd.read_block('bgcmd')
            type = bgcmd['type']
            self.bgcmds.append(bgcmd)

            rd.print_dict(bgcmd, 'bgcmd', pad=15, showdec=True, numspaces=4)
            log(f'cmd #{n:02X}: {type:08X} ------------------------^')
            if type == 0: break

            n += 1

    def read_bgportals(self, header):
        log('{PRIMARYDATA.PORTALS}:')
        rd = self.rd

        start = header['portals']
        # end = start - 0xf000000
        rd.set_cursor(start - 0x0f000000)
        n = 0
        while True:
            # verts = self.read_bgportal()
            portal = rd.read_block('bgportal')
            self.portals.append(portal)

            verts = portal['verticesoffset']

            rd.print_dict(portal, 'bgportal', pad=15, showdec=True, numspaces=4)
            log(f'portal #{n:02X}: {verts:08X} [{rd.cursor:08X}]------------------------^')

            if verts == 0: break
            n += 1

        log(f'numportals: {n:02X}')
        self.read_bgportalvertices()

    def read_bgportalvertices(self):
        rd = self.rd
        # end = len(self.primarydata)

        c = align(rd.cursor, 4)
        rd.set_cursor(c)
        # n = 0
        for n, portal in enumerate(self.portals):
            log(f'portalvertex: {n:02X} [{rd.cursor:08X}]')
            count = rd.peek('u8')
            # rd.declare('portalvertices', decl_portalvertices, vars={'N': count})
            TypeInfo.register('portalvertices', decl_portalvertices, False, varmap={'N': count})
            # vtx = rd.read_block('portalvertices', endmarker=('u8', 0))
            vtx = rd.read_block('portalvertices')
            self.portalvertices.append(vtx)
            # decl = rd.decl_map['portalvertices']
            # rd.print_dict(vtx, 'portalvertices', pad=15, showdec=True, numspaces=4)
            # rd.print_dict(vtx, decl, pad=15, showdec=True, numspaces=4)
        log(f'-- portalvtx [{rd.cursor:08X}] --')

    def read_section2(self):
        log('[SECTION2]')
        rd = self.rd
        rd.set_data(self.section2)
        # self.set_section(self.section2, output='section2')
        for i in range(0, self.numtextures):
            tex = rd.read_primitive('u16')
            self.textures.append(tex)
            rd.print(tex, 's16', f'tex_{i}', pad=15, showdec=True, numspaces=4)

    def read_section3(self):
        log('[SECTION3]')
        rd = self.rd
        rd.set_data(self.section3)

        for r in range(1, self.numrooms):
            log(f'room {r:02X} bbox:')
            bbox = rd.read_block('bbox')
            rd.print_dict(bbox, 'bbox', pad=15, showdec=True, numspaces=4)
            self.bboxes.append(bbox)

        log('[gfxdatalen]')
        for r in range(1, self.numrooms):
            datalen = rd.read_primitive('u16')
            # self.gfxdatalen[r] = datalen
            self.rooms[r]['gfxdatalen'] = datalen
            rd.print(datalen, 'u16', f'gfxdatalen_{r:02X}', pad=15, showdec=True, numspaces=4)

        log('[lights/room]')
        lightindex = 0
        totalights = 0
        for r in range(1, self.numrooms):
            numlights = rd.read_primitive('u8')
            rd.print(numlights, 'u8', f'numlights_{r:02X}', pad=15, showdec=True, numspaces=4)
            self.rooms[r]['numlights'] = numlights

            if numlights > 0:
                self.rooms[r]['lightindex'] = lightindex
                lightindex += numlights
            else:
                self.rooms[r]['lightindex'] = -1

            totalights += numlights

        log(f'totallights: 0x{totalights:04X} ({totalights})')
        log(f'numrooms: 0x{self.numrooms:04X} ({self.numrooms})')

    def read_gfxdata(self):
        for r in range(1, self.numrooms):
            self.load_roomgfxdata(r)

    def load_roomgfxdata(self, roomnum):
        start = self.rooms[roomnum]['id']
        next = self.rooms[roomnum+1]['id']
        complen = (self.rooms[roomnum+1]['id'] - start + 0xf) & ~0xf
        # log(f'___room: {roomnum:02X}')
        gfxdatalen = self.rooms[roomnum]['gfxdatalen'] * 0x10 + 0x100
        gfxdatalencomp = self.rooms[roomnum]['gfxdatalen']
        log(f'$room {roomnum:02X}: s={start:04X} complen={complen:04X} gfxlen={gfxdatalen:04X} ({gfxdatalencomp:04X}) next {next:08X}')

        if start < 0 or gfxdatalen < complen:
            log(f'no gfx data for room {roomnum:04X}')
            # return

        start -= 0x0f000000
        start -= self.offsetgfxdata
        # log(f'start:{start:08X}, len:{gfxdatalen:04X}')
        # print_bin('roomdata', self.bgdata[start:start + complen], 0, 32, 1, 16)

        self.gfxdata[roomnum] = decompress(self.bgdata[start:start + complen])
        self.rooms[roomnum]['prevgfxdatalen'] = len(self.gfxdata)

        log(f'start:{start:08X}, len:{gfxdatalen:04X}, loadedlen:{len(self.gfxdata):04X}')
        # print_bin('gfxdata:', self.data, start - 32, 64+32, 4)
        # write_file(debug_dir, f'gfxdata_room{roomnum:02X}.bin', self.gfxdata)
        self.read_roomgfxdata(roomnum)

    def read_roomgfxdata(self, roomnum):
        rd = self.rd
        room = self.rooms[roomnum]
        roomid = room['id']
        # log(f'{{ROOMGFXDATA}} # {roomnum:04X} {roomid:08X} [{rd.cursor:08X}]')
        log(f'{{ROOMGFXDATA}} # {roomnum:04X}')

        rd.set_data(self.gfxdata[roomnum])
        gfxdata = rd.read_block('roomgfxdata')
        room['gfxdata'] = gfxdata
        rd.print_dict(gfxdata, 'roomgfxdata', pad=15, showdec=True, numspaces=4)

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
        # log(f'  READ_colors: {time.time() - t:2.5f}')

        room['vtx'] = vtxs
        room['colors'] = colors

        # read GDLs
        log(f'ROOM {roomnum:04X} GDLs')
        room['_gdldata'] = {}
        ngdl = len(gdls)
        # make each address relative to the room id
        gdls = list(map(lambda e: e - roomid, gdls))
        gdls.append(None) # add the end marker
        for i in range(0, ngdl):
            start = gdls[i]
            end = gdls[i + 1]
            gdldata = rd.read_block_raw(start, end)
            # room['_gdldata'].append(gdldata)
            if enableLog:
                e = end if end else 0
                log(f'GDL #{i:02} [{start:04X}:{e:04X}]')
                # if sz['pointer'] == 8: printGDL(gdldata.bytes, 2, 'little')
                # else: printGDL_x86(gdldata.bytes, 2)
                printGDL(gdldata.bytes, 2)

            # if start not in room['_gdldata']: room['_gdldata'][start] = []
            room['_gdldata'][start] = gdldata

        log(f'room {roomnum:02X} # GDLS: {ngdl}')

    def read_roomblocks(self, end, roomnum, roomid):
        rd = self.rd

        room = self.rooms[roomnum]
        offset = room['id']
        rd.ofs = offset
        log(f'>blocks [{rd.cursor:08X}] (len {len(self.gfxdata):04X}, offset {self.offsetgfxdata:04X}) end {end:08X}')
        end -= offset
        # log(f'>blocks [{self.cursor:08X}] (len={len(self.section):04X}, end={end:04X})')

        blocks = {}

        gdls = []
        n = 0
        blocksize = 4 * TypeInfo.sizeof('u8') + 4 * TypeInfo.sizeof('pointer')
        while (rd.cursor + blocksize) <= end:
            blockaddr = rd.cursor + offset
            log(f'  .blockaddr={blockaddr:08X}/{blockaddr-self.offset:08X}')
            # log(f'  .blockaddr={blockaddr:08X}/--')

            roomblock = rd.read_block('roomblock')

            rd.print_dict(roomblock, 'roomblock', pad=15, showdec=True, numspaces=4)
            log(f'------ block {n:02X} c={rd.cursor:08X}, end={end:08X}')

            type = roomblock['type']
            verts = roomblock['vertices|coord1']
            verts -= offset
            if type == ROOMBLOCKTYPE_PARENT and verts < end:
                end = verts

            if type == ROOMBLOCKTYPE_PARENT:
                cu = rd.cursor
                addr = roomblock['vertices|coord1']
                rd.set_cursor(addr - roomid)
                coord0 = rd.read_block('coord')
                coord1 = rd.read_block('coord')
                
                roomblock['coord_0'] = coord0
                roomblock['coord_1'] = coord1
                rd.set_cursor(cu)

            if type == ROOMBLOCKTYPE_LEAF:
                gdl = roomblock['gdl|child']
                if gdl != 0: gdls.append(gdl)

            blocks[blockaddr] = roomblock
            n += 1

        room['roomblocks'] = blocks
        rd.ofs = 0
        return gdls

    # currently too slow
    def _read_vertices(self, start, end):
        rd = self.rd
        rd.set_cursor(start)

        vtxs = []
        while rd.cursor < end:
            v = rd.read_block('gfxvtx')
            vtxs.append(v)

        return vtxs

    def read_vertices(self, start, end):
        # savedaddr = self.cursor
        if start == 0: return None

        rd = self.rd

        # self.cursor = start
        vtx = rd.read_block_raw(start, end)

        log(f'[VTXS] [{start:04X}:{end:04X}] (.nvtx {(end-start)//12})')
        if enableLog: print_bin('^VTX', vtx.bytes, 0, 128, 2, 6)

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

            v = (x, y, z, f, c, s, t)
            # log(f'{v[0]:04X}{v[1]:04X} {v[2]:04X}'
            #       f'{v[3]:02X}{v[4]:02X} '
            #       f'{v[5]:04X}{v[6]:04X}'
            # )

            addr += 12

        vtxs = []
        n = 0
        return vtx

    def read_colors(self, start, end):
        # savedaddr = self.cursor
        if start <= 0: return None

        rd = self.rd

        # self.cursor = start
        colors = rd.read_block_raw(start, end)
        # if not colors: print(f'>COLOR NONE! {start:04X}:{end:04X} -------------------')

        log(f'[COLORS] [{start:04X}:{end:04X}] ({end - start:04X})')
        data = colors.bytes

        addr = 0
        end = len(data)
        n = 0
        while addr < end:
            col = int.from_bytes(data[addr:addr+4], 'big')
            # rd.print(col, 'u32', f'color_{n:02X}', pad=15, showdec=True, numspaces=4)
            addr += 4
            n += 1

        return colors

    def patch(self):
        section1 = self.patch_section1()
        section2 = self.patch_section2()
        section3 = self.patch_section3()

        return section1 + section2 + section3

    def patch_gfxdata(self, roomnum, currentoffset):
        rd = self.rd

        dataout = bytearray()
        room = self.rooms[roomnum]

        rd.pointers = []

        offset = (0 if roomnum <= 1 else self.rooms[roomnum - 1]['id']) & 0x00ffffff
        # print(f'NUM: {roomnum}')
        # rd.ofs = (0 if roomnum <= 1 else self.rooms[roomnum - 1]['id'])
        rd.ofs = self.rooms[roomnum]['id']
        rd.ofs_w = currentoffset #+ 0x0F000000
        # print(f'patch {idx}: ', room)
        # print(f'room {roomnum:02X} # vtxs: ', len(room['vtx']))
        # print(f'room {roomnum:02X} ({rd.ofs:02X}) # vtxs: ', len(room['vtx']))
        header = room['gfxdata']

        rd.write_block(dataout, 'roomgfxdata', header)

        s = time.time()
        for block in room['roomblocks']:
            rd.write_block(dataout, 'roomblock', block)
        rd.add_padding(dataout, 8)
        # print(f'  roomblocks: {time.time() - s:2.5f}')

        if roomnum == 27 or True:
            n = len(room['roomblocks'])
            # print(f'  .patch roomblocks cur {len(dataout):04X} .nblocks {n} (+{n*4})')

        for coord in room['blockcoords']:
            rd.write_block(dataout, 'coord', coord)
        rd.add_padding(dataout, 8)

        s = time.time()
        # currently too slow to read vertices this way...
        # for vtx in room['vtx']:
        #     print(vtx)
        #     rd.write_block(dataout, 'gfxvtx', vtx)

        v = header['vertices']
        vtxs = room['vtx']
        colors = room['colors']

        # log(f'>write vtx: {v:08X}')
        # ... instead, we read it as a single block, without changing the byte order
        if vtxs: rd.write_block_raw(dataout, room['vtx'], 8)
        # print(f'  vtx: {time.time() - s:2.5f}')

        s = time.time()
        if colors: rd.write_block_raw(dataout, room['colors'], 8)
        # print(f'  color: {time.time() - s:2.5f}')

        # we need to patch the pointers to vtx/colors manually, because the vtx/colors were
        # read/written as a raw block, so the individual pointers were not registered
        vtxbase_new = room['vtx']['write_addr'] + currentoffset if vtxs else 0  # + 0x0F000000
        vtxbase = header['vertices']

        colorbase_new = room['colors']['write_addr'] + currentoffset if colors else 0 # + 0x0F000000
        colorbase = header['colours']

        # print(f'room {roomnum:02X} >vtx {vtxbase_new:08X} prev {vtxbase:08X}')

        for idx, block in enumerate(room['roomblocks']):
            vtx = block['vertices|coord1']
            if block['type'] != ROOMBLOCKTYPE_LEAF: continue

            if vtx != 0:
                diff = vtx - vtxbase
                vtxnew = vtxbase_new + diff

                OUT_PTR_SIZE = 4
                addr = block['write_addr'] + 4 + 2 * OUT_PTR_SIZE
                # log(f'  room {roomnum:02X}/b{idx:02X} a {addr:04X} .vtx {vtx:08X} vtxnew {vtxnew:08X} base {vtxbase:08X}')

                dataout[addr:addr + OUT_PTR_SIZE] = vtxnew.to_bytes(OUT_PTR_SIZE, DEST_BO)
                # remove the pointer so it won't be patched again later
                rd.pointers.remove(addr)

            # print(f'  room {roomnum:02X}/b{idx:02X} .col {col:08X} colnew {colornew:08X} base {colorbase:08X}')

            col = block['colours']
            if col == 0: continue

            diff = col - colorbase
            colornew = colorbase_new + diff

            addr = block['write_addr'] + 4 + 3 * OUT_PTR_SIZE
            dataout[addr:addr + OUT_PTR_SIZE] = colornew.to_bytes(OUT_PTR_SIZE, DEST_BO)

            # remove the pointer so it won't be patched again later
            rd.pointers.remove(addr)

        # write GDLs data
        for idx, gdldata in enumerate(room['_gdldata']):
            rd.write_block_raw(dataout, gdldata)

        rd.patch_pointers(dataout, 0)
        rd.ofs = 0
        return dataout

    def patch_section1(self):
        rd = self.rd
        primarydata = bytearray(6 * TypeInfo.sizeof('u32'))

        #### primary data
        ofs_rooms = len(primarydata)
        rd.write_block_list(primarydata, 'bgroom', self.rooms, pad=8)

        ofs_lights = len(primarydata)
        rd.write_block_list(primarydata, 'light', self.lights, pad=8)

        ofs_cmds = len(primarydata)
        rd.write_block_list(primarydata, 'bgcmd', self.bgcmds, pad=0)

        ofs_portals = len(primarydata)
        rd.write_block_list(primarydata, 'bgportal', self.portals, pad=0)

        rd.write_block_list(primarydata, 'portalvertices', self.portalvertices, pad=8)

        headers = [-0x0F000000, ofs_rooms, ofs_portals, ofs_cmds, ofs_lights, -0x0F000000]
        addr = 0
        for h in headers:
            primarydata[addr:addr+4] = (h + 0x0F000000).to_bytes(TypeInfo.sizeof('u32'), DEST_BO)
            addr += 4

        primsize = len(primarydata)

        #### patch all gfx data
        gfxdata = bytearray()

        currentoffset = primsize + 0x0f000000
        self.rooms[0]['id'] = 0
        for r in range(1, self.numrooms):
            roomgfxdata = self.patch_gfxdata(r, currentoffset)
            currentgfxdatalen = len(roomgfxdata)
            comp = compress(roomgfxdata)
            complen = len(comp)

            # save the new gfxdatalen into the room obj
            diff = currentgfxdatalen - self.rooms[r]['prevgfxdatalen']
            gfxdatalencomp = self.rooms[r]['gfxdatalen']
            gfxdatalen = gfxdatalencomp * 0x10 + 0x100
            newgfxdatalen = ((gfxdatalen + diff) - 0x100) // 0x10
            self.rooms[r]['gfxdatalen'] = newgfxdatalen
            # log(f'.r {r:02X} prev {gfxdatalencomp:04X} new {newgfxdatalen:04X} '
            #       f'prev {gfxdatalen:04X} new {gfxdatalen + diff:04X} ')

            self.rooms[r]['id'] = currentoffset
            currentoffset += complen
            gfxdata += comp

        # last room is not included in the previous loop, need to patch the id here
        self.rooms[self.numrooms]['id'] = currentoffset

        # now we need to overwrite the room ids in the primarydata
        for r in range(0, self.numrooms+1):
            room = self.rooms[r]
            addr = room['write_addr']
            sz = TypeInfo.sizeof('u32')
            primarydata[addr:addr+sz] = room['id'].to_bytes(sz, DEST_BO)

        # compress the data and write the headers
        primarydata_comp = compress(primarydata)
        primcompsize = len(primarydata_comp)

        section1 = primarydata_comp + gfxdata
        section1size = len(section1)

        header = make_header([
            ('u32', primsize),
            ('u32', section1size),
            ('u32', primcompsize)
        ])

        return header + section1

    def patch_section2(self):
        rd = self.rd
        dataout = bytearray()

        for tex in self.textures:
            rd.write(dataout, tex, 's16')

        return pack(dataout, mask=0x7fff)

    def patch_section3(self):
        rd = self.rd
        dataout = bytearray()

        #### bboxes
        for bbox in self.bboxes:
            rd.write_block(dataout, 'bbox', bbox)

        #### gfxdatalen
        for r in range(1, self.numrooms):
            gfxdatalen = self.rooms[r]['gfxdatalen']
            # log(f'{gfxdatalen:08X}')
            rd.write(dataout, gfxdatalen, 'u16')

        #### lights/room
        for r in range(1, self.numrooms):
            numlights = self.rooms[r]['numlights']
            rd.write(dataout, numlights, 'u8')

        return pack(dataout, 0x7fff)
