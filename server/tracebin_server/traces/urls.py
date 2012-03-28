from django.conf.urls import patterns, include, url

from . import views


urlpatterns = patterns("",
    url(r"^new/$", views.trace_upload, name="trace_upload"),
    url(r"^(?P<id>\d+)/$", views.trace_overview, name="trace_overview"),
    url(r"^(?P<id>\d+)/compiled/$", views.trace_compiled_list, name="trace_compiled_list"),
    url(r"^(?P<id>\d+)/compiled/(?P<compiled_id>\d+)/$", views.trace_compiled_detail, name="trace_compiled_detail"),
    url(r"^(?P<id>\d+)/timeline/$", views.trace_timeline, name="trace_timeline"),

    url(r"^(?P<id>\d+)/timeline-call-data\.json", views.trace_timeline_call_data, name="trace_timeline_call_data"),
    url(r"^(?P<id>\d+)/call-data\.json", views.trace_call_data, name="trace_call_data"),
)