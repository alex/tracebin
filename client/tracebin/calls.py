class BaseCall(object):
    def __init__(self, start_time, end_time):
        self.start_time = start_time
        self.end_time = end_time

class PythonCall(BaseCall):
    def __init__(self, func_name, start_time, end_time):
        super(PythonCall, self).__init__(start_time, end_time)
        self.func_name = func_name