import os
import subprocess
import shutil
import tempfile
import time

import requests


class TracebinServer(object):
    def __init__(self, server_dir, venv_dir):
        self.server_dir = server_dir
        self.venv_dir = venv_dir
        self.proc = None

    def start(self):
        # A stupid empty JSON file to appease testever.
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            f.write("[]")

        self.proc = subprocess.Popen([
            os.path.join(self.venv_dir, "bin", "python"),
            os.path.join(self.server_dir, "manage.py"),
            "development",
            "testserver",
            f.name,
        ], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self._check_proc()
        # Give the server time to start up before trying to make a request
        # against it.
        time.sleep(.5)

    def shutdown(self):
        if self.proc is not None:
            self.proc.terminate()
            self.proc = None

    def _check_proc(self):
        status = self.proc.poll()
        assert status is None

    def get(self, path):
        self._check_proc()
        return requests.get("http://localhost:8000" + path)


def pytest_funcarg__server(request):
    venv_dir = tempfile.mkdtemp()
    server_dir = os.path.join(os.path.dirname(__file__), os.pardir, os.pardir, "server")

    subprocess.check_call([
        "virtualenv", "-p", "/usr/bin/python", venv_dir
    ])
    subprocess.check_call([
        os.path.join(venv_dir, "bin", "pip"), "install", "-r", os.path.join(server_dir, "requirements", "development.txt")
    ])
    server = TracebinServer(server_dir, venv_dir)

    request.addfinalizer(server.shutdown)
    request.addfinalizer(lambda: shutil.rmtree(venv_dir))

    server.start()
    return server