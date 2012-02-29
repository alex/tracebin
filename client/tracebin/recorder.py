import io
import inspect
import mmap
import pypyjit
import struct
import sys
import time
from collections import defaultdict
from contextlib import contextmanager

from logbook import Logger

from tracebin.aborts import PythonAbort
from tracebin.calls import PythonCall
from tracebin.traces import PythonTrace
from tracebin.utils import read_unpack


PROFILE_IDENTIFIER = 72

CALL_EVENT = 0
RETURN_EVENT = 1

@contextmanager
def record(**kwargs):
    recorder = Recorder()
    with recorder.record(**kwargs):
        yield recorder

class Recorder(object):
    def __init__(self):
        self.log = Logger()
        self.traces = []
        self.aborts = []
        self.calls = None
        self.options = {
            "build": {},
            "jit": {},
            "gc": {},
        }

    @contextmanager
    def record(self, profile=False):
        self.enable(profile=profile)
        try:
            yield
        finally:
            self.disable(profile)

    def enable(self, profile):
        pypyjit.set_compile_hook(self.on_compile)
        pypyjit.set_abort_hook(self.on_abort)
        self._backup_stdout = sys.stdout
        self._backup_stderr = sys.stderr
        sys.stdout = RecordingStream(sys.stdout)
        sys.stderr = RecordingStream(sys.stderr)

        self.options["build"]["gc"] = sys.pypy_translation_info["translation.gc"]
        self.options["build"]["gcrootfinder"] = sys.pypy_translation_info["translation.gcrootfinder"]
        self.options["build"]["pypy_version"] = sys._mercurial[2]

        if profile:
            self._profile_mmaps = []
            self._new_mmap()
            sys.setprofile(self.on_profile)

        self._start_time = time.time()

    def disable(self, profile):
        self.runtime = time.time() - self._start_time
        del self._start_time

        if profile:
            sys.setprofile(None)

        pypyjit.set_compile_hook(None)
        pypyjit.set_abort_hook(None)

        self.stdout = sys.stdout._content.getvalue()
        self.stderr = sys.stderr._content.getvalue()
        sys.stdout = self._backup_stdout
        sys.stderr = self._backup_stderr
        del self._backup_stdout
        del self._backup_stderr

        if profile:
            self._find_calls()

    def _new_mmap(self):
        self._current_profile_mmap = mmap.mmap(-1, 4 * 1024 * 1024)
        self._profile_mmaps.append(self._current_profile_mmap)

    def _find_calls(self):
        calls = []
        stack = []
        for m in self._profile_mmaps:
            m.seek(0)
            while True:
                b = m.read(struct.calcsize("=B"))
                if not b:
                    break
                marker, = struct.unpack("=B", b)
                if marker == 0:
                    m.close()
                    break
                elif marker != PROFILE_IDENTIFIER:
                    raise Exception

                event_id, timestamp = read_unpack("=Bd", m)
                if event_id == CALL_EVENT:
                    func_name_len, = read_unpack("=L", m)
                    func_name = m.read(func_name_len)
                    stack.append((func_name, timestamp))
                elif event_id == RETURN_EVENT:
                    try:
                        prev_func_name, prev_timestamp = stack.pop()
                    except IndexError:
                        # The function where the profile hook was enabled
                        # (and everything up the stack from there) will
                        # have returns recorded, but no call, so we ignore
                        # them.
                        if not stack:
                            continue
                    calls.append(PythonCall(prev_func_name, prev_timestamp, timestamp))

        self.calls = calls

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

    def on_profile(self, frame, event, arg):
        if event == "call" or event == "c_call":
            event_id = CALL_EVENT
            if event == "call":
                target = frame.f_code.co_name
            elif event == "c_call":
                target = arg.__name__
            content = struct.pack("=BBdL", PROFILE_IDENTIFIER, event_id, time.time(), len(target)) + target
        elif event == "return" or event == "c_return":
            event_id = RETURN_EVENT
            content = struct.pack("=BBd", PROFILE_IDENTIFIER, event_id, time.time())

        if self._current_profile_mmap.tell() + len(content) > len(self._current_profile_mmap):
            self._new_mmap()
        self._current_profile_mmap.write(content)

    def visit(self, visitor):
        return visitor.visit_recorder(self)


class RecordingStream(object):
    def __init__(self, real_stream):
        self._content = io.BytesIO()
        self._real_stream = real_stream

    def write(self, content):
        self._content.write(content)
        self._real_stream.write(content)
