class BitReader:
    def __init__(self, buffer):
        self.buffer = buffer
        self.accum_value = 0
        self.accum_nbits = 0
        self.idx = 0

    def read(self, nbits):
        while self.accum_nbits < nbits:
            self.accum_value = self.buffer[self.idx] | (self.accum_value << 8)
            self.idx += 1
            self.accum_nbits += 8

        self.accum_nbits -= nbits
        return (self.accum_value >> self.accum_nbits) & ((1 << nbits) - 1)

    def cur_buffer(self):
        return self.buffer[self.idx:]
