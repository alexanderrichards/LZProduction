class coroutine(object):
    def __init__(self, func):
        self._func = func
    def __call__(self, *args, **kwargs):
        cr = self._func(*args, **kwargs)
        cr.next()
        return cr

@coroutine
def status_accumulator(priorities):
    status = priorities[0]
    while True:
        new_status = (yield status)
        status = priorities[max(priorities.index(status),
                                priorities.index(new_status))]
