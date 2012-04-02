import json
import zlib
from operator import attrgetter

from django.core.urlresolvers import reverse
from django.test import TestCase

from .models import (Log, RuntimeEnviroment, PythonTrace, RegexTrace,
    NumPyPyTrace, TraceSection, ResOpChunk, PythonChunk, Call)


class BaseTraceTests(TestCase):
    def _request(self, method, url_name, **kwargs):
        status_code = kwargs.pop("status_code", 200)
        meth_kwargs = {}
        for key in ["data", "content_type", "CONTENT_ENCODING"]:
            if key in kwargs:
                meth_kwargs[key] = kwargs.pop(key)

        url = reverse(url_name, kwargs=kwargs)
        response = getattr(self.client, method)(url, **meth_kwargs)
        self.assertEqual(response.status_code, status_code)
        return response

    def get(self, url_name, **kwargs):
        return self._request("get", url_name, **kwargs)

    def post(self, url_name, **kwargs):
        return self._request("post", url_name, **kwargs)


    def assert_attributes(self, obj, **kwargs):
        for attr, value in kwargs.iteritems():
            self.assertEqual(getattr(obj, attr), value)

    def assert_json_response(self, response, expected_data):
        self.assertEqual(response["Content-type"], "application/json")
        actual_data = json.loads(response.content)
        self.assertEqual(actual_data, expected_data)


    def create_log(self):
        defaults = {
            "runtime": 42,
        }
        return Log.objects.create(**defaults)

    def create_trace(self, cls, log):
        return cls.objects.create(log=log)

    def create_env_option(self, log):
        return log.enviroment_options.create(log=log, kind=RuntimeEnviroment.JIT_OPTION)

    def create_timeline_event(self, event_type, start_time, end_time, log):
        return log.timeline_events.create(event_type=event_type, start_time=start_time, end_time=end_time)

    def create_call(self, log, name="", start_time=0, end_time=0, parent=None):
        if parent is None:
            call_depth = 0
        else:
            call_depth = parent.call_depth + 1
        return Call.objects.create(
            log=log,
            parent=parent,
            name=name,
            start_time=start_time,
            end_time=end_time,
            call_depth=call_depth
        )


class InheritanceManagerTests(BaseTraceTests):
    def test_simple(self):
        log = self.create_log()
        py_trace = self.create_trace(PythonTrace, log=log)
        re_trace = self.create_trace(RegexTrace, log=log)
        num_trace = self.create_trace(NumPyPyTrace, log=log)

        self.assertQuerysetEqual(log.traces.order_by("id"), [
            (PythonTrace, py_trace.id),
            (RegexTrace, re_trace.id),
            (NumPyPyTrace, num_trace.id),
        ], attrgetter("__class__", "id"))

        with self.assertNumQueries(1):
            list(log.traces.all())

class LogTests(BaseTraceTests):
    def test_options(self):
        log = self.create_log()
        opt = self.create_env_option(log=log)

        with self.assertNumQueries(1):
            self.assertEqual(log.options, {
                "jit": {opt.key: opt},
                "gc": {},
                "build": {},
            })
        with self.assertNumQueries(0):
            log.options

    def test_section_times(self):
        log = self.create_log()
        self.create_timeline_event("a", 0, 10, log=log)
        self.create_timeline_event("b", 10, 20, log=log)
        self.create_timeline_event("a", 20, 40, log=log)

        with self.assertNumQueries(1):
            log.section_times
            log.section_times
        self.assertEqual(log.section_times, [
            ("a", 75),
            ("b", 25),
        ])

