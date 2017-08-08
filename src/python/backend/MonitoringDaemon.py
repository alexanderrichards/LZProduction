import logging
import time
from datetime import datetime

import requests
from daemonize import Daemonize

from utils import logging_utils, sqlalchemy_utils
from tables import Requests, Services
MINS = 60


class MonitoringDaemon(Daemonize):
    """Monitoring Daemon."""

    def __init__(self, dburl, delay, cert, verify=False, **kwargs):
        """Initialisation."""
        super(MonitoringDaemon, self).__init__(action=self.main, **kwargs)
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
        super(MonitoringDaemon, self).exit()

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
        MonitoringDaemon.reset_loggers()  # use only the root loggers handler.

        # Setup scoped_session within the daemon otherwise the file descriptor
        # will be closed
        self.session = sqlalchemy_utils.setup_session(self.dburl)
        try:
            while True:
                self.check_services()
                self.monitor_requests()
                time.sleep(self.delay * MINS)
        except Exception:
            self.logger.exception("Unhandled exception while running daemon.")

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
            if requests.get("https://dirac.gridpp.ac.uk/DIRAC/",
                            cert=self.cert, verify=self.verify)\
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
