"""LZ Production Web Server."""
import os
import jinja2
import cherrypy
from daemonize import Daemonize
from sql.tables import create_all_tables
from utils.apache_utils import CredentialDispatcher
import utils.jinja2_utils
from .services import HTMLPageServer, CVMFSAppVersions, GitTagMacros, Admins#, RequestsDBAPI
from sql.tables import Requests

class LZProductionServer(Daemonize):
    """LZ Production Web Server Daemon."""

    def __init__(self,
                 production_root,
                 dburl="sqlite:///",
                 socket_host='0.0.0.0',
                 socket_port=8080,
                 thread_pool=8,
                 git_repo='git@lz-git.ua.edu:sim/TDRAnalysis.git',
                 git_dir=None,
                 **kwargs):
        """Initialisation."""
        super(LZProductionServer, self).__init__(action=self.main, **kwargs)
        self._dburl = dburl
        self._socket_host = socket_host
        self._socket_port = socket_port
        self._thread_pool = thread_pool
        self._git_repo = git_repo
        self._src_root = os.path.join(production_root, 'src')
        self._git_dir = git_dir or os.path.join(production_root, 'git', 'TDRAnalysis')

    def main(self):
        """Daemon main."""
        create_all_tables(self._dburl)
        template_env = jinja2.Environment(loader=jinja2.FileSystemLoader(searchpath=self._src_root))

        config = {
            'global': {
                'tools.gzip.on': True,
                'tools.staticdir.root': os.path.join(self._src_root, 'html'),
                'tools.staticdir.on': True,
                'tools.staticdir.dir': '',
                'server.socket_host': self._socket_host,
                'server.socket_port': self._socket_port,
                'server.thread_pool': self._thread_pool,
                'tools.expires.on': True,
                'tools.expires.secs': 3,  # expire in an hour, 3 secs for debug
                'checker.check_static_paths': None
            }
        }

        cherrypy.config.update(config)  # global vars need updating global config
        cherrypy.tree.mount(HTMLPageServer(template_env),
                            '/',
                            {'/': {'request.dispatch': CredentialDispatcher(cherrypy.dispatch.Dispatcher())}})
        cherrypy.tree.mount(Requests,
                            '/api',
                            {'/': {'request.dispatch': CredentialDispatcher(cherrypy.dispatch.MethodDispatcher())}})
        cherrypy.tree.mount(ParametricJobs,
                            '/parametricjobs',
                            {'/': {'request.dispatch': CredentialDispatcher(cherrypy.dispatch.MethodDispatcher())}})
        cherrypy.tree.mount(CVMFSAppVersions('/cvmfs/lz.opensciencegrid.org',
                                                      ['LUXSim', 'BACCARAT', 'TDRAnalysis', 'fastNEST', 'DER', 'LZap']),
                            '/appversion',
                            {'/': {'request.dispatch': CredentialDispatcher(cherrypy.dispatch.Dispatcher())}})
        cherrypy.tree.mount(GitTagMacros(self._git_repo, self._git_dir, template_env),
                            '/tags',
                            {'/': {'request.dispatch': CredentialDispatcher(cherrypy.dispatch.Dispatcher())}})
        cherrypy.tree.mount(Admins(template_env),
                            '/admins',
                            {'/': {'request.dispatch': CredentialDispatcher(cherrypy.dispatch.MethodDispatcher(),
                                                                                          admin_only=True)}})
        cherrypy.engine.start()
        cherrypy.engine.block()
