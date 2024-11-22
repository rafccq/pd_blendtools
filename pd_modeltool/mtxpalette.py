mtxpalette = [
    0xa9a9a9, 0xdcdcdc, 0x2f4f4f, 0x556b2f, 0xa0522d, 0xa52a2a, 0x2e8b57, 0x191970,
    0x708090, 0x808000, 0x483d8b, 0x008000, 0xbc8f8f, 0x663399, 0x008080, 0xbdb76b,
    0x4682b4, 0x000080, 0xd2691e, 0x9acd32, 0x20b2aa, 0xcd5c5c, 0x32cd32, 0xdaa520,
    0x7f007f, 0x8fbc8f, 0xb03060, 0xd2b48c, 0x66cdaa, 0x9932cc, 0xff4500, 0xffa500,
    0xffd700, 0xc71585, 0x0000cd, 0x7cfc00, 0x00ff00, 0x00ff7f, 0x4169e1, 0xe9967a,
    0xdc143c, 0x00ffff, 0x00bfff, 0xf4a460, 0x9370db, 0x0000ff, 0xa020f0, 0xff6347,
    0xda70d6, 0xd8bfd8, 0xff00ff, 0xdb7093, 0xf0e68c, 0xffff54, 0x6495ed, 0xdda0dd,
    0x90ee90, 0x87ceeb, 0xff1493, 0xafeeee, 0x7fffd4, 0xff69b4, 0xffe4c4, 0xffb6c1,
]

# col is a tuple of floats with each element in the range [0,1]
def hex2col(hexcol):
    conv = lambda e: e/255.0
    r, g, b = ((hexcol & 0xff0000) >> 16), ((hexcol & 0xff00) >> 8), (hexcol & 0xff),
    col = (conv(r), conv(g), conv(b), 1)
    return col

def color2mtx(col):
    conv = lambda e: round(e*255)
    col = (conv(col[0]) << 16) | (conv(col[1]) << 8) |(conv(col[2]))
    return mtxpalette.index(col)

def mtx2color(mtx):
    col = mtxpalette[mtx]
    return hex2col(col)

def print_table():
    conv = lambda e: e/255.0
    for idx, c in enumerate(mtxpalette):
        r, g, b = ((c & 0xff0000) >> 16), ((c & 0xff00) >> 8), (c & 0xff),
        col = (conv(r), conv(g), conv(b))
        print(f'{idx:02X} 0x{c:06X} {col}')
