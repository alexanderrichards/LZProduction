#!/usr/bin/env python
# pylint: disable=invalid-name
"""Script to start the LZ Production web server."""
import os
import sys
import argparse
import importlib
import pkg_resources
import logging
from logging.handlers import TimedRotatingFileHandler

if __name__ == '__main__':
    app_name = os.path.splitext(os.path.basename(__file__))[0]
    lzprod_root = os.path.dirname(
        os.path.dirname(
            os.path.expanduser(
                os.path.expandvars(
                    os.path.realpath(
                        os.path.abspath(__file__))))))

    parser = argparse.ArgumentParser(description='Run the LZ production web server.')
    parser.add_argument('-v', '--verbose', default=logging.INFO, action="store_const",
                        const=logging.DEBUG, dest='logginglevel',
                        help="Increase the verbosity of output")
    parser.add_argument('-l', '--log-dir', default=os.path.join(lzprod_root, 'log'),
                        help="Path to the log directory. Will be created if doesn't exist "
                             "[default: %(default)s]")
    parser.add_argument('-r', '--git-repo', default='git@lz-git.ua.edu:sim/TDRAnalysis.git',
                        help="Git repo url [default: %(default)s]")
    parser.add_argument('-g', '--git-dir', default=os.path.join(lzprod_root, 'git', 'TDRAnalysis'),
                        help="Path to the directory where to clone TDRAnalysis git repo "
                             "[default: %(default)s]")
    parser.add_argument('-d', '--dburl',
                        default="sqlite:///" + os.path.join(lzprod_root, 'requests.db'),
                        help="URL for the requests DB. Note can use the prefix 'mysql+pymysql://' "
                             "if you have a problem with MySQLdb.py [default: %(default)s]")
    parser.add_argument('-a', '--socket-host', default='0.0.0.0',
                        help="The host address to listen on (0.0.0.0 means all available "
                             "interfaces) [default: %(default)s]")
    parser.add_argument('-p', '--socket-port', default=8080, type=int,
                        help="The host port to listen on [default: %(default)s]")
    parser.add_argument('-t', '--thread-pool', default=8, type=int,
                        help="The number of threads in the pool [default: %(default)s]")
    parser.add_argument('-i', '--pid-file', default=os.path.join(lzprod_root, 'webserver-daemon.pid'),
                        help="The pid file used by the daemon [default: %(default)s]")
    parser.add_argument('--debug-mode', action='store_true', default=False,
                        help="Run the daemon in a debug interactive monitoring mode. "
                             "(debugging only)")
    args = parser.parse_args()

    # Dynamic imports to module level
    ###########################################################################
    # Add the python src path to the sys.path for future imports
    sys.path.append(lzprod_root)
#    LZProductionServer = importlib.import_module('lzproduction.webapp.WebServer').LZProductionServer
    LZProductionServer = pkg_resources.load_entry_point('lzproduction', 'webapp.daemon', 'lz')

    # Logging setup
    ###########################################################################
    # check and create logging dir
    if not os.path.isdir(args.log_dir):
        if os.path.exists(args.log_dir):
            raise Exception("%s path already exists and is not a directory so cant make log dir"
                            % args.log_dir)
        os.mkdir(args.log_dir)

    # setup the handler
    fhandler = TimedRotatingFileHandler(os.path.join(args.log_dir, 'LZWebServer.log'),
                                        when='midnight', backupCount=5)
    if args.debug_mode:
        fhandler = logging.StreamHandler()
    fhandler.setFormatter(logging.Formatter("[%(asctime)s] %(name)15s : %(levelname)8s : %(message)s"))
    # setup the root logger
    root_logger = logging.getLogger()
    root_logger.addHandler(fhandler)
    root_logger.setLevel(args.logginglevel)

    # NOTE: all current loggers can be found with:
    #     logging.Logger.manager.loggerDict.keys()
    # Force cherrypy to log to our handler
    for logger_handle in ['cherrypy', 'cherrypy.access', 'cherrypy.error']:
        cherrypy_logger = logging.getLogger(logger_handle)
        cherrypy_logger.setLevel(logging.NOTSET)
        cherrypy_logger.handlers = []

    # setup the main app logger
    logger = logging.getLogger("LZWebServer")
    logger.debug("Script called with args: %s", args)

    # Daemon setup
    ###########################################################################
    daemon = LZProductionServer(production_root=lzprod_root,
                                dburl=args.dburl,
                                socket_host=args.socket_host,
                                socket_port=args.socket_port,
                                thread_pool=args.thread_pool,
                                git_repo=args.git_repo,
                                git_dir=args.git_dir,
                                app=app_name,
                                pid=args.pid_file,
                                logger=logger,
                                keep_fds=[fhandler.stream.fileno()],
                                foreground=args.debug_mode)
    daemon.start()
