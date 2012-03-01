import tempfile

from tracebin_server.settings.base import *


DEBUG = TEMPLATE_DEBUG = True

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "TEST_NAME": tempfile.mktemp(suffix=".db"),
    },
}

