"""DIRAC RPC Server."""
import logging
from types import FunctionType
import rpyc
from rpyc.utils.server import ThreadedServer
from daemonize import Daemonize
from DIRAC.Interfaces.API.Job import Job
from DIRAC.Interfaces.API.Dirac import Dirac


logger = logging.getLogger(__name__)  # pylint: disable=invalid-name


#def autoexpose(cls):
#    """Tag all methods as exposed."""
#    for i, j in vars(cls).copy().iteritems():
#        if isinstance(j, FunctionType) and not\
#           (i.startswith('__') or i.startswith('exposed_')):
#            setattr(cls, "exposed_%s" % i, j)
#    return cls

class FixedJob(Job):
    """Fixed DIRAC Job class."""

    def setInputSandbox(self, files):
        """
        Set the input sandbox.

        This method uses if type(files) == list in DIRAC which fails for
        rpc type <netref list>. isinstance should be used instead. Solution
        is to intercept this arg and cast it to a list.
        """
        if isinstance(files, list):
            files = list(files)
        return super(NewJob, self).setInputSandbox(files)


class FixedDirac(Dirac):
    """Fixed DIRAC Dirac class."""

    def status(self, jobid):
        """
        Return the status of DIRAC jobs.

        This method does not have an encoder setup for type set
        let alone rpc type type <netref set>. we intercept the arg here and
        cast to a list.
        """
        if isinstance(jobid, (list, set)):
            jobid = list(jobid)
        return super(NewDirac, self).status(jobid)


class DiracService(rpyc.Service):
    """DIRAC RPyC Service."""

    exposed_Job = FixedJob
    exposed_dirac_api = FixedDirac()


class DiracDaemon(Daemonize):
    """DIRAC daemon to host the server."""

    def __init__(self, address, **kwargs):
        """Initialise."""
        self._address = address
        super(DiracDaemon, self).__init__(action=self.main, **kwargs)

    def main(self):
        """Daemon main."""
        # Set up the threaded server in the daemon main
        # else the file descriptors will be closed when daemon starts.
        hostname, port = self._address
        ThreadedServer(DiracService,
                       hostname=hostname,
                       port=port,
                       logger=logger,
                       protocol_config={"allow_public_attrs": True,
                                        "allow_pickle": True}).start()
