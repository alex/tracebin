from django.conf.urls import patterns, include, url
from django.contrib.staticfiles.urls import staticfiles_urlpatterns

from . import views


urlpatterns = patterns("",
    url(r"^$", views.home, name="home"),
    url(r"^trace/", include("tracebin_server.traces.urls")),
    url(r"^users/", include("django.contrib.auth.urls")),
) + staticfiles_urlpatterns()
