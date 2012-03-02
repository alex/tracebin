import json

from django.shortcuts import render, get_object_or_404, redirect
from django.views.decorators.csrf import csrf_exempt

from .models import (Log, RuntimeEnviroment, PythonTrace, TraceSection,
    ResOpChunk, PythonChunk, PythonCall)


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

    for trace in data.get("traces", []):
        kwargs = {"log": log}
        if trace["type"] == "python":
            kwargs["root_file"] = trace["root_file"]
            kwargs["root_function"] = trace["root_function"]
            cls = PythonTrace

        trace_obj = cls.objects.create(**kwargs)
        for i, section in enumerate(trace["sections"]):
            if section["label"] == "Entry":
                label = TraceSection.ENTRY
            elif section["label"] == "Preamble":
                label = TraceSection.PREAMBLE
            elif section["label"] == "Loop body":
                label = TraceSection.LOOP_BODY

            section_obj = trace_obj.sections.create(ordering=i, label=label)
            for i, chunk in enumerate(section["chunks"]):
                kwargs = {
                    "section": section_obj,
                    "ordering": i,
                }
                if chunk["type"] == "resop":
                    cls = ResOpChunk
                    kwargs["raw_source"] = chunk["ops"]
                elif chunk["type"] == "python":
                    cls = PythonChunk
                    kwargs["raw_source"] = chunk["source"]
                    assert sorted(chunk["linenos"]) == chunk["linenos"]
                    kwargs["start_line"] = chunk["linenos"][0]
                    kwargs["end_line"] = chunk["linenos"][-1] + 1
                cls.objects.create(**kwargs)


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