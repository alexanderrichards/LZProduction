#!/usr/bin/env python
import os
import time
import sys
import argparse
import atexit
from datetime import datetime
import importlib
import requests
import ganga
from contextlib import contextmanager
from daemonize import Daemonize
import logging
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler

MINS = 60

@contextmanager
def auto_cleanup_request():
    req = ganga.LZRequest()
    try:
        yield req
    except:
        req.pause()  # must pause task before removing if running
        req.remove(remove_jobs=True)
        raise

def getGangaRequest(requestdb_id):
    # note could use tasks.select here
    for t in ganga.tasks:
        if t.requestdb_id == requestdb_id:
            return t
    return None

@contextmanager
def subsession(session, req_id):
    try:
        with session.begin_nested():
            yield
    except:
        logger.exception("Problem with request id: %i, rolling back", req_id)

def exit_status(dburl):
    with sqlalchemy_utils.db_session(dburl) as session:
        session.query(Services)\
               .filter(Services.name == "gangad")\
               .update({'status': 'down',
                        'timestamp': datetime.utcnow()})

def daemon_main(dburl, delay, cert, verify=False):
    ganga.enableMonitoring()
    while True:
        with sqlalchemy_utils.db_session(dburl) as session:
            check_services(session, cert, verify)
            monitor_requests(session)
        time.sleep(delay * MINS)

def check_services(session, cert, verify):
    query = session.query(Services)

    # DIRAC
    query_dirac = query.filter(Services.name == "DIRAC")
    status = 'down'
    if requests.get("https://dirac.gridpp.ac.uk/DIRAC/", cert=cert, verify=verify).status_code == 200:
        status = 'up'
    if query_dirac.one_or_none() is None:
        session.add(Services(name='DIRAC', status=status, timestamp=datetime.now()))
    else:
        query_dirac.update({'status': status, 'timestamp': datetime.now()})

    # gangad
    query_gangad = query.filter(Services.name == "gangad")
    if query_gangad.one_or_none() is None:
        session.add(Services(name='gangad', status='up', timestamp=datetime.now()))
    else:
        query_gangad.update({'status': 'up', 'timestamp': datetime.now()})

def monitor_requests(session):
    monitored_requests = session.query(Requests)\
                                .filter(Requests.status != 'Completed')\
                                .filter(Requests.status != 'Requested')\
                                .all()

    approved_requests = ((r, getGangaRequest(r.id)) for r in monitored_requests
                         if r.status == "Approved")
    paused_requests = ((r, getGangaRequest(r.id)) for r in monitored_requests
                       if r.status == "Pause")
    running_requests = ((r, getGangaRequest(r.id)) for r in monitored_requests
                        if r.status == "Running")

    for request, ganga_request in approved_requests:
        with subsession(session, request.id):
            if ganga_request is not None:
                # why is it still approved?
                session.query(Requests)\
                       .filter(Requests.id == request.id)\
                       .update({'status': ganga_request.status.capitalize()})
                continue

            with auto_cleanup_request() as t:
                t.requestdb_id = int(request.id)
                tr = ganga.CoreTransform(backend=ganga.LZDirac())
                tr.application = ganga.LZApp()
                tr.application.luxsim_version=request.app_version
                tr.application.reduction_version = request.reduction_version
                tr.application.tag = request.tag
                macros, njobs, nevents, seed = zip(*(i.split() for i in request.selected_macros.splitlines()))
                tr.unit_splitter = ganga.GenericSplitter()
                tr.unit_splitter.multi_attrs={'application.macro': macros,
                                              'application.njobs': [int(i) for i in njobs],
                                              'application.nevents': [int(i) for i in nevents],
                                              'application.seed': [int(i) for i in seed]}
                t.appendTransform(tr)
                t.float = 100
                t.run()
                session.query(Requests)\
                       .filter(Requests.id == request.id)\
                       .update({'status': t.status.capitalize()})

    for request, ganga_request in paused_requests:
        if ganga_request is None:
            logger.error("Request %i has gone missing!", request.id)
            continue

        if ganga_request.status != "pause":
            with subsession(session, request.id):
                session.query(Requests)\
                       .filter(Requests.id == request.id)\
                       .update({'status': ganga_request.status.capitalize()})


    for request, ganga_request in running_requests:
        if ganga_request is None:
            logger.error("Request %i has gone missing!", request.id)
            continue

        if ganga_request.status == 'running':
            continue

        if ganga_request.status not in ['pause', 'completed']:
            logger.error("Ganga reports 'Running' request %i in state: %s",
                         request.id, ganga_request.status)
            continue


        with subsession(session, request.id):
            if ganga_request.status == "completed":
                # job completed, time to feed stuff back
                pass

            session.query(Requests)\
                   .filter(Requests.id == request.id)\
                   .update({'status': ganga_request.status.capitalize()})



