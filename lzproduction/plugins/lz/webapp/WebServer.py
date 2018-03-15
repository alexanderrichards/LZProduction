"""LZ Production Web Server."""
import os
import jinja2
import pkg_resources
import cherrypy
from lzproduction.utils.apache_utils import CredentialDispatcher
from lzproduction.webapp.WebServer import ProductionServer
from .services import CVMFSAppVersions, GitTagMacros


class LZProductionServer(ProductionServer):
    """LZ Production Web Server Daemon."""

    def __init__(self,
                 production_root,
                 git_repo='git@lz-git.ua.edu:sim/TDRAnalysis.git',
                 git_dir=None,
                 *args, **kwargs):
        """Initialisation."""
        super(LZProductionServer, self).__init__(*args, **kwargs)
        self._git_repo = git_repo
        self._git_dir = git_dir or os.path.join(production_root, 'git', 'TDRAnalysis')

    def mountpoints(self):
        super(LZProductionServer, self).mountpoints()
        template_resources = pkg_resources.resource_filename('lzproduction', 'plugins/lz/resources/templates')
        template_env = jinja2.Environment(loader=jinja2.FileSystemLoader(searchpath=template_resources))
        cherrypy.tree.mount(CVMFSAppVersions('/cvmfs/lz.opensciencegrid.org',
                                             ['LUXSim', 'BACCARAT', 'TDRAnalysis', 'fastNEST', 'DER', 'LZap']),
                            '/appversion',
                            {'/': {'request.dispatch': CredentialDispatcher(cherrypy.dispatch.Dispatcher())}})
        cherrypy.tree.mount(GitTagMacros(self._git_repo, self._git_dir, template_env),
                            '/tags',
                            {'/': {'request.dispatch': CredentialDispatcher(cherrypy.dispatch.Dispatcher())}})
