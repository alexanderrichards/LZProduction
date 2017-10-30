"""DIRAC RPC Server."""
from types import FunctionType
import rpyc
from rpyc.utils.server import ThreadedServer
from daemonize import Daemonize
from DIRAC.Interfaces.API.Job import Job
from DIRAC.Interfaces.API.Dirac import Dirac


def autoexpose(cls):
    """Tag all methods as exposed."""
    for i, j in vars(cls).copy().iteritems():
        if isinstance(j, FunctionType) and not\
           (i.startswith('__') or i.startswith('exposed_')):
            setattr(cls, "exposed_%s" % i, j)
    return cls


class DiracService(rpyc.Service):
    """DIRAC RPyC Service."""

    exposed_Job = autoexpose(Job)
    exposed_dirac_api = autoexpose(Dirac)()


class DiracDaemon(Daemonize):
    """DIRAC daemon to host the server."""

    def __init__(self, address, **kwargs):
        """Initialise."""
        self._address = address
        self._logger = kwargs.get('logger')
        super(DiracDaemon, self).__init__(action=self.main, **kwargs)

    def main(self):
        # Set up the threaded server in the daemon main
        # else the file descriptors will be closed when daemon starts.
        hostname, port = self._address
        ThreadedServer(DiracService,
                       hostname=hostname,
                       port=port,
                       logger=self._logger).start()
