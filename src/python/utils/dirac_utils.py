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

def counter_magic(dirac_counter):
    counter = Counter(status_map.get(status, 'Unknown') for status in dirac_counter.elements())
    return '{Completed}/{Failed}/{Killed}/{Deleted}/{Unknown}/{Running}/{Submitted}'.format(**counter)
    

class DiracClient(xmlrpclib.ServerProxy):

    def __enter__(self):
        return self

    def __exit__(self, exec_type, value, tb):
        if isinstance(value, xmlrpclib.ProtocolError):
            logger.exception("Protocol error reaching server.")
        elif isinstance(value, xmlrpclib.Fault):
            logger.exception("Exception raised in server.")
        return False

    def submit_lfn_parametric_job(self, name, executable,  input_lfn_dir, args='', input_sandbox=None,
                                  platform='ANY', output_log='', chunk_size=1000):
        (status, c), dirac_jobs = xmlrpclib.ServerProxy.__getattr__(self, 'submit_lfn_parametric_job')(name,
                                                                                                  executable,
                                                                                                  input_lfn_dir,
                                                                                                  args,
                                                                                                  input_sandbox,
                                                                                                  platform,
                                                                                                  output_log,
                                                                                                  chunk_size)
        return status_map.get(status, "Unknown"), counter_magic(c), dirac_jobs

    def submit_ranged_parametric_job(self, name, executable,  start, stop, step=1, args='', input_sandbox=None,
                                     platform='ANY', output_log='', chunk_size=1000):
        (status, c), dirac_jobs = xmlrpclib.ServerProxy.__getattr__(self, 'submit_ranged_parametric_job')(name,
                                                                                                     executable,
                                                                                                     start,
                                                                                                     stop,
                                                                                                     step,
                                                                                                     args,
                                                                                                     input_sandbox,
                                                                                                     platform,
                                                                                                     output_log,
                                                                                                     chunk_size)
        return status_map.get(status, "Unknown"), counter_magic(c), dirac_jobs

    def submit_parametric_job(self, name, executable,  parameters, args='', input_sandbox=None,
                              platform='ANY', output_log='', chunk_size=1000):
        (status, c), dirac_jobs = xmlrpclib.ServerProxy.__getattr__(self, 'submit_parametric_job')(name,
                                                                                              executable,
                                                                                              parameters,
                                                                                              args,
                                                                                              input_sandbox,
                                                                                              platform,
                                                                                              output_log,
                                                                                              chunk_size)
        return status_map.get(status, "Unknown"), counter_magic(c), dirac_jobs

    def status(self, ids):
        status, counter = xmlrpclib.ServerProxy.__getattr__(self, 'status')(ids)
        return status_map.get(status, "Unknown"), counter_magic(counter)

    def auto_reschedule(self, ids):
        status, counter = xmlrpclib.ServerProxy.__getattr__(self, 'auto_reschedule')(ids)
        return status_map.get(status, "Unknown"), counter_magic(counter)

    def reschedule(self, ids):
        status, counter = xmlrpclib.ServerProxy.__getattr__(self, 'reschedule')(ids)
        return status_map.get(status, "Unknown"), counter_magic(counter)
