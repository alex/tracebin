import json

from django.shortcuts import render, get_object_or_404, redirect
from django.views.decorators.csrf import csrf_exempt

from .models import Log


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
        command=data["command"],
        stdout=data["stdout"],
        stderr=data["stderr"],
        runtime=data["runtime"],
    )
    return redirect(log)

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