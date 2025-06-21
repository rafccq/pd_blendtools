from collections import namedtuple

from bytereader import *
from decl_padsfile import *
from typeinfo import TypeInfo
import pd_utils as pdu


def log(*args):
    if enableLog:
        print(''.join(args))

Vec3 = namedtuple('Vec3', 'x y z')
Bbox = namedtuple('Bbox', 'xmin xmax ymin ymax zmin zmax')
Pad = namedtuple('Pad', 'pos look up normal bbox header')


class Pad_:
    def __init__(self, pos, look = (0,0,0), up = (0,0,0), bbox = (0,0,0,0,0,0)):
        self.pos = pos
        self.look = look
        self.up = up
        self.bbox = bbox
        self.normal = Vec3(0, 0, 0)

        self.calculate_normal()

    def calculate_normal(self):
        nx = self.up.y * self.look.z - self.look.y * self.up.z
        ny = self.up.z * self.look.x - self.look.z * self.up.x
        nz = self.up.x * self.look.y - self.look.x * self.up.y

        self.normal = Vec3(nx, ny, nz)


class PD_PadsFile:
    def __init__(self, padsfiledata, srcBO = 'big', destBO = 'little'):
        self.padsfiledata = padsfiledata
        self.rd = ByteReader(padsfiledata, srcBO, destBO)

        self.paddata = []
        self.padindices = [] # index of each pad into paddata
        self.covers = []
        self.waypoints = []
        self.waygroups = []

        self._read()

    def _read(self):
        rd = self.rd

        numpads = rd.peek('u32')

        TypeInfo.register('padsfileheader', decl_padsfileheader, varmap={'N': numpads})
        self.header = header = rd.read_block('padsfileheader')

        # log(f'{{PADDATA}} [{rd.cursor:04X}]')
        for i in range(0, numpads):
            ofs = header['padoffsets']
            size = ofs[i+1] - ofs[i] if i + 1 < numpads and ofs[i + 1] else 0x40
            self.read_paddata(ofs[i], size)

        self.read_waypoints()
        self.read_waygroups()
        self.read_covers()

    curpad = 0
    def read_paddata(self, offset, size):
        rd = self.rd

        self.padindices.append(len(self.paddata))

        def read_coords(typename, num):
            fieldsmap = {
                1: ['_pad_'],
                3: ['x', 'y', 'z'],
                6: ['minx', 'miny', 'minz', 'maxx', 'maxy', 'maxz']
            }

            fields = fieldsmap[num] if num in fieldsmap else None

            for i in range(0, num):
                val = rd.read_primitive(typename)
                rd.print(val, typename, fields[i] if fields else '_pad_', pad=6, numspaces=2)
                self.paddata.append((typename, val))

        rd.set_cursor(offset)
        end = rd.cursor + size
        header = rd.read_primitive('u32')
        self.paddata.append(('u32', header))

        flags = header >> 14

        log(f'pad #{self.curpad:04X} f {header:08X} sz {size:02X} [{offset:04X}]')

        self.curpad += 1
        if (flags & PADFLAG_INTPOS) or size <= 12:
            read_coords('s16', 3)
            read_coords('s16', 1)
        else:
            read_coords('f32', 3)

        if not (flags & (PADFLAG_UPALIGNTOX | PADFLAG_UPALIGNTOY | PADFLAG_UPALIGNTOZ)) and end >= rd.cursor + 12:
            read_coords('f32', 3)

        if not (flags & (PADFLAG_LOOKALIGNTOX | PADFLAG_LOOKALIGNTOY | PADFLAG_LOOKALIGNTOZ)) and end >= rd.cursor + 12:
            read_coords('f32', 3)

        if (flags & PADFLAG_HASBBOXDATA) and end >= rd.cursor + 24:
            read_coords('f32', 6)

    def read_covers(self):
        rd = self.rd

        log(f'{{COVERS}} [{rd.cursor:04X}]')

        header = self.header
        ofs = header['coversoffset']

        rd.set_cursor(ofs)

        n = header['numcovers']
        for i in range(0, n):
            cover = rd.read_block('cover')
            # rd.print_dict(cover, 'coverdefinition', pad=16, numspaces=2)
            self.covers.append(cover)

    def read_waypoints(self):
        rd = self.rd

        # log(f'{{WAYPOINTS}} [{rd.cursor:04X}]')

        header = self.header
        ofs = header['waypointsoffset']

        rd.set_cursor(ofs)

        while True:
            # log(f'[{rd.cursor:04X}]')
            wp = rd.read_block('waypoint')
            self.waypoints.append(wp)
            wp['neighbours_list'] = []

            # rd.print_dict(wp, 'waypoint', pad=16, numspaces=2)

            if wp['padnum'] == 0xffffffff: break

            savedcur = rd.cursor
            rd.set_cursor(wp['neighbours'])

            log(f'  neighbours:')
            while True:
                cur = rd.cursor
                block = rd.read_block('arrays32')
                wp['neighbours_list'].append(block)

                neighbour = block['value']
                log(f'    {neighbour:08X} [{cur:08X}]')
                # rd.print_dict(wp, decl, pad=16, numspaces=2)
                if neighbour == 0xffffffff: break

            rd.set_cursor(savedcur)

    def read_waygroups(self):
        rd = self.rd

        # log(f'{{WAYGROUPS}} [{rd.cursor:04X}]')

        header = self.header
        ofs = header['waygroupsoffset']

        rd.set_cursor(ofs)

        while True:
            # log(f'[{rd.cursor:04X}]')
            wg = rd.read_block('waygroup')
            self.waygroups.append(wg)
            wg['neighbours_list'] = []
            wg['waypoints_list'] = []

            # rd.print_dict(wg, 'waygroup', pad=16, numspaces=2)

            if wg['neighbours'] == 0: break

            savedcur = rd.cursor

            # waygroup neighbours
            rd.set_cursor(wg['neighbours'])

            # log(f'  neighbours:')
            while True:
                cur = rd.cursor
                # read it as a block, so pointers to it will be patched later
                block = rd.read_block('arrays32')
                wg['neighbours_list'].append(block)
                neighbour = block['value']

                # log(f'    {neighbour:08X} [{cur:08X}]')
                if neighbour == 0xffffffff: break

            # waygroup waypoints
            rd.set_cursor(wg['waypoints'])
            log(f'  waypoints:')
            while True:
                cur = rd.cursor
                # read it as a block, so pointers to it will be patched later
                block = rd.read_block('arrays32')
                wg['waypoints_list'].append(block)
                wg_waypoint = block['value']

                log(f'    {wg_waypoint:08X} [{cur:08X}]')
                if wg_waypoint == 0xffffffff: break

            rd.set_cursor(savedcur)

    def patch(self):
        rd = self.rd

        numpads = self.header['numpads']
        headersz = 5 * sz['s32'] + numpads * sz['s16']
        rd.pointers = []

        log('<PATCH>')
        # -------- pad data
        dataout = bytearray(headersz)
        rd.add_padding(dataout, 4)

        i = 0
        for (type, val) in self.paddata:
            # log(f'{type} {val}')
            log(f'offset #{i:03d}: {len(dataout):04X}')
            rd.write(dataout, val, type)
            i += 1

        # -------- waypoints
        ofs_waypoints = 0
        for wp in self.waypoints:
            rd.write_block(dataout, 'waypoint', wp)
            ofs_waypoints = wp['write_addr'] if not ofs_waypoints else ofs_waypoints

        # neighbor data
        for wp in self.waypoints:
            neighbours = wp['neighbours_list']
            for nbr in neighbours:
                rd.write_block(dataout, 'arrays32', nbr)

        # -------- waygroups
        ofs_waygroups = 0
        for wg in self.waygroups:
            rd.write_block(dataout, 'waygroup', wg)
            ofs_waygroups = wg['write_addr'] if not ofs_waygroups else ofs_waygroups

        for wg in self.waygroups:
            neighbours = wg['neighbours_list']
            for nbr in neighbours:
                rd.write_block(dataout, 'arrays32', nbr)

        for wg in self.waygroups:
            wg_waypoints = wg['waypoints_list']
            for waypoint in wg_waypoints:
                rd.write_block(dataout, 'arrays32', waypoint)

        # -------- covers
        ofs_covers = 0
        for cover in self.covers:
            rd.write_block(dataout, 'coverdefinition', cover)
            ofs_covers = cover['write_addr'] if not ofs_covers else ofs_covers

        rd.patch_pointers(dataout, mask=0)

        self.header['waypointsoffset'] = ofs_waypoints # if ofs_waypoints else 0
        self.header['waygroupsoffset'] = ofs_waygroups # if ofs_waygroups else 0
        self.header['coversoffset'] = ofs_covers # if ofs_covers else 0

        header = bytearray()
        rd.set_data(header)
        # print(self.header)
        rd.write_block(header, 'padsfileheader', self.header)

        dataout[:headersz] = header

        return dataout

    @cache
    def pad_unpack(self, padnum, fields):
        if padnum == 0xffff:
            return None

        # padoffset = self.header['padoffsets'][padnum]
        # print(f'ofs {padoffset:04X}')

        padidx = self.padindices[padnum]
        header = self.paddata[padidx]

        flags = header[1] >> 14

        # log(f'pad #{self.curpad:04X} f {header:08X} sz {size:02X} [{offset:04X}]')

        pos, up, look, bbox = Vec3(0,0,0), Vec3(0,0,0), Vec3(0,0,0), Bbox(*[0]*6)
        normal = Vec3(0,0,0)

        idx = padidx + 1
        if flags & PADFLAG_INTPOS:
            if fields & PADFIELD_POS:
                pos = Vec3(*[pdu.s16(self.paddata[i][1]) for i in range(idx, idx+3)])
            idx += 4
        elif fields & PADFIELD_POS:
            pos = Vec3(*[pdu.f32(self.paddata[i][1]) for i in range(idx, idx+3)])
            idx += 3

        if flags & (PADFLAG_UPALIGNTOX | PADFLAG_UPALIGNTOY | PADFLAG_UPALIGNTOZ):
            if fields & (PADFIELD_UP | PADFIELD_NORMAL):
                if flags & PADFLAG_UPALIGNTOX:
                    x = -1 if flags & PADFLAG_UPALIGNINVERT else 1
                    y, z = 0, 0
                elif flags & PADFLAG_UPALIGNTOY:
                    y = -1 if flags & PADFLAG_UPALIGNINVERT else 1
                    x, z = 0, 0
                else:
                    z = -1 if flags & PADFLAG_UPALIGNINVERT else 1
                    x, y = 0, 0
                up = Vec3(x, y, z)
        else:
            if fields & (PADFIELD_UP | PADFIELD_NORMAL):
                up = Vec3(*[pdu.f32(self.paddata[i][1]) for i in range(idx, idx+3)])
            idx += 3

        if flags & (PADFLAG_LOOKALIGNTOX | PADFLAG_LOOKALIGNTOY | PADFLAG_LOOKALIGNTOZ):
            if fields & (PADFIELD_LOOK | PADFIELD_NORMAL):
                if flags & PADFLAG_LOOKALIGNTOX:
                    x = -1 if flags & PADFLAG_LOOKALIGNINVERT else 1
                    y, z = 0, 0
                elif flags & PADFLAG_LOOKALIGNTOY:
                    y = -1 if flags & PADFLAG_LOOKALIGNINVERT else 1
                    x, z = 0, 0
                else:
                    z = -1 if flags & PADFLAG_LOOKALIGNINVERT else 1
                    x, y = 0, 0
                look = Vec3(x, y, z)
        else:
            if fields & (PADFIELD_LOOK | PADFIELD_NORMAL):
                look = Vec3(*[pdu.f32(self.paddata[i][1]) for i in range(idx, idx+3)])
            idx += 3

        if fields & PADFIELD_NORMAL:
            nx = up.y * look.z - look.y * up.z
            ny = up.z * look.x - look.z * up.x
            nz = up.x * look.y - look.x * up.y
            normal = Vec3(nx, ny, nz)

        if flags & PADFLAG_HASBBOXDATA:
            if fields & PADFIELD_BBOX:
                bbox = Bbox(*[pdu.f32(self.paddata[i][1]) for i in range(idx, idx+6)])
        elif fields & PADFIELD_BBOX:
            bbox = Bbox(-100, 100, -100, 100, 100, 100)

        return Pad(pos, look, up, normal, bbox, header[1])

    def pad_flags(self, padnum):
        padidx = self.padindices[padnum]
        header = self.paddata[padidx]

        return header[1] >> 14

    def pad_hasbbox(self, padnum):
        flags = self.pad_flags(padnum)
        return bool(flags & PADFLAG_HASBBOXDATA)

