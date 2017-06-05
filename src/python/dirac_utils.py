"""DIRAC utility module."""
import logging
import xmlrpclib
from contextlib import contextmanager

from coroutine_utils import status_accumulator

logger = logging.getLogger(__name__)

status_map = {'Done': 'Completed',
              'Failed': 'Failed',
              'Waiting': 'Submitted',
              'Queued': 'Submitted',
              'Checking': 'Submitted',
              'Running': 'Running',
              'Received': 'Requested',
              'Killed': 'Killed',
              'Deleted': 'Deleted'}

class DiracClient(xmlrpclib.ServerProxy):

    def __enter__(self):
        return self

    def __exit__(self, exec_type, value, tb):
        if isinstance(value, xmlrpclib.ProtocolError):
            logger.exception("Protocol error reaching server.")
        elif isinstance(value, xmlrpclib.Fault):
            logger.exception("Exception raised in server.")
        return False

    def _status_accumulate(self, status_dict):
        ret = {}
        status = "Unknown"
        status_acc = status_accumulator(('Deleted', 'Killed', 'Done', 'Failed', 'Received',
                                         'Queued', 'Waiting', 'Running'))
        for k, v in status_dict.iteritems():
            ret[int(k)] = v
            status = status_acc.send(v['Status'])
        return status_map.get(status, "Unknown"), ret

    def submit_job(self, *args):
        return self._status_accumulate(xmlrpclib.ServerProxy.__getattr__(self, 'submit_job')(*args))

    def status(self, ids):
        return self._status_accumulate(xmlrpclib.ServerProxy.__getattr__(self, 'status')(ids))

    def auto_reschedule(self, ids):
        return self._status_accumulate(xmlrpclib.ServerProxy.__getattr__(self, 'auto_reschedule')(ids))

    def reschedule(self, ids):
        return self._status_accumulate(xmlrpclib.ServerProxy.__getattr__(self, 'reschedule')(ids))

'''
@contextmanager
def dirac_server(url):
    """RPC context for communication with dirac environment API."""
    try:
        yield DiracClient(url)
#        yield xmlrpclib.ServerProxy(url)
    except xmlrpclib.ProtocolError:
        logger.exception("Protocol error reaching server.")
    except xmlrpclib.Fault:
        logger.exception("Exception raised in server.")
'''
