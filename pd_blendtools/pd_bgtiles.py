import numpy as np
import warnings

from bytereader import *
from decl_bgtiles import *
from typeinfo import TypeInfo

# enablelog = False
enablelog = True

warnings.filterwarnings("ignore", category=DeprecationWarning)

def log(*args):
    if enablelog:
        print(''.join(args))

def skip(rd, n):
    for i in range(n):
        v = rd.read_primitive('u8')
        # rd.print(v, 'u8', f'skip', pad=15, showdec=True, numspaces=4)

geotypes = {
    GEOTYPE_TILE_I: 'GEOTYPE_TILE_I',
    GEOTYPE_TILE_F: 'GEOTYPE_TILE_F',
    GEOTYPE_BLOCK: 'GEOTYPE_BLOCK',
    GEOTYPE_CYL: 'GEOTYPE_CYL',
}

class PatchBGTiles:
    def __init__(self, tilesdata, srcBO = 'big', destBO = 'little'):
        self.tilesdata = tilesdata
        rd = self.rd = ByteReader(tilesdata, srcBO, destBO)

        self.tilerooms = []
        self.geos = []
        self._read()

    def _read(self):
        rd = self.rd

        numrooms = rd.read_primitive('u32')

        log(f'numrooms: {numrooms:04X} ({numrooms:03})')

        for i in range(0, numrooms+1):
            room = rd.read_primitive('u32')
            self.tilerooms.append(room)

        end = self.tilerooms[numrooms]

        rd.set_cursor(self.tilerooms[0])

        self.geos = []
        i = 0
        room = 1
        while rd.cursor < end:
            geotype, numvtx = rd.peek('u8', 2)

            # log(f'  geo # {i:04X} t {geotype:02X} ({geotypes[geotype]}) n {numvtx:04d} R {room:02X} [{rd.cursor:04X}]')
            if rd.cursor > self.tilerooms[room]:
                room += 1
            # log(f'  geo # {i:04X} t {geotype:02X} ({geotypes[geotype]}) n {numvtx:04d}')

            decl = ''
            if geotype == GEOTYPE_TILE_I:
                TypeInfo.register('geotilei', decl_geotilei, varmap={'N': numvtx})
                geo = rd.read_block('geotilei')
                decl = 'geotilei'
                for v in range(0, numvtx*3, 3):
                    x = geo['vertices'][v]
                    y = geo['vertices'][v+1]
                    z = geo['vertices'][v+2]

                    x = np.int16(x)
                    y = np.int16(y)
                    z = np.int16(z)

                    xmin, xmax = geo['xmin']*6+14, geo['xmax']*6+14
                    ymin, ymax = geo['ymin']*6+16, geo['ymax']*6+16
                    zmin, zmax = geo['zmin']*6+18, geo['zmax']*6+18
                    # print(f'  {x:.3f} {y:.3f} {z:.3f} bbox ({xmin} {xmax} {ymin} {ymax} {zmin} {zmax})')
            elif geotype == GEOTYPE_TILE_F:
                TypeInfo.register('geotilef', decl_geotilei, varmap={'N': numvtx})
                geo = rd.read_block('geotilef')
            elif geotype == GEOTYPE_BLOCK:
                geo = rd.read_block('geoblock')
            elif geotype == GEOTYPE_CYL:
                geo = rd.read_block('geocyl')
            else:
                log(f'WARNING: wrong geo geotype {geotype:02X}')
                break

            self.geos.append(geo)
            i += 1

    def patch(self):
        rd = self.rd
        dataout = bytearray()

        return dataout
