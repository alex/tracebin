import subprocess
import sys
import textwrap
import urlparse

import py

from tracebin import cmdline


class TestCommandLine(object):
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

    def test_dump(self, tmpdir, capsys, serializer_cls):
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

        res = cmdline.main(
            [sys.executable, str(tmpdir.join("t.py")), "--action=dump", "--dump-format={}".format(serializer_cls.name)]
        )
        assert res == 0

        stdout, stderr = capsys.readouterr()
        assert not stderr
        data = serializer_cls.load(stdout)
        assert data.viewkeys() == {"stdout", "stderr", "aborts", "runtime", "traces", "options", "calls", "command"}
        assert len(data["traces"]) == 1
        assert data["stdout"] == ""
        assert data["stderr"] == ""
        assert data["aborts"] == []
        assert data["calls"] is None

    def test_profile(self, tmpdir, capsys, serializer_cls):
        tmpdir.join("t.py").write(textwrap.dedent("""
        def add(x, y):
            return x + y

        def main():
            i = 0
            while i < 1500:
                i = add(i, 1)

        if __name__ == "__main__":
            main()
        """))

        res = cmdline.main(
            [sys.executable, str(tmpdir.join("t.py")), "--action=dump", "--dump-format={}".format(serializer_cls.name), "--profile"]
        )
        assert res == 0

        stdout, stderr = capsys.readouterr()
        data = serializer_cls.load(stdout)
        assert data["calls"] is not None