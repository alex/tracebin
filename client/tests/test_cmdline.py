import subprocess
import sys
import textwrap
import urlparse

import py


class TestCommandLine(object):
    def test_module_executability(self, tmpdir, serializer_cls):
        tmpdir.join("t.py").write(textwrap.dedent("""
        import sys

        def main():
            for i in xrange(1500):
                pass

        if __name__ == "__main__":
            main()
        else:
            sys.exit(__name__)
        """))

        stdout = subprocess.check_output(
            [sys.executable, "-mtracebin", str(tmpdir.join("t.py")), "--action=dump", "--dump-format={}".format(serializer_cls.name)],
        )

        data = serializer_cls.load(stdout)
        assert data.viewkeys() == {"stdout", "stderr", "aborts", "runtime", "traces", "options", "calls", "command"}
        assert len(data["traces"]) == 1
        assert data["stdout"] == ""
        assert data["stderr"] == ""
        assert data["aborts"] == []

    def test_upload(self, tmpdir, server):
        tmpdir.join("t.py").write(textwrap.dedent("""
        import sys

        def main():
            for i in xrange(1500):
                pass

        if __name__ == "__main__":
            main()
        else:
            sys.exit(__name__)
        """))

        stdout = subprocess.check_output(
            [sys.executable, "-mtracebin", "--config={}".format(server.write_config(tmpdir)), str(tmpdir.join("t.py"))]
        )
        [line] = stdout.splitlines()
        url = urlparse.urlparse(line)
        assert url.netloc == "{}:{}".format(server.host, server.port)
        assert url.path == "/trace/1/"

        response = server.get(url.path)
        assert response.status_code == 200
