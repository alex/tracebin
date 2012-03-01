import sys

import py

import tracebin


class TestSerialization(object):
    def test_recorder(self, serializer_cls):
        with tracebin.record() as recorder:
            pass

        serializer = serializer_cls(recorder)
        data = serializer.get_data()
        assert data.viewkeys() == {"traces", "aborts", "runtime", "stdout", "stderr", "options", "calls"}
        assert data["calls"] is None
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

    def test_calls(self, serializer_cls):
        def f():
            pass
        def main():
            f()
            f()
            f()

        with tracebin.record(profile=True) as recorder:
            main()

        serializer = serializer_cls(recorder)
        dump = serializer.dump()
        data = serializer.load(dump)

        assert len(data["calls"]) == 2
        assert len(data["calls"][1]["subcalls"]) == 3