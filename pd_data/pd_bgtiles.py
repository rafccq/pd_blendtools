import warnings

from data.bytestream import ByteStream
from .decl_bgtiles import *
from data.typeinfo import TypeInfo

warnings.filterwarnings("ignore", category=DeprecationWarning)

class PD_TilesFile:
    def __init__(self, tilesdata):
        self.tilesdata = tilesdata
        self.bs = ByteStream(tilesdata)

        self.tilerooms = []
        self.geos = []
        self._read()

    def _read(self):
        bs = self.bs

        numrooms = bs.read_primitive('u32')

        for i in range(0, numrooms+1):
            room = bs.read_primitive('u32')
            self.tilerooms.append(room)

        end = self.tilerooms[numrooms]

        bs.set_cursor(self.tilerooms[0])

        self.geos = []
        i = 0
        room = 1
        while bs.cursor < end:
            geotype, numvtx = bs.peek('u8', 2)

            if bs.cursor >= self.tilerooms[room]:
                room += 1

            if geotype == GEOTYPE_TILE_I:
                TypeInfo.register('geotilei', decl_geotilei, varmap={'N': numvtx})
                geo = bs.read_block('geotilei')
            elif geotype == GEOTYPE_TILE_F:
                TypeInfo.register('geotilef', decl_geotilei, varmap={'N': numvtx})
                geo = bs.read_block('geotilef')
            elif geotype == GEOTYPE_BLOCK:
                geo = bs.read_block('geoblock')
            elif geotype == GEOTYPE_CYL:
                geo = bs.read_block('geocyl')
            else:
                break

            geo['room'] = room-1
            self.geos.append(geo)
            i += 1
