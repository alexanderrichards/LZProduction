#!/usr/bin/env python
"""Dirac daemon run script."""
import os
import argparse
import logging
from SimpleXMLRPCServer import SimpleXMLRPCServer
from daemonize import Daemonize
from DIRAC.Core.Base import Script
Script.parseCommandLine(ignoreErrors=True)
from DIRAC.Interfaces.API.Dirac import Dirac
from DIRAC.Interfaces.API.Job import Job

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
        dirac_server.serve_forever()

    def status(self, ids):
        """
        Return the status of Dirac jobs with ids.

        This method will essentially be overriding Dirac().status to ensure that the dict
        keys which are the ids of the jobs are cast to strings such that they can be sent
        over xmlrpc socket.
        """
        return {str(k): v for k, v in self._dirac_api.status(ids).get("Value", {}).iteritems()}

    def submit_job(self, request_id, executable, macro, starting_seed=8000000, njobs=10, platform='ANY', output_log='lzproduction_output.log'):
        """
        Submit LZProduction job to DIRAC.

        Args:
            request_id (int): The id number of the associated request
            executable (str): The full path to the executable job script
            macro (str): The full path to the macro for this job
            starting_seed (int): The random seed for the first of the parametric jobs
            njobs (int): The number of parametric jobs to create
            platform (str): The required platform
            output_log (str): The file name for the output log file

        Returns:
           list: The list of created parametric job DIRAC ids
        """
        j=Job()
        j.setName(os.path.splitext(os.path.basename(macro))[0] + '%(args)s')
        j.setExecutable(os.path.basename(executable), os.path.basename(macro) + ' %(args)s', output_log)
        j.setInputSandbox([executable, macro])
        j.setParameterSequence("args", [str(i) for i in xrange(starting_seed, starting_seed + njobs)], addToWorkflow=True)
        j.setPlatform(platform)

        return self.status(self._dirac_api.submit(j).get("Value", []))



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
    parser.add_argument('--debug-mode', action='store_true', default=False,
                        help="Run the daemon in a debug interactive monitoring mode. "
                             "(debugging only)")
    args = parser.parse_args()

    # Daemon setup
    ###########################################################################
    DiracDaemon(address=(args.host, args.port),
                app=app_name,
                pid=args.pid_file,
                foreground=args.debug_mode).start()
