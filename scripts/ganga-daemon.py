#!/usr/bin/env python
# pylint: disable=invalid-name
"""
DB monitoring daemon.

Daemon that monitors the DB and creates Ganga jobs from new requests. It
also runs the Ganga monitoring loop to keep Ganga jobs up to date.
"""
import os
import sys
import time
import argparse
import importlib
import logging
from logging.handlers import TimedRotatingFileHandler
from datetime import datetime

import requests
from daemonize import Daemonize
from git import Git

MINS = 60

class GangaDaemon(Daemonize):
    """Ganga Daemon."""

    def __init__(self, dburl, delay, cert, verify=False, **kwargs):
        """Initialisation."""
        super(GangaDaemon, self).__init__(action=self.main, **kwargs)
        self.session = None
        self.dburl = dburl
        self.delay = delay
        self.cert = cert
        self.verify = verify

    def exit(self):
        """Update the gangad status on exit."""
        with sqlalchemy_utils.continuing(self.session) as session:
            session.query(Services)\
                   .filter(Services.name == "gangad")\
                   .update({'status': 'down',
                            'timestamp': datetime.now()})
        super(GangaDaemon, self).exit()

    @staticmethod
    def reset_loggers():
        """Clear all non-root log handlers and set level to NOTSET."""
        for _, log in logging_utils.loggers_not_at_level(logging.NOTSET):
            log.setLevel(logging.NOTSET)
        for _, log in logging_utils.loggers_with_handlers():
            log.handlers = []
        logging.getLogger("sqlalchemy").setLevel(logging.WARNING)
        logging.getLogger("cherrypy").setLevel(logging.WARNING)  # Why is cherrypy present?
        logging.getLogger("git").setLevel(logging.WARNING)
        logging.getLogger("requests").setLevel(logging.WARNING)
        logging.getLogger("stomp.py").setLevel(logging.WARNING)

    def main(self):
        """Daemon main function."""
        # import ganga within the daemon process as problem with file
        # descriptors otherwise
#        ganga = importlib.import_module("ganga")
        GangaDaemon.reset_loggers()  # use only the root loggers handler.

        # Setup scoped_session within the daemon otherwise the file descriptor
        # will be closed
        self.session = sqlalchemy_utils.setup_session(self.dburl)
#        try:
#            sqlalchemy_utils.create_db(self.dburl)
#        except Exception:
#            logger.exception("Failed to connect to/create DB.")
#        else:
#            logger.debug("Connected to DB.")

