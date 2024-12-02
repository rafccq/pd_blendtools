import pd_utils as pdu
import imageutils as imu
from bitreader import BitReader

# format consts
PDFORMAT_RGBA32 = 0
PDFORMAT_RGBA16 = 1
PDFORMAT_RGB24 = 2
PDFORMAT_RGB15 = 3
PDFORMAT_IA16 = 4
PDFORMAT_IA8 = 5
PDFORMAT_IA4 = 6
PDFORMAT_I8 = 7
PDFORMAT_I4 = 8
PDFORMAT_RGBA16_CI8 = 9
PDFORMAT_RGBA16_CI4 = 10
PDFORMAT_IA16_CI8 = 11
PDFORMAT_IA4_CI4 = 12

# compression consts
PDCOMPRESSION_HUFFMAN = 2
PDCOMPRESSION_HUFFMANPERHCHANNEL = 3
PDCOMPRESSION_RLE = 4
PDCOMPRESSION_LOOKUP = 5
PDCOMPRESSION_HUFFMANLOOKUP = 6
PDCOMPRESSION_RLELOOKUP = 7
PDCOMPRESSION_HUFFMANBLUR = 8
PDCOMPRESSION_RLEBLUR = 9

# format features
TexFormatNumChannels = [4, 3, 3, 3, 2, 2, 1, 1, 1, 1, 1, 1, 1]
TexFormatHas1BitAlpha = [0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0]
TexFormatChannelSizes = [256, 32, 256, 32, 256, 16, 8, 256, 16, 256, 16, 256, 16]
TexFormatBitsPerPixel = [32, 16, 24, 15, 16, 8, 4, 8, 4, 16, 16, 16, 16]

class Image:
    def __init__(self):
        self.format = 0
        self.compression = 0
        self.width = 0
        self.height = 0
        self.pixels = []

class PDTex:
    def __init__(self):
        self.palette = []
        self.image = Image()
        self.numcolors = 0

def tex_inflate_zlib(br, sp14a8, lod):
    fmt = br.read(8)

    tex = PDTex()

    numcolors = br.read(8) + 1
    palette = [0] * numcolors*2

    for i in range(0, numcolors):
        palette[i*2 + 0] = br.read(8)
        palette[i*2 + 1] = br.read(8)

    tex.numcolors = numcolors
    tex.palette = palette

    numimages = 1 # here we just need to load 1 image
    for i in range(0, numimages):
        img = tex.image
        img.format = fmt
        img.width = br.read(8)
        img.height = br.read(8)

        imgdata = pdu.decompress(br.cur_buffer())
        tex_align_indices(imgdata, img)

    return tex

