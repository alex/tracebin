#!/usr/bin/env python

import os
import sys


if __name__ == "__main__":
    from django.core.management import execute_from_command_line

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tracebin_server.settings.{}".format(sys.argv[1]))
    execute_from_command_line([sys.argv[0]] + sys.argv[2:])