class UploadLogTests(BaseTraceTests):
    def test_get_page(self):
        self.get("trace_upload")

    def test_simple_upload(self):
        response = self.post("trace_upload", data=json.dumps({
            "command": "pypy x.py",
            "stdout": "",
            "stderr": "",
            "runtime": 2.3
        }), content_type="application/json", status_code=302)
        log = Log.objects.get()
        self.assert_attributes(log, command="pypy x.py", runtime=2.3, public=True)

    def test_options(self):
        response = self.post("trace_upload", data=json.dumps({
            "command": "pypy x.py",
            "stdout": "",
            "stderr": "",
            "runtime": 2.3,
            "options": {
                "build": {
                    "gc": "minimark",
                    "gcrootfinder": "asmgcc",
                    "pypy_version": "1.8",
                },
                "jit": {
                    "trace_limit": 6000,
                },
                "gc": {
                    "PYPY_GC_NURSERY": "4MB",
                }
            }
        }), content_type="application/json", status_code=302)
        log = Log.objects.get()
        self.assertQuerysetEqual(log.enviroment_options.order_by("kind", "key"), [
            (RuntimeEnviroment.BUILD_OPTION, "gc", "minimark"),
            (RuntimeEnviroment.BUILD_OPTION, "gcrootfinder", "asmgcc"),
            (RuntimeEnviroment.BUILD_OPTION, "pypy_version", "1.8"),
            (RuntimeEnviroment.GC_OPTION, "PYPY_GC_NURSERY", "4MB"),
            (RuntimeEnviroment.JIT_OPTION, "trace_limit", "6000"),
        ], attrgetter("kind", "key", "value"))

    def test_calls(self):
        response = self.post("trace_upload", data=json.dumps({
            "command": "pypy x.py",
            "stdout": "",
            "stderr": "",
            "runtime": 2.3,
            "calls": [
                {
                    "type": "python",
                    "name": "time",
                    "start_time": 0.0,
                    "end_time": 0.1,
                    "subcalls": [],
                },
                {
                    "type": "python",
                    "name": "main",
                    "start_time": 0.11,
                    "end_time": 2.0,
                    "subcalls": [
                        {
                            "type": "python",
                            "name": "f",
                            "start_time": .2,
                            "end_time": .4,
                            "subcalls": [
                                {
                                    "type": "python",
                                    "name": "g",
                                    "start_time": .25,
                                    "end_time": .35,
                                    "subcalls": [],
                                }
                            ]
                        },
                        {
                            "type": "python",
                            "name": "h",
                            "start_time": 1.2,
                            "end_time": 1.8,
                            "subcalls": [],
                        }
                    ],
                },
            ],
        }), content_type="application/json", status_code=302)
        log = Log.objects.get()
        self.assertQuerysetEqual(log.calls.order_by("start_time"), [
            (log, "time", 0.0, 0.1, 0),
            (log, "main", 0.11, 2.0, 0),
            (log, "f", 0.2, 0.4, 1),
            (log, "g", 0.25, 0.35, 2),
            (log, "h", 1.2, 1.8, 1),
        ], attrgetter("log", "name", "start_time", "end_time", "call_depth"))
        subcall = log.calls.get(call_depth=2)
        self.assertEqual(subcall.name, "g")
        self.assertEqual(subcall.parent.name, "f")

    def test_trace(self):
        response = self.post("trace_upload", data=json.dumps({
            "command": "pypy x.py",
            "stdout": "",
            "stderr": "",
            "runtime": 2.3,
            "calls": None,
            "traces": [
                {
                    "type": "python",
                    "root_file": "x.py",
                    "root_function": "main",
                    "sections": [
                        {
                            "label": "Entry",
                            "chunks": [],
                        },
                        {
                            "label": "Preamble",
                            "chunks": [],
                        },
                        {
                            "label": "Loop body",
                            "chunks": [
                                {
                                    "type": "resop",
                                    "ops": "label(i1, i2, descr=TargetToken(700)",
                                },
                                {
                                    "type": "python",
                                    "linenos": [87, 88, 89],
                                    "source": "        def f():\n            i = 1500\n            while i > 0:\n"
                                }
                            ]
                        }
                    ],
                }
            ],
        }), content_type="application/json", status_code=302)

        log = Log.objects.get()
        trace = log.traces.get()
        self.assert_attributes(trace, root_function="main", root_file="x.py", __class__=PythonTrace)
        self.assertQuerysetEqual(trace.sections.all(), [
            (0, TraceSection.ENTRY),
            (1, TraceSection.PREAMBLE),
            (2, TraceSection.LOOP_BODY),
        ], attrgetter("ordering", "label"))
        section = trace.sections.get(label=TraceSection.LOOP_BODY)
        self.assertQuerysetEqual(section.chunks.all(), [
            (ResOpChunk, 0, "label(i1, i2, descr=TargetToken(700)"),
            (PythonChunk, 1, "        def f():\n            i = 1500\n            while i > 0:\n"),
        ], attrgetter("__class__", "ordering", "raw_source"))

        chunk = section.chunks.get(ordering=1)
        self.assert_attributes(chunk, start_line=87, end_line=90)

    def test_efficiency(self):
        subcalls = [
            {
                "type": "python",
                "name": "foo",
                "start_time": i,
                "end_time": i + 1,
                "subcalls": [],
            }
            for i in xrange(1, 99)
        ]
        with self.assertNumQueries(3):
            self.post("trace_upload", data=json.dumps({
                "command": "pypy x.py",
                "stdout": "",
                "stderr": "",
                "runtime": 0,
                "options": {},
                "calls": [
                    {
                        "type": "python",
                        "name": "main",
                        "start_time": 0,
                        "end_time": 100,
                        "subcalls": subcalls,
                    },
                ],
            }), content_type="application/json", status_code=302)

    def test_compressed_data(self):
        data = json.dumps({
            "command": "pypy x.py",
            "stdout": "",
            "stderr": "",
            "runtime": 20,
            "options": {},
            "calls": [],
        })
        self.post("trace_upload", data=zlib.compress(data), content_type="application/json", CONTENT_ENCODING="gzip", status_code=302)
        log = Log.objects.get()
        self.assert_attributes(log, command="pypy x.py", stderr="", runtime=20)