def tex_inflate_nonzlib(br):
    scratch = [0] * 0x20000
    lookup = [0] * 0x10000
    numimages = 1

    tex = PDTex()

    for i in range(numimages):
        img = tex.image
        img.format = br.read(4)
        img.width = br.read(8)
        img.height = br.read(8)
        img.compression = br.read(4)

        fmt, w, h = img.format, img.width, img.height
        img.pixels = [0] * w * h * 4

        if img.compression == PDCOMPRESSION_HUFFMAN:
            tex_inflate_huffman(br, scratch, 0, TexFormatNumChannels[fmt]*w*h, TexFormatChannelSizes[fmt])

            if TexFormatHas1BitAlpha[fmt]:
                tex_read_alpha_bits(br, scratch, img)

            tex_channels_to_pixels(scratch, img)
        elif img.compression == PDCOMPRESSION_HUFFMANPERHCHANNEL:
            for j in range(TexFormatNumChannels[fmt]):
                tex_inflate_huffman(br, scratch, w*h*j, w*h, TexFormatChannelSizes[fmt])

            if TexFormatHas1BitAlpha[fmt]:
                tex_read_alpha_bits(br, scratch, img)

            tex_channels_to_pixels(scratch, img)
        elif img.compression == PDCOMPRESSION_RLE:
            tex_inflate_rle(br, scratch, TexFormatNumChannels[fmt] * w * h)

            if TexFormatHas1BitAlpha[fmt]:
                tex_read_alpha_bits(br, scratch, img)

            tex_channels_to_pixels(scratch, img)
        elif img.compression == PDCOMPRESSION_LOOKUP:
            value = tex_build_lookup(br, lookup, TexFormatBitsPerPixel[fmt])
            tex_inflate_lookup(br, img, lookup, value)
        elif img.compression == PDCOMPRESSION_HUFFMANLOOKUP:
            value = tex_build_lookup(br, lookup, TexFormatBitsPerPixel[fmt])
            tex_inflate_huffman(br, scratch, 0, w * h, value)
            tex_inflate_lookup_from_buffer(scratch, img, lookup, value)
        elif img.compression == PDCOMPRESSION_RLELOOKUP:
            value = tex_build_lookup(br, lookup, TexFormatBitsPerPixel[fmt])
            tex_inflate_rle(br, scratch, w * h)
            tex_inflate_lookup_from_buffer(scratch, img, lookup, value)
        elif img.compression == PDCOMPRESSION_HUFFMANBLUR:
            value = br.read(3)
            tex_inflate_huffman(br, scratch, 0, TexFormatNumChannels[fmt] * w * h, TexFormatChannelSizes[fmt])
            tex_blur(scratch, w, TexFormatNumChannels[fmt]*h, value, TexFormatChannelSizes[fmt])

            if TexFormatHas1BitAlpha[fmt]:
                tex_read_alpha_bits(br, scratch, img)

            tex_channels_to_pixels(scratch, img)
        elif img.compression == PDCOMPRESSION_RLEBLUR:
            value = br.read(3)
            tex_inflate_rle(br, scratch, TexFormatNumChannels[fmt] * w * h)
            tex_blur(scratch, w, TexFormatNumChannels[fmt]*h, value, TexFormatChannelSizes[fmt])

            if TexFormatHas1BitAlpha[fmt]:
                tex_read_alpha_bits(br, scratch, img)

            tex_channels_to_pixels(scratch, img)

    return tex

def tex_read_alpha_bits(br, dst, img):
    w, h = img.width, img.height
    start = w * h * 3
    count = w * h
    for i in range(count):
        dst[start + i] = br.read(1)

def tex_channels_to_pixels(src, img):
    fmt, w, h = img.format, img.width, img.height
    mult = w * h
    pos = 0
    row = 0
    dst = img.pixels

    if fmt == PDFORMAT_RGBA32:
        for y in range(h):
            for x in range(w):
                dst[row + x*4 + 0] = src[pos]
                dst[row + x*4 + 1] = src[pos + mult]
                dst[row + x*4 + 2] = src[pos + mult*2]
                dst[row + x*4 + 3] = src[pos + mult*3]
                pos += 1
            row += w*4
    elif fmt == PDFORMAT_RGB24:
        for y in range(h):
            for x in range(w):
                dst[row + x*3 + 0] = src[pos]
                dst[row + x*3 + 1] = src[pos + mult]
                dst[row + x*3 + 2] = src[pos + mult*2]
                pos += 1
            row += w*3
    elif fmt == PDFORMAT_RGBA16:
        for y in range(h):
            for x in range(w):
                dst[row + x*2 + 0] = src[pos] << 3 | src[pos + mult] >> 2
                dst[row + x*2 + 1] = src[pos + mult] << 6 | src[pos + mult * 2] << 1 | src[pos + mult * 3]
                pos += 1
            row += w*2
    elif fmt == PDFORMAT_IA16:
        for y in range(h):
            for x in range(w):
                dst[row + x*2 + 0] = src[pos]
                dst[row + x*2 + 1] = src[pos + mult]
                pos += 1
            row += w*2
    elif fmt == PDFORMAT_RGB15:
        for y in range(h):
            for x in range(w):
                dst[row + x*2 + 0] = src[pos] << 3 | src[pos + mult] >> 2
                dst[row + x*2 + 1] = src[pos + mult] << 6 | src[pos + mult * 2] << 1 | 1
                pos += 1
            row += w*2
    elif fmt == PDFORMAT_IA8:
        for y in range(h):
            for x in range(w):
                dst[row + x] = src[pos] << 4 | src[pos + mult]
                pos += 1
            row += w
    elif fmt == PDFORMAT_I8:
        for y in range(h):
            for x in range(w):
                dst[row + x] = src[pos]
                pos += 1
            row += w
    elif fmt == PDFORMAT_IA4:
        for y in range(h):
            for x in range(0, w, 2):
                dst[row + x >> 1] = src[pos] << 5 | src[pos + mult * 3] << 4 | src[pos + 1] << 1 | src[pos + mult * 3 + 1]
                pos += 2

            if w & 1:
                pos -= 1
            row += w
    elif fmt == PDFORMAT_I4:
        for i in range(w*h):
            dst[i] = src[i]

