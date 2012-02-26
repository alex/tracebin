import io
import inspect
import pypyjit
import sys
import time
from contextlib import contextmanager

from logbook import Logger

from tracebin.aborts import PythonAbort
from tracebin.traces import PythonTrace


@contextmanager
def record():
    recorder = Recorder()
    with recorder.record():
        yield recorder


class Recorder(object):
    def __init__(self):
        self.log = Logger()
        self.traces = []
        self.aborts = []
        self.options = {
            "build": {},
            "jit": {},
            "gc": {},
        }

    @contextmanager
    def record(self):
        self.enable()
        try:
            yield
        finally:
            self.disable()

    def enable(self):
        pypyjit.set_compile_hook(self.on_compile)
        pypyjit.set_abort_hook(self.on_abort)
        self._backup_stdout = sys.stdout
        self._backup_stderr = sys.stderr
        sys.stdout = RecordingStream(sys.stdout)
        sys.stderr = RecordingStream(sys.stderr)

        self.options["build"]["gc"] = sys.pypy_translation_info["translation.gc"]
        self.options["build"]["gcrootfinder"] = sys.pypy_translation_info["translation.gcrootfinder"]
        self.options["build"]["pypy_version"] = sys._mercurial[2]

        # self.options["jit"].update(pypyjit.get_params())

        self._start_time = time.time()

    def disable(self):
        self.runtime = time.time() - self._start_time
        del self._start_time

        pypyjit.set_compile_hook(None)
        pypyjit.set_abort_hook(None)

        self.stdout = sys.stdout._content.getvalue()
        self.stderr = sys.stderr._content.getvalue()
        sys.stdout = self._backup_stdout
        sys.stderr = self._backup_stderr
        del self._backup_stdout
        del self._backup_stderr

    def on_compile(self, jitdriver_name, kind, greenkey, ops, asm_ptr, asm_len):
        if kind != "loop":
            self.log.warning("[compile] Unhandled compiled kind: %s" % kind)
            return

        if jitdriver_name == "pypyjit":
            self.traces.append(PythonTrace(greenkey, ops, asm_ptr, asm_len))
        else:
            self.log.warning("[compile] Unhandled jitdriver: %s" % jitdriver_name)

    def on_abort(self, jitdriver_name, greenkey, reason):
        if jitdriver_name == "pypyjit":
            frame = inspect.currentframe().f_back
            self.aborts.append(
                PythonAbort(reason, frame.f_code, frame.f_lineno)
            )
        else:
            self.log.warning("[abort] Unhandled jitdriver: %s" % jitdriver_name)

    def visit(self, visitor):
        return visitor.visit_recorder(self)


class RecordingStream(object):
    def __init__(self, real_stream):
        self._content = io.BytesIO()
        self._real_stream = real_stream

    def write(self, content):
        self._content.write(content)
        self._real_stream.write(content)
