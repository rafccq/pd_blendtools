G_MTX               = 0x01
G_VTX               = 0x04
G_COL               = 0x07
G_TRI4              = 0xb1
G_CLEARGEOMETRYMODE = 0xb6
G_SETGEOMETRYMODE   = 0xb7
G_SetOtherMode_L    = 0xb9
G_SetOtherMode_H    = 0xba
G_TEXTURE           = 0xbb
G_PDTEX             = 0xc0
G_RDPPIPESYNC       = 0xe7
G_SETCOMBINE        = 0xfc
G_END               = 0xb8

G_LIGHTING           = 0x00020000
G_TEXTURE_GEN        = 0x00040000
G_TEXTURE_GEN_LINEAR = 0x00080000

G_ZBUFFER        = 0x00000001
G_SHADE          = 0x00000004
G_CULL_FRONT     = 0x00001000
G_CULL_BACK      = 0x00002000
G_SHADING_SMOOTH = 0x00000200

G_IM_FMT_RGBA = 0
G_IM_FMT_YUV  = 1
G_IM_FMT_CI	  = 2
G_IM_FMT_IA	  = 3
G_IM_FMT_I	  = 4

G_IM_SIZ_4b	  = 0
G_IM_SIZ_8b	  = 1
G_IM_SIZ_16b  = 2
G_IM_SIZ_32b  = 3
G_IM_SIZ_DD	  = 5

def cmd_G_COL(count, offset):
    offset |= 0x05000000
    cmd = bytearray([0x07, 0x00])
    cmd += count.to_bytes(2, 'big')
    cmd += offset.to_bytes(4, 'big')
    return cmd

def cmd_G_VTX_EXT(nverts, offset, idx = 0):
    offset |= 0x05000000
    cmd = bytearray([0x45, 0, idx, nverts])
    cmd += offset.to_bytes(4, 'big')
    return cmd

def cmd_G_VTX(nverts, offset, idx = 0):
    ni = ((nverts - 1) << 4) | idx
    cmd = bytearray([0x04, ni])
    cmd += (nverts*12).to_bytes(2, 'big')
    cmd += (offset | 0x05000000).to_bytes(4, 'big')
    return cmd

def cmd_G_MTX(mtx):
    offset = 0x03000000 | (mtx * 64)
    cmd = bytearray([0x01, 0x02, 0x000, 0x40])
    cmd += offset.to_bytes(4, 'big')
    return cmd

def cmd_G_TRI(tri):
    cmd = bytearray([0xbf, 0x00, 0x00, 0x00, 0x00])
    if len(tri) != 3:
        print(f'WARNING: invalid tri: {tri}')
    cmd += bytearray([v for v in tri])
    return cmd

def cmd_G_TRI4(trigroup):
    # if the size of the group < 4, fill it with "zero" entries until it reaches 4
    for _ in range(4 - len(trigroup)): trigroup.append((0,0,0))

    w0, w1 = 0xb1000000, 0
    ofs0, ofs1 = 0, 0

    for i0, i1, i2 in trigroup:
        w1 |= ((i1 << 4) | i0) << ofs1
        w0 |= i2 << ofs0

        ofs0 += 4
        ofs1 += 8

    cmd = bytearray(w0.to_bytes(4, 'big'))
    cmd += bytearray(w1.to_bytes(4, 'big'))

    return cmd

def cmd_G_RDPPIPESYNC():
    return bytearray.fromhex('E700000000000000')

def cmd_G_END():
    return bytearray.fromhex('B800000000000000')

def cmd_G_CLEARGEOMETRY(geobits):
    cmd = bytearray([0xb6, 0x00, 0x00, 0x00])
    cmd += bytearray(geobits.to_bytes(4, 'big'))
    return cmd
