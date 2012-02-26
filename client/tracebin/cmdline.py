from __future__ import print_function

import argparse
import runpy

from tracebin.recorder import record
from tracebin.serializers import BaseSerializer


def main(argv):
    parser = argparse.ArgumentParser(description="tracebin")
    parser.add_argument("file")
    parser.add_argument(
        "--dump", choices=BaseSerializer.ALL_SERIALIZERS.viewkeys(),
    )

    args = parser.parse_args(argv[1:])

    with record() as recorder:
        runpy.run_path(args.file, run_name="__main__")

    if args.dump:
        serializer_cls = BaseSerializer.ALL_SERIALIZERS[args.dump]
        serializer = serializer_cls(recorder)
        print(serializer.dump())

    return 0