"""Requests Table."""
import logging
from datetime import datetime
from sqlalchemy import Column, Integer, String, TIMESTAMP, ForeignKey
from sql.utils import session_scope
from utils.coroutine_utils import status_accumulator
from .SQLTableBase import SQLTableBase
from .ParametricJobs import ParametricJobs

logger = logging.getLogger(__name__)  # pylint: disable=invalid-name


class Requests(SQLTableBase):
    """Requests SQL Table."""

    __tablename__ = 'requests'
    id = Column(Integer, primary_key=True)  # pylint: disable=invalid-name
    requester_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    request_date = Column(String(250), nullable=False)
    source = Column(String(250), nullable=False)
    detector = Column(String(250), nullable=False)
    sim_lead = Column(String(250), nullable=False)
    status = Column(String(250), nullable=False)
    description = Column(String(250), nullable=False)
    timestamp = Column(TIMESTAMP, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    def submit(self, scoped_session):
        """Submit a request."""
        self.status = "Submitting"
        with session_scope(scoped_session) as session:
            jobs = session.query(ParametricJobs).filter(ParametricJobs.request_id == self.id).all()
            this = session.query(Requests).filter(Requests.id == self.id).first()
            if this is not None:
                this.status = self.status
                logger.info("Request %s moved to state %s", self.id, self.status)
            session.expunge_all()
        status_acc = status_accumulator(('Unknown', 'Deleted', 'Killed', 'Completed', 'Failed', 'Requested', 'Approved', 'Submitted', 'Submitting', 'Running'))

        try:
            logger.info("Submitting request %s", self.id)
            for i, job in enumerate(jobs):
                self.status = status_acc.send(job.submit(scoped_session))
        except:
            logger.exception("Exception while submitting request %s", self.id)
            logger.info("Resetting associated ParametricJobs")
            for j in jobs[:i]:
                j.reset()
        else:
            with session_scope(scoped_session, reraise=False) as session:
                this = session.query(Requests).filter(Requests.id == self.id).first()
                if this is not None:
                    this.status = self.status
                    logger.info("Request %s moved to state %s", self.id, self.status)

    def update_status(self, scoped_session):
        """Update request status."""
        status_acc = status_accumulator(('Unknown', 'Deleted', 'Killed', 'Completed', 'Failed', 'Requested', 'Approved', 'Submitted', 'Submitting', 'Running'))
        # with sqlalchemy_utils.db_session(self.dburl) as session:
        with session_scope(scoped_session) as session:
            jobs = session.query(ParametricJobs).filter(ParametricJobs.request_id == self.id).all()
            session.expunge_all()
        update = True
        init_status = self.status
        for job in jobs:
            try:
                # with sqlalchemy_utils.db_subsession(session):
                self.status = status_acc.send(job.update_status(scoped_session))
            except:
                logger.exception("Exception updating ParametricJob %s", job.id)
                update = False

        if update and self.status != init_status:
            with session_scope(scoped_session, reraise=False) as session:
                this = session.query(Requests).filter(Requests.id == self.id).first()
                if this is not None:
                    this.status = self.status
                    logger.info("Request %s moved to state %s", self.id, self.status)
