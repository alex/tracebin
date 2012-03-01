import json
from operator import attrgetter

from django.core.urlresolvers import reverse
from django.test import TestCase

from .models import Log, RuntimeEnviroment, PythonTrace, RegexTrace, NumPyPyTrace


class BaseTraceTests(TestCase):
    def _request(self, method, url_name, url_kwargs, **kwargs):
        status_code = url_kwargs.pop("status_code", 200)
        url = reverse(url_name, kwargs=url_kwargs)
        response = getattr(self.client, method)(url, **kwargs)
        self.assertEqual(response.status_code, status_code)
        return response

    def get(self, url_name, **kwargs):
        return self._request("get", url_name, url_kwargs=kwargs)

    def post(self, url_name, **kwargs):
        url_kwargs = kwargs
        kwargs = {}
        for key in ["data", "content_type"]:
            if key in url_kwargs:
                kwargs[key] = url_kwargs.pop(key)
        return self._request("post", url_name, url_kwargs=url_kwargs, **kwargs)


    def assert_attributes(self, obj, **kwargs):
        for attr, value in kwargs.iteritems():
            self.assertEqual(getattr(obj, attr), value)


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
