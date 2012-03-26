import os
import struct
import sys
from __pypy__ import time


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

if sys.platform.startswith("linux"):
    def get_current_command():
        with open("/proc/{:d}/cmdline".format(os.getpid())) as f:
            return f.read().rstrip("\x00").replace("\x00", " ")

    def high_res_time():
        return time.clock_gettime(time.CLOCK_MONOTONIC_RAW)
