import inspect

import disassembler


class BaseTrace(object):
    def __init__(self, ops):
        super(BaseTrace, self).__init__()
        self.sections = [
            TraceSection(label, self.split_section(ops))
            for label, ops in self.split_trace(ops)
        ]

    @classmethod
    def split_trace(cls, ops):
        sections = []
        start_idx = 0
        labels = iter(["Entry", "Preamble", "Loop body"])
        for idx, op in enumerate(ops):
            if op.name == "label":
                sections.append((next(labels), ops[start_idx:idx]))
                start_idx = idx
        sections.append((next(labels), ops[start_idx:]))
        return sections

class PythonTrace(BaseTrace):
    def __init__(self, greenkey, ops, asm_start, asm_len):
        super(PythonTrace, self).__init__(ops)
        self.root_file = greenkey[0].co_filename
        self.root_function = greenkey[0].co_name

    @classmethod
    def split_section(cls, ops):
        chunks = []
        cls._split_section(ops, i=0, call_depth=0, chunks=chunks)
        return chunks

    @classmethod
    def _split_section(cls, ops, i, call_depth, chunks):
        start_idx = i
        current_line = None

        while i < len(ops):
            op = ops[i]
            if op.name == "debug_merge_point":
                if op.call_depth > call_depth:
                    chunks.append(
                        ResOpChunk(ops[start_idx:i])
                    )
                    i = start_idx = cls._split_section(ops, i, op.call_depth, chunks)
                elif op.call_depth < call_depth:
                    chunks.append(
                        ResOpChunk(ops[start_idx:i])
                    )
                    return i
                else:
                    code = disassembler.dis(op.pycode)
                    py_op = code.map[op.bytecode_no]
                    sourcecode, startline = inspect.getsourcelines(code.co)

                    if current_line is None or py_op.lineno > current_line:
                        if start_idx != i:
                            chunks.append(
                                ResOpChunk(ops[start_idx:i])
                            )
                        lines_end = py_op.lineno - startline
                        if current_line is None:
                            source = sourcecode[:lines_end+1]
                            linenos = range(startline, py_op.lineno + 1)
                        else:
                            source = [sourcecode[lines_end]]
                            linenos = [py_op.lineno]
                        chunks.append(PythonChunk(source, linenos))
                        current_line = py_op.lineno
                        start_idx = i
            i += 1
        chunks.append(ResOpChunk(ops[start_idx:]))

    def visit(self, visitor):
        return visitor.visit_python_trace(self)


class TraceSection(object):
    def __init__(self, label, chunks):
        self.label = label
        self.chunks = chunks

    def visit(self, visitor):
        return visitor.visit_trace_section(self)

class BaseChunk(object):
    pass

class ResOpChunk(BaseChunk):
    def __init__(self, ops):
        self.ops = ops

    def get_op_names(self):
        return [op.name for op in self.ops]

    def visit(self, visitor):
        return visitor.visit_resop_chunk(self)

class PythonChunk(BaseChunk):
    def __init__(self, sourcelines, linenos):
        self.sourcelines = sourcelines
        self.linenos = linenos

    def visit(self, visitor):
        return visitor.visit_python_chunk(self)
