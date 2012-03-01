import struct


def read_unpack(fmt, file):
    # This is different from struct.unpack_from because it advances the
    # position in the file
    size = struct.calcsize(fmt)
    return struct.unpack(fmt, file.read(size))

def dict_merge(*dicts):
    result = {}
    for d in dicts:
        result.update(d)
    return result