if __name__ == '__main__':
    lzprod_root = os.path.dirname(os.path.dirname(os.path.expanduser(os.path.expandvars(os.path.realpath(os.path.abspath(__file__))))))

    parser = argparse.ArgumentParser(description='Run the ganga job submission daemon.')
    parser.add_argument('-f', '--frequency', default=5, type=int,
                        help="The frequency that the daemon does it's main functionality (in mins) [default: %(default)s]")
    parser.add_argument('-p', '--pid-file', default=os.path.join(lzprod_root, 'ganga-daemon.pid'),
                        help="The pid file used by the daemon [default: %(default)s]")
    parser.add_argument('-l', '--log-dir', default=os.path.join(lzprod_root, 'log'),
                        help="Path to the log directory. Will be created if doesn't exist [default: %(default)s]")
    parser.add_argument('-c', '--cert', default=os.path.expanduser('~/.globus/usercert.pem'),
                        help='Path to cert .pem file [default: %(default)s]')
    parser.add_argument('-k', '--key', default=os.path.expanduser('~/.globus/userkey.pem'),
                        help='Path to key .pem file. Note must be an unencrypted key. [default: %(default)s]')
    parser.add_argument('-v', '--verbose', action='count',
                        help="Increate the logged verbosite, can be used twice")
    parser.add_argument('-d', '--dburl', default="sqlite:///" + os.path.join(lzprod_root, 'requests.db'),
                        help="URL for the requests DB. Note can use the prefix 'mysql+pymysql://' if you have a problem with MySQLdb.py [default: %(default)s]")
    parser.add_argument('-y', '--verify', default=False, action="store_true",
                        help="Verify the DIRAC server.")
    parser.add_argument('-t', '--trusted-cas', default='',
                        help="Path to the trusted CA_BUNDLE file or directory containing the certificates of trusted CAs. Note if set to a directory, the directory must have been processed using the c_rehash utility supplied with OpenSSL. If using a CA_BUNDLE file can also consider using the REQUESTS_CA_BUNDLE environment variable instead (this may cause pip to fail to validate against PyPI). This option implies and superseeds -y")
    parser.add_argument('--debug-mode', action='store_true', default=False,
                        help="Run the daemon in a debug interactive monitoring mode. (debugging only)")
    args = parser.parse_args()
    if args.trusted_cas:
        args.verify = args.trusted_cas

    if not os.path.isdir(args.log_dir):
        if os.path.exists(args.log_dir):
            raise Exception("%s path already exists and is not a directory so cant make log dir" % args.log_dir)
        os.mkdir(args.log_dir)

    fhandler = TimedRotatingFileHandler(os.path.join(args.log_dir, 'ganga-daemon.log'),
                                        when='midnight', backupCount=5)
    if args.debug_mode:
        fhandler = logging.StreamHandler()
    fhandler.setFormatter(logging.Formatter("[%(asctime)s] %(name)15s : %(levelname)8s : %(message)s"))
    root_logger = logging.getLogger()
    ganga_handlers = [h for h in root_logger.handlers if isinstance(h, RotatingFileHandler)]
    root_logger.handlers = [fhandler]  # importing ganga adds root handlers so use this to replace them rather than logger.addHandler
    root_logger.setLevel({None: logging.WARNING,
                          1: logging.INFO,
                          2: logging.DEBUG}.get(args.verbose, logging.DEBUG))

    # use the level from the root rather than the gangarc
    ganga_logger = logging.getLogger("Ganga")
    ganga_logger.setLevel(logging.NOTSET)
    ganga_logger.handlers = ganga_handlers

    logger = logging.getLogger(os.path.splitext(os.path.basename(__file__))[0])
    logger.debug("Script called with args: %s", args)

    # Add the python src path to the sys.path for future imports
    sys.path = [os.path.join(lzprod_root, 'src', 'python')] + sys.path

    tables = importlib.import_module('tables')
    Requests = tables.Requests
    Services = tables.Services
    sqlalchemy_utils = importlib.import_module('sqlalchemy_utils')


    atexit.register(exit_status, args.dburl)
    sqlalchemy_utils.create_db(args.dburl)
    daemon = Daemonize(app=os.path.splitext(os.path.basename(__file__))[0],
                       pid=args.pid_file,
                       action=daemon_main(args.dburl, args.frequency, cert=(args.cert, args.key), verify=args.verify),
                       keep_fds=[fhandler.stream.fileno()],
                       foreground=not args.debug_mode)
    daemon.start()
