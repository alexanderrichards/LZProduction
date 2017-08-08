import os
from SimpleXMLRPCServer import SimpleXMLRPCServer
from enum import IntEnum, unique
from daemonize import Daemonize

from DIRAC.Interfaces.API.Dirac import Dirac
from DIRAC.Interfaces.API.Job import Job
from DIRAC.Resources.Catalog.FileCatalog import FileCatalog

def ListSplitter(sequence, nentries):
    ## iterable must be of type Sequence
    for i in xrange(0, len(sequence), nentries):
        yield sequence[i : i + nentries]

def param_slicer(params, nentries):  # , param_index=1):
#    param_lens = [len(i[param_index]) for i in parameters]
    param_lens = [len(i[1]) for i in params]
    if min(param_lens) != max(param_lens):
        raise ValueError("parameters wront size!")

#    param_splitters = [map(lambda i, x: ListSplitter(x, nentries) if i == param_index else x,
#                           enumerate(p))
#                       for p in params]
#    param_splitters = [tuple(ListSplitter(x, nentries) if i == param_index else x
#                             for i, x in enumerate(p))
#                       for p in params]
    param_splitters = [(i, ListSplitter(j, nentries), k) for i, j, k in params]
    while True:
#        yield [tuple(map(lambda i, x: x.next() if i == param_index else x,
#                         enumerate(p)))
#               for p in param_splitters]
#        yield [tuple(x.next() if i == param_index else x
#                     for i, x in enumerate(p))
#               for p in param_splitters]
        yield [(i, j.next(), k) for i, j, k in param_splitters]

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
        dirac_server.register_instance(self._dirac_api)  # Maybe don't want to expose the whole dirac api
        # override Dirac().status to reduce the list of parametric statuses
        dirac_server.register_function(self.status)
        dirac_server.register_function(self.submit_parametric_job)
        dirac_server.register_function(self.submit_lfn_parametric_job)
        dirac_server.register_function(self.submit_ranged_parametric_job)
        dirac_server.register_function(self.reschedule)
        dirac_server.register_function(self.auto_reschedule)
        dirac_server.register_function(self.list_lfns)
        dirac_server.serve_forever()

    def list_lfns(self, root_dir):
        file_catalog = FileCatalog()
        return file_catalog.listDirectory(root_dir, timeout=360)\
                           .get('Value', {})\
                           .get('Successful', {})\
                           .get(root_dir, {})\
                           .get('Files', {}).keys()

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

    def submit_lfn_parametric_job(self, name, executable,  input_lfn_dir, args='', input_sandbox=None,
                                  platform='ANY', output_log='', chunk_size=1000):
        lfns = self.list_lfns(input_lfn_dir)
        parameters = [('args', [os.path.basename(l) for l in lfns], False),
                      ('InputData', lfns, 'ParametricInputData')]
        return self.submit_parametric_job(name, executable,  parameters, args, input_sandbox,
                                          platform, output_log, chunk_size)

    def submit_ranged_parametric_job(self, name, executable, start, stop, step=1, args='', input_sandbox=None,
                                     platform='ANY', output_log='', chunk_size=1000):
        parameters = [('args', range(start, stop, step), False)]
        return self.submit_parametric_job(name, executable,  parameters, args, input_sandbox,
                                          platform, output_log, chunk_size)

    def submit_parametric_job(self, name, executable,  parameters, args='', input_sandbox=None,
                              platform='ANY', output_log='', chunk_size=1000):
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
            for seqname, params, workflow in param_slice:
                j.setParameterSequence(seqname, params, addToWorkflow=workflow)
            dirac_jobs.update(self._dirac_api.submit(j).get("Value", []))
        dirac_jobs = list(dirac_jobs)
        return self.status(dirac_jobs), dirac_jobs

#    def submit_parametric_job(self, name, executable, args='', input_sandbox=None, parameters,
#                              param_seqname, workflow, platform, output_log='', chunk_size=1000):
#        """
#        Submit LZProduction job to DIRAC.
#
#        Args:
#            executable (str): The full path to the executable job script
#            macro (str): The full path to the macro for this job
#            starting_seed (int): The random seed for the first of the parametric jobs
#            njobs (int): The number of parametric jobs to create
#            platform (str): The required platform
#            output_log (str): The file name for the output log file
#
#        Returns:
#           list: The list of created parametric job DIRAC ids
#        """
#        dirac_jobs = set()
#        for i in ListSplitter(parameters, chunk_size):
#            j = Job()
#            j.setName(name)
#            j.setPlatform(platform)
#            j.setExecutable(executable, args, output_log)
#            j.setInputSandbox(input_sandbox)
#            j.setParameterSequence(param_seqname, i, addToWorkflow=workflow)
#            dirac_jobs.update(self._dirac_api.submit(j).get("Value", []))
#        dirac_jobs = list(dirac_jobs)
#        return self.status(dirac_jobs), dirac_jobs

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
        2) The job hasn't reached a reschedule count of 2
        """
        status_map = {}
        for k, v in self._dirac_api.status(ids).get("Value", {}).iteritems():
            status_map.setdefault(v['Status'], []).append(k)

        failed_jobs = [job for job in status_map.get('Failed')
                       if int(self._dirac_api.attributes(job)
                                             .get('Value', {})
                                             .get('RescheduleCounter', 0)) < 2]
        if failed_jobs and status_map.get('Done'):
            self._dirac_api.reschedule(failed_jobs)
        return self.status(ids)