def tex_inflate_huffman(br, dst, dstofs, numiterations, chansize):
    frequencies = [0] * 2048
    nodes = [[-1,-1] for _ in range(2048)]
    done = False

    # Read the frequencies list
    for i in range(chansize):
        frequencies[i] = br.read(8)

    # Find the 2 smallest frequencies
    minfreq1 = 9999
    minfreq2 = 9999

    rootindex = 0
    minindex1 = 0
    minindex2 = 0

    for i in range(chansize):
        if frequencies[i] < minfreq1:
            if minfreq2 < minfreq1:
                minfreq1 = frequencies[i]
                minindex1 = i
            else:
                minfreq2 = frequencies[i]
                minindex2 = i
        elif frequencies[i] < minfreq2:
            minfreq2 = frequencies[i]
            minindex2 = i


    # Build the tree.
	# For each node in tree, a branch value < 10000 means this branch
	# leads to another node, and the value is the target node's index.
	# A branch value >= 10000 means the branch is a leaf node,
	# and the value is the channel value + 10000.
    while not done:
        sumfreq = frequencies[minindex1] + frequencies[minindex2]
        if sumfreq == 0: sumfreq = 1

        frequencies[minindex1] = 9999
        frequencies[minindex2] = 9999

        if nodes[minindex1][0] < 0 and nodes[minindex1][1] < 0:
            nodes[minindex1][0] = minindex1 + 10000
            rootindex = minindex1
            frequencies[minindex1] = sumfreq

            if nodes[minindex2][0] < 0 and nodes[minindex2][1] < 0:
                nodes[minindex1][1] = minindex2 + 10000
            else:
                nodes[minindex1][1] = minindex2
        elif nodes[minindex2][0] < 0 and nodes[minindex2][1] < 0:
            nodes[minindex2][0] = minindex2 + 10000
            rootindex = minindex2
            frequencies[minindex2] = sumfreq

            if nodes[minindex1][0] < 0 and nodes[minindex1][1] < 0:
                nodes[minindex2][1] = minindex1 + 10000
            else:
                nodes[minindex2][1] = minindex1
        else:
            rootindex = 0
            while nodes[rootindex][0] >= 0 or \
                  nodes[rootindex][1] >= 0 or \
                  frequencies[rootindex] < 9999:
                rootindex += 1

            frequencies[rootindex] = sumfreq
            nodes[rootindex][0] = minindex1
            nodes[rootindex][1] = minindex2

        # Find the two smallest frequencies again for the next iteration
        minfreq1 = 9999
        minfreq2 = 9999

        for i in range(chansize):
            if frequencies[i] < minfreq1:
                if minfreq1 > minfreq2:
                    minfreq1 = frequencies[i]
                    minindex1 = i
                else:
                    minfreq2 = frequencies[i]
                    minindex2 = i
            elif frequencies[i] < minfreq2:
                minfreq2 = frequencies[i]
                minindex2 = i

        if minfreq1 == 9999 or minindex2 == 9999:
            done = True

    #  Read bits off the bitstring, traverse the tree
    #  and write the channel values to dst
    for i in range(numiterations):
        indexorvalue = rootindex

        while indexorvalue < 10000:
            indexorvalue: int = nodes[indexorvalue][br.read(1)]

        if chansize <= 256:
            dst[dstofs + i] = indexorvalue - 10000
        else:
            value = indexorvalue - 10000
            dst[dstofs + 2 * i + 0] = value >> 8
            dst[dstofs + 2 * i + 1] = value & 0xff

