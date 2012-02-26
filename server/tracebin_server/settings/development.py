import os

from tracebin_server.settings.base import *


DEBUG = TEMPLATE_DEBUG = True

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": os.path.join(PROJECT_ROOT, "dev.db"),
    },
}

INSTALLED_APPS = INSTALLED_APPS + [
    "fixture_generator",
]