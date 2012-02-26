from textwrap import dedent

from fixture_generator import fixture_generator

from .models import (Log, RuntimeEnviroment, TimelineEvent, StatCounter,
    BaseTrace, PythonTrace, RegexTrace, NumPyPyTrace, TraceSection, TraceChunk,
    PythonChunk, ResOpChunk)


@fixture_generator(
    Log, RuntimeEnviroment, TimelineEvent, StatCounter, BaseTrace, PythonTrace,
    RegexTrace, NumPyPyTrace, TraceSection, TraceChunk, PythonChunk, ResOpChunk
)
def demo_data():
    log = Log.objects.create(
        uploader=None, public=True, command="pypy test.py", runtime=9.8,
    )
    for kind, key, value in [
        (RuntimeEnviroment.JIT_OPTION, "trace_limit", "6000"),
        (RuntimeEnviroment.JIT_OPTION, "loop_longevity", "1000"),
        (RuntimeEnviroment.JIT_OPTION, "retrace_limit", "5"),
        (RuntimeEnviroment.JIT_OPTION, "trace_eagerness", "200"),
        (RuntimeEnviroment.JIT_OPTION, "enable_opts", "all"),
        (RuntimeEnviroment.JIT_OPTION, "max_retrace_guards", "15"),
        (RuntimeEnviroment.JIT_OPTION, "treshold", "1039"),
        (RuntimeEnviroment.JIT_OPTION, "function_threshold", "1619"),
        (RuntimeEnviroment.JIT_OPTION, "inlining", "1"),
        (RuntimeEnviroment.GC_OPTION, "PYPY_GC_NURSERY", "4MB"),
        (RuntimeEnviroment.GC_OPTION, "PYPY_GC_MAJOR_COLLECT", "1.82"),
        (RuntimeEnviroment.GC_OPTION, "PYPY_GC_GROWTH", "1.4"),
        (RuntimeEnviroment.BUILD_OPTION, "PyPy Version", "c2d42bf471da"),
        (RuntimeEnviroment.BUILD_OPTION, "GC root finder", "asmgcc"),
        (RuntimeEnviroment.BUILD_OPTION, "Garbage collector", "minimark"),
    ]:
        log.enviroment_options.create(kind=kind, key=key, value=value)

    # For now we just care about the percent of total time, so this idiotic
    # representation is fine, these add up to 100.
    start_time = 0
    for event_type, duration in [
        ("jit-running", 65),
        ("gc-major", 12),
        ("jit-tracing", 8),
        ("gc-mior", 8),
        ("jit-backend-compile", 7),
    ]:
        log.timeline_events.create(
            event_type=event_type,
            start_time=start_time,
            end_time=start_time + duration
        )
        start_time += duration

    for label, value in [
        ("traces_compiled", 3),
        ("traces_aborted", 0),
        ("gc_major", 12),
        ("gc_minor", 37),
    ]:
        log.counters.create(label=label, count=value)

    py_trace = PythonTrace.objects.create(
        log=log, root_file="test.py", root_function="main",
    )
    RegexTrace.objects.create(
        log=log, pattern=r"\w+",
    )
    NumPyPyTrace.objects.create(
        log=log, debug_repr="Call1(sin, Call2(multiply, Array, Scalar))",
    )

    entry = py_trace.sections.create(label=TraceSection.ENTRY)
    ResOpChunk.objects.create(
        section=entry,
        ordering=0,
        raw_source=dedent("""
        [p0, p1]
        p2 = getfield_gc(p0, descr=<FieldP pypy.interpreter.pyframe.PyFrame.inst_last_exception 80>)
        p3 = getfield_gc(p0, descr=<FieldP pypy.interpreter.pyframe.PyFrame.inst_pycode 120>)
        i4 = getfield_gc(p0, descr=<FieldU pypy.interpreter.pyframe.PyFrame.inst_is_being_profiled 150>)
        p5 = getfield_gc(p0, descr=<FieldP pypy.interpreter.pyframe.PyFrame.inst_lastblock 96>)
        i6 = getfield_gc(p0, descr=<FieldS pypy.interpreter.pyframe.PyFrame.inst_valuestackdepth 128>)
        i7 = getfield_gc(p0, descr=<FieldS pypy.interpreter.pyframe.PyFrame.inst_last_instr 88>)
        p8 = getfield_gc(p0, descr=<FieldP pypy.interpreter.pyframe.PyFrame.inst_locals_stack_w 104>)
        p10 = getarrayitem_gc(p8, 0, descr=<ArrayP 8>)
        p12 = getarrayitem_gc(p8, 1, descr=<ArrayP 8>)
        p14 = getarrayitem_gc(p8, 2, descr=<ArrayP 8>)
        p16 = getarrayitem_gc(p8, 3, descr=<ArrayP 8>)
        p18 = getarrayitem_gc(p8, 4, descr=<ArrayP 8>)
        p20 = getarrayitem_gc(p8, 5, descr=<ArrayP 8>)
        p22 = getarrayitem_gc(p8, 6, descr=<ArrayP 8>)
        p23 = getfield_gc(p0, descr=<FieldP pypy.interpreter.pyframe.PyFrame.inst_cells 40>)
        """),
    )

    preamble = py_trace.sections.create(label=TraceSection.PREAMBLE)
    ResOpChunk.objects.create(
        section=preamble,
        ordering=0,
        raw_source=dedent("""
        label(p0, p1, p2, p3, i4, p5, i6, i7, p10, p12, p14, p16, p18, p20, p22, descr=TargetToken(140048017138976))
        """),
    )
    PythonChunk.objects.create(
        section=preamble,
        ordering=1,
        start_line=3,
        end_line=6,
        raw_source=dedent("""
        def main():
            data = [0] * N
            for i in xrange(N):
        """),
    )
    ResOpChunk.objects.create(
        section=preamble,
        ordering=2,
        raw_source=dedent("""
        debug_merge_point(0, '<code object main. file 'test.py'. line 3> #26 FOR_ITER')
        guard_value(i6, 4, descr=<Guard4>) [i6, p1, p0, p2, p3, i4, p5, i7, p10, p12, p14, p16, p18, p20, p22]
        guard_class(p16, 38449928, descr=<Guard5>) [p1, p0, p16, p2, p3, i4, p5, p10, p12, p14, p18, p20, p22]
        i26 = getfield_gc(p16, descr=<FieldS pypy.module.__builtin__.functional.W_XRangeIterator.inst_remaining 16>)
        i28 = int_gt(i26, 0)
        guard_true(i28, descr=<Guard6>) [p1, p0, p16, p2, p3, i4, p5, p10, p12, p14, p18, p20, p22]
        i29 = getfield_gc(p16, descr=<FieldS pypy.module.__builtin__.functional.W_XRangeIterator.inst_current 8>)
        i30 = getfield_gc(p16, descr=<FieldS pypy.module.__builtin__.functional.W_XRangeIterator.inst_step 24>)
        i31 = int_add(i29, i30)
        i33 = int_sub(i26, 1)
        setfield_gc(p16, i31, descr=<FieldS pypy.module.__builtin__.functional.W_XRangeIterator.inst_current 8>)
        setfield_gc(p16, i33, descr=<FieldS pypy.module.__builtin__.functional.W_XRangeIterator.inst_remaining 16>)
        guard_value(i4, 0, descr=<Guard7>) [i4, p1, p0, p2, p3, p5, p10, p12, p14, p16, p20, p22, i29]
        debug_merge_point(0, '<code object main. file 'test.py'. line 3> #29 STORE_FAST')
    """)
    )
    PythonChunk.objects.create(
        section=preamble,
        ordering=3,
        start_line=6,
        end_line=7,
        raw_source="""        x = i ^ 3"""
    )
    ResOpChunk.objects.create(
        section=preamble,
        ordering=4,
        raw_source=dedent("""
        debug_merge_point(0, '<code object main. file 'test.py'. line 3> #32 LOAD_FAST')
        debug_merge_point(0, '<code object main. file 'test.py'. line 3> #35 LOAD_CONST')
        guard_value(p3, ConstPtr(ptr35), descr=<Guard8>) [p1, p0, p3, p2, p5, p10, p14, p16, p20, p22, i29]
        debug_merge_point(0, '<code object main. file 'test.py'. line 3> #38 BINARY_XOR')
        i37 = int_xor(i29, 3)
        debug_merge_point(0, '<code object main. file 'test.py'. line 3> #39 STORE_FAST')
        """),
    )
    PythonChunk.objects.create(
        section=preamble,
        ordering=5,
        start_line=7,
        end_line=8,
        raw_source="""        x <<= 2"""
    )
    ResOpChunk.objects.create(
        section=preamble,
        ordering=6,
        raw_source=dedent("""
        debug_merge_point(0, '<code object main. file 'test.py'. line 3> #42 LOAD_FAST')
        debug_merge_point(0, '<code object main. file 'test.py'. line 3> #45 LOAD_CONST')
        debug_merge_point(0, '<code object main. file 'test.py'. line 3> #48 INPLACE_LSHIFT')
        i39 = int_lshift(i37, 2)
        i40 = int_rshift(i39, 2)
        i41 = int_ne(i40, i37)
        guard_false(i41, descr=<Guard9>) [p1, p0, i39, p2, p5, p10, p16, p22, i37, i29]
        debug_merge_point(0, '<code object main. file 'test.py'. line 3> #49 STORE_FAST')
        """),
    )
    PythonChunk.objects.create(
        section=preamble,
        ordering=7,
        start_line=8,
        end_line=9,
        raw_source="""        x *= 7""",
    )
    ResOpChunk.objects.create(
        section=preamble,
        ordering=8,
        raw_source=dedent("""
        debug_merge_point(0, '<code object main. file 'test.py'. line 3> #52 LOAD_FAST')
        debug_merge_point(0, '<code object main. file 'test.py'. line 3> #55 LOAD_CONST')
        debug_merge_point(0, '<code object main. file 'test.py'. line 3> #58 INPLACE_MULTIPLY')
        i43 = int_mul_ovf(i39, 7)
        guard_no_overflow(, descr=<Guard10>) [p1, p0, i43, p2, p5, p10, p16, p22, i39, None, i29]
        debug_merge_point(0, '<code object main. file 'test.py'. line 3> #59 STORE_FAST')
        """)
    )
    PythonChunk.objects.create(
        section=preamble,
        ordering=9,
        start_line=9,
        end_line=10,
        raw_source="""        x -= 1""",
    )
    ResOpChunk.objects.create(
        section=preamble,
        ordering=10,
        raw_source=dedent("""
        debug_merge_point(0, '<code object main. file 'test.py'. line 3> #62 LOAD_FAST')
        debug_merge_point(0, '<code object main. file 'test.py'. line 3> #65 LOAD_CONST')
        debug_merge_point(0, '<code object main. file 'test.py'. line 3> #68 INPLACE_SUBTRACT')
        i46 = int_sub_ovf(i43, 1)
        guard_no_overflow(, descr=<Guard11>) [p1, p0, i46, p2, p5, p10, p16, p22, i43, None, None, i29]
        debug_merge_point(0, '<code object main. file 'test.py'. line 3> #69 STORE_FAST')
        """)
    )
    PythonChunk.objects.create(
        section=preamble,
        ordering=11,
        start_line=10,
        end_line=11,
        raw_source="""        data[i] = x""",
    )
    ResOpChunk.objects.create(
        section=preamble,
        ordering=12,
        raw_source=dedent("""
        debug_merge_point(0, '<code object main. file 'test.py'. line 3> #72 LOAD_FAST')
        debug_merge_point(0, '<code object main. file 'test.py'. line 3> #75 LOAD_FAST')
        guard_nonnull_class(p10, ConstClass(W_ListObject), descr=<Guard12>) [p1, p0, p10, p2, p5, p16, p22, i46, None, None, None, i29]
        debug_merge_point(0, '<code object main. file 'test.py'. line 3> #78 LOAD_FAST')
        debug_merge_point(0, '<code object main. file 'test.py'. line 3> #81 STORE_SUBSCR')
        p48 = getfield_gc(p10, descr=<FieldP pypy.objspace.std.listobject.W_ListObject.inst_strategy 16>)
        guard_class(p48, 38554720, descr=<Guard13>) [p1, p0, p10, i29, p48, p2, p5, p16, i46, None, None, None, None]
        p50 = getfield_gc(p10, descr=<FieldP pypy.objspace.std.listobject.W_ListObject.inst_lstorage 8>)
        i51 = getfield_gc(p50, descr=<FieldS list.length 8>)
        i52 = uint_ge(i29, i51)
        guard_false(i52, descr=<Guard14>) [p1, p0, p10, i51, i46, i29, p50, p2, p5, p16, None, None, None, None, None]
        p53 = getfield_gc(p50, descr=<FieldP list.items 16>)
        setarrayitem_gc(p53, i29, i46, descr=<ArrayS 8>)
        debug_merge_point(0, '<code object main. file 'test.py'. line 3> #82 JUMP_ABSOLUTE')
        guard_not_invalidated(, descr=<Guard15>) [p1, p0, p2, p5, p10, p16, i46, None, None, None, i29]
        i55 = getfield_raw(43922552, descr=<FieldS pypysig_long_struct.c_value 0>)
        i57 = int_lt(i55, 0)
        guard_false(i57, descr=<Guard16>) [p1, p0, p2, p5, p10, p16, i46, None, None, None, i29]
        debug_merge_point(0, '<code object main. file 'test.py'. line 3> #26 FOR_ITER')
        i58 = same_as(i46)
        i59 = same_as(i31)
        """)
    )

    loop = py_trace.sections.create(label=TraceSection.LOOP_BODY)
    ResOpChunk.objects.create(
        section=loop,
        ordering=0,
        raw_source=dedent("""
        label(p0, p1, p2, p5, p10, i29, i46, p16, i33, i59, i30, p50, descr=TargetToken(140048017139056))
        """)
    )
    PythonChunk.objects.create(
        section=loop,
        ordering=1,
        start_line=3,
        end_line=6,
        raw_source=dedent("""
        def main():
            data = [0] * N
            for i in xrange(N):
        """),
    )
    ResOpChunk.objects.create(
        section=loop,
        ordering=2,
        raw_source=dedent("""
        debug_merge_point(0, '<code object main. file 'test.py'. line 3> #26 FOR_ITER')
        i60 = int_gt(i33, 0)
        guard_true(i60, descr=<Guard17>) [p1, p0, p16, p2, p5, p10, i29, i46]
        i61 = int_add(i59, i30)
        i62 = int_sub(i33, 1)
        debug_merge_point(0, '<code object main. file 'test.py'. line 3> #29 STORE_FAST')
        """)
    )
    PythonChunk.objects.create(
        section=loop,
        ordering=3,
        start_line=6,
        end_line=7,
        raw_source="""        x = i ^ 3""",
    )
    ResOpChunk.objects.create(
        section=loop,
        ordering=4,
        raw_source=dedent("""
        debug_merge_point(0, '<code object main. file 'test.py'. line 3> #32 LOAD_FAST')
        debug_merge_point(0, '<code object main. file 'test.py'. line 3> #35 LOAD_CONST')
        debug_merge_point(0, '<code object main. file 'test.py'. line 3> #38 BINARY_XOR')
        i63 = int_xor(i59, 3)
        debug_merge_point(0, '<code object main. file 'test.py'. line 3> #39 STORE_FAST')
        """)
    )
    PythonChunk.objects.create(
        section=loop,
        ordering=5,
        start_line=7,
        end_line=8,
        raw_source="""        x <<= 2""",
    )
    ResOpChunk.objects.create(
        section=loop,
        ordering=6,
        raw_source=dedent("""
        debug_merge_point(0, '<code object main. file 'test.py'. line 3> #42 LOAD_FAST')
        debug_merge_point(0, '<code object main. file 'test.py'. line 3> #45 LOAD_CONST')
        debug_merge_point(0, '<code object main. file 'test.py'. line 3> #48 INPLACE_LSHIFT')
        i64 = int_lshift(i63, 2)
        i65 = int_rshift(i64, 2)
        setfield_gc(p16, i61, descr=<FieldS pypy.module.__builtin__.functional.W_XRangeIterator.inst_current 8>)
        setfield_gc(p16, i62, descr=<FieldS pypy.module.__builtin__.functional.W_XRangeIterator.inst_remaining 16>)
        i66 = int_ne(i65, i63)
        guard_false(i66, descr=<Guard18>) [p1, p0, i64, p2, p5, p10, p16, i63, i59, None, None]
        debug_merge_point(0, '<code object main. file 'test.py'. line 3> #49 STORE_FAST')
        """),
    )
    PythonChunk.objects.create(
        section=loop,
        ordering=7,
        start_line=8,
        end_line=9,
        raw_source="""        x *= 7""",
    )
    ResOpChunk.objects.create(
        section=loop,
        ordering=8,
        raw_source=dedent("""
        debug_merge_point(0, '<code object main. file 'test.py'. line 3> #52 LOAD_FAST')
        debug_merge_point(0, '<code object main. file 'test.py'. line 3> #55 LOAD_CONST')
        debug_merge_point(0, '<code object main. file 'test.py'. line 3> #58 INPLACE_MULTIPLY')
        i67 = int_mul_ovf(i64, 7)
        guard_no_overflow(, descr=<Guard19>) [p1, p0, i67, p2, p5, p10, p16, i64, None, i59, None, None]
        debug_merge_point(0, '<code object main. file 'test.py'. line 3> #59 STORE_FAST')
        """)
    )
    PythonChunk.objects.create(
        section=loop,
        ordering=9,
        start_line=9,
        end_line=10,
        raw_source="""        x -= 1""",
    )
    ResOpChunk.objects.create(
        section=loop,
        ordering=10,
        raw_source=dedent("""
        debug_merge_point(0, '<code object main. file 'test.py'. line 3> #62 LOAD_FAST')
        debug_merge_point(0, '<code object main. file 'test.py'. line 3> #65 LOAD_CONST')
        debug_merge_point(0, '<code object main. file 'test.py'. line 3> #68 INPLACE_SUBTRACT')
        i68 = int_sub_ovf(i67, 1)
        guard_no_overflow(, descr=<Guard20>) [p1, p0, i68, p2, p5, p10, p16, i67, None, None, i59, None, None]
        debug_merge_point(0, '<code object main. file 'test.py'. line 3> #69 STORE_FAST')
        """),
    )
    PythonChunk.objects.create(
        section=loop,
        ordering=11,
        start_line=10,
        end_line=11,
        raw_source="""        data[i] = x""",
    )
    ResOpChunk.objects.create(
        section=loop,
        ordering=12,
        raw_source=dedent("""
        debug_merge_point(0, '<code object main. file 'test.py'. line 3> #72 LOAD_FAST')
        debug_merge_point(0, '<code object main. file 'test.py'. line 3> #75 LOAD_FAST')
        debug_merge_point(0, '<code object main. file 'test.py'. line 3> #78 LOAD_FAST')
        debug_merge_point(0, '<code object main. file 'test.py'. line 3> #81 STORE_SUBSCR')
        i69 = getfield_gc(p50, descr=<FieldS list.length 8>)
        i70 = uint_ge(i59, i69)
        guard_false(i70, descr=<Guard21>) [p1, p0, p10, i69, i68, i59, p50, p2, p5, p16, None, None, None, None, None, None]
        p71 = getfield_gc(p50, descr=<FieldP list.items 16>)
        setarrayitem_gc(p71, i59, i68, descr=<ArrayS 8>)
        debug_merge_point(0, '<code object main. file 'test.py'. line 3> #82 JUMP_ABSOLUTE')
        guard_not_invalidated(, descr=<Guard22>) [p1, p0, p2, p5, p10, p16, i68, None, None, None, i59, None, None]
        i72 = getfield_raw(43922552, descr=<FieldS pypysig_long_struct.c_value 0>)
        i73 = int_lt(i72, 0)
        guard_false(i73, descr=<Guard23>) [p1, p0, p2, p5, p10, p16, i68, None, None, None, i59, None, None]
        debug_merge_point(0, '<code object main. file 'test.py'. line 3> #26 FOR_ITER')
        jump(p0, p1, p2, p5, p10, i59, i68, p16, i62, i61, i30, p50, descr=TargetToken(140048017139056))
        """)
    )


    py_trace_inline = PythonTrace.objects.create(
        log=log, root_file="test.py", root_function="main_inline",
    )
    entry = py_trace_inline.sections.create(label=TraceSection.ENTRY)
    ResOpChunk.objects.create(
        section=entry,
        ordering=0,
        raw_source=dedent("""
        [p0, p1]
        p2 = getfield_gc(p0, descr=<FieldP pypy.interpreter.pyframe.PyFrame.inst_last_exception 80>)
        p3 = getfield_gc(p0, descr=<FieldP pypy.interpreter.pyframe.PyFrame.inst_pycode 120>)
        i4 = getfield_gc(p0, descr=<FieldU pypy.interpreter.pyframe.PyFrame.inst_is_being_profiled 150>)
        p5 = getfield_gc(p0, descr=<FieldP pypy.interpreter.pyframe.PyFrame.inst_lastblock 96>)
        i6 = getfield_gc(p0, descr=<FieldS pypy.interpreter.pyframe.PyFrame.inst_valuestackdepth 128>)
        i7 = getfield_gc(p0, descr=<FieldS pypy.interpreter.pyframe.PyFrame.inst_last_instr 88>)
        p8 = getfield_gc(p0, descr=<FieldP pypy.interpreter.pyframe.PyFrame.inst_locals_stack_w 104>)
        p10 = getarrayitem_gc(p8, 0, descr=<ArrayP 8>)
        p12 = getarrayitem_gc(p8, 1, descr=<ArrayP 8>)
        p14 = getarrayitem_gc(p8, 2, descr=<ArrayP 8>)
        p15 = getfield_gc(p0, descr=<FieldP pypy.interpreter.pyframe.PyFrame.inst_cells 40>)
        """),
    )

    preamble = py_trace_inline.sections.create(label=TraceSection.PREAMBLE)
    ResOpChunk.objects.create(
        section=preamble,
        ordering=1,
        raw_source=dedent("""
        label(p0, p1, p2, p3, i4, p5, i6, i7, p10, p12, p14, descr=TargetToken(139725302244320))
        """),
    )
    PythonChunk.objects.create(
        section=preamble,
        ordering=2,
        start_line=4,
        end_line=7,
        raw_source=dedent("""
        def main():
            i = 0
            while i < 10000:
        """),
    )
    ResOpChunk.objects.create(
        section=preamble,
        ordering=3,
        raw_source=dedent("""
        debug_merge_point(0, '<code object main_inline. file 'test.py'. line 4> #9 LOAD_FAST')
        guard_value(i6, 1, descr=<Guard4>) [i6, p1, p0, p2, p3, i4, p5, i7, p10, p12, p14]
        guard_nonnull_class(p10, ConstClass(W_IntObject), descr=<Guard5>) [p1, p0, p10, p2, p3, i4, p5, p12, p14]
        guard_value(i4, 0, descr=<Guard6>) [i4, p1, p0, p2, p3, p5, p10, p14]
        debug_merge_point(0, '<code object main_inline. file 'test.py'. line 4> #12 LOAD_CONST')
        guard_value(p3, ConstPtr(ptr19), descr=<Guard7>) [p1, p0, p3, p2, p5, p10, p14]
        debug_merge_point(0, '<code object main_inline. file 'test.py'. line 4> #15 COMPARE_OP')
        i20 = getfield_gc_pure(p10, descr=<FieldS pypy.objspace.std.intobject.W_IntObject.inst_intval 8>)
        i22 = int_lt(i20, 10000)
        guard_true(i22, descr=<Guard8>) [p1, p0, p10, p2, p5]
        debug_merge_point(0, '<code object main_inline. file 'test.py'. line 4> #18 POP_JUMP_IF_FALSE')
        """),
    )
    PythonChunk.objects.create(
        section=preamble,
        ordering=4,
        start_line=7,
        end_line=8,
        raw_source="""        i = f(i)""",
    )
    ResOpChunk.objects.create(
        section=preamble,
        ordering=5,
        raw_source=dedent("""
        debug_merge_point(0, '<code object main_inline. file 'test.py'. line 4> #21 LOAD_GLOBAL')
        p23 = getfield_gc(p0, descr=<FieldP pypy.interpreter.eval.Frame.inst_w_globals 8>)
        guard_value(p23, ConstPtr(ptr24), descr=<Guard9>) [p1, p0, p23, p2, p5, p10]
        p25 = getfield_gc(p23, descr=<FieldP pypy.objspace.std.dictmultiobject.W_DictMultiObject.inst_strategy 16>)
        guard_value(p25, ConstPtr(ptr26), descr=<Guard10>) [p1, p0, p25, p23, p2, p5, p10]
        guard_not_invalidated(, descr=<Guard11>) [p1, p0, p23, p2, p5, p10]
        debug_merge_point(0, '<code object main_inline. file 'test.py'. line 4> #24 LOAD_FAST')
        debug_merge_point(0, '<code object main_inline. file 'test.py'. line 4> #27 CALL_FUNCTION')
        p28 = call(ConstClass(getexecutioncontext), descr=<Callr 8 EF=1>)
        p29 = getfield_gc(p28, descr=<FieldP pypy.interpreter.executioncontext.ExecutionContext.inst_topframeref 64>)
        i30 = force_token()
        p31 = getfield_gc(p28, descr=<FieldP pypy.interpreter.executioncontext.ExecutionContext.inst_w_tracefunc 80>)
        guard_isnull(p31, descr=<Guard12>) [p1, p0, p28, p31, p2, p5, p10, i30, p29]
        i32 = getfield_gc(p28, descr=<FieldU pypy.interpreter.executioncontext.ExecutionContext.inst_profilefunc 40>)
        i33 = int_is_zero(i32)
        guard_true(i33, descr=<Guard13>) [p1, p0, p28, p2, p5, p10, i30, p29]
        """),
    )
    PythonChunk.objects.create(
        section=preamble,
        ordering=6,
        start_line=1,
        end_line=3,
        raw_source=dedent("""
        def f(i):
            return i + 1
        """),
    )
    ResOpChunk.objects.create(
        section=preamble,
        ordering=7,
        raw_source=dedent("""
        debug_merge_point(1, '<code object f. file 'test.py'. line 1> #0 LOAD_FAST')
        debug_merge_point(1, '<code object f. file 'test.py'. line 1> #3 LOAD_CONST')
        debug_merge_point(1, '<code object f. file 'test.py'. line 1> #6 BINARY_ADD')
        i35 = int_add(i20, 1)
        debug_merge_point(1, '<code object f. file 'test.py'. line 1> #7 RETURN_VALUE')
        """),
    )
    ResOpChunk.objects.create(
        section=preamble,
        ordering=8,
        raw_source=dedent("""
        debug_merge_point(0, '<code object main_inline. file 'test.py'. line 4> #30 STORE_FAST')
        debug_merge_point(0, '<code object main_inline. file 'test.py'. line 4> #33 JUMP_ABSOLUTE')
        guard_not_invalidated(, descr=<Guard14>) [p1, p0, p2, p5, i35, None, None]
        i38 = getfield_raw(44216344, descr=<FieldS pypysig_long_struct.c_value 0>)
        i40 = int_lt(i38, 0)
        guard_false(i40, descr=<Guard15>) [p1, p0, p2, p5, i35, None, None]
        debug_merge_point(0, '<code object main_inline. file 'test.py'. line 4> #9 LOAD_FAST')
        p41 = same_as(ConstPtr(ptr26))
        """),
    )

    loop = py_trace_inline.sections.create(label=TraceSection.LOOP_BODY)
    ResOpChunk.objects.create(
        section=loop,
        ordering=0,
        raw_source=dedent("""
        label(p0, p1, p2, p5, i35, descr=TargetToken(139725302244400))
        """),
    )
    PythonChunk.objects.create(
        section=loop,
        ordering=1,
        start_line=4,
        end_line=7,
        raw_source=dedent("""
        def main():
            i = 0
            while i < 10000:
        """),
    )
    ResOpChunk.objects.create(
        section=loop,
        ordering=2,
        raw_source=dedent("""
        debug_merge_point(0, '<code object main_inline. file 'test.py'. line 4> #9 LOAD_FAST')
        debug_merge_point(0, '<code object main_inline. file 'test.py'. line 4> #12 LOAD_CONST')
        debug_merge_point(0, '<code object main_inline. file 'test.py'. line 4> #15 COMPARE_OP')
        i42 = int_lt(i35, 10000)
        guard_true(i42, descr=<Guard16>) [p1, p0, p2, p5, i35]
        debug_merge_point(0, '<code object main_inline. file 'test.py'. line 4> #18 POP_JUMP_IF_FALSE')
        """),
    )
    PythonChunk.objects.create(
        section=loop,
        ordering=3,
        start_line=7,
        end_line=8,
        raw_source="""        i = f(i)""",
    )
    ResOpChunk.objects.create(
        section=loop,
        ordering=4,
        raw_source=dedent("""
        debug_merge_point(0, '<code object main_inline. file 'test.py'. line 4> #21 LOAD_GLOBAL')
        guard_not_invalidated(, descr=<Guard17>) [p1, p0, p2, p5, i35]
        debug_merge_point(0, '<code object main_inline. file 'test.py'. line 4> #24 LOAD_FAST')
        debug_merge_point(0, '<code object main_inline. file 'test.py'. line 4> #27 CALL_FUNCTION')
        i43 = force_token()
        """),
    )
    PythonChunk.objects.create(
        section=loop,
        ordering=5,
        start_line=1,
        end_line=3,
        raw_source=dedent("""
        def f(i):
            return i + 1
        """),
    )
    ResOpChunk.objects.create(
        section=loop,
        ordering=6,
        raw_source=dedent("""
        debug_merge_point(1, '<code object f. file 'test.py'. line 1> #0 LOAD_FAST')
        debug_merge_point(1, '<code object f. file 'test.py'. line 1> #3 LOAD_CONST')
        debug_merge_point(1, '<code object f. file 'test.py'. line 1> #6 BINARY_ADD')
        i44 = int_add(i35, 1)
        debug_merge_point(1, '<code object f. file 'test.py'. line 1> #7 RETURN_VALUE')
        """),
    )
    ResOpChunk.objects.create(
        section=loop,
        ordering=7,
        raw_source=dedent("""
        debug_merge_point(0, '<code object main_inline. file 'test.py'. line 4> #30 STORE_FAST')
        debug_merge_point(0, '<code object main_inline. file 'test.py'. line 4> #33 JUMP_ABSOLUTE')
        i45 = getfield_raw(44216344, descr=<FieldS pypysig_long_struct.c_value 0>)
        i46 = int_lt(i45, 0)
        guard_false(i46, descr=<Guard18>) [p1, p0, p2, p5, i44, None]
        debug_merge_point(0, '<code object main_inline. file 'test.py'. line 4> #9 LOAD_FAST')
        jump(p0, p1, p2, p5, i44, descr=TargetToken(139725302244400))
        """),
    )