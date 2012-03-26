from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.db import models
from django.utils.functional import cached_property

from .managers import InheritanceManager


class Log(models.Model):
    # Anonymous users are None.
    uploader = models.ForeignKey(User, null=True)
    public = models.BooleanField(default=False)

    command = models.CharField(max_length=255)
    stdout = models.TextField()
    stderr = models.TextField()

    runtime = models.FloatField()

    def get_absolute_url(self):
        return reverse("trace_overview", kwargs={"id": self.id})

    @cached_property
    def options(self):
        opts = {
            "build": {},
            "gc": {},
            "jit": {}
        }
        for option in self.enviroment_options.all():
            opts[option.get_kind_display()][option.key] = option
        return opts

    @cached_property
    def stats(self):
        stats = {}
        stats["runtime"] = StatCounter(log=self, label="runtime", count=self.runtime)
        for stat in self.counters.all():
            stats[stat.label] = stat
        return stats

    @cached_property
    def section_times(self):
        qs = sorted(self.timeline_events.values(
            "event_type"
        ).annotate(
            start_times=models.Sum("start_time"), end_times=models.Sum("end_time")
        ), key=lambda o: o["end_times"] - o["start_times"], reverse=True)
        total_time = 0.0
        for section in qs:
            total_time += section["end_times"] - section["start_times"]
        return [
            (section["event_type"], 100 * (section["end_times"] - section["start_times"]) / total_time)
            for section in qs
        ]


class RuntimeEnviroment(models.Model):
    BUILD_OPTION, GC_OPTION, JIT_OPTION = 1, 2, 3
    KIND_CHOICES = [
        (BUILD_OPTION, "build"),
        (GC_OPTION, "gc"),
        (JIT_OPTION, "jit")
    ]

    log = models.ForeignKey(Log, related_name="enviroment_options")
    kind = models.IntegerField(choices=KIND_CHOICES)
    key = models.CharField(max_length=255)
    value = models.CharField(max_length=255)

    class Meta:
        unique_together = [
            ("log", "kind", "key"),
        ]

class TimelineEvent(models.Model):
    log = models.ForeignKey(Log, related_name="timeline_events")
    # 100 should be enough for anyone. And it really sucks for you if it isn't,
    # because you'll get an IntegerityError or something.
    event_type = models.CharField(max_length=100)
    # These are measured in some weird format which I think represents big
    # numbers, the exact units don't matter ATM, all we plan to do is display
    # the breakdowns and a timeline.
    start_time = models.BigIntegerField()
    end_time = models.BigIntegerField()


class StatCounter(models.Model):
    log = models.ForeignKey(Log, related_name="counters")
    # Turn this to an IntegerField with choices, so we can supply verbose
    # descriptive text.
    label = models.CharField(max_length=255)
    count = models.IntegerField()

class BaseTrace(models.Model):
    log = models.ForeignKey(Log, related_name="traces")

    objects = InheritanceManager()

class PythonTrace(BaseTrace):
    is_python = True
    description = "Python loops"

    root_file = models.CharField(max_length=255)
    root_function = models.CharField(max_length=255)

class RegexTrace(BaseTrace):
    is_regex = True
    description = "Regular expressions"

    pattern = models.CharField(max_length=255)

class NumPyPyTrace(BaseTrace):
    is_numpypy = True
    description = "NumPyPy expressions"

    # Not sure how long these could be, TextField to be safe.
    debug_repr = models.TextField()


class TraceSection(models.Model):
    ENTRY, PREAMBLE, LOOP_BODY = 1, 2, 3
    LABEL_CHOICES = [
        (ENTRY, "Entry"),
        (PREAMBLE, "Preamble"),
        (LOOP_BODY, "Loop body"),
    ]

    ordering = models.IntegerField()
    trace = models.ForeignKey(BaseTrace, related_name="sections")
    label = models.IntegerField(choices=LABEL_CHOICES)

    class Meta:
        unique_together = [
            ("ordering", "trace")
        ]

class TraceChunk(models.Model):
    section = models.ForeignKey(TraceSection, related_name="chunks")
    ordering = models.IntegerField()
    # Consider breaking raw_source up into individaul lines, especailly for
    # ResOps (where we might want to make the op, args, result, and descr into
    # seperate thigns so we can display them better, and do statistics without
    # needing to parse them)
    raw_source = models.TextField()

    objects = InheritanceManager()

    class Meta:
        unique_together = [
            ("section", "ordering"),
        ]
        ordering = ["ordering"]

class PythonChunk(TraceChunk):
    is_python = True

    # [start_line, end_line)
    start_line = models.PositiveIntegerField()
    end_line = models.PositiveIntegerField()

    @property
    def linenos(self):
        return xrange(self.start_line, self.end_line)

class ResOpChunk(TraceChunk):
    is_resop = True

class AssemblerChunk(TraceChunk):
    pass


class Call(models.Model):
    log = models.ForeignKey(Log, related_name="calls")

    start_time = models.FloatField()
    end_time = models.FloatField()
    call_depth = models.PositiveIntegerField()
    parent = models.ForeignKey("self", null=True)

    objects = InheritanceManager()

class PythonCall(Call):
    func_name = models.CharField(max_length=255)

    @property
    def name(self):
        return self.func_name