import os
from SimpleXMLRPCServer import SimpleXMLRPCServer
from enum import IntEnum, unique
from daemonize import Daemonize

from DIRAC.Interfaces.API.Dirac import Dirac
from DIRAC.Interfaces.API.Job import Job


@unique
class DIRACSTATUS(IntEnum):
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
    pass


class DiracDaemon(Daemonize):
    """Dirac Daemon."""

    def __init__(self, address, **kwargs):
        """Initialise."""
        super(DiracDaemon, self).__init__(action=self.main, **kwargs)
        self._address = address
        self._dirac_api = Dirac()

    def main(self):
        """Daemon main."""
        # Defer creation of server to inside the daemon context otherwise the socket will be
        # closed when daemonising
        dirac_server = SimpleXMLRPCServer(self._address)
        dirac_server.register_introspection_functions()
        dirac_server.register_instance(self._dirac_api)
        # override Dirac().status to make sure that the keys are strings.
        dirac_server.register_function(self.status)
        dirac_server.register_function(self.submit_job)
        dirac_server.register_function(self.reschedule)
        dirac_server.register_function(self.auto_reschedule)
        dirac_server.serve_forever()

    def status(self, ids):
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
        return reduce(max,
                      (DIRACSTATUS[info['Status']] for info in dirac_statuses.itervalues()),
                      DIRACSTATUS.Unknown).name

    def submit_job(self, executable, macro, starting_seed=8000000, njobs=10, platform='ANY',
                   output_log='lzproduction_output.log'):
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
        for i in xrange(starting_seed, starting_seed + njobs, 1000):
            j = Job()
            j.setName(os.path.splitext(os.path.basename(macro))[0] + '-%(args)s')
            j.setExecutable(os.path.basename(executable), os.path.basename(macro) + ' %(args)s',
                            output_log)
            j.setInputSandbox([executable, macro])
            j.setParameterSequence("args",
                                   map(str, xrange(i, min(i + 1000, starting_seed + njobs))),
                                   addToWorkflow=True)
            j.setPlatform(platform)
            dirac_jobs.update(self._dirac_api.submit(j).get("Value", []))
        dirac_jobs = list(dirac_jobs)
        return self.status(dirac_jobs), dirac_jobs

    def reschedule(self, ids):
        """
        Reschedule all jobs in state Failed.
        """
        failed_jobs = [k for k, v in self._dirac_api.status(ids).get("Value", {}).iteritems()
                       if v['Status'] == "Failed"]
        if failed_jobs:
            self._dirac_api.reschedule(failed_jobs)
        return self.status(ids)

    def auto_reschedule(self, ids):
        """
        Automatically reschedule jobs that meet certain criteria.

        This method will reschedule jobs from a list that are in state failed,
        so long as:
        1) There is at least one job in the list in the Done state
        2) The job hasn't reached a reschedule count of 5
        """
        status_map = {}
        for k, v in self._dirac_api.status(ids).get("Value", {}).iteritems():
            status_map.setdefault(v['Status'], []).append(k)

        failed_jobs = [job for job in status_map.get('Failed')
                       if int(self._dirac_api.attributes(job)
                                             .get('Value', {})
                                             .get('RescheduleCounter', 0)) < 5]
        if failed_jobs and status_map.get('Done'):
            self._dirac_api.reschedule(failed_jobs)
        return self.status(ids)