def pad_center(pad):
    x = pad.pos.x + (
            (pad.bbox.xmin + pad.bbox.xmax) * pad.normal.x +
            (pad.bbox.ymin + pad.bbox.ymax) * pad.up.x +
            (pad.bbox.zmin + pad.bbox.zmax) * pad.look.x) * 0.5

    y = pad.pos.y + (
            (pad.bbox.xmin + pad.bbox.xmax) * pad.normal.y +
            (pad.bbox.ymin + pad.bbox.ymax) * pad.up.y +
            (pad.bbox.zmin + pad.bbox.zmax) * pad.look.y) * 0.5

    z = pad.pos.z + (
            (pad.bbox.xmin + pad.bbox.xmax) * pad.normal.z +
            (pad.bbox.ymin + pad.bbox.ymax) * pad.up.z +
            (pad.bbox.zmin + pad.bbox.zmax) * pad.look.z) * 0.5

    return Vec3(x, y, z)

def pad_pos(center, bbox, look, up, normal):
    px = center.x - (
            (bbox.xmin + bbox.xmax) * normal.x +
            (bbox.ymin + bbox.ymax) * up.x +
            (bbox.zmin + bbox.zmax) * look.x) * 0.5

    py = center.y - (
            (bbox.xmin + bbox.xmax) * normal.y +
            (bbox.ymin + bbox.ymax) * up.y +
            (bbox.zmin + bbox.zmax) * look.y) * 0.5

    pz = center.z - (
            (bbox.xmin + bbox.xmax) * normal.z +
            (bbox.ymin + bbox.ymax) * up.z +
            (bbox.zmin + bbox.zmax) * look.z) * 0.5

    return Vec3(px, py, pz)

def pad_room(pad):
    return (pad.header & 0x3ff0) >> 4

def pad_lift(pad):
    return pad.header & 0xf

def pad_flags(pad):
    return pad.header >> 14

def pad_hasbbox(pad):
    flags = pad_flags(pad)
    return bool(flags & PADFLAG_HASBBOXDATA)

def pad_makeheader(flags, room, lift):
    return (flags << 14) | (room << 4) | lift

