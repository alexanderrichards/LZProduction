"""LZ Production Web Server."""
import os
import pkg_resources
import jinja2
import cherrypy
from daemonize import Daemonize
import lzproduction.utils.jinja2_utils
from lzproduction.utils.apache_utils import CredentialDispatcher
from lzproduction.sql.tables import create_all_tables, Requests, ParametricJobs
from .services import HTMLPageServer, Admins


class ProductionServer(Daemonize):
    """LZ Production Web Server Daemon."""

    def __init__(self,
                 dburl="sqlite:///",
                 socket_host='0.0.0.0',
                 socket_port=8080,
                 thread_pool=8,
                 **kwargs):
        """Initialisation."""
        super(ProductionServer, self).__init__(action=self.main, **kwargs)
        self._dburl = dburl
        self._socket_host = socket_host
        self._socket_port = socket_port
        self._thread_pool = thread_pool

    def config(self):
        static_resources = pkg_resources.resource_filename('lzproduction', 'resources/static')
        return {
            'global': {
                'tools.gzip.on': True,
                'tools.staticdir.root': static_resources,
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

    def mountpoints(self):
        template_resources = pkg_resources.resource_filename('lzproduction', 'resources/templates')
        template_env = jinja2.Environment(loader=jinja2.FileSystemLoader(searchpath=template_resources))
        cherrypy.tree.mount(HTMLPageServer(template_env),
                            '/',
                            {'/': {'request.dispatch': CredentialDispatcher(cherrypy.dispatch.Dispatcher())}})
        cherrypy.tree.mount(Requests,
                            '/api',
                            {'/': {'request.dispatch': CredentialDispatcher(cherrypy.dispatch.MethodDispatcher())}})
        cherrypy.tree.mount(ParametricJobs,
                            '/parametricjobs',
                            {'/': {'request.dispatch': CredentialDispatcher(cherrypy.dispatch.MethodDispatcher())}})

        cherrypy.tree.mount(Admins(template_env),
                            '/admins',
                            {'/': {'request.dispatch': CredentialDispatcher(cherrypy.dispatch.MethodDispatcher(),
                                                                                          admin_only=True)}})


    def main(self):
        """Daemon main."""
        create_all_tables(self._dburl)
        cherrypy.config.update(self.config())  # global vars need updating global config
        self.mountpoints()
        cherrypy.engine.start()
        cherrypy.engine.block()
