from data.bytestream import ByteStream
from .decl_setupfile import *
from data.typeinfo import TypeInfo


class PD_SetupFile:
    def __init__(self, setupdata):
        self.bs = ByteStream(setupdata)

        self.props = []
        self.introcmds = []
        self.paths = []
        self.pads = []
        self.ailists = []
        self.lists = []
        self.headers = None

        self.read()

    def read(self):
        self.headers = self.bs.read_block('stagesetup')

        self.read_objs()
        self.read_intro()
        self.read_paths()
        self.read_pads()
        self.read_ailists()
        self.read_lists()

    def obj_type(self):
        header = self.bs.peek('u8', 4)
        return header[3] if header[3] != 0 else header[0]

    def read_objs(self):
        bs = self.bs
        bs.set_cursor(self.headers['props'])

        type = self.obj_type()
        n = 1

        while type != 0x34:
            name = OBJ_NAMES[type]
            obj = bs.read_block(type)
            obj['_type_'] = type

            self.props.append(obj)

            type = self.obj_type()
            n += 1

        obj = bs.read_block('obj_header')
        obj['_type_'] = ENDMARKER_PROPS
        self.props.append(obj)

    def read_intro(self):
        bs = self.bs

        bs.set_cursor(self.headers['intro'])

        i = 0
        cmd = bs.peek('s32')
        s = bs.cursor
        while cmd != ENDMARKER_INTROCMD:
            numargs = cmd_size[cmd] - 1
            TypeInfo.register('intro', decl_intro_cmd, varmap={'N': numargs})
            intro = bs.read_block('intro')
            self.introcmds.append(intro)
            cmd = bs.peek('s32')
            i += 1

    def read_paths(self):
        bs = self.bs

        bs.set_cursor(self.headers['paths'])
        s = bs.cursor

        padsptr = bs.peek('s32*')
        n = 1
        while padsptr != 0:
            path = bs.read_block('path')
            self.paths.append(path)
            padsptr = bs.peek('s32*')
            n += 1

        self.paths.sort(key=lambda path: path['pads'])

    def read_pads(self):
        bs = self.bs

        padstotal = 0
        for path in self.paths:
            bs.set_cursor(path['pads'])
            s = bs.cursor
            endmarker = ('s32', 0xffffffff, 'includelast')
            pads = bs.read_block('pads', endmarker=endmarker)
            padstotal += bs.cursor - s
            self.pads.append(pads)

    def read_ailists(self):
        bs = self.bs
        bs.set_cursor(self.headers['ailists'])
        listptr = bs.peek('s32*')

        while listptr != 0:
            ailist = bs.read_block('ailist')
            self.ailists.append(ailist)
            listptr = bs.peek('s32*')

    def read_lists(self):
        bs = self.bs

        listaddrs = [(ailist['list'], ailist['id']) for ailist in self.ailists]
        listaddrs.append((self.headers['ailists'], 0))
        listaddrs = sorted(listaddrs, key=lambda e: e[0])

        n = len(listaddrs)-1
        totalsize = 0
        for i in range(n):
            start = listaddrs[i][0]
            end = listaddrs[i+1][0]
            totalsize += end - start
            block = bs.read_block_raw(start, end)
            self.lists.append(block)
