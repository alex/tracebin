import os
import random
import subprocess
import shutil
import tempfile
import time
from ConfigParser import ConfigParser

import requests

from tracebin.serializers import JSONSerializer


class TracebinServer(object):
    def __init__(self, server_dir, venv_dir):
        self.server_dir = server_dir
        self.venv_dir = venv_dir
        self.proc = None
        self.port = random.randrange(8000, 9000)

    def start(self):
        self.proc = subprocess.Popen([
            os.path.join(self.venv_dir, "bin", "python"),
            os.path.join(self.server_dir, "manage.py"),
            "client_test",
            "testserver",
            "--addrport={:d}".format(self.port)
        ])
        self._check_proc()
        # Give the server time to start up before trying to make a request
        # against it.
        time.sleep(12)

    def shutdown(self):
        if self.proc is not None:
            self.proc.terminate()
            self.proc = None

    def _check_proc(self):
        status = self.proc.poll()
        assert status is None

    @property
    def host(self):
        return "localhost"

    def write_config(self, tmpdir):
        c = ConfigParser()
        c.add_section("server")
        c.set("server", "host", self.host)
        c.set("server", "port", self.port)
        with tmpdir.join("config.ini").open("w") as f:
            c.write(f)
        return f.name

    def get(self, path):
        self._check_proc()
        return requests.get("http://{}:{}{}".format(self.host, self.port, path))


def pytest_funcarg__server(request):
    venv_dir = tempfile.mkdtemp()
    server_dir = os.path.join(os.path.dirname(__file__), os.pardir, os.pardir, "server")

    subprocess.check_call([
        "virtualenv", "-p", "/usr/bin/python", venv_dir
    ])
    subprocess.check_call([
        os.path.join(venv_dir, "bin", "pip"), "install", "-r", os.path.join(server_dir, "requirements", "production.txt")
    ])
    server = TracebinServer(server_dir, venv_dir)

    request.addfinalizer(server.shutdown)
    request.addfinalizer(lambda: shutil.rmtree(venv_dir))

    server.start()
    return server

def pytest_generate_tests(metafunc):
    if "serializer_cls" in metafunc.funcargnames:
        metafunc.parametrize("serializer_cls", [JSONSerializer])