def tex_build_lookup(br, lookup, bitsperpixel):
    numcolors = br.read(11)

    if bitsperpixel <= 16:
        for i in range(numcolors):
            value = br.read(bitsperpixel)
            lookup[2*i + 0] = (value >> 8) & 0xff
            lookup[2*i + 1] = value & 0xff
    elif bitsperpixel <= 24:
        for i in range(numcolors):
            value = br.read(bitsperpixel)
            lookup[4*i + 0] = (value >> 24)
            lookup[4*i + 1] = (value >> 16) & 0xff
            lookup[4*i + 2] = (value >>  8) & 0xff
            lookup[4*i + 3] = value & 0xff
    else:
        for i in range(numcolors):
            value = br.read(24) << 8 | br.read(bitsperpixel - 24)
            lookup[4*i + 0] = (value >> 24)
            lookup[4*i + 1] = (value >> 16) & 0xff
            lookup[4*i + 2] = (value >>  8) & 0xff
            lookup[4*i + 3] = value & 0xff

    return numcolors

def tex_get_bit_size(decimal):
    count = 0
    decimal -= 1

    while decimal > 0:
        decimal >>= 1
        count += 1

    return count

def tex_inflate_lookup(br, image, lookup, numcolors):
    bitspercolor = tex_get_bit_size(numcolors)
    fmt, w, h = image.format, image.width, image.height

    dst = image.pixels
    dstofs = 0
    if fmt == PDFORMAT_RGBA32:
        for y in range(h):
            for x in range(w):
                index = br.read(bitspercolor)
                dst[dstofs + 4*x + 0] = lookup[4*index + 0]
                dst[dstofs + 4*x + 1] = lookup[4*index + 1]
                dst[dstofs + 4*x + 2] = lookup[4*index + 2]
                dst[dstofs + 4*x + 3] = lookup[4*index + 3]

            dstofs += w*4
    elif fmt == PDFORMAT_RGB24:
        for y in range(h):
            for x in range(w):
                index = br.read(bitspercolor)
                dst[dstofs + 3*x + 0] = lookup[4 * index + 1]
                dst[dstofs + 3*x + 1] = lookup[4 * index + 2]
                dst[dstofs + 3*x + 2] = lookup[4 * index + 3]

            dstofs += w * 3
    elif fmt in [PDFORMAT_IA16, PDFORMAT_RGBA16]:
        for y in range(h):
            for x in range(w):
                index = br.read(bitspercolor)
                dst[dstofs + 2*x + 0] = lookup[2 * index + 0]
                dst[dstofs + 2*x + 1] = lookup[2 * index + 1]

            dstofs += w * 2
    elif fmt == PDFORMAT_RGB15:
        for y in range(h):
            for x in range(w):
                index = br.read(bitspercolor)
                dst[dstofs + 2*x + 0] = lookup[2*index + 0] << 1 | ((lookup[2*index + 1] >> 7) & 1)
                dst[dstofs + 2*x + 1] = lookup[2*index + 1] << 1 | 1

            dstofs += w * 2
    elif fmt in [PDFORMAT_IA8, PDFORMAT_I8]:
        for y in range(h):
            for x in range(w):
                dst[dstofs + x] = lookup[br.read(bitspercolor) * 2 + 1]

            dstofs += w
    elif fmt in [PDFORMAT_IA4, PDFORMAT_I4]:
        for y in range(h):
            for x in range(0, w, 2):
                dst[dstofs + (x >> 1)] = lookup[br.read(bitspercolor) * 2] << 4

                if x + 1 < w:
                    dst[dstofs + (x >> 1)] |= lookup[(br.read(bitspercolor) * 2) + 1]

            dstofs += ((w+15) & 0xff0) >> 1

