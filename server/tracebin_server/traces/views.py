import json

from django.shortcuts import render, get_object_or_404, redirect
from django.views.decorators.csrf import csrf_exempt

from .models import Log, RuntimeEnviroment, PythonCall


def trace_overview(request, id):
    log = get_object_or_404(Log, id=id)
    return render(request, "traces/trace/overview.html", {
        "page": "overview",
        "log": log,
    })

@csrf_exempt
def trace_upload(request):
    if request.method == "GET":
        return render(request, "traces/trace/new.html")
    assert request.method == "POST"
    assert request.META["CONTENT_TYPE"] == "application/json"
    data = json.loads(request.raw_post_data)
    # They're all public=True until we have authentication for the client.
    log = Log.objects.create(
        public=True,
        command=data.get("command", u""),
        stdout=data.get("stdout", u""),
        stderr=data.get("stderr", u""),
        runtime=data.get("runtime"),
    )
    for key, value in data.get("options", {}).iteritems():
        if key == "jit":
            kind = RuntimeEnviroment.JIT_OPTION
        elif key == "gc":
            kind = RuntimeEnviroment.GC_OPTION
        elif key == "build":
            kind = RuntimeEnviroment.BUILD_OPTION

        for key, value in value.iteritems():
            log.enviroment_options.create(kind=kind, key=key, value=value)

    _add_calls(log, data.get("calls"))
    return redirect(log)

def _add_calls(log, calls, parent=None):
    if calls is None:
        return
    if parent is None:
        depth = 0
    else:
        depth = parent.call_depth + 1
    for call in calls:
        kwargs = {
            "start_time": call["start_time"],
            "end_time": call["end_time"],
            "call_depth": depth,
            "parent": parent,
            "log": log,
        }
        if call["type"] == "python":
            kwargs["func_name"] = call["func_name"]
            cls = PythonCall
        inst = cls.objects.create(**kwargs)
        _add_calls(log, call["subcalls"], parent=inst)


def trace_compiled_list(request, id):
    log = get_object_or_404(Log, id=id)
    return render(request, "traces/trace/compiled_list.html", {
        "page": "compiled",
        "log": log,
    })

def trace_timeline(request, id):
    pass

def trace_compiled_detail(request, id, compiled_id):
    log = get_object_or_404(Log, id=id)
    trace = get_object_or_404(log.traces.all(), id=compiled_id)
    return render(request, "traces/trace/compiled_detail.html", {
        "page": "compiled",
        "log": log,
        "trace": trace,
    })