import json


class BaseSerializer(object):
    ALL_SERIALIZERS = {}

    def __init__(self, obj):
        self.obj = obj

    @classmethod
    def register(cls, subcls):
        assert subcls.name not in cls.ALL_SERIALIZERS
        cls.ALL_SERIALIZERS[subcls.name] = subcls
        return subcls

    def get_data(self):
        return self.visit(self.obj)

    def visit(self, obj):
        return obj.visit(self)

    def visit_recorder(self, recorder):
        return {
            "traces": [self.visit(trace) for trace in recorder.traces],
            "aborts": [self.visit(abort) for abort in recorder.aborts],
            "options": {k: v.copy() for k, v in recorder.options.iteritems()},
            "runtime": recorder.runtime,
            "stdout": recorder.stdout,
            "stderr": recorder.stderr,
        }

    def visit_python_trace(self, trace):
        return {
            "type": "python",
            "root_file": trace.root_file,
            "root_function": trace.root_function,
            "sections": [self.visit(section) for section in trace.sections],
        }

    def visit_trace_section(self, section):
        return {
            "label": section.label,
            "chunks": [self.visit(chunk) for chunk in section.chunks]
        }

    def visit_resop_chunk(self, chunk):
        return {
            "type": "resop",
            "ops": u"\n".join(repr(op for op in chunk.ops))
        }

    def visit_python_chunk(self, chunk):
        return {
            "type": "python",
            "source": u"".join(chunk.sourcelines),
            "linenos": chunk.linenos,
        }

    def visit_python_abort(self, abort):
        return {
            "type": "python",
            "filename": abort.pycode.co_filename,
            "lineno": abort.lineno,
            "reason": abort.reason,
        }


@BaseSerializer.register
class JSONSerializer(BaseSerializer):
    name = "json"

    def dump(self):
        return json.dumps(self.get_data())

    @classmethod
    def load(cls, data):
        return json.loads(data)