class CallDataTests(BaseTraceTests):
    def test_basic_timeline_data(self):
        log = self.create_log()
        call1 = self.create_call(log=log)
        call2 = self.create_call(log=log)
        call3 = self.create_call(log=log, parent=call2)

        response = self.get("trace_timeline_call_data", id=log.id)
        self.assert_json_response(response, [
            {
                "name": call1.name,
                "start_time": call1.start_time,
                "end_time": call1.end_time,
                "depth": 0,
                "id": call1.id,
            },
            {
                "name": call2.name,
                "start_time": call2.start_time,
                "end_time": call2.end_time,
                "depth": 0,
                "id": call2.id,
            },
            {
                "name": call3.name,
                "start_time": call3.start_time,
                "end_time": call3.end_time,
                "depth": 1,
                "id": call3.id,
            },
        ])

    def test_call_data(self):
        log = self.create_log()
        call1 = self.create_call(log=log, name="a", start_time=0, end_time=2)
        call2 = self.create_call(log=log, name="b", start_time=.5, end_time=1.5, parent=call1)
        call3 = self.create_call(log=log, name="a", start_time=2, end_time=3)

        response = self.get("trace_call_data", id=log.id, data={
            "call_id": call2.id
        })
        self.assert_json_response(response, {
            "call_time": 1,
            "call_exclusive_time": 1,
            "func_time": 1,
            "func_exclusive_time": 1,
        })

        response = self.get("trace_call_data", id=log.id, data={
            "call_id": call1.id
        })
        self.assert_json_response(response, {
            "call_time": 2,
            "call_exclusive_time": 1,
            "func_time": 3,
            "func_exclusive_time": 2,
        })

    def test_call_data_multiple_subcall(self):
        log = self.create_log()
        call = self.create_call(log=log, name="a", start_time=0, end_time=10)
        for i in xrange(1, 9):
            self.create_call(log=log, name="b", start_time=i, end_time=i+1, parent=call)

        response = self.get("trace_call_data", id=log.id, data={
            "call_id": call.id,
        })
        self.assert_json_response(response, {
            "call_time": 10,
            "call_exclusive_time": 2,
            "func_time": 10,
            "func_exclusive_time": 2,
        })