from __future__ import print_function

import sys
import pypyjit

import py

import tracebin


class TestHook(object):
    def test_record_loop(self):
        def f(n):
            while n > 0:
                n -= 1

        with tracebin.record() as recorder:
            f(1500)

        assert len(recorder.traces) == 1
        [trace] = recorder.traces
        assert trace.root_file == __file__
        assert trace.root_function == "f"
        assert len(trace.sections) == 3
        assert [s.label for s in trace.sections] == ["Entry", "Preamble", "Loop body"]

    def test_record_stdout(self):
        with tracebin.record() as recorder:
            pass
        assert recorder.stdout == ""
        assert recorder.stderr == ""

        with tracebin.record() as recorder:
            print(None)
        assert recorder.stdout == "None\n"
        assert recorder.stderr == ""

        with tracebin.record() as recorder:
            print(None, file=sys.stderr)
        assert recorder.stdout == ""
        assert recorder.stderr == "None\n"

    def test_record_build_options(self):
        with tracebin.record() as recorder:
            pass

        assert recorder.options["build"]["gc"] == sys.pypy_translation_info["translation.gc"]
        assert recorder.options["build"]["gcrootfinder"] == sys.pypy_translation_info["translation.gcrootfinder"]
        assert recorder.options["build"]["pypy_version"] == sys._mercurial[2]

    @py.test.mark.xfail
    def test_record_jit_options(self):
        with tracebin.record() as recorder:
            pass

        assert recorder.options["jit"].viewkeys() == pypyjit.defaults.viewkeys()

    def test_record_runtime(self):
        with tracebin.record() as recorder:
            pass

        assert recorder.runtime < 1

    def test_record_aborts(self):
        def f():
            for i in xrange(1500):
                sys.exc_info()
        with tracebin.record() as recorder:
            f()

        assert len(recorder.aborts) == 1
        [abort] = recorder.aborts
        assert abort.reason == "ABORT_ESCAPE"
        assert abort.pycode is f.__code__
        # If this fails check to make sure it still matches the line
        # `sys.exc_info`
        assert abort.lineno == 67

    def test_code_interpolation(self):
        # This test is pretty fragile, but I don't see how else to make sure we
        # don't screw this up.
        def f():
            i = 1500
            while i > 0:
                i -= 1
                i

        with tracebin.record() as recorder:
            f()

        [trace] = recorder.traces
        [entry, preamble, loop] = trace.sections
        assert len(loop.chunks) == 7

        assert loop.chunks[0].get_op_names() == ["label"]
        assert loop.chunks[1].sourcelines == [
            """        def f():\n""",
            """            i = 1500\n""",
            """            while i > 0:\n"""
        ]
        assert loop.chunks[1].linenos == [82, 83, 84]
        assert loop.chunks[2].get_op_names() == ["debug_merge_point", "debug_merge_point", "debug_merge_point", "int_gt", "guard_true", "debug_merge_point"]
        assert loop.chunks[3].sourcelines == [
            """                i -= 1\n"""
        ]
        assert loop.chunks[3].linenos == [85]
        assert loop.chunks[4].get_op_names() == ["debug_merge_point", "debug_merge_point", "debug_merge_point", "int_sub", "debug_merge_point"]
        assert loop.chunks[5].sourcelines == [
            """                i\n"""
        ]
        assert loop.chunks[6].get_op_names() == ["debug_merge_point", "debug_merge_point", "debug_merge_point", "guard_not_invalidated", "getfield_raw", "int_lt", "guard_false", "debug_merge_point", "jump"]

    def test_inlined_function(self):
        def f(i):
            return i - 1
        def main():
            i = 1500
            while i > 0:
                i = f(i)
                i

        with tracebin.record() as recorder:
            main()

        [trace] = recorder.traces
        [entry, preamble, loop] = trace.sections
        assert len(loop.chunks) == 10

        assert loop.chunks[0].get_op_names() == ["label"]
        assert loop.chunks[1].sourcelines == [
            """        def main():\n""",
            """            i = 1500\n""",
            """            while i > 0:\n""",
        ]
        assert loop.chunks[2].get_op_names() == ["debug_merge_point", "debug_merge_point", "debug_merge_point", "int_gt", "guard_true", "debug_merge_point"]
        assert loop.chunks[3].sourcelines == [
            """                i = f(i)\n""",
        ]
        assert loop.chunks[4].get_op_names() == ["debug_merge_point", "debug_merge_point", "debug_merge_point", "force_token"]
        assert loop.chunks[5].sourcelines == [
            """        def f(i):\n""",
            """            return i - 1\n""",
        ]
        assert loop.chunks[5].linenos == [114, 115]
        assert loop.chunks[6].get_op_names() == ["debug_merge_point", "debug_merge_point", "debug_merge_point", "int_sub", "debug_merge_point"]
        assert loop.chunks[7].get_op_names() == ["debug_merge_point"]
        assert loop.chunks[8].sourcelines == [
            """                i\n""",
        ]
        assert loop.chunks[9].get_op_names() == ["debug_merge_point", "debug_merge_point", "debug_merge_point", "guard_not_invalidated", "getfield_raw", "int_lt", "guard_false", "debug_merge_point", "jump"]
