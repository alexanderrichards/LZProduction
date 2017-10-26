#from collections import Counter
#from enum import IntEnum, unique
import rpyc
from DIRAC.Interfaces.API.Job import Job
from DIRAC.Interfaces.API.Dirac import Dirac

def autoexpose(cls):
    for i, j in vars(cls).copy().iteritems():
        if isinstance(j, FunctionType) and not\
           (i.startswith('__') or i.startswith('exposed_')):
            setattr(cls, "exposed_%s" % i, j)
    return cls
'''
@unique
class DIRACSTATUS(IntEnum):
    """DIRAC Status Enum."""

    Unknown = 0
    Deleted = 1
    Killed = 2
    Done = 3
    Completed = 4
    Failed = 5
    Stalled = 6
    Running = 7
    Received = 8
    Queued = 9
    Waiting = 10
    Checking = 11
    Matched = 12


class DiracError(RuntimeError):
    """DIRAC Error."""

    pass
'''
class DiracService(rpyc.Service):
    exposed_Job = autoexpose(Job)
    exposed_dirac_api = autoexpose(Dirac)()
'''
    def __init__(self, conn):
        self._dirac_api = Dirac()

    def exposed_status(self, ids):
        """
        Return the status of Dirac jobs with ids.

        This method will essentially be overriding Dirac().status to ensure that the dict
        keys which are the ids of the jobs are cast to strings such that they can be sent
        over xmlrpc socket.
        """
        dirac_answer = self._dirac_api.status(ids)
        if not dirac_answer['OK']:
            raise DiracError(dirac_answer['Message'])
        dirac_statuses = dirac_answer['Value']
        if not dirac_statuses:
            self.logger.warning("Returning status 'Unknown' as no information in DIRAC for ids: %s",
                                ids)
        counter = Counter(info['Status'] for info in dirac_statuses.itervalues())
        ### can probably just use max!!! no need for reduce
        return reduce(max,
                      (DIRACSTATUS[status] for status in counter),
                      DIRACSTATUS.Unknown).name, dict(counter)

    def submit_lfn_parametric_job(self, name, executable, input_lfn_dir, **kwargs):
        """Submit LFN parametric job."""
        lfns = self.list_lfns(input_lfn_dir)
        parameters = [('args', [os.path.basename(l) for l in lfns], False),
                      ('InputData', lfns, 'ParametricInputData')]
        return self.submit_parametric_job(name, executable, parameters, **kwargs)        

    def submit_ranged_parametric_job(self, name, executable, start, stop, step=1, **kwargs):
        """Submit seed ranged parametric job."""
        parameters = [('args', range(start, stop, step), False)]
        return self.submit_parametric_job(name, executable, parameters, **kwargs)


    def submit_parametric_job(self, name, executable, parameters, args='', input_sandbox=None,
                              platform='ANY', site='ANY', output_log='', chunk_size=1000):
        """
        Submit LZProduction job to DIRAC.

        Args:
            executable (str): The full path to the executable job script
            macro (str): The full path to the macro for this job
            starting_seed (int): The random seed for the first of the parametric jobs
            njobs (int): The number of parametric jobs to create
            platform (str): The required platform
            output_log (str): The file name for the output log file

        Returns:
           list: The list of created parametric job DIRAC ids
        """
        dirac_jobs = set()
        for param_slice in param_slicer(parameters, chunk_size):
            j = Job()
            j.setName(name)
            j.setPlatform(platform)
            j.setExecutable(executable, args, output_log)
            j.setInputSandbox(input_sandbox)
            j.setDestination(site)
            for seqname, params, workflow in param_slice:
                j.setParameterSequence(seqname, params, addToWorkflow=workflow)
            dirac_jobs.update(self._dirac_api.submit(j).get("Value", []))
        dirac_jobs = list(dirac_jobs)
        return self.status(dirac_jobs), dirac_jobs

if __name__ == '__main__':
    from rpyc.utils.server import ThreadedServer
    t = ThreadedServer(DiracService, port = 18861)
    t.start()
'''
