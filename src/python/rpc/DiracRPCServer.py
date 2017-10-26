"""DIRAC RPC Server."""
import rpyc
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
