import json
import zlib
from collections import defaultdict

from django.db import transaction
from django.db.models import Sum, Min, Max
from django.shortcuts import render, get_object_or_404, redirect
from django.views.decorators.csrf import csrf_exempt

from tracebin_server.utils import JSONResponse

from .models import (Log, RuntimeEnviroment, PythonTrace, TraceSection,
    ResOpChunk, PythonChunk, Call)


def trace_overview(request, id):
    log = get_object_or_404(Log, id=id)
    return render(request, "traces/trace/overview.html", {
        "page": "overview",
        "log": log,
    })

@csrf_exempt
@transaction.commit_on_success
def trace_upload(request):
    if request.method == "GET":
        return render(request, "traces/trace/new.html")
    assert request.method == "POST"
    assert request.META["CONTENT_TYPE"] == "application/json"
    encoding = request.META.get("CONTENT_ENCODING")
    if encoding == "gzip":
        raw_data = zlib.decompress(request.raw_post_data)
    elif encoding is None:
        raw_data = request.raw_post_data
    else:
        raise NotImplementedError(encoding)
    data = json.loads(raw_data)
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
    # These are calls which can be grouped together into a single insert.
    no_children_calls = []
    for call in calls:
        kwargs = {
            "start_time": call["start_time"],
            "end_time": call["end_time"],
            "call_depth": depth,
            "name": call["name"],
            "parent": parent,
            "log": log,
        }
        if call["subcalls"]:
            inst = Call.objects.create(**kwargs)
            _add_calls(log, call["subcalls"], parent=inst)
        else:
            no_children_calls.append(Call(**kwargs))
    if no_children_calls:
        Call.objects.bulk_create(no_children_calls)



def trace_compiled_list(request, id):
    log = get_object_or_404(Log, id=id)
    return render(request, "traces/trace/compiled_list.html", {
        "page": "compiled",
        "log": log,
    })

def trace_timeline(request, id):
    log = get_object_or_404(Log, id=id)
    return render(request, "traces/trace/timeline.html", {
        "page": "timeline",
        "log": log,
    })

def trace_compiled_detail(request, id, compiled_id):
    log = get_object_or_404(Log, id=id)
    trace = get_object_or_404(log.traces.all(), id=compiled_id)
    return render(request, "traces/trace/compiled_detail.html", {
        "page": "compiled",
        "log": log,
        "trace": trace,
    })

def trace_timeline_call_data(request, id):
    log = get_object_or_404(Log, id=id)

    start_percent = float(request.GET.get("start_percent", 0))
    end_percent = float(request.GET.get("end_percent", 1))

    absolute_start_end = log.calls.aggregate(Min("start_time"), Max("end_time"))
    absolute_start = absolute_start_end["start_time__min"]
    absolute_end = absolute_start_end["end_time__max"]

    filters = {
        "end_time__gte": absolute_start + (start_percent * (absolute_end - absolute_start)),
        "start_time__lte": absolute_start + (end_percent * (absolute_end - absolute_start)),
    }

    data = []
    calls = log.calls.filter(**filters)
    for call in calls.iterator():
        data.append({
            "name": call.name,
            "start_time": call.start_time,
            "end_time": call.end_time,
            "depth": call.call_depth,
            "id": call.id,
        })

    return JSONResponse(data)

def trace_call_data(request, id):
    log = get_object_or_404(Log, id=id)
    call = get_object_or_404(log.calls.all(), id=request.GET["call_id"])

    call_time = call.end_time - call.start_time

    subcall_times = call.subcalls.aggregate(
        total_start_time=Sum("start_time"),
        total_end_time=Sum("end_time")
    )
    call_total_subcall_start_time = subcall_times["total_start_time"] or 0
    call_total_subcall_end_time = subcall_times["total_end_time"] or 0
    call_subcall_time = call_total_subcall_end_time - call_total_subcall_start_time

    call_exclusive_time = call_time - call_subcall_time

    func_times = log.calls.filter(name=call.name).aggregate(
        total_start_time=Sum("start_time"),
        total_end_time=Sum("end_time"),
    )
    func_total_start_time = func_times["total_start_time"] or 0
    func_total_end_time = func_times["total_end_time"] or 0

    func_time = func_total_end_time - func_total_start_time

    func_subcall_times = log.calls.filter(name=call.name).aggregate(
        total_subcalls_start_time=Sum("subcalls__start_time"),
        total_subcalls_end_time=Sum("subcalls__end_time"),
    )
    func_total_subcall_start_time = func_subcall_times["total_subcalls_start_time"] or 0
    func_total_subcall_end_time = func_subcall_times["total_subcalls_end_time"] or 0
    func_subcalls_time = func_total_subcall_end_time - func_total_subcall_start_time

    func_exclusive_time = func_time - func_subcalls_time

    data = {
        "call_time": call_time,
        "call_exclusive_time": call_exclusive_time,
        "func_time": func_time,
        "func_exclusive_time": func_exclusive_time,
    }
    return JSONResponse(data)