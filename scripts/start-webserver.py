#!/usr/bin/env python
import os
import sys
import logging
import argparse
import importlib
import cherrypy
from logging.handlers import TimedRotatingFileHandler

class WebServer(object):
    def __init__(self, index_page):
        self.index_page = index_page

    @cherrypy.expose
    def index(self):
        with open(self.index_page, 'rb') as front_page:
            return front_page.read()

if __name__ == '__main__':
    lzprod_root = os.path.dirname(os.path.dirname(os.path.expanduser(os.path.expandvars(os.path.realpath(os.path.abspath(__file__))))))
    parser = argparse.ArgumentParser(description='Run the LZ production web server.')
    parser.add_argument('-v', '--verbose', default=logging.INFO, action="store_const",
                        const=logging.DEBUG, dest='logginglevel',
                        help="Increase the verbosity of output")
    parser.add_argument('-l', '--log-dir', default=os.path.join(lzprod_root, 'log'),
                        help="Path to the log directory. Will be created if doesn't exist [default: %(default)s]")
    parser.add_argument('-g', '--git-dir', default=os.path.join(lzprod_root, 'git', 'TDRAnalysis'),
                        help="Path to the directory where to clone TDRAnalysis git repo [default: %(default)s]")
    parser.add_argument('-a', '--socket-host', default='0.0.0.0',
                        help="The host address to listen on (0.0.0.0 means all available) [default: %(default)s]")
    parser.add_argument('-p', '--socket-port', default=8080, type=int,
                        help="The host port to listen on [default: %(default)s]")
    parser.add_argument('-t', '--thread-pool', default=8, type=int,
                        help="The number of threads in the pool [default: %(default)s]")
    args = parser.parse_args()

    if not os.path.isdir(args.log_dir):
        if os.path.exists(args.log_dir):
            raise Exception("%s path already exists and is not a directory so cant make log dir" % args.log_dir)
        os.mkdir(args.log_dir)

    fhandler = TimedRotatingFileHandler(os.path.join(args.log_dir, 'LZWebServer.log'),
                                        when='midnight', backupCount=5)
    fhandler.setFormatter(logging.Formatter("[%(asctime)s] %(name)15s : %(levelname)8s : %(message)s"))
    root_logger = logging.getLogger()
    root_logger.addHandler(fhandler)
    root_logger.setLevel(args.logginglevel)

    # force cherrypy to log to the logfile
    cherrypy_logger = logging.getLogger('cherrypy.error')
    cherrypy_logger.setLevel(logging.NOTSET)
    handlers = cherrypy_logger.handlers[:]
    for h in handlers:
        cherrypy_logger.removeHandler(h)


    logger = logging.getLogger("LZWebServer")
    logger.debug("Script called with args: %s", args)
#    sys.exit(0)

    # Add the python src path to the sys.path for future imports
    sys.path = [os.path.join(lzprod_root, 'src', 'python')] + sys.path

    RequestsDB = importlib.import_module('services.RequestsDB')
    CVMFSAppVersions = importlib.import_module('services.CVMFSAppVersions')
    GitTagMacros = importlib.import_module('services.GitTagMacros')

    config = {
        'global': {
            'tools.gzip.on': True,
            'tools.staticdir.root': os.path.join(lzprod_root, 'src', 'html'),
            'tools.staticdir.on': True,
            'tools.staticdir.dir': '',
            'server.socket_host': args.socket_host,
            'server.socket_port': args.socket_port,
            'server.thread_pool': args.thread_pool,
            'tools.expires.on'    : True,
            'tools.expires.secs'  : 3 # expire in an hour
        }
    }

    cherrypy.config.update(config)  # global vars need updating global config
    cherrypy.tree.mount(WebServer(os.path.join(lzprod_root, 'src', 'html', 'index.html')), '/')
    cherrypy.tree.mount(RequestsDB.RequestsDB("sqlite:///requests.db"),
                        '/api',
                        {'/': {'request.dispatch': cherrypy.dispatch.MethodDispatcher()}})
    cherrypy.tree.mount(CVMFSAppVersions.CVMFSAppVersions('/cvmfs/lz.opensciencegrid.org',
                                                          ['LUXSim', 'BACCARAT', 'TDRAnalysis']),
                        '/appversion',
                        {'/': {'request.dispatch': cherrypy.dispatch.MethodDispatcher()}})
    cherrypy.tree.mount(GitTagMacros.GitTagMacros('git@lz-git.ua.edu:sim/TDRAnalysis.git',
                                                  args.git_dir),
                        '/tags',
                        {'/': {'request.dispatch': cherrypy.dispatch.MethodDispatcher()}})
    cherrypy.engine.start()
    cherrypy.engine.block()

    logging.shutdown()
