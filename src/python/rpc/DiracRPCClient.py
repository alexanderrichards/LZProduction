"""DIRAC RPC Client utilities."""
import logging
from contextlib import contextmanager
import rpyc

logger = logging.getLogger(__name__)  # pylint: disable=invalid-name


@contextmanager
def dirac_api_client(host="localhost", port=18861):
    """RPC DIRAC API client context."""
    conn = rpyc.connect(host, port)
    try:
        yield conn.root.dirac_api
    finally:
        conn.close()


class ParametricDiracJobClient(object):
    """
    RPC DIRAC parametric job context.

    This class behaves like a context and automatically
    attempts to submit the DIRAC job at context exit. It
    also keeps a record of the DIRAC job ids for sucessfully
    submitted jobs.
    """

    def __init__(self, host='localhost', port=18861):
        """Initialisation."""
        self._address = (host, port)
        self._dirac_job_ids = set()
        self._conn = None
        self._job = None

    def __enter__(self):
        """Enter context."""
        self._conn = rpyc.connect(*self._address)
        self._job = self._conn.root.Job()
        self._dirac_job_ids.clear()
        return self._job

    def __exit__(self, exc_type, exc_value, traceback):
        """Exit context."""
        if exc_type is not None:
            logger.exception("Error setting up parametric job.")
            self._conn.close()
            return False

        try:
            self._dirac_job_ids.update(self._conn.root.dirac_api.submit(self._job).get("Value", []))
        except:
            logger.exception("Error submitting job.")
            raise
        finally:
            self._conn.close()
        return False

    @property
    def subjob_ids(self):
        """Return the DIRAC jobs created."""
        return list(self._dirac_job_ids)
