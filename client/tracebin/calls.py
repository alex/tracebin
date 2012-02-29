class BaseCall(object):
    def __init__(self, start_time, end_time, subcalls):
        self.start_time = start_time
        self.end_time = end_time
        self.subcalls = subcalls

class PythonCall(BaseCall):
    def __init__(self, func_name, start_time, end_time, subcalls):
        super(PythonCall, self).__init__(start_time, end_time, subcalls)
        self.func_name = func_name

    def visit(self, visitor):
        return visitor.visit_python_call(self)