import struct


def read_unpack(fmt, file):
    size = struct.calcsize(fmt)
    return struct.unpack(fmt, file.read(size))