#        try:
#            ganga.enableMonitoring()
#        except Exception:
#            logger.exception("Failed to enable the Ganga monitoring.")
#        else:
#            logger.debug("Ganga monitoring enabled.")

        try:
            while True:
                self.check_services()
                self.monitor_requests()
                time.sleep(self.delay * MINS)
        except Exception:
            logger.exception("Unhandled exception while running daemon.")

    def check_services(self):
        """
        Check the status of the services.

        This function checks the status of the DIRAC status as well as updating the
        timestamp for the current gangad service.
        """
        with sqlalchemy_utils.reraising(self.session) as session:
            query = session.query(Services)

            # DIRAC
            query_dirac = query.filter(Services.name == "DIRAC")
            status = 'down'
            if requests.get("https://dirac.gridpp.ac.uk/DIRAC/", cert=self.cert, verify=self.verify)\
                       .status_code == 200:
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

    def monitor_requests(self):
        """
        Monitor the DB requests.

        Check the status of ongoing DB requests and either update them or
        create new Ganga tasks for new requests.
        """
        with sqlalchemy_utils.nonexpiring(self.session) as session:
            monitored_requests = session.query(Requests)\
                                        .filter(Requests.status.in_(('Approved',
                                                                     'Submitted',
                                                                     'Running')))\
                                        .all()

        for request in monitored_requests:
            if request.status == "Approved":
                request.submit(self.session)
            request.update_status(self.session)


        """
        # Approved Requests
        # ####################################################################################
        for request in approved_requests:
            jobs = session.query(ParametricJobs)\
                          .filter(ParametricJobs.request_id == request.id)\
                          .all()
            with sqlalchemy_utils.db_subsession(session):
                for job in jobs:
                    with dirac_utils.dirac_server("http://localhost:8000/") as dirac:
                        job_ids = submit_job(request.id, blah, job.macro, job.seed, job.njobs)
                    job.dirac_jobs = dict(zip(job_ids, repeat({'status': "Submitted"}, len(job_ids))))
                    job.status = "Submitted"
                request.status = "Submitted"

## below will work but the above IF it works will be nicer
#        for request in approved_requests:
#            jobs = session.query(ParametricJobs)\
#                          .filter(ParametricJobs.request_id == request.id)\
#                          .all()
#            with sqlalchemy_utils.db_subsession(session):
#                dirac_jobs = {}
#                for job in jobs:
#                    with dirac_utils.dirac_server("http://localhost:8000/") as dirac:
#                        job_ids = submit_job(request.id, blah, job.macro, job.seed, job.njobs)
#                    dirac_jobs = dict(zip(job_ids, repeat("Submitted", len(job_ids))))
#                    
#                    session.query(ParametricJobs)\
#                           .filter(ParametricJobs.id == job.id)\
#                           .update({'status': "Submitted",
#                                    'dirac_jobs': dirac_jobs})
#                session.query(Requests).filter(Requests.id == request.id).update({'status': "Submitted"})

        # Submitted Requests
        # ####################################################################################
        for request in submitted_requests:
            with sqlalchemy_utils.db_subsession(session):
                jobs = session.query(ParametricJobs)\
                              .filter(ParametricJobs.request_id == request.id)\
                              .filter(ParametricJobs.status in ("Submitted", "Running"))\
                              .all()
                for job in jobs:
                    job.status = reduce(accumulate_status, (subjob['status'] for subjob in job.dirac_jobs.itervalues()))
                request.status = reduce(accumulate_status, (job.status for job in jobs))


        # Running Requests
        # ####################################################################################
        for request, ganga_request in running_requests:
            jobs = session.query(ParametricJobs)\
                          .filter(ParametricJobs.request_id == request.id)\
                          .all()
            with sqlalchemy_utils.db_subsession(session):
                for job in jobs:
                    for subjob, subjob_info in job.dirac_jobs.iteritems():
                        with dirac_utils.dirac_server("http://localhost:8000/") as dirac:
                            status = dirac.status(subjob)
                            subjob_info['status'] = status
                            if status == "Completed":
                                subjob_info['output_lfn'] = dirac.getJobOutputLFNs(subjob.backend.id)\
                                                                 .get('Value', [])
                    job.status = reduce()
                request.status = reduce()
"""

