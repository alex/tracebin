import sys

import py

import tracebin
from tracebin.serializers import JSONSerializer


@py.test.mark.parametrize("serializer_cls", [JSONSerializer])
class TestSerialization(object):
    def test_recorder(self, serializer_cls):
        with tracebin.record() as recorder:
            pass

        serializer = serializer_cls(recorder)
        data = serializer.get_data()
        assert data.viewkeys() == {"traces", "aborts", "runtime", "stdout", "stderr", "options"}
        dump = serializer.dump()
        assert data == serializer_cls.load(dump)

    def test_trace(self, serializer_cls):
        with tracebin.record() as recorder:
            for i in xrange(1500):
                pass

        serializer = serializer_cls(recorder)
        serializer.dump()

    def test_abort(self, serializer_cls):
        with tracebin.record() as recorder:
            for i in xrange(1500):
                sys.exc_info()

        serializer = serializer_cls(recorder)
        serializer.dump()
