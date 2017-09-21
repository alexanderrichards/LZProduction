# pylint: disable=invalid-name
"""Coroutine utils."""
import logging

logger = logging.getLogger(__name__)


class coroutine(object):
    """Coroutine decorator."""

    def __init__(self, func):
        """Initialise."""
        self._func = func

    def __call__(self, *args, **kwargs):
        """Prime the coroutine."""
        cr = self._func(*args, **kwargs)
        cr.next()
        return cr


@coroutine
def status_accumulator(priorities):
    """Accumulate statuses."""
    status = priorities[0]
    while True:
        new_status = (yield status)
        try:
            status = priorities[max(priorities.index(status),
                                    priorities.index(new_status))]
        except ValueError:
            logger.exception("Error accumulating status: existing=%s, new=%s, known=%s",
                             status, new_status, priorities)
