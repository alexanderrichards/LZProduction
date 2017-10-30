"""DIRAC RPC Server."""
import rpyc
from rpyc.utils.server import ThreadedServer
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
        hostname, port = address
        self._server = ThreadedServer(DiracService,
                                      hostname=hostname,
                                      port=port,
                                      logger=kwargs.get('logger'))
        super(DiracDaemon, self).__init__(action=self._server.start, **kwargs)
