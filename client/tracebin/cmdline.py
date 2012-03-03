from __future__ import print_function

import argparse
import runpy
import sys
from ConfigParser import ConfigParser

import requests

from tracebin.recorder import record
from tracebin.serializers import BaseSerializer
from tracebin.utils import get_current_command


def main(argv):
    parser = argparse.ArgumentParser(description="tracebin")
    parser.add_argument("file")
    parser.add_argument("--config", type=argparse.FileType("r"))
    parser.add_argument(
        "--action", choices={"upload", "dump"}, default="upload",
    )
    parser.add_argument(
        "--profile", action="store_true",
    )

    parser.add_argument(
        "--dump-format", choices=BaseSerializer.ALL_SERIALIZERS.viewkeys(),
    )

    args = parser.parse_args(argv[1:])

    if args.action != "dump" and args.dump_format:
        parser.error()

    if args.config:
        config = ConfigParser()
        with args.config:
            config.readfp(args.config)

    command = get_current_command()

    with record(profile=args.profile) as recorder:
        runpy.run_path(args.file, run_name="__main__")

    serializer_cls = BaseSerializer.ALL_SERIALIZERS[args.dump_format if args.dump_format else "json"]
    serializer = serializer_cls(recorder)

    dump = serializer.dump(extra_data={"command": command})
    if args.action == "dump":
        print(dump)
    elif args.action == "upload":
        url = "http://{}:{}/trace/new/".format(config.get("server", "host"), config.getint("server", "port"))
        response = requests.post(url, data=dump, headers={"Content-type": "application/json"})
        response.raise_for_status()
        print(response.headers["Location"])

    return 0