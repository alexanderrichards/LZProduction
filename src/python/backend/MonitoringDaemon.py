"""Monitoring Daemon."""
import logging
import time
from datetime import datetime

import requests
from daemonize import Daemonize

from utils import logging_utils
from sql.statuses import LOCALSTATUS, SERVICESTATUS
from sql.utils import db_session
from sql.tables import Requests, Services, create_all_tables
MINS = 60


class MonitoringDaemon(Daemonize):
    """Monitoring Daemon."""

    def __init__(self, dburl, delay, cert, verify=False, **kwargs):
        """Initialisation."""
        super(MonitoringDaemon, self).__init__(action=self.main, **kwargs)
        self.dburl = dburl
        self.delay = delay
        self.cert = cert
        self.verify = verify

    def exit(self):
        """Update the monitoringd status on exit."""
        with db_session(reraise=False) as session:
            session.query(Services)\
                   .filter(Services.name == "monitoringd")\
                   .update({'status': SERVICESTATUS.Down})
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

        # Setup tables within the daemon otherwise the file descriptor
        # will be closed
        create_all_tables(self.dburl)
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
        timestamp for the current monitoringd service.
        """
        with db_session() as session:
            query = session.query(Services)

            # DIRAC
            query_dirac = query.filter(Services.name == "DIRAC")
            status = SERVICESTATUS.Down
            if requests.get("https://dirac.gridpp.ac.uk/DIRAC/",
                            cert=self.cert, verify=self.verify)\
                       .status_code == 200:
                status = SERVICESTATUS.Up
            if query_dirac.one_or_none() is None:
                session.add(Services(name='DIRAC', status=status))
            else:
                query_dirac.update({'status': status})

            # monitoringd
            query_monitoringd = query.filter(Services.name == "monitoringd")
            if query_monitoringd.one_or_none() is None:
                session.add(Services(name='monitoringd', status=SERVICESTATUS.Up))
            else:
                query_monitoringd.update({'status': SERVICESTATUS.Up})

    def monitor_requests(self):
        """
        Monitor the DB requests.

        Check the status of ongoing DB requests and either update them or
        create new Ganga tasks for new requests.
        """
        with db_session() as session:
            monitored_requests = session.query(Requests)\
                                        .filter(Requests.status.in_((LOCALSTATUS.Approved,
                                                                     LOCALSTATUS.Submitted,
                                                                     LOCALSTATUS.Running)))\
                                        .all()
            session.expunge_all()

        for request in monitored_requests:
            if request.status == LOCALSTATUS.Approved:
                request.submit()
            request.update_status()
