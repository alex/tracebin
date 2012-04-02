from __future__ import print_function

import argparse
import runpy
import sys
import zlib
from ConfigParser import ConfigParser

import logbook

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

    parser.add_argument(
        "-v", "--verbose", action="store_true",
    )


    args = parser.parse_args(argv[1:])

    logger = logbook.Logger(level=logbook.INFO if args.verbose else logbook.WARNING)

    if args.action != "dump" and args.dump_format:
        parser.error()

    config = ConfigParser()

    # Setup some defaults, eventually there should be some sort of better
    # abstraction for this.
    config.add_section("server")
    config.set("server", "host", "localhost")
    config.set("server", "port", "8000")

    if args.config:
        with args.config:
            config.readfp(args.config)

    command = get_current_command()

    logger.info("Starting running")
    with record(logger=logger, profile=args.profile) as recorder:
        runpy.run_path(args.file, run_name="__main__")
    logger.info("User program finished")

    serializer_cls = BaseSerializer.ALL_SERIALIZERS[args.dump_format if args.dump_format else "json"]
    serializer = serializer_cls(recorder)

    logger.info("Starting serialization")
    dump = serializer.dump(extra_data={"command": command})
    logger.info("Serialization finished")
    if args.action == "dump":
        print(dump)
    elif args.action == "upload":
        url = "http://{}:{}/trace/new/".format(config.get("server", "host"), config.getint("server", "port"))
        logger.info("Starting upload")

        # level 9 is the slowest, but compresses best.
        data = zlib.compress(dump, level=9)

        response = requests.post(url,
            data=dump,
            headers={
                "Content-type": "application/json",
                "Content-encoding": "gzip",
            },
            allow_redirects=False,
        )
        logger.info("Upload finished")
        response.raise_for_status()
        print(response.headers["Location"])

    return 0
