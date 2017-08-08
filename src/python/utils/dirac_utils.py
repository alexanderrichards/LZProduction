"""DIRAC utility module."""
import logging
import xmlrpclib
#from contextlib import contextmanager

#from utils.coroutine_utils import status_accumulator

logger = logging.getLogger(__name__)
#base_dispatcher = xmlrpclib.ServerProxy.__getattr__

status_map = {'Done': 'Completed',
              'Failed': 'Failed',
              'Waiting': 'Submitted',
              'Queued': 'Submitted',
              'Checking': 'Submitted',
              'Running': 'Running',
              'Completed': 'Running',
              'Received': 'Submitted',
              'Stalled': 'Failed',
              'Unknown': 'Unknown',
              'Matched': 'Submitted',
              'Killed': 'Killed',
              'Deleted': 'Deleted'}


def apply_status_map(func):
    def wrapper(*args, **kwargs):
        return status_map.get(func(*args, **kwargs), 'Unknown')
    return wrapper


class DiracClient(xmlrpclib.ServerProxy):

    def __enter__(self):
        return self

    def __exit__(self, exec_type, value, tb):
        if isinstance(value, xmlrpclib.ProtocolError):
            logger.exception("Protocol error reaching server.")
        elif isinstance(value, xmlrpclib.Fault):
            logger.exception("Exception raised in server.")
        return False

#    def _status_accumulate(self, status_dict):
#        ret = {}
#        status = "Unknown"
#        status_acc = status_accumulator(('Unknown', 'Deleted', 'Killed', 'Done',
#                                         'Failed', 'Stalled', 'Completed', 'Received', 'Matched',
#                                         'Checking', 'Queued', 'Waiting', 'Running'))
#        if not status_dict:
#            logger.warning("status dict is empty! Unknown status will be returned.")
#        for k, v in status_dict.iteritems():
#            ret[int(k)] = v
#            status = status_acc.send(v['Status'])
#        return status_map.get(status, "Unknown"), ret


    def __getattr__(self, item):
        return apply_status_map(xmlrpclib.ServerProxy.__getattr__(self, item))

    def submit_lfn_parametric_job(self, name, executable,  input_lfn_dir, args='', input_sandbox=None,
                                  platform='ANY', output_log='', chunk_size=1000):
        status, dirac_jobs = xmlrpclib.ServerProxy.__getattr__(self, 'submit_lfn_parametric_job')(name,
                                                                                                  executable,
                                                                                                  input_lfn_dir,
                                                                                                  args,
                                                                                                  input_sandbox,
                                                                                                  platform,
                                                                                                  output_log,
                                                                                                  chunk_size)
        return status_map.get(status, "Unknown"), dirac_jobs

    def submit_ranged_parametric_job(self, name, executable,  start, stop, step=1, args='', input_sandbox=None,
                                     platform='ANY', output_log='', chunk_size=1000):
        status, dirac_jobs = xmlrpclib.ServerProxy.__getattr__(self, 'submit_ranged_parametric_job')(name,
                                                                                                     executable,
                                                                                                     start,
                                                                                                     stop,
                                                                                                     step,
                                                                                                     args,
                                                                                                     input_sandbox,
                                                                                                     platform,
                                                                                                     output_log,
                                                                                                     chunk_size)
        return status_map.get(status, "Unknown"), dirac_jobs

    def submit_parametric_job(self, name, executable,  parameters, args='', input_sandbox=None,
                              platform='ANY', output_log='', chunk_size=1000):
        status, dirac_jobs = xmlrpclib.ServerProxy.__getattr__(self, 'submit_parametric_job')(name,
                                                                                              executable,
                                                                                              parameters,
                                                                                              args,
                                                                                              input_sandbox,
                                                                                              platform,
                                                                                              output_log,
                                                                                              chunk_size)
        return status_map.get(status, "Unknown"), dirac_jobs

#    def status(self, ids):
#        return status_map.get(xmlrpclib.ServerProxy.__getattr__(self, 'status')(ids), "Unknown")

#    def auto_reschedule(self, ids):
#        return status_map.get(xmlrpclib.ServerProxy.__getattr__(self, 'auto_reschedule')(ids),
#                              "Unknown")

#    def reschedule(self, ids):
#        return status_map.get(xmlrpclib.ServerProxy.__getattr__(self, 'reschedule')(ids), "Unknown")

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
