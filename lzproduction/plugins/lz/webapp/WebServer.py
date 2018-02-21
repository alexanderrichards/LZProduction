"""LZ Production Web Server."""
import os
import pkg_resources
import jinja2
import cherrypy
from daemonize import Daemonize
import lzproduction.utils.jinja2_utils
from lzproduction.webapp.WebServer import ProductionServer
from lzproduction.utils.apache_utils import CredentialDispatcher
from lzproduction.sql.tables import create_all_tables, Requests, ParametricJobs
from .services import HTMLPageServer, Admins
from .services import GitTagMacros, CVMFSAppVersions

class LZProductionServer(ProductionServer):
    """LZ Production Web Server Daemon."""

    def __init__(self,
                 production_root,
                 git_repo='git@lz-git.ua.edu:sim/TDRAnalysis.git',
                 git_dir=None,
                 **kwargs):
        """Initialisation."""
        super(LZProductionServer, self).__init__(**kwargs)
        self._git_repo = git_repo
        self._git_dir = git_dir or os.path.join(production_root, 'git', 'TDRAnalysis')

        def _setup_mountpoints(self):
            cherrypy.tree.mount(CVMFSAppVersions('/cvmfs/lz.opensciencegrid.org',
                                                 ['LUXSim', 'BACCARAT', 'TDRAnalysis', 'fastNEST',
                                                  'DER',
                                                  'LZap']),
                                '/appversion',
                                {'/': {'request.dispatch': CredentialDispatcher(
                                    cherrypy.dispatch.Dispatcher())}})

            cherrypy.tree.mount(GitTagMacros(self._git_repo, self._git_dir, template_env),
                                '/tags',
                                {'/': {'request.dispatch': CredentialDispatcher(
                                    cherrypy.dispatch.Dispatcher())}})
