import subprocess
import sys
import textwrap

import py

from tracebin.serializers import JSONSerializer


@py.test.mark.parametrize("serializer_cls", [JSONSerializer])
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
            [sys.executable, "-mtracebin", str(tmpdir.join("t.py")), "--dump={}".format(serializer_cls.name)],
        )

        data = serializer_cls.load(stdout)
        assert data.viewkeys() == {"stdout", "stderr", "aborts", "runtime", "traces", "options", "calls"}
        assert len(data["traces"]) == 1
        assert data["stdout"] == ""
        assert data["stderr"] == ""
        assert data["aborts"] == []
