"""DIRAC utility module."""
import logging
import xmlrpclib
from collections import Counter
from .string_utils import DefaultFormatter

logger = logging.getLogger(__name__)  # pylint: disable=invalid-name
# BASE_DISPATCHER = xmlrpclib.ServerProxy.__getattr__

STATUS_MAP = {'Done': 'Completed',
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
    """Decorate finctions with status_map."""
    def wrapper(*args, **kwargs):
        """wrapper."""
        return STATUS_MAP.get(func(*args, **kwargs), 'Unknown')
    return wrapper


def counter_magic(dirac_counter):
    """Get counter string."""
    dirac_counter = Counter(dirac_counter)  # Can't serialise Counter so must convert back
    counter = Counter(STATUS_MAP.get(status, 'Unknown') for status in dirac_counter.elements())
    counter_str = '{Completed}/{Failed}/{Killed}/{Deleted}/{Unknown}/{Running}/{Submitted}'
    return DefaultFormatter(0).format(counter_str, **counter)


class DiracClient(xmlrpclib.ServerProxy):
    """DIRAC RPC Client."""

    def __enter__(self):
        """Enter context."""
        return self

    def __exit__(self, exec_type, value, traceback):
        """Exit context."""
        if isinstance(value, xmlrpclib.ProtocolError):
            logger.exception("Protocol error reaching server.")
        elif isinstance(value, xmlrpclib.Fault):
            logger.exception("Exception raised in server.")
        return False

    def submit_lfn_parametric_job(self, name, executable, input_lfn_dir, args='',
                                  input_sandbox=None, platform='ANY', output_log='',
                                  chunk_size=1000):
        """Submit LFN parametric job."""
        rpc_method = xmlrpclib.ServerProxy.__getattr__(self, 'submit_lfn_parametric_job')
        (status, counter), dirac_jobs = rpc_method(name,
                                                   executable,
                                                   input_lfn_dir,
                                                   args,
                                                   input_sandbox,
                                                   platform,
                                                   output_log,
                                                   chunk_size)
        return STATUS_MAP.get(status, "Unknown"), counter_magic(counter), dirac_jobs

    def submit_ranged_parametric_job(self, name, executable, start, stop, step=1, args='',
                                     input_sandbox=None, platform='ANY', output_log='',
                                     chunk_size=1000):
        """Submit seed ranged parametric job."""
        rpc_method = xmlrpclib.ServerProxy.__getattr__(self, 'submit_ranged_parametric_job')
        (status, counter), dirac_jobs = rpc_method(name,
                                                   executable,
                                                   start,
                                                   stop,
                                                   step,
                                                   args,
                                                   input_sandbox,
                                                   platform,
                                                   output_log,
                                                   chunk_size)
        return STATUS_MAP.get(status, "Unknown"), counter_magic(counter), dirac_jobs

    def submit_parametric_job(self, name, executable, parameters, args='', input_sandbox=None,
                              platform='ANY', output_log='', chunk_size=1000):
        """Submit parametric job."""
        rpc_method = xmlrpclib.ServerProxy.__getattr__(self, 'submit_parametric_job')
        (status, counter), dirac_jobs = rpc_method(name,
                                                   executable,
                                                   parameters,
                                                   args,
                                                   input_sandbox,
                                                   platform,
                                                   output_log,
                                                   chunk_size)
        return STATUS_MAP.get(status, "Unknown"), counter_magic(counter), dirac_jobs

    def status(self, ids):
        """Return accumulated status."""
        status, counter = xmlrpclib.ServerProxy.__getattr__(self, 'status')(ids)
        return STATUS_MAP.get(status, "Unknown"), counter_magic(counter)

    def auto_reschedule(self, ids):
        """Auto reschedule."""
        status, counter = xmlrpclib.ServerProxy.__getattr__(self, 'auto_reschedule')(ids)
        return STATUS_MAP.get(status, "Unknown"), counter_magic(counter)

    def reschedule(self, ids):
        """Reschedule."""
        status, counter = xmlrpclib.ServerProxy.__getattr__(self, 'reschedule')(ids)
        return STATUS_MAP.get(status, "Unknown"), counter_magic(counter)
