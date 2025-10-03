from functools import cache

from utils import pd_utils as pdu


class TypeInfo:
    SIZE_PTR = 4

    sizes = {
        'pointer': SIZE_PTR,
        'u8': 1,
        's8': 1,
        's16': 2,
        'u16': 2,
        's32': 4,
        'u32': 4,
        'f32': 4,
        's64': 8,
        'f64': 8,
        'u64': 8,
    }

    decl_map = {}

    @classmethod
    def register_all(cls, decls):
        for name, decl in decls.items():
            cls.register(name, decl)

    @classmethod
    def clear_cache(cls):
        cls.sizeof.cache_clear()
        cls.offsetof.cache_clear()
        cls._struct_size.cache_clear()

    @classmethod
    def register(cls, name, declaration, add_padding=True, varmap=None):
        if varmap:
            cls.clear_cache()

            # replace variables in the declaration. Example: 'u8 val[N]' -> 'u8 val[5]'
            # where _vars = {'N': 5}
            decl = declaration.copy()
            n = len(decl)
            pairs = [(idx, key) for idx in range(n) for key in varmap.keys()]
            for (idx, key) in pairs: decl[idx] = decl[idx].replace(key, str(varmap[key]))

            cls.decl_map[name] = decl
            return

        if add_padding:
            declaration = cls.add_padding(declaration)

        cls.decl_map[name] = declaration
        if name not in cls.sizes:
            cls.sizes[name], _ = cls._struct_size(name)

    @classmethod
    def add_padding(cls, decl):
        # log = True
        log = False

        cur_offset = 0
        new_decl = []

        pad_n = 0
        max_sz = 0

        for field in decl:
            info = field_info(field)
            # print(info)

            if info['is_struct']:
                name = info['typename']
                fieldname = info['fieldname']
                if log: print(f'/*{cur_offset:02x}*/ struct {name} {fieldname}')
                struct_sz, type_sz = cls._struct_size(info['typename'])

                cur_offset += struct_sz
                max_sz = max(max_sz, type_sz)
                new_decl.append(field)
                continue

            type_sz = cls.sizeof(info['typename'])
            max_sz = max(max_sz, type_sz)

            # add pads if needed
            pad_sz = pdu.align(cur_offset, type_sz) - cur_offset
            if type_sz > 1 and pad_sz > 0:
                new_decl.append(f'u8 __pad{pad_n}__[{pad_sz}]')
                if log: print(f'/*{cur_offset:02x}*/ u8 __pad__[{pad_sz}]')
                cur_offset += pad_sz
                pad_n += 1

            if log: print(f'/*{cur_offset:02x}*/ {field}')
            new_decl.append(field)

            arr = info['is_array']
            cur_offset += type_sz * info['array_size'] if arr else type_sz

        remaining = cur_offset % max_sz
        if max_sz > 1 and remaining > 0:
            pad_sz = max_sz - remaining
            new_decl.append(f'u8 __pad{pad_n}__[{pad_sz}]')
            if log: print(f'/*{cur_offset:02x}*/ u8 __pad__[{pad_sz}] (max={max_sz}, cur_ofs={cur_offset:03x})')

        return new_decl

    @classmethod
    @cache
    def _struct_size(cls, name):
        struct = cls.get_decl(name)

        size = 0
        max_sz = 0

        for decl in struct:
            info = field_info(decl)
            if info['is_struct']:
                struct_sz, type_sz = cls._struct_size(info['typename'])
                size += struct_sz
                max_sz = max(max_sz, type_sz)
                continue

            type_sz = cls.sizeof(info['typename'])
            max_sz = max(max_sz, type_sz)
            if info['is_array']:
                size += type_sz * info['array_size']
            else:
                size += type_sz

        cls.sizes[name] = size

        return size, max_sz

    @classmethod
    @cache
    def sizeof(cls, typename):
        if '*' in typename: return cls.sizes['pointer']

        if typename not in cls.sizes:
            raise Exception(f'type not registered: {typename}')

        return cls.sizes[typename]

    @classmethod
    def get_decl(cls, typename):
        if typename not in cls.decl_map:
            print(cls.decl_map)
            raise Exception(f'type not registered: {typename}')

        return cls.decl_map[typename]

    @classmethod
    @cache
    def offsetof(cls, decl_name, fieldname):
        decl = cls.get_decl(decl_name)

        ofs = 0
        for field in decl:
            info = field_info(field)

            if info['fieldname'] == fieldname: break
            if field == decl[-1]:
                raise Exception(f'declaration {decl_name} does not contain the field {field}')

            size = cls.sizeof(info['typename'])
            if info['is_array']:
                size *= info['array_size']
            ofs += size

        return ofs


def field_info(decl):
    """
    supported types are primitives, structs, arrays and pointers:
    - primitives (there's no actual processing of tokens, so "anything" can be a primitive),
        however, when used by bytereader, primitives must be the ones declared in the "sz" map
        Examples:
            'f32 xmin'
            'f32 xmax'
            'u16 rwdataindex'

    - structs: which are declarations that must be registered
        Examples:
            'struct coord pos'

    - arrays of supported types, of any dimension
        Examples:
            'struct coord vertices[4]'
            's16 mtxindexes[3]'
            'u8* parts[3]'
            's16 rotmtx[3][3]'
            'f32 3dsomething[3][3][3]'

        - arrays of undetermined size are also supported:
            's32 values[]'
            in such cases, an "endmarker" must be supplied to bytereader

    - pointers to any type
        Examples:
            'void *baseaddr'
            'struct textureconfig *texture'
            'struct modelnode **parts'
    """
    # print('decl:', decl)
    decl = decl.strip()
    decl.replace('\t', ' ')

    is_struct = decl.startswith('struct') and '*' not in decl
    decl = decl.replace('struct', '').strip()

    first_space = decl.find(' ')
    typename, field = decl[:first_space].strip(), decl[first_space:].strip()

    is_pointer = '*' in typename or field.startswith('*')
    is_array = '[' in decl and ']' in decl
    # print('field:', field)

    i = 0
    while field[i] == '*':
        typename += '*'
        i += 1

    array_size = parse_array_size(field) if is_array else None
    field = field.replace('*', '')

    if is_array: field = field[:field.find('[')]

    field = field.strip()

    return {
        'typename': typename,
        'fieldname': field,
        'is_pointer': is_pointer,
        'is_array': is_array,
        'is_struct': is_struct,
        'array_size': array_size,
    }

# returns the expression inside an array declaration, ex: [15+96], returns 15+96
def parse_array(decl):
    open = decl.find('[')
    close = decl.find(']')

    if open + 1 == close:
        return '0', decl[close+1:]
    if open < 0 and close < 0:
        # print('not found')
        return None, decl
    elif open > close:
        print('parse error: bracket')
        return None, None

    return decl[open + 1:close], decl[close+1:]

def parse_array_size(decl):
    total = 1
    while True:
        expr, decl = parse_array(decl)
        if expr:
            total *= eval(expr)
        else: break
        if not decl: break

    # print(s)
    return total
