import logging
from contextlib import contextmanager
import rpyc

logger = logging.getLogger(__name__)
#@contextmanager
#def parametric_dirac_job(parametricjob):
#    try:
#        conn = rpyc.connect("localhost", 18861)
#        job = conn.root.Job()
#        yield job
#        job_ids = conn.root.dirac_api.submit(job).get('Value', [])
#        parametricjob.diracjobs.update(job_ids)
#    finally:
#        conn.close()

@contextmanager
def dirac_api_client(host="localhost", port=18861):
    conn = rpyc.connect(host, port)
    try:
        yield conn.root.dirac_api
    finally:
        conn.close()


class ParametricDiracJobClient(object):
    def __init__(self, host='localhost', port=18861):
        self._address = (host, port)
        self._dirac_job_ids = set()
        self._conn = None
        self._job = None

    def __enter__(self):
        self._conn = rpyc.connect(*self._address)
        self._job = self._conn.root.Job()
        self._dirac_job_ids.clear()
        return self._job

    def __exit__(self, exc_type, exc_value, traceback):
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
        return list(self._dirac_job_ids)


if __name__ == '__main__':
    parametric_job = ParametricDiracJobClient()
    with parametric_job as j:
        j.setName(name)
        j.setPlatform(platform)
        j.setExecutable(executable, args, output_log)
        j.setInputSandbox(input_sandbox)
        j.setDestination(site)
    parametric_job.subjob_ids

    
