import warnings

from bytereader import *
from decl_bgtiles import *
from typeinfo import TypeInfo

warnings.filterwarnings("ignore", category=DeprecationWarning)

class PatchBGTiles:
    def __init__(self, tilesdata):
        self.tilesdata = tilesdata
        self.rd = ByteReader(tilesdata)

        self.tilerooms = []
        self.geos = []
        self._read()

    def _read(self):
        rd = self.rd

        numrooms = rd.read_primitive('u32')

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

            if rd.cursor >= self.tilerooms[room]:
                room += 1

            if geotype == GEOTYPE_TILE_I:
                TypeInfo.register('geotilei', decl_geotilei, varmap={'N': numvtx})
                geo = rd.read_block('geotilei')
            elif geotype == GEOTYPE_TILE_F:
                TypeInfo.register('geotilef', decl_geotilei, varmap={'N': numvtx})
                geo = rd.read_block('geotilef')
            elif geotype == GEOTYPE_BLOCK:
                geo = rd.read_block('geoblock')
            elif geotype == GEOTYPE_CYL:
                geo = rd.read_block('geocyl')
            else:
                break

            geo['room'] = room-1
            self.geos.append(geo)
            i += 1