if __name__ == '__main__':
    app_name = os.path.splitext(os.path.basename(__file__))[0]
    lzprod_root = os.path.dirname(
        os.path.dirname(
            os.path.expanduser(
                os.path.expandvars(
                    os.path.realpath(
                        os.path.abspath(__file__))))))

    parser = argparse.ArgumentParser(description='Run the ganga job submission daemon.')
    parser.add_argument('-f', '--frequency', default=5, type=int,
                        help="The frequency that the daemon does it's main functionality (in mins) "
                             "[default: %(default)s]")
    parser.add_argument('-p', '--pid-file', default=os.path.join(lzprod_root, app_name + '.pid'),
                        help="The pid file used by the daemon [default: %(default)s]")
    parser.add_argument('-l', '--log-dir', default=os.path.join(lzprod_root, 'log'),
                        help="Path to the log directory. Will be created if doesn't exist "
                             "[default: %(default)s]")
    parser.add_argument('-c', '--cert', default=os.path.expanduser('~/.globus/usercert.pem'),
                        help='Path to cert .pem file [default: %(default)s]')
    parser.add_argument('-k', '--key', default=os.path.expanduser('~/.globus/userkey.pem'),
                        help='Path to key .pem file. Note must be an unencrypted key. '
                             '[default: %(default)s]')
    parser.add_argument('-v', '--verbose', action='count',
                        help="Increase the logged verbosite, can be used twice")
    parser.add_argument('-d', '--dburl',
                        default="sqlite:///" + os.path.join(lzprod_root, 'requests.db'),
                        help="URL for the requests DB. Note can use the prefix 'mysql+pymysql://' "
                             "if you have a problem with MySQLdb.py [default: %(default)s]")
    parser.add_argument('-y', '--verify', default=False, action="store_true",
                        help="Verify the DIRAC server.")
    parser.add_argument('-t', '--trusted-cas', default='',
                        help="Path to the trusted CA_BUNDLE file or directory containing the "
                             "certificates of trusted CAs. Note if set to a directory, the "
                             "directory must have been processed using the c_rehash utility "
                             "supplied with OpenSSL. If using a CA_BUNDLE file can also consider "
                             "using the REQUESTS_CA_BUNDLE environment variable instead (this may "
                             "cause pip to fail to validate against PyPI). This option implies and "
                             "superseeds -y")
    parser.add_argument('--debug-mode', action='store_true', default=False,
                        help="Run the daemon in a debug interactive monitoring mode. "
                             "(debugging only)")
    args = parser.parse_args()

    # Modify the verify arg based on trusted_cas path
    if args.trusted_cas:
        args.verify = args.trusted_cas

    # Dynamic imports to module level
    ###########################################################################
    # Add the python src path to the sys.path for future imports
    sys.path = [os.path.join(lzprod_root, 'src', 'python')] + sys.path

    # do the imports
    Requests = importlib.import_module('tables').Requests
    Services = importlib.import_module('tables').Services
    ParametricJobs = importlib.import_module('tables').ParametricJobs
    logging_utils = importlib.import_module('logging_utils')
    SelectedMacro = importlib.import_module('services.RequestsDB').SelectedMacro  # includes the cherrypy logger as imports cherrypy. We should move SelectedMacro elsewhere probably with the table!
    sqlalchemy_utils = importlib.import_module('sqlalchemy_utils')
    dirac_utils = importlib.import_module('dirac_utils')

    # Logging setup
    ###########################################################################
    # check and create logging dir
    if not os.path.isdir(args.log_dir):
        if os.path.exists(args.log_dir):
            raise Exception("%s path already exists and is not a directory so cant make log dir"
                            % args.log_dir)
        os.mkdir(args.log_dir)

    # setup the handler
    fhandler = TimedRotatingFileHandler(os.path.join(args.log_dir, 'ganga-daemon.log'),
                                        when='midnight', backupCount=5)
    if args.debug_mode:
        fhandler = logging.StreamHandler()
    fhandler.setFormatter(logging.Formatter("[%(asctime)s] %(name)15s : %(levelname)8s : %(message)s"))

    # setup the root logger
    root_logger = logging.getLogger()
    root_logger.handlers = [fhandler]
    root_logger.setLevel({None: logging.WARNING,
                          1: logging.INFO,
                          2: logging.DEBUG}.get(args.verbose, logging.DEBUG))

    # setup the main app logger
    logger = logging.getLogger(app_name)
    logger.debug("Script called with args: %s", args)

    # TDRAnalysis git repo setup
    git_dir = os.path.join(lzprod_root, 'git', 'TDRAnalysis')
    if not os.path.isdir(git_dir):
        Git().clone('git@lz-git.ua.edu:sim/TDRAnalysis.git', git_dir)

    # Daemon setup
    ###########################################################################
    daemon = GangaDaemon(dburl=args.dburl,
                         delay=args.frequency,
                         cert=(args.cert, args.key),
                         verify=args.verify,
                         app=app_name,
                         pid=args.pid_file,
                         logger=logger,
                         keep_fds=[fhandler.stream.fileno()],
                         foreground=args.debug_mode)
    daemon.start()
