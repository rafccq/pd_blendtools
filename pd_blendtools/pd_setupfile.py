from bytereader import *
from decl_setupfile import *
from typeinfo import TypeInfo


# enableLog = True
enableLog = False

def log(*args):
    if not enableLog: return
    print(''.join(args))


class PD_SetupFile:
    def __init__(self, setupdata, srcBO = 'big', destBO = 'little'):
        rd = self.rd = ByteReader(setupdata, srcBO, destBO)

        self.props = []
        self.introcmds = []
        self.paths = []
        self.pads = []
        self.ailists = []
        self.lists = []
        self.headers = None

        self.read()

    def read(self):
        self.headers = self.rd.read_block('stagesetup')
        # self.rd.print_dict(self.headers, 'stagesetup', pad=15)

        self.read_objs()
        self.read_intro()
        self.read_paths()
        self.read_pads()
        self.read_ailists()
        self.read_lists()

    def obj_type(self):
        header = self.rd.peek('u8', 4)
        return header[3] if header[3] != 0 else header[0]

    def read_objs(self):
        log('READ:OBJS')

        rd = self.rd
        rd.set_cursor(self.headers['props'])

        type = self.obj_type()
        n = 1

        s = rd.cursor
        # print(f'type {type:02X}')
        while type != 0x34:
            name = OBJ_NAMES[type]
            log(f'#{n:02} obj 0x{type:02X} name {name} [0x{rd.cursor:04X}]')
            obj = rd.read_block(type)
            obj['_type_'] = type

            self.props.append(obj)

            type = self.obj_type()
            n += 1

        obj = rd.read_block('obj_header')
        obj['_type_'] = ENDMARKER_PROPS
        self.props.append(obj)
        log(f'n_obj {n-1}')

    def read_intro(self):
        rd = self.rd

        rd.set_cursor(self.headers['intro'])

        log(f'READ:INTRO {rd.cursor:04X}')

        i = 0
        cmd = rd.peek('s32')
        s = rd.cursor
        while cmd != ENDMARKER_INTROCMD:
            log(f'intro #{i:02X} {cmd:08X} [{rd.cursor:04X}]')

            params = self.rd.peek('u32', cmd_size[cmd])
            # for p in params:
            #     log(f'  {p:08X}')

            numargs = cmd_size[cmd] - 1
            TypeInfo.register('intro', decl_intro_cmd, varmap={'N': numargs})
            intro = rd.read_block('intro')
            self.introcmds.append(intro)
            cmd = rd.peek('s32')
            i += 1

    def read_paths(self):
        rd = self.rd

        log(f'READ:PATHS {rd.cursor:04X}')

        rd.set_cursor(self.headers['paths'])
        s = rd.cursor

        padsptr = rd.peek('s32*')
        n = 1
        while padsptr != 0:
            log(f'path #{n:02X}')
            path = rd.read_block('path')
            self.paths.append(path)
            rd.print_dict(path, 'path', pad=8, numspaces=2)
            padsptr = rd.peek('s32*')
            n += 1

        self.paths.sort(key=lambda path: path['pads'])

    def read_pads(self):
        rd = self.rd

        log(f'READ:PADS {rd.cursor:04X}')

        padstotal = 0
        for path in self.paths:
            rd.set_cursor(path['pads'])
            s = rd.cursor
            endmarker = ('s32', 0xffffffff, 'includelast')
            pads = rd.read_block('pads', endmarker=endmarker)
            padstotal += rd.cursor - s
            self.pads.append(pads)

        log(f'PADS TOTAL: {padstotal}')

    def read_ailists(self):
        rd = self.rd
        rd.set_cursor(self.headers['ailists'])
        s = rd.cursor

        log(f'READ:AILISTS [{rd.cursor:04X}]')

        listptr = rd.peek('s32*')

        while listptr != 0:
            ailist = rd.read_block('ailist')
            self.ailists.append(ailist)
            listptr = rd.peek('s32*')

        # self.ailists.sort(key=lambda item: item['list'])

        # just logging
        # for ailist in self.ailists:
        #     id, list = ailist['id'], ailist['list']
        #     log(f'id {id:08X} list {list:08X}')

    def read_lists(self):
        rd = self.rd

        log(f'READ:LISTS {rd.cursor:04X}')

        listaddrs = [(ailist['list'], ailist['id']) for ailist in self.ailists]
        listaddrs.append((self.headers['ailists'], 0))
        listaddrs = sorted(listaddrs, key=lambda e: e[0])

        n = len(listaddrs)-1
        totalsize = 0
        for i in range(n):
            start = listaddrs[i][0]
            end = listaddrs[i+1][0]
            totalsize += end - start
            log(f'[{start:04X}:{end:04X}]')
            block = rd.read_block_raw(start, end)
            self.lists.append(block)

        log(f'LIST TOTAL: {totalsize}')


    def patch(self):
        # sections = ['header', 'intro', 'props', 'paths', 'pads', 'ailists', 'lists']
        dataout = bytearray()
        rd = self.rd

        headers = self.headers
        rd.write_block(dataout, 'stagesetup', headers)

        # log('PROPS')
        n = 1
        for obj in self.props:
            addr = obj['_addr_']
            type = obj['_type_']
            # log(f'.obj #{n}: {type:02x} addr {addr:08X}')
            rd.ref = len(dataout)
            rd.write_block(dataout, obj['_type_'], obj)
            n += 1

        # log('INTRO')
        for cmd in self.introcmds:
            numargs = cmd_size[cmd['cmd']] - 1
            TypeInfo.register('intro', decl_intro_cmd, {'N': numargs})
            rd.write_block(dataout, 'intro', cmd)
        rd.write(dataout, ENDMARKER_INTROCMD, 's32')

        # log('>patch LISTS')
        for list in self.lists: rd.write_block_raw(dataout, list)

        rd.write_block_list(dataout, 'ailist', self.ailists, endmarker=('s32*', 0), dbg=0)

        # log('>patch PATHS')
        if len(self.paths) == 0:
            rd.pointers_map[headers['paths']] = len(dataout)
        rd.write_block_list(dataout, 'path', self.paths, endmarker=('s32*', 0))

        # log('PADS')
        rd.write_block_list(dataout, 'pads', self.pads, dbg=0)
        return dataout
