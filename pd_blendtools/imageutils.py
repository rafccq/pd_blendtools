import zlib
import struct

def png_rgba32(buf, width, height):
    width_byte_4 = width * 4
    raw_data = b"".join(b'\x00' + buf[span:span + width_byte_4] for span in range((height - 1) * width * 4, -1, - width_byte_4))
    def png_pack(png_tag, data):
        chunk_head = png_tag + data
        return struct.pack("!I", len(data)) + chunk_head + struct.pack("!I", 0xFFFFFFFF & zlib.crc32(chunk_head))
    return b"".join([
        b'\x89PNG\r\n\x1a\n',
        png_pack(b'IHDR', struct.pack("!2I5B", width, height, 8, 6, 0, 0, 0)),
        png_pack(b'IDAT', zlib.compress(raw_data, 9)),
        png_pack(b'IEND', b'')])

def png_ia16(buf, width, height):
    width_byte_2 = width * 2
    raw_data = b"".join(
        b'\x00' + buf[span:span + width_byte_2] for span in range((height - 1) * width * 2, -1, - width_byte_2))
    def png_pack(png_tag, data):
        chunk_head = png_tag + data
        return struct.pack("!I", len(data)) + chunk_head + struct.pack("!I", 0xFFFFFFFF & zlib.crc32(chunk_head))
    return b"".join([
        b'\x89PNG\r\n\x1a\n',
        png_pack(b'IHDR', struct.pack("!2I5B", width, height, 8, 4, 0, 0, 0)),
        png_pack(b'IDAT', zlib.compress(raw_data, 9)),
        png_pack(b'IEND', b'')])

def png_rgb24(buf, width, height):
    width_byte_3 = width * 3
    raw_data = b"".join(
        b'\x00' + buf[span:span + width_byte_3] for span in range((height - 1) * width * 3, -1, - width_byte_3))
    def png_pack(png_tag, data):
        chunk_head = png_tag + data
        return struct.pack("!I", len(data)) + chunk_head + struct.pack("!I", 0xFFFFFFFF & zlib.crc32(chunk_head))
    return b"".join([
        b'\x89PNG\r\n\x1a\n',
        png_pack(b'IHDR', struct.pack("!2I5B", width, height, 8, 2, 0, 0, 0)),
        png_pack(b'IDAT', zlib.compress(raw_data, 9)),
        png_pack(b'IEND', b'')])

def rgba16_to_rgba32(colors, numpixels):
    out = bytearray()
    for i in range(numpixels):
        rgba16 = colors[i*2] << 8 | colors[i*2 + 1]
        r = (rgba16 >> 11) & 0x1f
        g = (rgba16 >> 6) & 0x1f
        b = (rgba16 >> 1) & 0x1f

        out.append(r * 8)
        out.append(g * 8)
        out.append(b * 8)
        out.append((rgba16 & 1) * 255)

    return out

def rgb15_to_rgb24(colors, numpixels):
    out = bytearray()
    for i in range(numpixels):
        rgb15 = colors[i*2] << 8 | colors[i*2 + 1]
        r = (rgb15 >> 11) & 0x1f
        g = (rgb15 >> 6) & 0x1f
        b = (rgb15 >> 1) & 0x1f

        out.append(r * 8)
        out.append(g * 8)
        out.append(b * 8)

    return out

def ia8_to_ia16(colors, numpixels):
    out = bytearray()
    for i in range(numpixels):
        out.append(((colors[i] >> 4) & 0xf) * 16)
        out.append((colors[i] & 0xf) * 16)
    return out


def ia8_to_rgba32(colors, numpixels):
    out = bytearray()
    for i in range(numpixels):
        val = ((colors[i] >> 4) & 0xf) * 16
        a = (colors[i] & 0xf) * 16
        out.append(val)
        out.append(val)
        out.append(val)
        out.append(a)

    return out

def ia16_to_rgba32(colors, numpixels):
    out = bytearray()
    for i in range(numpixels):
        val = ((colors[i] >> 4) & 0xf) * 16
        a = (colors[i] & 0xf) * 16
        out.append(val)
        out.append(val)
        out.append(val)
        out.append(a)

    return out

def ia4_to_ia16(colors, numpixels):
    out = bytearray()
    for i in range(numpixels):
        val = ((colors[i] >> 1) & 7) * 32
        a = (colors[i] & 1) * 255
        out.append(val)
        out.append(a)

    return out

def ia16_to_rgba32(colors, numpixels):
    out = bytearray()
    for i in range(0, numpixels*2, 2):
        val = colors[i]
        a = colors[i+1]
        out.append(val)
        out.append(val)
        out.append(val)
        out.append(a)

    return out

def i8_to_rgb24(colors, numpixels):
    out = bytearray()
    for i in range(numpixels):
        val = colors[i]
        out.append(val)
        out.append(val)
        out.append(val)

    return out

def i4_to_rgb24(colors, numpixels):
    out = bytearray()
    for i in range(numpixels):
        val = colors[i]*16
        out.append(val)
        out.append(val)
        out.append(val)

    return out
