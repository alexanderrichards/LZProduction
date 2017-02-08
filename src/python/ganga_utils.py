"""
Ganga utility module.

A collection of helper functions for working with ganga task
object.
"""
from contextlib import contextmanager
from pylru import lrudecorator
import ganga


@contextmanager
def removing_request():
    """Self cleaning job context."""
    req = ganga.LZRequest()
    try:
        yield req
    except:
        req.pause()  # must pause task before removing if running
        req.remove(remove_jobs=True)
        raise


# This could be cached.
@lrudecorator(100)
def ganga_request(requestdb_id):
    """
    Get Ganga task from DB request number.

    Args:
        requestdb_id (int): The request id from the web app DB

    Returns:
        ganga.LZRequest: The Ganga task corresponding to the DB
                         requestdb_id arg.
    """
    # note could use tasks.select here
    for task in ganga.tasks:
        if task.requestdb_id == requestdb_id:
            return task
    return None

def ganga_request_task(requests, status=None):
    tasks = ganga.tasks  # optimize, avoid lookup in each requests loop
    for request in requests:
        if status is not None and request.status != status:
            continue
        for task in tasks:
            if request.id == task.requestdb_id:
                yield request, task
                break
        else:
            yield request, None


def ganga_macro_jobs(request, task):
    units = task.transforms[0].units  # optimize, avoid looking this up in loop
    for macro in request.selected_macros:
        for unit in units:
            if macro.path == unit.application.macro:
                yield macro, ganga.jobs(unit._impl.active_job_ids[0])