def tex_inflate_rle(br, dst, blockstotal):
    btfieldsize = br.read(3)
    rlfieldsize = br.read(3)
    blocksize = br.read(4)

    cost = btfieldsize + rlfieldsize + blocksize + 1
    fudge = 0

    while cost > 0:
        cost = cost - blocksize - 1
        fudge += 1

    blocksdone = 0

    while blocksdone < blockstotal:
        if br.read(1) == 0:
            # Found a literal directive
            if blocksize <= 8:
                dst[blocksdone] = br.read(blocksize)
                blocksdone += 1
            else:
                val = br.read(blocksize)
                dst[2*blocksdone + 0] = val >> 8
                dst[2*blocksdone + 1] = val & 0xff
                blocksdone += 1
        else:
            # Found a run directive
            startblockindex = blocksdone - br.read(btfieldsize) - 1
            runnumblocks = br.read(rlfieldsize) + fudge

            if blocksize <= 8:
                for i in range(startblockindex, startblockindex + runnumblocks):
                    dst[blocksdone] = dst[i]
                    blocksdone += 1

                # The next instruction must be a literal
                dst[blocksdone] = br.read(blocksize)
                blocksdone += 1
            else:
                for i in range(startblockindex, startblockindex + runnumblocks):
                    dst[2*blocksdone + 0] = dst[2*i + 0]
                    dst[2*blocksdone + 1] = dst[2*i + 1]
                    blocksdone += 1

                # The next instruction must be a literal
                val = br.read(blocksize)
                dst[2*blocksdone + 0] = val >> 8
                dst[2*blocksdone + 1] = val & 0xff
                blocksdone += 1

def tex_inflate_lookup_from_buffer(src, img, lookup, numcolors):
    fmt, w, h = img.format, img.width, img.height
    indices = [0] * 0x2000

    if numcolors <= 256:
        for i in range(w*h):
            indices[i] = src[i]
    else:
        for i in range(w*h):
            indices[i] = src[2*i]

    dst = img.pixels
    row = 0
    idxofs = 0
    if fmt == PDFORMAT_RGBA32:
        for y in range(h):
            for x in range(w):
                dst[row + x*4 + 0] = lookup[indices[idxofs + x]*4 + 0]
                dst[row + x*4 + 1] = lookup[indices[idxofs + x]*4 + 1]
                dst[row + x*4 + 2] = lookup[indices[idxofs + x]*4 + 2]
                dst[row + x*4 + 3] = lookup[indices[idxofs + x]*4 + 3]
            row += w*4
            idxofs += w
    elif fmt == PDFORMAT_RGB24:
        for y in range(h):
            for x in range(w):
                dst[row + x*3 + 0] = lookup[indices[idxofs + x]*4 + 1]
                dst[row + x*3 + 1] = lookup[indices[idxofs + x]*4 + 2]
                dst[row + x*3 + 2] = lookup[indices[idxofs + x]*4 + 3]
            row += w*3
            idxofs += w
    elif fmt in [PDFORMAT_RGBA16, PDFORMAT_IA16]:
        for y in range(h):
            for x in range(w):
                dst[row + x*2 + 0] = lookup[indices[idxofs + x]*2 + 0]
                dst[row + x*2 + 1] = lookup[indices[idxofs + x]*2 + 1]
            row += w*2
            idxofs += w
    elif fmt == PDFORMAT_RGB15:
        for y in range(h):
            for x in range(w):
                dst[row + x*2 + 0] = lookup[indices[idxofs + x]*2] << 1 | (lookup[indices[idxofs + x]*2 + 1] >> 7)
                dst[row + x*2 + 1] = lookup[indices[idxofs + x]*2 + 1] << 1 | 1
            row += w*2
            idxofs += w
    elif fmt in [PDFORMAT_IA8, PDFORMAT_I8]:
        for y in range(h):
            for x in range(w):
                dst[row + x] = lookup[indices[idxofs + x]*2 + 1]
            row += w
            idxofs += w
    elif fmt in [PDFORMAT_IA4, PDFORMAT_I4]:
        for y in range(h):
            for x in range(0, w, 2):
                dst[row + (x >> 1)] = lookup[indices[idxofs + x]*2] << 4 | lookup[indices[idxofs + x + 1]*2]
            row += w >> 1
            idxofs += w

