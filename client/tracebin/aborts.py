class BaseAbort(object):
    def __init__(self, reason):
        self.reason = reason

class PythonAbort(BaseAbort):
    def __init__(self, reason, pycode, lineno):
        super(PythonAbort, self).__init__(reason)
        self.pycode = pycode
        self.lineno = lineno

    def visit(self, visitor):
        return visitor.visit_python_abort(self)