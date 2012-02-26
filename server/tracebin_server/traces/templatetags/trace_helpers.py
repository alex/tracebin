import itertools

from django import template
from django.template.loader import render_to_string
from django.utils.encoding import force_unicode


register = template.Library()


@register.filter
def compiled_trace_description(compiled):
    return render_to_string("traces/partials/compiled_trace_description.html", {
        "compiled": compiled,
    })

@register.filter
def group_traces_by_type(traces):
    traces = sorted(traces, key=type)
    return [
        (k, list(v))
        for k, v in itertools.groupby(traces, key=type)
    ]


@register.filter
def newlinejoin(values):
    return u"\n".join(map(force_unicode, values))