def tex_blur(pixels, width, height, method, chansize):
    for y in range(height):
        for x in range(width):
            cur = pixels[y*width + x] + chansize*2
            left = pixels[y*width + x - 1] if x > 0 else 0
            above = pixels[(y-1)*width + x] if y > 0 else 0
            aboveleft = pixels[(y-1)*width + x - 1] if x > 0 and y > 0 else 0

            if method == 0:
                pixels[y * width + x] = (cur + left) % chansize
            elif method == 1:
                pixels[y * width + x] = (cur + above) % chansize
            elif method == 2:
                pixels[y * width + x] = (cur + aboveleft) % chansize
            elif method == 3:
                pixels[y * width + x] = (cur + (left + above - aboveleft)) % chansize
            elif method == 4:
                pixels[y * width + x] = (cur + (int((above - aboveleft) / 2) + left)) % chansize
            elif method == 5:
                pixels[y * width + x] = (cur + (int((left - aboveleft) / 2) + above)) % chansize
            elif method == 6:
                pixels[y * width + x] = (cur + (int((left + above) / 2))) % chansize

def tex_align_indices(imgdata, img):
    fmt, width, height = img.format, img.width, img.height
    if fmt == PDFORMAT_RGBA16_CI8 or fmt == PDFORMAT_IA16_CI8:
        n = width * height
        img.pixels = [imgdata[i] for i in range(n)]
    elif fmt == PDFORMAT_RGBA16_CI4 or fmt == PDFORMAT_IA4_CI4:
        row = 0
        for y in range(height):
            readside = 0
            src = imgdata[row:]
            for x in range(width):
                value = src[x//2] & 0xf if readside else src[x//2] >> 4
                img.pixels.append(value)
                readside = 1 - readside

            row += (width+1)//2

def tex_load(filedata, outdir, texid):
    br = BitReader(filedata)

    sp14a8 = br.read(1)
    iszlib = br.read(1)
    lod = br.read(6)

    if iszlib:
        tex = tex_inflate_zlib(br, sp14a8, lod)
    else:
        tex = tex_inflate_nonzlib(br)

    tex_write_image(outdir, tex, texid)

def tex_write_image(outdir, tex, filename):
    colbuffer = bytearray()

    image = tex.image
    fmt, comp, w, h = image.format, image.compression, image.width, image.height

    copy = lambda pixels, _: bytearray(pixels)

    ConversionFuncs = {
        PDFORMAT_RGBA32:     (copy, imu.png_rgba32),
        PDFORMAT_RGBA16:     (imu.rgba16_to_rgba32, imu.png_rgba32),
        PDFORMAT_RGB24:      (copy, imu.png_rgb24),
        PDFORMAT_RGB15:      (imu.rgba15_to_rgb24, imu.png_rgb24),
        PDFORMAT_IA8:        (imu.ia8_to_rgba32, imu.png_rgba32),
        PDFORMAT_IA4:        (imu.ia4_to_rgba32, imu.png_rgb24),
        PDFORMAT_I8:         (imu.i8_to_rgb24, imu.png_rgb24),
        PDFORMAT_I4:         (imu.i4_to_rgb24, imu.png_rgb24),
        PDFORMAT_RGBA16_CI8: (imu.rgba16_to_rgba32, imu.png_rgba32),
        PDFORMAT_RGBA16_CI4: (imu.rgba16_to_rgba32, imu.png_rgba32),
        PDFORMAT_IA16_CI8:   (imu.ia16_to_rgba32, imu.png_rgba32),
        PDFORMAT_IA4_CI4:    (imu.ia8_to_rgba32, imu.png_rgb24),
    }

    if fmt not in ConversionFuncs:
        print(f'ERROR: Invalid color format: {fmt}')

    is_paletted = fmt in [PDFORMAT_RGBA16_CI4, PDFORMAT_RGBA16_CI8, PDFORMAT_IA16_CI8]

    if is_paletted:
        colors = ConversionFuncs[fmt][0](tex.palette, tex.numcolors)
        for px in image.pixels:
            colbuffer += bytearray([colors[px * 4 + i] for i in range(4)])
        pngdata = ConversionFuncs[fmt][1](colbuffer, w, h)
    else:
        colbuffer = ConversionFuncs[fmt][0](image.pixels, w * h)
        pngdata = ConversionFuncs[fmt][1](colbuffer, w, h)

    pdu.write_file(f'{outdir}/{filename}', pngdata, log=False)
