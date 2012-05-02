import colorsys
import itertools
import json
import zlib
from collections import defaultdict, namedtuple
from operator import attrgetter

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

CallNode = namedtuple("CallNode", ["name", "start_time", "end_time", "depth", "color"])

SATURATION = .8
VALUE = .8

def generate_colors():
    # Code from Marty Alchin
    for i in itertools.count():
        h = i * .15
        s = .3 + ((i * .15) % .7)
        v = .3 + (((i + 3) * .15) % .7)
        r, g, b = colorsys.hsv_to_rgb(h, s, v)
        yield int(r * 255), int(g * 255), int(b * 255)

def compute_pixels(node, slice_start, slice_end):
    slice_width = slice_end - slice_start
    return 675 * ((node.end_time - node.start_time) / slice_width)

def merge_nodes(node1, node2):
    names = node1.name | node2.name
    start_time = min(node1.start_time, node2.start_time)
    end_time = max(node1.start_time, node2.start_time)
    assert node1.depth == node2.depth

    node1_weight = (node1.end_time - node1.start_time) / (end_time - start_time)
    node2_weight = (node2.end_time - node2.start_time) / (end_time - start_time)
    r = node1.color[0] * node1_weight + node2.color[0] * node2_weight
    g = node1.color[1] * node1_weight + node2.color[1] * node2_weight
    b = node1.color[2] * node1_weight + node2.color[2] * node2_weight
    return CallNode(names, start_time, end_time, node1.depth, (int(r), int(g), int(b)))

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

    data = defaultdict(list)
    calls = log.calls.filter(**filters)
    color_generator = generate_colors()
    known_colors = {}
    for call in calls.iterator():
        if call.name not in known_colors:
            known_colors[call.name] = color_generator.next()
        data[call.call_depth].append(CallNode(
            {call.name}, call.start_time, call.end_time, call.call_depth,
            known_colors[call.name]
        ))

    slice_start = float("inf")
    slice_end = float("-inf")
    for calls in data.itervalues():
        slice_start = min(slice_start, min(map(attrgetter("start_time"), calls)))
        slice_end = max(slice_end, max(map(attrgetter("end_time"), calls)))

    for depth, calls in data.items():
        new_calls = []
        iterator = iter(sorted(calls, key=attrgetter("start_time")))
        for node in iterator:
            while compute_pixels(node, slice_start, slice_end) < 2:
                try:
                    next_node = iterator.next()
                except StopIteration:
                    break
                node = merge_nodes(node, next_node)
            new_calls.append(node)
        data[depth] = new_calls


    return JSONResponse([
        {
            "name": ", ".join(node.name),
            "start_time": node.start_time,
            "end_time": node.end_time,
            "depth": node.depth,
            "color": "#%02X%02X%02X" % node.color,
        }
        for depth in data.itervalues() for node in depth
    ])

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