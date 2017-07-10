import logging

logger = logging.getLogger(__name__)


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
        try:
            status = priorities[max(priorities.index(status),
                                    priorities.index(new_status))]
        except ValueError:
            logger.exception("Error accumulating status: existing=%s, new=%s, known=%s",
                             status, new_status, priorities)
