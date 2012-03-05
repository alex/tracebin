import os

from tracebin_server.settings.base import *


DEBUG = TEMPLATE_DEBUG = True

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql_psycopg2",
        "NAME": "tracebin_server",
        "HOST": "localhost",
    },
}

INSTALLED_APPS = INSTALLED_APPS + [
    "fixture_generator",
]
