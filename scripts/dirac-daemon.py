#!/usr/bin/env python
"""Dirac daemon run script."""
import os
import sys
import argparse
import logging
from logging.handlers import TimedRotatingFileHandler
from SimpleXMLRPCServer import SimpleXMLRPCServer
from enum import IntEnum, unique
from daemonize import Daemonize
from DIRAC.Core.Base import Script
# DIRAC will parse our command line args unless we remove them
tmp, sys.argv = sys.argv, sys.argv[:1]
Script.parseCommandLine(ignoreErrors=True)
sys.argv = tmp
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
            logger.warning("Returning status 'Unknown' as no information in DIRAC for ids: %s", ids)
        return reduce(max,
                      (DIRACSTATUS[info['Status']] for info in dirac_statuses.itervalues()),
                      DIRACSTATUS.Unknown).name

    def submit_job(self, executable, macro, starting_seed=8000000, njobs=10, platform='ANY', output_log='lzproduction_output.log'):
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
            j=Job()
            j.setName(os.path.splitext(os.path.basename(macro))[0] + '%(args)s')
            j.setExecutable(os.path.basename(executable), os.path.basename(macro) + ' %(args)s', output_log)
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
                       if int(self._dirac_api.attributes(job)\
                                             .get('Value', {})\
                                             .get('RescheduleCounter', 0)) < 5]
        if failed_jobs and status_map.get('Done'):
            self._dirac_api.reschedule(failed_jobs)
        return self.status(ids)

if __name__ == '__main__':
    app_name = os.path.splitext(os.path.basename(__file__))[0]
    lzprod_root = os.path.dirname(
        os.path.dirname(
            os.path.expanduser(
                os.path.expandvars(
                    os.path.realpath(
                        os.path.abspath(__file__))))))
    parser = argparse.ArgumentParser(description='Run the DIRAC environment daemon.')
    parser.add_argument('-s', '--host', default='localhost',
                        help="The dirac environment API host [default: %(default)s]")
    parser.add_argument('-p', '--port', default=8000, type=int,
                        help="The dirac environment API port [default: %(default)s]")
    parser.add_argument('-f', '--pid-file', default=os.path.join(lzprod_root, app_name + '.pid'),
                        help="The pid file used by the daemon [default: %(default)s]")
    parser.add_argument('-l', '--log-dir', default=os.path.join(lzprod_root, 'log'),
                        help="Path to the log directory. Will be created if doesn't exist "
                             "[default: %(default)s]")
    parser.add_argument('-v', '--verbose', action='count',
                        help="Increase the logged verbosite, can be used twice")
    parser.add_argument('--debug-mode', action='store_true', default=False,
                        help="Run the daemon in a debug interactive monitoring mode. "
                             "(debugging only)")
    args = parser.parse_args()

    # Logging setup
    ###########################################################################
    # check and create logging dir
    if not os.path.isdir(args.log_dir):
        if os.path.exists(args.log_dir):
            raise Exception("%s path already exists and is not a directory so cant make log dir"
                            % args.log_dir)
        os.mkdir(args.log_dir)

    # setup the handler
    fhandler = TimedRotatingFileHandler(os.path.join(args.log_dir, 'dirac-daemon.log'),
                                        when='midnight', backupCount=5)
    if args.debug_mode:
        fhandler = logging.StreamHandler()
    fhandler.setFormatter(logging.Formatter("[%(asctime)s] %(name)15s : %(levelname)8s : %(message)s"))

    # setup the root logger
    root_logger = logging.getLogger()
    root_logger.handlers = [fhandler]
    root_logger.setLevel({None: logging.INFO,
                          1: logging.INFO,
                          2: logging.DEBUG}.get(args.verbose, logging.DEBUG))

    # setup the main app logger
    logger = logging.getLogger(app_name)
    logger.debug("Script called with args: %s", args)

    # Daemon setup
    ###########################################################################
    DiracDaemon(address=(args.host, args.port),
                app=app_name,
                pid=args.pid_file,
                logger=logger,
                keep_fds=[fhandler.stream.fileno()],
                foreground=args.debug_mode).start()
